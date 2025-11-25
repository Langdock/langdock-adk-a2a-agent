"""Test Statista MCP using the exact example from their documentation."""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import asyncio
import json
import os
from dotenv import load_dotenv
from fastmcp import Client
from fastmcp.client.transports import StreamableHttpTransport

load_dotenv()

# Get configuration
mcp_api_key = os.getenv("STATISTA_API_KEY")
mcp_server_url = os.getenv("STATISTA_MCP_URL", "https://api.statista.ai/v1/mcp")

print(f"Testing with Statista MCP server: {mcp_server_url}")
print(f"API key present: {bool(mcp_api_key)}\n")

mcp_client = Client(
    transport=StreamableHttpTransport(
        mcp_server_url,
        headers={"x-api-key": mcp_api_key},
    ),
)

async def main():
    print("=" * 80)
    print("Testing Statista MCP Integration - Following Official Example")
    print("=" * 80)

    async with mcp_client as client:
        # Step 1: List available tools
        print("\n1️⃣  Listing available tools...")
        tools = await client.list_tools()
        print(f"✅ Found {len(tools)} tools:")
        for tool in tools:
            print(f"   - {tool.name}")

        # Step 2: Call search-statistics with a natural language query
        print("\n2️⃣  Searching for 'What's the GDP of Japan?'...")
        statistics = await client.call_tool(
            "search-statistics",
            {"query": "What's the GDP of Japan?"}  # Use "query" per actual schema
        )

        print(f"✅ Search completed")
        print(f"   Response type: {type(statistics)}")
        print(f"   Content items: {len(statistics.content)}")

        # Parse the response
        search_results = json.loads(statistics.content[0].text)
        print(f"   Number of results: {len(search_results.get('items', []))}")

        # Show first result
        if search_results.get('items'):
            first_result = search_results['items'][0]
            print(f"\n   First result:")
            print(f"   - ID: {first_result.get('identifier')}")
            print(f"   - Title: {first_result.get('title', 'N/A')[:80]}...")
            print(f"   - Subject: {first_result.get('subject', 'N/A')}")

        # Step 3: Grab the first statistic id
        print("\n3️⃣  Extracting first statistic ID...")
        grab_statistic_id = json.loads(statistics.content[0].text)["items"][0]["identifier"]
        print(f"✅ Statistic ID: {grab_statistic_id}")

        # Step 4: Fetch chart data for a specific statistic id
        print(f"\n4️⃣  Fetching chart data for statistic {grab_statistic_id}...")
        statistic_chart_data = await client.call_tool(
            "get-chart-data-by-id",
            {"id": int(grab_statistic_id)}  # Use "id" per actual schema
        )

        print(f"✅ Chart data retrieved")
        print(f"   Response type: {type(statistic_chart_data)}")
        print(f"   Content items: {len(statistic_chart_data.content)}")

        # Step 5: Inspect all content items
        print("\n5️⃣  Inspecting all content items...")
        for idx, item in enumerate(statistic_chart_data.content):
            print(f"\n   Content[{idx}]:")
            print(f"   - Type: {type(item)}")
            if hasattr(item, 'type'):
                print(f"   - item.type: {item.type}")
            if hasattr(item, 'text'):
                text = item.text
                print(f"   - Text length: {len(text)}")
                print(f"   - Text preview: {text[:200] if text else 'EMPTY'}...")
                # Try to parse as JSON
                if text:
                    try:
                        parsed = json.loads(text)
                        print(f"   - ✅ Valid JSON, type: {type(parsed)}")
                        if isinstance(parsed, dict):
                            print(f"   - JSON keys: {list(parsed.keys())}")
                    except:
                        print(f"   - ❌ Not valid JSON")

        # Parse based on inspection
        print("\n6️⃣  Parsing chart data response...")
        statistic_metadata = json.loads(statistic_chart_data.content[0].text)
        chart_data = None

        # Find the chart data (first non-empty text content after metadata)
        for idx in range(1, len(statistic_chart_data.content)):
            if hasattr(statistic_chart_data.content[idx], 'text') and statistic_chart_data.content[idx].text:
                try:
                    chart_data = json.loads(statistic_chart_data.content[idx].text)
                    print(f"   Found chart data in content[{idx}]")
                    break
                except:
                    continue

        print(f"✅ Metadata parsed:")
        print(f"   Keys: {list(statistic_metadata.keys())}")

        print(f"\n✅ Chart data parsed:")
        if isinstance(chart_data, list):
            print(f"   Type: list with {len(chart_data)} items")
            if chart_data:
                print(f"   First item keys: {list(chart_data[0].keys()) if isinstance(chart_data[0], dict) else 'Not a dict'}")
        elif isinstance(chart_data, dict):
            print(f"   Type: dict with keys: {list(chart_data.keys())}")

        # Display formatted results
        print("\n" + "=" * 80)
        print("COMPLETE RESULTS")
        print("=" * 80)

        print(f"\n📊 Statistic Metadata:")
        print(f"   Title: {statistic_metadata.get('title', 'N/A')}")
        print(f"   ID: {statistic_metadata.get('identifier', grab_statistic_id)}")
        if 'source' in statistic_metadata:
            print(f"   Source: {statistic_metadata['source']}")
        if 'date' in statistic_metadata:
            print(f"   Date: {statistic_metadata['date']}")

        print(f"\n📈 Chart Data:")
        if isinstance(chart_data, list) and len(chart_data) > 0:
            print(f"   Showing first 5 data points:")
            for i, point in enumerate(chart_data[:5], 1):
                if isinstance(point, dict):
                    label = point.get('label', point.get('name', point.get('x', 'N/A')))
                    value = point.get('value', point.get('y', 'N/A'))
                    print(f"   {i}. {label}: {value}")
                else:
                    print(f"   {i}. {point}")

        print("\n" + "=" * 80)
        print("✅ ALL TESTS PASSED!")
        print("=" * 80)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except Exception as e:
        print(f"\n❌ Test failed with error:")
        print(f"   {type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()
