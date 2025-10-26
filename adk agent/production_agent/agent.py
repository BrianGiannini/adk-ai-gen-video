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

os.environ.setdefault("GOOGLE_CLOUD_LOCATION", "us-central1")
os.environ.setdefault("GOOGLE_GENAI_USE_VERTEXAI", "True")

# Set up Cloud Logging
logging_client = google_cloud_logging.Client()
logger = logging_client.logger("production-adk-agent")


# Configure the deployed model endpoint
gemma_model_name = os.getenv("GEMMA_MODEL_NAME", "gemma3:4b")  # Gemma model name
api_base = os.getenv("OLLAMA_API_BASE", "http://localhost:10010")  # Location of Ollama server

from production_agent.tools.veo_tool import generate_video_and_upload


# Production Gemma Agent - GPU-accelerated conversational assistant
# 1. Connects to your deployed Gemma backend via LiteLlm
# 2. Creates a simple conversational agent
# 3. Configures Google Cloud integration
production_agent = Agent(
    model=LiteLlm(model=f"ollama_chat/{gemma_model_name}", api_base=api_base),
    name="production_agent",
    description="A production-ready conversational assistant powered by GPU-accelerated Gemma that can generate videos.",
    instruction="""
        You are a helpful assistant that can generate videos.

        Here is your workflow:
        1. When a user asks you to generate a video, you MUST call the `generate_video_and_upload` tool with the user's prompt.
        2. The tool will run and then return a string, which is a GCS URI (it will start with "gs://").
        3. When you receive this GCS URI string from the tool, this means the task is COMPLETE and SUCCESSFUL.
        4. Your final response to the user MUST be to present this GCS URI. You should say something like, "Your video has been generated and is available at: [the_gcs_uri_string]".
        5. **DO NOT** call the `generate_video_and_upload` tool again if you have already received a GCS URI for the user's request.
        
        You can also help users write better prompts for video generation if they ask for help.
    """,
    
    tools=[generate_video_and_upload],
)

# Set as root agent
root_agent = production_agent