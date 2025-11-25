"""Statista MCP integration tools for the agent."""

import asyncio
import json
import logging
import os
import time
from typing import Any, Dict, List, Optional

from fastmcp import Client
from fastmcp.client.transports import StreamableHttpTransport
from google.adk.tools.tool_context import ToolContext

# Configure logging
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

# Retry configuration
MAX_RETRIES = 2
RETRY_DELAY = 2  # seconds


# Global MCP client instance
_mcp_client: Optional[Client] = None


class StatisaAuthenticationError(Exception):
    """Raised when authentication with Statista API fails."""
    pass


class StatisaTimeoutError(Exception):
    """Raised when a request to Statista API times out."""
    pass


class StatisaAPIError(Exception):
    """Raised when Statista API returns an error."""
    pass


def _get_mcp_client() -> Client:
    """Get or create the Statista MCP client.

    Raises:
        StatisaAuthenticationError: If API key is missing or invalid
        StatisaAPIError: If client creation fails
    """
    global _mcp_client

    if _mcp_client is None:
        mcp_api_key = os.getenv("STATISTA_API_KEY")
        mcp_server_url = os.getenv("STATISTA_MCP_URL", "https://api.statista.ai/v1/mcp")

        logger.info(f"Initializing Statista MCP client")
        logger.debug(f"MCP Server URL: {mcp_server_url}")
        logger.debug(f"API Key present: {bool(mcp_api_key)}")
        logger.debug(f"API Key length: {len(mcp_api_key) if mcp_api_key else 0}")

        if not mcp_api_key:
            logger.error("STATISTA_API_KEY environment variable is not set")
            raise StatisaAuthenticationError(
                "Authentication failed: STATISTA_API_KEY environment variable is required. "
                "Please set your Statista API key in the .env file."
            )

        try:
            _mcp_client = Client(
                transport=StreamableHttpTransport(
                    mcp_server_url,
                    headers={"x-api-key": mcp_api_key},
                ),
            )
            logger.info("Statista MCP client created successfully")
        except Exception as e:
            logger.error(f"Failed to create MCP client: {type(e).__name__}: {e}")
            raise StatisaAPIError(f"Failed to create Statista MCP client: {e}") from e

    return _mcp_client


