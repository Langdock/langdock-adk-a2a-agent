# Quick Start Guide

## Installation

```bash
# Clone/navigate to the repository
cd statista-agent

# Create virtual environment (if not exists)
python3 -m venv venv

# Install dependencies
source venv/bin/activate
pip install -r requirements.txt

# Configure environment
cp .env.example .env  # If you have an example file
# Edit .env with your credentials
```

## Configuration

Edit `.env` with your credentials:

```bash
# Google Cloud / Vertex AI
GOOGLE_GENAI_USE_VERTEXAI=1
GOOGLE_CLOUD_PROJECT=your-project-id
GOOGLE_CLOUD_LOCATION=your-region

# Statista MCP
STATISTA_API_KEY=your-statista-api-key
STATISTA_MCP_URL=https://api.statista.ai/v1/mcp
```

## Running the Agent

```bash
# Start the agent (auto-reload enabled)
./run_a2a_agent.sh

# Or manually:
source venv/bin/activate
python -m uvicorn a2a_rootagent:a2a_app --host 0.0.0.0 --port 8001 --reload
```

Agent will be available at:
- **A2A Endpoint**: http://localhost:8001/
- **Agent Card**: http://localhost:8001/.well-known/agent-card.json

The agent card includes:
- Statista branding (name, icon, description)
- Two skills: Search Statistics and Get Chart Data
- Supported input/output modes
- A2A protocol version 0.3.0

## Testing

```bash
# Quick configuration check
python test_full_workflow.py

# Full MCP integration test
python test_statista_example.py

# View MCP tool schemas
python test_list_tool_schemas.py
```

## Usage Examples

Ask the agent:

```
"Find revenue statistics for BASF"
"Get detailed chart data for statistic 263596"
"What's the GDP of Japan?"
```

## Project Structure

```
statista-agent/
├── venv/                    # Virtual environment (symlink)
├── statista_agent/          # Agent package
│   ├── agent.py            # Agent configuration
│   └── statista_tools.py   # MCP tools (search, chart data)
├── a2a_rootagent.py        # A2A server entry point
├── logging_config.py       # Logging configuration
├── run_a2a_agent.sh        # Startup script
└── test_*.py               # Test files
```

## Key Features

✅ Correct MCP parameter names (`query`, `id`)
✅ Parses all 6 content items from chart data
✅ Auto-reload on code changes
✅ DEBUG logging for troubleshooting
✅ Production-ready error handling

## Troubleshooting

### Import Errors
```bash
# Ensure you're using the venv
source venv/bin/activate
```

### API Key Issues
```bash
# Check .env file exists and has correct keys
cat .env | grep STATISTA_API_KEY
```

### Connection Issues
```bash
# Test MCP connection directly
python test_list_tool_schemas.py
```

## Documentation

- [README.md](README.md) - Full documentation
- [PROJECT_STRUCTURE.md](PROJECT_STRUCTURE.md) - File overview

## Support

Check logs in terminal for detailed error messages with `[DEBUG]` markers.
