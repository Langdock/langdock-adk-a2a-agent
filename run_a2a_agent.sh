#!/bin/bash

# Activate the virtual environment
source venv/bin/activate

# Run the A2A agent with auto-reload on code changes
python -m uvicorn a2a_rootagent:a2a_app --host 0.0.0.0 --port 8001 --reload