async def search_statistics(
    query: str,
    tool_context: ToolContext,
    max_results: int = 10
) -> str:
    """Search Statista's database for statistics matching the query.

    This tool searches across Statista's comprehensive statistical database
    including charts, reports, and forecasts across various industries and topics.

    Args:
        query: Natural language search query (e.g., "GDP of Japan", "electric vehicle sales")
        tool_context: The tool context for state management
        max_results: Maximum number of results to return (default: 10)

    Returns:
        A formatted string containing search results with statistic IDs, titles,
        descriptions, and metadata that can be used to retrieve detailed chart data.
    """
    logger.info(f"Searching Statista for: '{query}' (max_results={max_results})")

    try:
        client = _get_mcp_client()
        logger.debug(f"MCP client obtained, opening connection...")

        search_args = {"query": query}
        logger.info(f"[DEBUG] Exact MCP call arguments: {search_args}")
        logger.info(f"[DEBUG] Query string that will be sent: '{query}'")

        async with client:
            result = await client.call_tool(
                "search-statistics",
                arguments=search_args
            )
            logger.info(f"[SUCCESS] Search completed. Result type: {type(result)}")
            logger.info(f"[DEBUG] Full result object: {result}")
            logger.info(f"[DEBUG] Result.is_error: {result.is_error if hasattr(result, 'is_error') else 'N/A'}")

            # Log the raw result structure in detail
            if hasattr(result, 'content'):
                logger.info(f"[DEBUG] Result.content length: {len(result.content)}")
                for idx, content_item in enumerate(result.content):
                    logger.info(f"[DEBUG] Content[{idx}] type: {type(content_item)}")
                    if hasattr(content_item, 'text'):
                        text = content_item.text
                        logger.info(f"[DEBUG] Content[{idx}].text length: {len(text)}")
                        logger.info(f"[DEBUG] Content[{idx}].text (full): {text}")
                    if hasattr(content_item, 'type'):
                        logger.info(f"[DEBUG] Content[{idx}].type: {content_item.type}")
            else:
                logger.warning(f"[WARNING] Result has no 'content' attribute!")
                logger.info(f"[DEBUG] Result.__dict__: {result.__dict__ if hasattr(result, '__dict__') else 'N/A'}")

    except (StatisaAuthenticationError, StatisaTimeoutError, StatisaAPIError):
        # Re-raise our custom exceptions so they can be handled by A2A framework
        raise
    except Exception as e:
        error_msg = str(e)
        error_lower = error_msg.lower()
        logger.error(f"[ERROR] Search failed: {type(e).__name__}: {error_msg}")
        logger.error(f"[ERROR] Full exception details:", exc_info=True)

        # Log the URL that failed (if available in error message)
        if "https://" in error_msg:
            import re
            urls = re.findall(r'https://[^\s]+', error_msg)
            if urls:
                logger.error(f"[ERROR] Failed URL: {urls[0]}")

        # Detect authentication errors
        if any(keyword in error_lower for keyword in [
            'unauthorized', '401', 'authentication', 'invalid token',
            'api key', 'missing token', 'expired token', 'invalid api key',
            'forbidden', '403'
        ]):
            raise StatisaAuthenticationError(
                f"Authentication failed while searching Statista: {error_msg}. "
                "Please check your API key is valid and not expired."
            ) from e

        # Detect timeout errors
        if any(keyword in error_lower for keyword in [
            'timeout', 'timed out', 'connection timeout', 'read timeout'
        ]):
            raise StatisaTimeoutError(
                f"Request timed out while searching Statista: {error_msg}"
            ) from e

        # Wrap other errors as API errors
        raise StatisaAPIError(
            f"Error searching Statista: {type(e).__name__}: {error_msg}"
        ) from e


    # Store search results in context for reference
    if 'statista_searches' not in tool_context.state:
        tool_context.state['statista_searches'] = []

    tool_context.state['statista_searches'].append({
        'query': query,
        'results': result
    })

    # Format the results for the LLM
    try:
        logger.info(f"Starting result formatting. Result type: {type(result)}")
        logger.info(f"Result attributes: {dir(result)}")

        content_text = None

        # Handle CallToolResult object directly
        if hasattr(result, 'content'):
            logger.info(f"Result has content attribute")
            content_items = result.content
            logger.info(f"Content items type: {type(content_items)}, length: {len(content_items) if hasattr(content_items, '__len__') else 'N/A'}")

            if content_items and len(content_items) > 0:
                first_content = content_items[0]
                logger.info(f"First content item type: {type(first_content)}")

                # Check if it's a TextContent object with a text attribute
                if hasattr(first_content, 'text'):
                    content_text = first_content.text
                    logger.info(f"Found text attribute, length: {len(content_text)}")
                    logger.info(f"Raw text content: {content_text}")
                else:
                    content_text = str(first_content)
                    logger.info(f"No text attribute, using str(): {content_text}")
            else:
                logger.warning("Content items is empty or None")
                return f"No results found for query: {query}"
        # Legacy handling for list results
        elif isinstance(result, list) and len(result) > 0:
            logger.info(f"Result is a list with {len(result)} items (legacy path)")
            first_item = result[0]
            logger.info(f"First result item type: {type(first_item)}")

            content_text = first_item.content if hasattr(first_item, 'content') else str(first_item)
            logger.info(f"Content type: {type(content_text)}")
        else:
            logger.warning(f"Unexpected result format: {type(result)}")
            return f"No results found for query: {query}"

        # At this point, content_text should be set
        if content_text is None:
            logger.warning("content_text is None after extraction")
            return f"No results found for query: {query}"

        logger.info(f"Content text extracted successfully, length: {len(content_text) if isinstance(content_text, str) else 'N/A'}")

        # Try to parse as JSON if it's a string
        if isinstance(content_text, str):
            logger.info(f"Content is string, attempting JSON parse...")
            try:
                data = json.loads(content_text)
                logger.info(f"Successfully parsed JSON. Data type: {type(data)}")
                logger.info(f"JSON data keys: {data.keys() if isinstance(data, dict) else 'not a dict'}")

                # Handle both direct list and {"items": [...]} format
                items = data.get('items', data) if isinstance(data, dict) else data
                logger.info(f"Extracted items type: {type(items)}, is list: {isinstance(items, list)}")

                if isinstance(items, list):
                    logger.info(f"Found {len(items)} statistics in search results")
                    formatted_results = []
                    for i, item in enumerate(items[:max_results], 1):
                        # Statista uses 'identifier' not 'id' in search results
                        stat_id = item.get('identifier', item.get('id', 'N/A'))
                        title = item.get('title', 'N/A')
                        subject = item.get('subject', '')
                        is_premium = item.get('is_premium', False)
                        link = item.get('link', '')

                        premium_marker = " [PREMIUM]" if is_premium else ""

                        formatted_results.append(
                            f"{i}. ID: {stat_id}{premium_marker}\n"
                            f"   Title: {title}\n"
                            f"   Subject: {subject}\n"
                            f"   Link: {link}"
                        )

                    return (
                        f"Found {len(items)} statistics for '{query}':\n\n" +
                        "\n\n".join(formatted_results) +
                        f"\n\nTo get detailed chart data, use get_chart_data(statistic_id) with the ID number."
                    )
            except json.JSONDecodeError as e:
                logger.warning(f"Failed to parse search results as JSON: {e}")
                logger.debug(f"Raw content: {content_text[:500]}...")

        # If we couldn't parse as JSON, return raw content
        return str(content_text)

    except Exception as e:
        logger.error(f"Error formatting search results: {type(e).__name__}: {e}", exc_info=True)
        return f"Error formatting results: {str(e)}"


