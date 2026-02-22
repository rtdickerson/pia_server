"""
Entry point: starts both the REST/GraphQL server (port 8000)
and the MCP server (port 8001) concurrently.
"""
from __future__ import annotations

import asyncio
import logging

import uvicorn

from pia_server.config import settings


def main() -> None:
    logging.basicConfig(
        level=getattr(logging, settings.log_level.upper(), logging.INFO),
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )

    from pia_server.api.app import create_app
    from pia_server.mcp_server.server import mcp

    rest_app = create_app()

    rest_config = uvicorn.Config(
        rest_app,
        host="0.0.0.0",
        port=settings.rest_port,
        log_level=settings.log_level.lower(),
    )
    mcp_config = uvicorn.Config(
        mcp.http_app(transport="sse"),
        host="0.0.0.0",
        port=settings.mcp_port,
        log_level=settings.log_level.lower(),
    )

    async def serve_both() -> None:
        await asyncio.gather(
            uvicorn.Server(rest_config).serve(),
            uvicorn.Server(mcp_config).serve(),
        )

    asyncio.run(serve_both())


if __name__ == "__main__":
    main()
