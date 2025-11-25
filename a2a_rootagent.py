import os
import logging
from dotenv import load_dotenv
from google.adk.a2a.utils.agent_to_a2a import to_a2a
from logging_config import setup_logging
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse
import traceback

# Load environment variables from .env file
load_dotenv()

# Setup logging
setup_logging(level=logging.INFO)
logger = logging.getLogger(__name__)
logger.info("Starting Statista A2A Agent")


class A2AErrorHandlerMiddleware(BaseHTTPMiddleware):
    """Middleware to handle errors and convert them to A2A-compliant JSON-RPC error responses.

    This middleware catches exceptions that occur during request processing and
    converts them into proper A2A/JSON-RPC error responses according to the specification.
    """

    # Error code mappings for common error scenarios
    AUTHENTICATION_ERROR_CODE = -32401  # Similar to HTTP 401
    MODEL_UNAVAILABLE_CODE = -32503  # Similar to HTTP 503 Service Unavailable
    EXTERNAL_SERVICE_ERROR_CODE = -32502  # Similar to HTTP 502 Bad Gateway
    INTERNAL_ERROR_CODE = -32603  # JSON-RPC Internal Error

    async def dispatch(self, request: Request, call_next):
        """Process the request and handle any errors."""
        try:
            response = await call_next(request)
            return response
        except Exception as exc:
            logger.error(f"Error during request processing: {type(exc).__name__}: {exc}")
            logger.error(traceback.format_exc())

            # Import here to avoid circular imports
            from statista_agent.statista_tools import (
                StatisaAuthenticationError,
                StatisaTimeoutError,
                StatisaAPIError,
            )

            # Determine error type and create appropriate JSON-RPC error
            error_response = self._create_error_response(exc, StatisaAuthenticationError, StatisaTimeoutError, StatisaAPIError)

            return JSONResponse(
                status_code=200,  # JSON-RPC always returns 200, errors are in the response body
                content=error_response
            )

    def _create_error_response(self, exc: Exception, AuthError, TimeoutError, APIError) -> dict:
        """Create a JSON-RPC error response based on the exception type."""
        error_msg = str(exc)
        error_lower = error_msg.lower()

        # Check for Statista-specific errors
        if isinstance(exc, AuthError):
            return {
                "jsonrpc": "2.0",
                "error": {
                    "code": self.AUTHENTICATION_ERROR_CODE,
                    "message": "Authentication failed",
                    "data": {
                        "error_type": "authentication_error",
                        "details": error_msg,
                        "auth_scheme": "API-Key",
                        "hint": "Please check that your STATISTA_API_KEY is valid and not expired."
                    }
                },
                "id": None
            }
        elif isinstance(exc, TimeoutError):
            return {
                "jsonrpc": "2.0",
                "error": {
                    "code": self.EXTERNAL_SERVICE_ERROR_CODE,
                    "message": "Request timeout",
                    "data": {
                        "error_type": "timeout_error",
                        "details": error_msg,
                        "hint": "The request timed out. Please try again."
                    }
                },
                "id": None
            }
        elif isinstance(exc, APIError):
            return {
                "jsonrpc": "2.0",
                "error": {
                    "code": self.EXTERNAL_SERVICE_ERROR_CODE,
                    "message": "External service error",
                    "data": {
                        "error_type": "api_error",
                        "details": error_msg,
                        "service": "Statista API"
                    }
                },
                "id": None
            }

        # Check for Vertex AI / Gemini model errors
        if any(keyword in error_lower for keyword in [
            'vertex', 'gemini', 'model', 'quota', 'service unavailable',
            'permission denied', 'api key not valid', 'resource exhausted'
        ]):
            return {
                "jsonrpc": "2.0",
                "error": {
                    "code": self.MODEL_UNAVAILABLE_CODE,
                    "message": "AI model unavailable",
                    "data": {
                        "error_type": "model_error",
                        "details": error_msg,
                        "service": "Vertex AI / Gemini",
                        "hint": "The AI model is not reachable. Check your Vertex AI credentials and quotas."
                    }
                },
                "id": None
            }

        # Check for authentication/authorization errors (Vertex AI)
        if any(keyword in error_lower for keyword in [
            'unauthorized', '401', '403', 'authentication', 'permission denied',
            'credentials', 'unauthenticated'
        ]):
            return {
                "jsonrpc": "2.0",
                "error": {
                    "code": self.AUTHENTICATION_ERROR_CODE,
                    "message": "Authentication failed",
                    "data": {
                        "error_type": "authentication_error",
                        "details": error_msg,
                        "hint": "Check your authentication credentials (API keys, service account, etc.)"
                    }
                },
                "id": None
            }

        # Generic internal error
        return {
            "jsonrpc": "2.0",
            "error": {
                "code": self.INTERNAL_ERROR_CODE,
                "message": "Internal error",
                "data": {
                    "error_type": type(exc).__name__,
                    "details": error_msg
                }
            },
            "id": None
        }


# Import agent after logging is configured
from statista_agent.agent import root_agent

# Convert the agent to an A2A application and expose it on port 8001
# Specify host, protocol, and agent card for proper A2A configuration
a2a_app = to_a2a(
    root_agent,
    host="0.0.0.0",
    port=8001,
    protocol="http",
    agent_card="agent_card.json"
)

# Add error handling middleware to the Starlette app
# This must be added after the app is created
a2a_app.add_middleware(A2AErrorHandlerMiddleware)

logger.info("A2A error handling middleware installed")
logger.info("The agent will now return A2A-compliant error responses for:")
logger.info("  - Statista API authentication errors")
logger.info("  - Statista API timeouts and failures")
logger.info("  - Vertex AI / Gemini model unavailability")
logger.info("  - General authentication and service errors")
