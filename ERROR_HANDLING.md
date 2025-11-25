# A2A Error Handling for Statista Agent

This document describes the A2A protocol-compliant error handling implemented in the Statista agent.

## Overview

The agent implements comprehensive error handling according to the [A2A Protocol Specification](https://a2a-protocol.org/latest/specification/). All errors are returned as JSON-RPC error responses with proper error codes, messages, and structured context.

## Error Types

### 1. Authentication Errors

**JSON-RPC Error Code**: `-32401` (similar to HTTP 401)

Raised when:
- Statista API key is missing or invalid
- Statista API key has expired
- Vertex AI credentials are missing or invalid
- Any authentication-related error occurs

**Example Response**:
```json
{
  "jsonrpc": "2.0",
  "error": {
    "code": -32401,
    "message": "Authentication failed",
    "data": {
      "error_type": "authentication_error",
      "details": "Authentication failed: STATISTA_API_KEY environment variable is required...",
      "auth_scheme": "API-Key",
      "hint": "Please check that your STATISTA_API_KEY is valid and not expired."
    }
  },
  "id": null
}
```

### 2. Timeout Errors

**JSON-RPC Error Code**: `-32502` (similar to HTTP 502 Bad Gateway)

Raised when:
- Request to Statista API times out
- Connection timeout occurs
- Read timeout occurs

**Example Response**:
```json
{
  "jsonrpc": "2.0",
  "error": {
    "code": -32502,
    "message": "Request timeout",
    "data": {
      "error_type": "timeout_error",
      "details": "Request timed out while searching Statista: ...",
      "hint": "The request timed out. Please try again."
    }
  },
  "id": null
}
```

### 3. Model Unavailable Errors

**JSON-RPC Error Code**: `-32503` (similar to HTTP 503 Service Unavailable)

Raised when:
- Vertex AI / Gemini model is not reachable
- Model quota is exceeded
- Model service is unavailable

**Example Response**:
```json
{
  "jsonrpc": "2.0",
  "error": {
    "code": -32503,
    "message": "AI model unavailable",
    "data": {
      "error_type": "model_error",
      "details": "...",
      "service": "Vertex AI / Gemini",
      "hint": "The AI model is not reachable. Check your Vertex AI credentials and quotas."
    }
  },
  "id": null
}
```

### 4. External Service Errors

**JSON-RPC Error Code**: `-32502` (similar to HTTP 502 Bad Gateway)

Raised when:
- Statista API returns an error
- External service communication fails

**Example Response**:
```json
{
  "jsonrpc": "2.0",
  "error": {
    "code": -32502,
    "message": "External service error",
    "data": {
      "error_type": "api_error",
      "details": "Error searching Statista: ...",
      "service": "Statista API"
    }
  },
  "id": null
}
```

### 5. Internal Errors

**JSON-RPC Error Code**: `-32603` (JSON-RPC Internal Error)

Raised when:
- An unexpected error occurs
- An unhandled exception is raised

**Example Response**:
```json
{
  "jsonrpc": "2.0",
  "error": {
    "code": -32603,
    "message": "Internal error",
    "data": {
      "error_type": "ValueError",
      "details": "..."
    }
  },
  "id": null
}
```

## Implementation Details

### Custom Exception Classes

The agent defines three custom exception classes in `statista_agent/statista_tools.py`:

```python
class StatisaAuthenticationError(Exception):
    """Raised when authentication with Statista API fails."""
    pass

class StatisaTimeoutError(Exception):
    """Raised when a request to Statista API times out."""
    pass

class StatisaAPIError(Exception):
    """Raised when Statista API returns an error."""
    pass
```

### Error Detection and Raising

The tools now properly **raise exceptions** instead of returning error strings:

```python
# Before (incorrect):
except Exception as e:
    return f"Error: {e}"

# After (correct):
except Exception as e:
    if 'authentication' in str(e).lower():
        raise StatisaAuthenticationError(f"Auth failed: {e}") from e
    raise StatisaAPIError(f"API error: {e}") from e
```

### Error Handling Middleware

The `A2AErrorHandlerMiddleware` in `a2a_rootagent.py` catches all exceptions and converts them to A2A-compliant JSON-RPC error responses:

```python
class A2AErrorHandlerMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        try:
            response = await call_next(request)
            return response
        except Exception as exc:
            # Convert exception to JSON-RPC error response
            error_response = self._create_error_response(exc, ...)
            return JSONResponse(status_code=200, content=error_response)
```

## Testing

Run the error handling test suite:

```bash
python test_error_handling.py
```

This tests:
1. Missing API key raises `StatisaAuthenticationError`
2. Invalid API key is detected and handled
3. Valid authentication works correctly

## A2A Protocol Compliance

The error handling implementation follows these A2A requirements:

1. **Error Code**: Machine-readable identifier (JSON-RPC error codes)
2. **Error Message**: Human-readable description
3. **Error Details**: Structured context with:
   - `error_type`: Type of error
   - `details`: Full error message
   - `hint`: Helpful message for resolution
   - Additional context (service name, auth scheme, etc.)
4. **Protocol-Specific Mapping**: JSON-RPC error response format

## Error Code Reference

| Error Code | HTTP Equivalent | Description |
|------------|----------------|-------------|
| -32401 | 401 Unauthorized | Authentication failed |
| -32502 | 502 Bad Gateway | External service error / timeout |
| -32503 | 503 Service Unavailable | Model/service unavailable |
| -32603 | 500 Internal Server Error | Internal error |

## Common Error Scenarios

### Scenario 1: Missing Statista API Key

**Trigger**: `STATISTA_API_KEY` environment variable is not set

**Response**:
```json
{
  "jsonrpc": "2.0",
  "error": {
    "code": -32401,
    "message": "Authentication failed",
    "data": {
      "error_type": "authentication_error",
      "details": "Authentication failed: STATISTA_API_KEY environment variable is required. Please set your Statista API key in the .env file.",
      "auth_scheme": "API-Key",
      "hint": "Please check that your STATISTA_API_KEY is valid and not expired."
    }
  }
}
```

### Scenario 2: Vertex AI Model Not Reachable

**Trigger**: Vertex AI credentials are missing, invalid, or quota exceeded

**Response**:
```json
{
  "jsonrpc": "2.0",
  "error": {
    "code": -32503,
    "message": "AI model unavailable",
    "data": {
      "error_type": "model_error",
      "details": "...",
      "service": "Vertex AI / Gemini",
      "hint": "The AI model is not reachable. Check your Vertex AI credentials and quotas."
    }
  }
}
```

### Scenario 3: Statista API Timeout

**Trigger**: Request to Statista API times out

**Response**:
```json
{
  "jsonrpc": "2.0",
  "error": {
    "code": -32502,
    "message": "Request timeout",
    "data": {
      "error_type": "timeout_error",
      "details": "Request timed out while searching Statista: ...",
      "hint": "The request timed out. Please try again."
    }
  }
}
```

## See Also

- [A2A Protocol Specification](https://a2a-protocol.org/latest/specification/)
- [JSON-RPC 2.0 Specification](https://www.jsonrpc.org/specification)
- `a2a_error_handler.py` - Error conversion utilities
- `test_error_handling.py` - Test suite for error handling
