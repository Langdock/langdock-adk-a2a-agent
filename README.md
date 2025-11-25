# Statista Research Agent

A powerful AI agent that provides access to Statista's comprehensive statistical database through Google ADK and MCP (Model Context Protocol).

## ✅ Status: Ready to Use

All tests passing with correct MCP parameter names and response parsing!

## Quick Start

```bash
# Start the agent
./run_a2a_agent.sh

# Agent available at:
# - A2A Endpoint: http://localhost:8001/
# - Agent Card: http://localhost:8001/.well-known/agent-card.json
```

The agent card is configured in [agent_card.json](agent_card.json) with:
- Statista branding (icon, name, description)
- Available capabilities (search and chart data retrieval)
- Contact information

## Testing

```bash
# Verify configuration
python test_full_workflow.py

# Test MCP integration
python test_statista_example.py

# View MCP schemas
python test_list_tool_schemas.py
```

## Architecture

```
User Query
    ↓
Google ADK Agent (gemini-2.5-flash)
    ↓
Tool Functions (search_statistics, get_chart_data)
    ↓
FastMCP Client
    ↓
Statista MCP Server (https://api.statista.ai/v1/mcp)
```

## Tools

### 1. search_statistics
Search Statista's database for statistics.

**Parameters:**
- `query` (str): Natural language search query
- `max_results` (int): Maximum results to return (default: 10)

**Example:**
```python
await search_statistics(
    query="BASF revenue",
    tool_context=context
)
```

**MCP Call:**
- Tool: `search-statistics`
- Parameter: `{"query": "..."}`
- Returns: 1 content item with JSON search results

### 2. get_chart_data
Retrieve detailed chart data for a specific statistic.

**Parameters:**
- `statistic_id` (int): Statistic identifier from search results

**Example:**
```python
await get_chart_data(
    statistic_id=263596,
    tool_context=context
)
```

**MCP Call:**
- Tool: `get-chart-data-by-id`
- Parameter: `{"id": 263596}`
- Returns: 6 content items (chart data, description, sources, ID, URLs)

## Configuration

### Environment Variables (`.env`)

```bash
# Google Cloud / Vertex AI
GOOGLE_GENAI_USE_VERTEXAI=1
GOOGLE_CLOUD_PROJECT=langdock-prod-gcp
GOOGLE_CLOUD_LOCATION=europe-west3

# Statista MCP
STATISTA_API_KEY=your_api_key_here
STATISTA_MCP_URL=https://api.statista.ai/v1/mcp
```

### Files

**Core:**
- `statista_agent/agent.py` - Agent configuration
- `statista_agent/statista_tools.py` - MCP integration tools
- `a2a_rootagent.py` - A2A server entry point
- `logging_config.py` - Logging configuration

**Tests:**
- `test_full_workflow.py` - Configuration test
- `test_statista_example.py` - MCP integration test
- `test_list_tool_schemas.py` - View MCP schemas

**Documentation:**
- `README.md` - This file
- `FINAL_SETUP.md` - Detailed setup guide
- `DEBUG.md` - Debugging guide

## Important Notes

### ⚠️ Correct Parameter Names

The Statista MCP server uses different parameter names than shown in their example documentation:

| Documentation | Actual Schema |
|---------------|---------------|
| `question` | ✅ `query` |
| `statistic_id` | ✅ `id` |

Our implementation uses the **correct** parameter names from the actual MCP schema.

### Response Structure

**search-statistics:**
- 1 content item with JSON array of results
- Each result has: `identifier`, `title`, `subject`, `link`, `is_premium`

**get-chart-data-by-id:**
- 6 content items:
  1. Chart data (JSON with `graphType`, `description`, `data`)
  2. HTML description
  3. Sources (JSON array)
  4. Statistic ID
  5. URL
  6. URL (duplicate)

## Features

✅ Auto-reload on code changes (`--reload`)
✅ Comprehensive DEBUG logging
✅ Proper error handling with stack traces
✅ Context state management for search/chart history
✅ Formatted output optimized for LLM consumption
✅ Multiple content item parsing
✅ Source attribution and metadata

## Example Usage

Ask the agent:

> "Find revenue statistics for BASF and show me the detailed data"

The agent will:
1. Call `search_statistics(query="BASF revenue")`
2. Parse results to extract statistic IDs
3. Call `get_chart_data(statistic_id=...)` for relevant statistics
4. Return formatted data with sources and context

## Troubleshooting

### View Logs
Logs appear in terminal when agent is running. Look for:
- `[DEBUG]` - Detailed MCP calls
- `[SUCCESS]` - Successful operations
- `[ERROR]` - Errors with stack traces

