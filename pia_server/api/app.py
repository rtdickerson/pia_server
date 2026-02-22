"""FastAPI application factory with lifespan (DB init + collection loop)."""
from __future__ import annotations

import asyncio
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI

from pia_server.collectors.base import MetricsCollector
from pia_server.collectors.mock import MockCollector
from pia_server.config import settings
from pia_server.db.database import get_db_connection
from pia_server.db import queries, schema

logger = logging.getLogger(__name__)


async def collection_loop(collector: MetricsCollector, interval: float) -> None:
    """Continuously collect system + Spark metrics and persist them."""
    await collector.startup()
    try:
        while True:
            try:
                async with get_db_connection() as conn:
                    sys_r = await collector.collect_system()
                    await queries.insert_and_prune_system(conn, sys_r)
                    for sid in range(1, 6):
                        sp_r = await collector.collect_spark(sid)
                        await queries.insert_and_prune_spark(conn, sp_r)
                logger.debug("Collection cycle complete")
            except Exception:
                logger.exception("Error during collection cycle; retrying next interval")
            await asyncio.sleep(interval)
    except asyncio.CancelledError:
        await collector.shutdown()
        raise


def _build_collector() -> MetricsCollector:
    if settings.collector_type == "real":
        from pia_server.collectors.real import RealCollector
        return RealCollector()  # type: ignore[return-value]
    return MockCollector()


def create_app() -> FastAPI:
    collector = _build_collector()
    collection_task: asyncio.Task | None = None

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        nonlocal collection_task
        # Initialise database schema
        async with get_db_connection() as conn:
            await schema.init_db(conn)
        logger.info("Database initialised")

        # Start background collection
        collection_task = asyncio.create_task(
            collection_loop(collector, settings.collection_interval_seconds)
        )
        logger.info(
            "Collection loop started (interval=%.1fs, collector=%s)",
            settings.collection_interval_seconds,
            settings.collector_type,
        )
        yield

        # Shutdown
        if collection_task and not collection_task.done():
            collection_task.cancel()
            try:
                await collection_task
            except asyncio.CancelledError:
                pass
        logger.info("Collection loop stopped")

    app = FastAPI(
        title="PIA Metrics Server",
        description="System thermals and NVIDIA Spark GPU metrics via REST, GraphQL, and MCP",
        version="0.1.0",
        lifespan=lifespan,
    )

    # REST routes
    from pia_server.api.routes.system import router as system_router
    from pia_server.api.routes.spark import router as spark_router

    app.include_router(system_router)
    app.include_router(spark_router)

    # GraphQL (Strawberry)
    from pia_server.graphql.schema import graphql_app

    app.include_router(graphql_app, prefix="/graphql")

    @app.get("/health", tags=["meta"])
    async def health():
        return {"status": "ok"}

    return app
