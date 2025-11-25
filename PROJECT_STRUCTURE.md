# Project Structure

Clean, production-ready Statista research agent.

## Files

### Core Application
```
.
├── .env                      # Environment variables (API keys, GCP config)
├── .gitignore               # Git ignore patterns
├── requirements.txt          # Python dependencies
├── run_a2a_agent.sh         # Agent startup script (with auto-reload)
├── a2a_rootagent.py         # A2A server entry point
├── agent_card.json          # A2A agent card configuration
├── logging_config.py        # Centralized logging setup
└── statista_agent/
    ├── __init__.py
    ├── agent.py             # Agent configuration with tools
    └── statista_tools.py    # FastMCP integration (search & chart data)
```

### Documentation
```
├── README.md                # Main documentation
└── PROJECT_STRUCTURE.md     # This file
```

### Tests
```
└── tests/
    ├── test_full_workflow.py    # Configuration verification
    ├── test_statista_example.py # Full MCP integration test
    └── test_list_tool_schemas.py # View actual MCP schemas
```

## Usage

### Start Agent
```bash
./run_a2a_agent.sh
```

### Run Tests
```bash
cd tests
python test_full_workflow.py      # Quick config check
python test_statista_example.py   # Full integration test
```

## Key Features

✅ Direct FastMCP integration with Statista MCP server
✅ Correct parameter names (`query`, `id`) per actual schema
✅ Proper parsing of all 6 content items from chart data
✅ Auto-reload on code changes
✅ Comprehensive DEBUG logging
✅ Production-ready error handling

## Dependencies

- `google-adk[a2a]` - Google Agent Development Kit
- `google-genai` - Google Generative AI
- `fastmcp` - FastMCP client for MCP integration

## Configuration

Environment variables in `.env`:
- Google Cloud / Vertex AI credentials
- Statista API key and MCP URL

See [README.md](README.md) for full configuration details.
