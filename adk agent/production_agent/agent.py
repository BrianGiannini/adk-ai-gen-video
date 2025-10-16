import os
from pathlib import Path
from typing import Dict, Any

from dotenv import load_dotenv
from google.adk.agents import LlmAgent, Agent
from google.adk.tools import google_search
from google.adk.models.lite_llm import LiteLlm
from google.cloud import logging as google_cloud_logging
import google.auth

# Load environment variables from .env file in root directory
root_dir = Path(__file__).parent.parent
dotenv_path = root_dir / ".env"
load_dotenv(dotenv_path=dotenv_path)

# Use default project from credentials if not in .env
try:
    _, project_id = google.auth.default()
    os.environ.setdefault("GOOGLE_CLOUD_PROJECT", project_id)
except Exception:
    # If no credentials available, continue without setting project
    pass

os.environ.setdefault("GOOGLE_CLOUD_LOCATION", "europe-west1")
os.environ.setdefault("GOOGLE_GENAI_USE_VERTEXAI", "True")

# Set up Cloud Logging
logging_client = google_cloud_logging.Client()
logger = logging_client.logger("production-adk-agent")


# Configure the deployed model endpoint
gemma_model_name = os.getenv("GEMMA_MODEL_NAME", "gemma3:4b")  # Gemma model name
api_base = os.getenv("OLLAMA_API_BASE", "http://localhost:10010")  # Location of Ollama server

# Production Gemma Agent - GPU-accelerated conversational assistant
# 1. Connects to your deployed Gemma backend via LiteLlm
# 2. Creates a simple conversational agent
# 3. Configures Google Cloud integration
production_agent = Agent(
    model=LiteLlm(model=f"ollama_chat/{gemma_model_name}", api_base=api_base),
    name="production_agent",
    description="A production-ready conversational assistant powered by GPU-accelerated Gemma.",
    instruction="""
        You are a helpful assistant that can writing prompts for video generation.
    """,
    
    tools=[],  # Gemma focuses on conversational capabilities
)

# Set as root agent
root_agent = production_agent