async def get_chart_data(
    statistic_id: int,
    tool_context: ToolContext
) -> str:
    """Retrieve detailed chart data for a specific statistic by ID.

    Use this tool after searching to get the complete data for a specific statistic,
    including numerical values, methodological details, source information, and context.

    Args:
        statistic_id: The unique identifier of the statistic (obtained from search results) - must be a number
        tool_context: The tool context for state management

    Returns:
        A formatted string containing the chart data, including data points, metadata,
        source information, and any relevant context or methodology notes.
    """
    logger.info(f"Retrieving chart data for statistic ID: {statistic_id}")

    try:
        client = _get_mcp_client()
        logger.debug(f"MCP client obtained, opening connection...")

        async with client:
            logger.debug(f"Calling get-chart-data-by-id tool with ID={statistic_id}...")
            result = await client.call_tool(
                "get-chart-data-by-id",
                arguments={"id": statistic_id}
            )
            logger.debug(f"Chart data retrieved. Result type: {type(result)}")

            # Log all content items (chart data returns 2 items)
            if hasattr(result, 'content'):
                logger.debug(f"Chart data has {len(result.content)} content items")
                for idx, item in enumerate(result.content):
                    if hasattr(item, 'text'):
                        logger.debug(f"Content[{idx}] text length: {len(item.text)}")
                        logger.debug(f"Content[{idx}] preview: {item.text[:200]}...")
    except (StatisaAuthenticationError, StatisaTimeoutError, StatisaAPIError):
        # Re-raise our custom exceptions so they can be handled by A2A framework
        raise
    except Exception as e:
        error_msg = str(e)
        error_lower = error_msg.lower()
        logger.error(f"Error getting chart data for ID {statistic_id}: {type(e).__name__}: {e}", exc_info=True)

        # Detect authentication errors
        if any(keyword in error_lower for keyword in [
            'unauthorized', '401', 'authentication', 'invalid token',
            'api key', 'missing token', 'expired token', 'invalid api key',
            'forbidden', '403'
        ]):
            raise StatisaAuthenticationError(
                f"Authentication failed while retrieving chart data: {error_msg}. "
                "Please check your API key is valid and not expired."
            ) from e

        # Detect timeout errors
        if any(keyword in error_lower for keyword in [
            'timeout', 'timed out', 'connection timeout', 'read timeout'
        ]):
            raise StatisaTimeoutError(
                f"Request timed out while retrieving chart data: {error_msg}"
            ) from e

        # Wrap other errors as API errors
        raise StatisaAPIError(
            f"Error retrieving chart data: {type(e).__name__}: {error_msg}"
        ) from e


    # Store retrieved chart data in context
    if 'statista_charts' not in tool_context.state:
        tool_context.state['statista_charts'] = []

    tool_context.state['statista_charts'].append({
        'statistic_id': statistic_id,
        'data': result
    })

    # Format the results - chart data returns multiple content items
    try:
        if hasattr(result, 'content') and len(result.content) > 0:
            # Content[0]: Chart data with graphType, description, data
            # Content[1]: HTML description
            # Content[2]: Sources
            # Content[3]: Statistic ID
            # Content[4]: URL
            # Content[5]: URL (duplicate)

            chart_info = None
            description_html = None
            sources = None
            url = None

            # Parse each content item
            for idx, item in enumerate(result.content):
                if not hasattr(item, 'text') or not item.text:
                    continue

                text = item.text
                logger.debug(f"Content[{idx}] length: {len(text)}, preview: {text[:100]}...")

                try:
                    parsed = json.loads(text)
                    if isinstance(parsed, dict) and 'graphType' in parsed:
                        chart_info = parsed
                        logger.debug(f"Found chart info in content[{idx}]")
                    elif isinstance(parsed, list) and idx == 2:
                        sources = parsed
                        logger.debug(f"Found sources in content[{idx}]")
                except json.JSONDecodeError:
                    # Not JSON, check if it's HTML description or URL
                    if text.startswith('<'):
                        description_html = text
                        logger.debug(f"Found HTML description in content[{idx}]")
                    elif text.startswith('http'):
                        if url is None:
                            url = text
                            logger.debug(f"Found URL in content[{idx}]")

            if not chart_info:
                logger.warning("Could not find chart info in response")
                return f"Chart data retrieved but could not parse structure for statistic ID: {statistic_id}"

            try:
                metadata = chart_info
                chart_data = metadata.get('data', {})

                # Extract key information from metadata
                title = metadata.get('title', metadata.get('name', 'N/A'))
                description = metadata.get('description', '')
                source = metadata.get('source', '')
                date = metadata.get('date', metadata.get('reference_date', ''))

                formatted = f"Statistic: {title}\n"
                formatted += f"ID: {statistic_id}\n"

                if date:
                    formatted += f"Date: {date}\n"

                if description:
                    formatted += f"\nDescription: {description}\n"

                # Format chart data - the data is in a dict with column names as keys
                if chart_data:
                    formatted += f"\nData Points:\n"
                    if isinstance(chart_data, dict):
                        # Statista returns data like {"Column1": [{"data": value, "name": label}, ...]}
                        for column_name, points in chart_data.items():
                            if isinstance(points, list):
                                for point in points:
                                    if isinstance(point, dict):
                                        name = point.get('name', '')
                                        value = point.get('data', point.get('value', ''))
                                        formatted += f"  - {name}: {value}\n"
                                    else:
                                        formatted += f"  - {point}\n"
                    elif isinstance(chart_data, list):
                        for point in chart_data:
                            if isinstance(point, dict):
                                label = point.get('label', point.get('name', point.get('category', '')))
                                value = point.get('value', point.get('data', point.get('y', '')))
                                formatted += f"  - {label}: {value}\n"
                            else:
                                formatted += f"  - {point}\n"

                # Add sources if available
                if sources and isinstance(sources, list):
                    formatted += f"\nSources:\n"
                    for source_obj in sources:
                        if isinstance(source_obj, dict):
                            title = source_obj.get('title', '')
                            subtitle = source_obj.get('subtitle', '')
                            if subtitle:
                                formatted += f"  - {subtitle}: {title}\n"
                            else:
                                formatted += f"  - {title}\n"

                # Add URL if available
                if url:
                    formatted += f"\nLink: {url}\n"

                return formatted

            except Exception as e:
                logger.warning(f"Failed to format chart data: {e}", exc_info=True)
                # Return raw data as fallback
                return f"Chart data for {statistic_id}:\n{json.dumps(chart_info, indent=2)}"

        # Fallback for unexpected format
        elif hasattr(result, 'content') and len(result.content) > 0:
            content_text = result.content[0].text if hasattr(result.content[0], 'text') else str(result.content[0])
            return f"Chart data:\n{content_text}"

    except Exception as e:
        logger.error(f"Error formatting chart data: {type(e).__name__}: {e}", exc_info=True)
        return f"Error formatting chart data: {str(e)}"

    return f"No data found for statistic ID: {statistic_id}"


