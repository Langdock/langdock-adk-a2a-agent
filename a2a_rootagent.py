import os
import logging
from dotenv import load_dotenv
from google.adk.a2a.utils.agent_to_a2a import to_a2a
from logging_config import setup_logging

# Load environment variables from .env file
load_dotenv()

# Setup logging
setup_logging(level=logging.INFO)
logger = logging.getLogger(__name__)
logger.info("Starting Statista A2A Agent")

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
