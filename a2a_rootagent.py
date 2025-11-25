import os
import logging
from dotenv import load_dotenv
from google.adk.a2a.utils.agent_to_a2a import to_a2a
from logging_config import setup_logging
from fastapi import Request, HTTPException, status
from fastapi.responses import JSONResponse

# Load environment variables from .env file
load_dotenv()

# Setup logging
setup_logging(level=logging.INFO)
logger = logging.getLogger(__name__)
logger.info("Starting Statista A2A Agent")

# Import agent after logging is configured
from statista_agent.agent import root_agent

# Get the bearer token from environment
A2A_BEARER_TOKEN = os.getenv("A2A_BEARER_TOKEN")

if not A2A_BEARER_TOKEN:
    logger.error("A2A_BEARER_TOKEN not set. All requests will be rejected with 401 Unauthorized.")
    logger.error("Please set A2A_BEARER_TOKEN in your .env file to enable authentication.")
else:
    logger.info("Bearer token authentication is enabled")

# Convert the agent to an A2A application and expose it on port 8001
# Specify host, protocol, and agent card for proper A2A configuration
a2a_app = to_a2a(
    root_agent,
    host="0.0.0.0",
    port=8001,
    protocol="http",
    agent_card="agent_card.json"
)

# Add authentication middleware
@a2a_app.middleware("http")
async def authenticate_bearer_token(request: Request, call_next):
    """
    Middleware to authenticate requests using bearer token as per A2A protocol.

    According to A2A specification:
    - All A2A implementations must support authentication
    - Clients must authenticate using schemes declared in AgentCard
    - Servers must reject requests with invalid or missing credentials
    """
    # Skip authentication for public agent card endpoint
    if request.url.path == "/.well-known/agent.json":
        return await call_next(request)

    # Extract Authorization header
    auth_header = request.headers.get("Authorization")

    # If no token is configured, reject all requests (authentication is mandatory)
    if not A2A_BEARER_TOKEN:
        logger.error(f"A2A_BEARER_TOKEN not configured but authentication is required for {request.url.path}")
        return JSONResponse(
            status_code=status.HTTP_401_UNAUTHORIZED,
            content={
                "error": "unauthorized",
                "message": "Server authentication not configured",
                "wwwAuthenticate": "Bearer"
            },
            headers={"WWW-Authenticate": "Bearer"}
        )

    if not auth_header:
        logger.warning(f"Missing Authorization header for {request.url.path}")
        return JSONResponse(
            status_code=status.HTTP_401_UNAUTHORIZED,
            content={
                "error": "unauthorized",
                "message": "Authorization header is required",
                "wwwAuthenticate": "Bearer"
            },
            headers={"WWW-Authenticate": "Bearer"}
        )

    # Validate bearer token format
    parts = auth_header.split()
    if len(parts) != 2 or parts[0].lower() != "bearer":
        logger.warning(f"Invalid Authorization header format for {request.url.path}")
        return JSONResponse(
            status_code=status.HTTP_401_UNAUTHORIZED,
            content={
                "error": "unauthorized",
                "message": "Invalid Authorization header format. Expected: Bearer <token>",
                "wwwAuthenticate": "Bearer"
            },
            headers={"WWW-Authenticate": "Bearer"}
        )

    token = parts[1]

    # Validate the token
    if token != A2A_BEARER_TOKEN:
        logger.warning(f"Invalid bearer token provided for {request.url.path}")
        return JSONResponse(
            status_code=status.HTTP_401_UNAUTHORIZED,
            content={
                "error": "unauthorized",
                "message": "Invalid bearer token",
                "wwwAuthenticate": "Bearer"
            },
            headers={"WWW-Authenticate": "Bearer"}
        )

    logger.debug(f"Authentication successful for {request.url.path}")
    return await call_next(request)

# Start the server
if __name__ == "__main__":
    import uvicorn
    logger.info("Starting A2A server on port 8001")
    uvicorn.run(a2a_app, host="0.0.0.0", port=8001)
