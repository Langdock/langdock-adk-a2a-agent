"""
Vertex AI Agent Engine deployment configuration.

This module provides the entry point for deploying the Statista agent
to Vertex AI Agent Engine. It wraps the agent for cloud deployment
and exposes it via the ADK framework.
"""

import os
import logging
from dotenv import load_dotenv
from logging_config import setup_logging

# Load environment variables
load_dotenv()

# Setup logging
setup_logging(level=logging.INFO)
logger = logging.getLogger(__name__)
logger.info("Initializing Statista Agent for Vertex AI Agent Engine")

# Import the agent after logging is configured
from statista_agent.agent import root_agent

# Export the agent for Vertex AI Agent Engine deployment
# The agent will be automatically discovered and deployed by the ADK CLI
agent = root_agent

# Optional: Add any deployment-specific configuration here
if __name__ == "__main__":
    logger.info("Agent Engine app initialized successfully")
    logger.info(f"Agent: {agent.name}")