### Common Issues

**Parameter validation errors:**
- Fix: We use correct parameter names (`query`, `id`)

**JSON parsing errors:**
- Fix: We parse all 6 content items from chart data response

**Connection errors:**
- Check: API key in `.env`
- Check: Network access to `api.statista.ai`

## Development

### Adding New Tools

1. Add async function to `statista_agent/statista_tools.py`
2. Use `_get_mcp_client()` for MCP connection
3. Add comprehensive logging
4. Format output for LLM consumption
5. Add to `root_agent.tools` in `statista_agent/agent.py`

### Testing Changes

```bash
# Auto-reload is enabled, just edit files
# Logs appear immediately in terminal
```

## Deployment to Vertex AI Agent Engine

This agent is configured for automated deployment to Google Cloud's Vertex AI Agent Engine via GitHub Actions.

### Prerequisites

1. **Google Cloud Project Setup:**
   - Create or select a GCP project
   - Enable required APIs:
     ```bash
     gcloud services enable \
       aiplatform.googleapis.com \
       artifactregistry.googleapis.com \
       cloudbuild.googleapis.com
     ```
   - Create an Artifact Registry repository:
     ```bash
     gcloud artifacts repositories create agents \
       --repository-format=docker \
       --location=us-central1
     ```

2. **Workload Identity Federation:**
   - Set up Workload Identity Federation for GitHub Actions
   - Create a service account with required permissions:
     - Vertex AI User
     - Artifact Registry Writer
     - Cloud Build Editor

3. **GitHub Secrets:**
   Configure the following secrets in your repository settings:
   - `GCP_PROJECT`: Your GCP project ID
   - `GCP_WORKLOAD_IDENTITY_PROVIDER`: Workload Identity Provider resource name
   - `GCP_SERVICE_ACCOUNT`: Service account email for deployment
   - `STATISTA_API_KEY`: Your Statista API key

### Deployment Workflows

#### Continuous Deployment (Automatic)
Push to `main` branch triggers automatic deployment to production:

```bash
git add .
git commit -m "Update agent"
git push origin main
```

The GitHub Actions workflow will:
1. Run CI tests (linting, type checking, unit tests)
2. Build Docker image
3. Push to Artifact Registry
4. Deploy to Vertex AI Agent Engine
5. Run smoke tests
6. Create a GitHub release

#### Manual Deployment (via CLI)
Deploy manually using the Makefile:

```bash
# Set environment variables
export GCP_PROJECT=your-project-id
export GCP_REGION=us-central1

# Deploy
make deploy
```

Or use the ADK CLI directly:

```bash
adk deploy agent_engine \
  --agent-module agent_engine_app \
  --display-name "Statista Agent" \
  --project your-project-id \
  --region us-central1
```

### Project Structure

```
statista-agent/
├── .github/
│   └── workflows/
│       ├── ci.yaml                    # CI pipeline (tests, linting)
│       └── deploy-production.yaml     # Production deployment
├── .cloudbuild/
│   └── cloudbuild.yaml               # Google Cloud Build config
├── statista_agent/
│   ├── agent.py                      # Agent configuration
│   └── statista_tools.py             # MCP integration tools
├── agent_engine_app.py               # Vertex AI entry point
├── a2a_rootagent.py                  # A2A server entry point
├── Dockerfile                        # Container definition
├── pyproject.toml                    # Python project config
├── Makefile                          # Development commands
└── agent_card.json                   # Agent metadata

```

### Environment Variables for Deployment

The agent requires the following environment variables in production:

```bash
GOOGLE_GENAI_USE_VERTEXAI=1
GOOGLE_CLOUD_PROJECT=your-project-id
GOOGLE_CLOUD_LOCATION=us-central1
STATISTA_API_KEY=your-api-key
STATISTA_MCP_URL=https://api.statista.ai/v1/mcp
```

These should be configured in your deployment environment (Cloud Run, Agent Engine, etc.).

### Local Development

```bash
# Install dependencies
make install-dev

# Run locally with A2A
make playground

# Run tests
make test

# Format code
make format

# Lint code
make lint
```

### Monitoring and Logs

After deployment, monitor your agent:

```bash
# View logs
gcloud logging read "resource.type=vertex_ai_agent_engine" \
  --project your-project-id \
  --limit 50

# Check agent status
gcloud ai agents list --project your-project-id --region us-central1
```

---

**Status**: ✅ Production Ready
**Last Updated**: 2025-11-25
**Version**: 1.0.0
**Repository**: [github.com/Langdock/langdock-adk-a2a-agent](https://github.com/Langdock/langdock-adk-a2a-agent)