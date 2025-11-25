"""List all Statista MCP tools with their complete schemas."""

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

mcp_api_key = os.getenv("STATISTA_API_KEY")
mcp_server_url = os.getenv("STATISTA_MCP_URL", "https://api.statista.ai/v1/mcp")

mcp_client = Client(
    transport=StreamableHttpTransport(
        mcp_server_url,
        headers={"x-api-key": mcp_api_key},
    ),
)

async def main():
    async with mcp_client as client:
        tools = await client.list_tools()

        print("=" * 80)
        print("STATISTA MCP TOOL SCHEMAS")
        print("=" * 80)

        for tool in tools:
            print(f"\n📦 Tool: {tool.name}")
            print(f"Description: {tool.description[:200]}...")

            if hasattr(tool, 'inputSchema'):
                print(f"\nInput Schema:")
                schema = tool.inputSchema
                print(json.dumps(schema, indent=2))
            else:
                print("No input schema available")

            print("\n" + "-" * 80)

if __name__ == "__main__":
    asyncio.run(main())
