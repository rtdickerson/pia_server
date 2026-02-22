"""Quick script to exercise all MCP tools against the running server."""
import asyncio
import json
import sys

# Force UTF-8 output on Windows
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

from fastmcp import Client


async def main():
    async with Client("http://localhost:8001/sse") as c:

        # --- list tools & resources ---
        tools = await c.list_tools()
        print("=== Tools ===")
        for t in tools:
            print(f"  {t.name}")

        resources = await c.list_resources()
        templates = await c.list_resource_templates()
        print(f"\n=== Resources ({len(resources)}) ===")
        for r in resources:
            print(f"  {r.uri}")
        print(f"\n=== Resource Templates ({len(templates)}) ===")
        for t in templates:
            print(f"  {t.uriTemplate}")

        # --- call every tool ---
        def text(r):
            """Extract JSON text from a CallToolResult (empty content = empty list)."""
            if not r.content:
                return []
            return json.loads(r.content[0].text)

        print("\n=== get_system_current ===")
        r = await c.call_tool("get_system_current", {})
        print(json.dumps(text(r), indent=2))

        print("\n=== get_system_history(limit=3) ===")
        r = await c.call_tool("get_system_history", {"limit": 3})
        print(json.dumps(text(r), indent=2))

        print("\n=== get_spark_current(server_id=2) ===")
        r = await c.call_tool("get_spark_current", {"server_id": 2})
        print(json.dumps(text(r), indent=2))

        print("\n=== get_spark_history(server_id=2, limit=3) ===")
        r = await c.call_tool("get_spark_history", {"server_id": 2, "limit": 3})
        print(json.dumps(text(r), indent=2))

        print("\n=== get_all_spark_current ===")
        r = await c.call_tool("get_all_spark_current", {})
        for s in text(r):
            print(f"  server {s['server_id']}: GPU {s['spark_gpu_temp_celsius']}C  "
                  f"throttle={s['spark_throttle_thermal']}  ttp={s['power_near_ttp']}")

        print("\n=== get_btu_summary ===")
        r = await c.call_tool("get_btu_summary", {})
        print(json.dumps(text(r), indent=2))

        print("\n=== get_thermal_alert_status ===")
        r = await c.call_tool("get_thermal_alert_status", {})
        alerts = text(r)
        print(f"  Active alerts: {len(alerts)}")
        for a in alerts:
            print(f"  {a}")

        # --- read resources ---
        def res_text(r):
            return json.loads(r[0].text)

        print("\n=== Resource: pia://config ===")
        r = await c.read_resource("pia://config")
        print(json.dumps(res_text(r), indent=2))

        print("\n=== Resource: pia://system/current ===")
        r = await c.read_resource("pia://system/current")
        data = res_text(r)
        print(f"  inlet={data['air_inlet_temp']}F  exhaust={data['air_exhaust_temp']}F  "
              f"BTU={data['btu_transfer']:.1f}")

        print("\n=== Resource Template: pia://spark/3/current ===")
        r = await c.read_resource("pia://spark/3/current")
        data = res_text(r)
        print(f"  server_id={data['server_id']}  GPU={data['spark_gpu_temp_celsius']}C  "
              f"clock={data['spark_sm_clock_mhz']}MHz")


asyncio.run(main())
