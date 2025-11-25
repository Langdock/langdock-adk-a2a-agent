import os
import logging
from dotenv import load_dotenv
from google.adk.a2a.utils.agent_to_a2a import to_a2a
from logging_config import setup_logging
from starlette.middleware import Middleware
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse
from starlette.requests import Request

# Load environment variables from .env file
load_dotenv()

# Setup logging
setup_logging(level=logging.INFO)
logger = logging.getLogger(__name__)
logger.info("Starting Statista A2A Agent")

# Import agent after logging is configured
from statista_agent.agent import root_agent


# Authentication middleware
class ApiKeyAuthMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        # Skip auth only for specific GET endpoints (health check and agent card)
        # The root path "/" should be protected for POST requests (which are RPC calls)
        if request.url.path in ["/health", "/.well-known/agent-card.json"]:
            logger.debug(f"Allowing unauthenticated access to {request.url.path}")
            return await call_next(request)

        # Allow GET requests to root for basic info, but protect POST (RPC calls)
        if request.url.path == "/" and request.method == "GET":
            logger.debug(f"Allowing unauthenticated GET request to {request.url.path}")
            return await call_next(request)

        # Get API key from environment
        expected_api_key = os.getenv("A2A_API_KEY")

        # If no API key is set, reject all requests
        if not expected_api_key:
            logger.error("A2A_API_KEY not set - rejecting request")
            return JSONResponse(
                status_code=500,
                content={"error": "Server authentication not configured"}
            )

        # Check X-API-Key header
        api_key = request.headers.get("X-API-Key")
        if not api_key:
            return JSONResponse(
                status_code=401,
                content={"error": "Missing X-API-Key header"}
            )

        # Validate API key
        if api_key != expected_api_key:
            logger.warning(f"Failed authentication attempt for {request.url.path}")
            return JSONResponse(
                status_code=403,
                content={"error": "Invalid API key"}
            )

        logger.debug(f"Authenticated request to {request.url.path}")
        return await call_next(request)


# Convert the agent to an A2A application and expose it on port 8001
# Specify host, protocol, and agent card for proper A2A configuration
a2a_app = to_a2a(
    root_agent,
    host="0.0.0.0",
    port=8001,
    protocol="http",
    agent_card="agent_card.json"
)

# Add authentication middleware - must be added BEFORE any routes are accessed
# The middleware will intercept all incoming requests
a2a_app.add_middleware(ApiKeyAuthMiddleware)

# Start the server
if __name__ == "__main__":
    import uvicorn
    logger.info("Starting A2A server on port 8001")
    uvicorn.run(a2a_app, host="0.0.0.0", port=8001)