async def get_available_tools(tool_context: ToolContext) -> str:
    """List all available Statista MCP tools and their capabilities.

    Args:
        tool_context: The tool context

    Returns:
        A formatted string describing all available Statista tools.
    """
    logger.info("Listing available Statista MCP tools")

    try:
        client = _get_mcp_client()
        logger.debug("MCP client obtained, opening connection...")

        async with client:
            logger.debug("Calling list_tools()...")
            tools = await client.list_tools()
            logger.debug(f"Retrieved {len(tools)} tools")

        formatted = "Available Statista Tools:\n\n"
        for tool in tools:
            name = tool.name if hasattr(tool, 'name') else str(tool)
            description = tool.description if hasattr(tool, 'description') else ''
            formatted += f"- {name}: {description}\n"
            logger.debug(f"Tool: {name}")

        logger.info(f"Successfully listed {len(tools)} tools")
        return formatted
    except (StatisaAuthenticationError, StatisaTimeoutError, StatisaAPIError):
        # Re-raise our custom exceptions so they can be handled by A2A framework
        raise
    except Exception as e:
        error_msg = str(e)
        error_lower = error_msg.lower()
        logger.error(f"Error listing tools: {type(e).__name__}: {e}", exc_info=True)

        # Detect authentication errors
        if any(keyword in error_lower for keyword in [
            'unauthorized', '401', 'authentication', 'invalid token',
            'api key', 'missing token', 'expired token', 'invalid api key',
            'forbidden', '403'
        ]):
            raise StatisaAuthenticationError(
                f"Authentication failed while listing tools: {error_msg}. "
                "Please check your API key is valid and not expired."
            ) from e

        # Detect timeout errors
        if any(keyword in error_lower for keyword in [
            'timeout', 'timed out', 'connection timeout', 'read timeout'
        ]):
            raise StatisaTimeoutError(
                f"Request timed out while listing tools: {error_msg}"
            ) from e

        # Wrap other errors as API errors
        raise StatisaAPIError(
            f"Error listing tools: {type(e).__name__}: {error_msg}"
        ) from e
