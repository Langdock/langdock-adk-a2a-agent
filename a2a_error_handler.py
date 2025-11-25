"""A2A error handler middleware for Statista agent.

This module provides error handling that converts Statista-specific exceptions
into A2A protocol-compliant JSON-RPC error responses.

According to the A2A specification (https://a2a-protocol.org/latest/specification/),
all error responses must convey:
1. Error Code: Machine-readable identifier
2. Error Message: Human-readable description
3. Error Details: Optional structured context
4. Protocol-Specific Mapping: Native error representations (JSON-RPC in this case)
"""

import logging
from typing import Any, Dict

from a2a.types import JSONRPCError, InternalError
from a2a.utils.errors import ServerError
from statista_agent.statista_tools import (
    StatisaAuthenticationError,
    StatisaTimeoutError,
    StatisaAPIError,
)

logger = logging.getLogger(__name__)


# Custom JSON-RPC error codes for authentication
# Following A2A pattern of using -32xxx codes
AUTHENTICATION_ERROR_CODE = -32401  # Unauthorized (similar to HTTP 401)
AUTHENTICATION_TIMEOUT_CODE = -32408  # Request Timeout (similar to HTTP 408)
EXTERNAL_SERVICE_ERROR_CODE = -32502  # Bad Gateway (similar to HTTP 502)


def handle_statista_exception(exc: Exception) -> ServerError:
    """Convert Statista exceptions to A2A-compliant ServerError.

    This function maps our custom Statista exceptions to proper A2A/JSON-RPC
    error responses that conform to the A2A protocol specification.

    Args:
        exc: The exception to convert

    Returns:
        ServerError containing the appropriate JSONRPCError
    """
    logger.error(f"Handling Statista exception: {type(exc).__name__}: {exc}")

    if isinstance(exc, StatisaAuthenticationError):
        # Authentication failed - return 401-like error
        error = JSONRPCError(
            code=AUTHENTICATION_ERROR_CODE,
            message="Authentication failed",
            data={
                "error_type": "authentication_error",
                "details": str(exc),
                "auth_scheme": "API-Key",
                "hint": "Please check that your STATISTA_API_KEY is valid and not expired.",
            },
        )
        logger.error(f"Authentication error: {error.message}")
        return ServerError(error)

    elif isinstance(exc, StatisaTimeoutError):
        # Request timeout - return 408-like error
        error = JSONRPCError(
            code=AUTHENTICATION_TIMEOUT_CODE,
            message="Request timeout",
            data={
                "error_type": "timeout_error",
                "details": str(exc),
                "hint": "The request to Statista API timed out. Please try again.",
            },
        )
        logger.error(f"Timeout error: {error.message}")
        return ServerError(error)

    elif isinstance(exc, StatisaAPIError):
        # General API error - return 502-like error (external service issue)
        error = JSONRPCError(
            code=EXTERNAL_SERVICE_ERROR_CODE,
            message="External service error",
            data={
                "error_type": "api_error",
                "details": str(exc),
                "service": "Statista API",
            },
        )
        logger.error(f"API error: {error.message}")
        return ServerError(error)

    else:
        # Unknown error - return internal error
        error = InternalError(
            message=f"Internal error: {str(exc)}",
            data={
                "error_type": type(exc).__name__,
                "details": str(exc),
            },
        )
        logger.error(f"Internal error: {error.message}")
        return ServerError(error)


def create_error_response(
    error_code: int, message: str, details: Dict[str, Any]
) -> Dict[str, Any]:
    """Create a JSON-RPC error response dictionary.

    Args:
        error_code: The JSON-RPC error code
        message: Human-readable error message
        details: Additional error details

    Returns:
        A dictionary formatted as a JSON-RPC error response
    """
    return {
        "code": error_code,
        "message": message,
        "data": details,
    }
