import os
from pathlib import Path
from typing import Dict, Any
import json
from dotenv import load_dotenv
from google.adk.agents import Agent, SequentialAgent
from google.adk.models.lite_llm import LiteLlm
from google.cloud import logging as google_cloud_logging
import google.auth

# --- Vertex AI Setup ---
try:
    _, project_id = google.auth.default()
    os.environ.setdefault("GOOGLE_CLOUD_PROJECT", project_id)
except Exception:
    pass
os.environ.setdefault("GOOGLE_GENAI_USE_VERTEXAI", "True")
os.environ.setdefault("GOOGLE_CLOUD_LOCATION", "us-central1")

logging_client = google_cloud_logging.Client()
logger = logging_client.logger("production-adk-agent")

# --- Model Definitions ---
PRO_MODEL = "gemini-2.5-pro"
FLASH_MODEL = "gemini-2.5-flash" 

# --- Import ALL our tools ---
from production_agent.tools.mock_veo_tool import generate_video_and_prompt_file
# from production_agent.tools.veo_tool import generate_video_and_prompt_file # <-- The REAL one
from production_agent.tools.safety_tool import check_prompt_safety

# --- AGENT CHAIN ---

# 1. Safety Check Agent (Unchanged)
safety_check_agent = Agent(
    model=LiteLlm(model=FLASH_MODEL),
    name="safety_check_agent",
    description="Calls the safety tool to classify a prompt.",
    instruction="""
    You will receive a plain text JSON string.
    
    JOB 1: If the input is a JSON string (e.g., '{"prompt":...}'):
    1.  Parse the JSON to get the `prompt` value.
    2.  Call the `check_prompt_safety` tool with this `prompt_text`.
    3.  The tool will return a verdict: "TOXIC", "BORDERLINE", "SAFE", or "SAFETY_API_FAILED".
    4.  You MUST then create a new JSON object that passes *all* the
        information to the next agent.
    5.  Respond in this *exact* JSON format:
        {
          "original_json_string": "[THE_ORIGINAL_INPUT_STRING]",
          "safety_verdict": "[VERDICT_FROM_TOOL]"
        }
    (Replace [THE_ORIGINAL_INPUT_STRING] with the full string you received,
     and [VERDICT_FROM_TOOL] with the tool's output.)

    JOB 2: If the input is *NOT* a JSON string (e.g., "[STOP]"):
    - Just output the text "[STOP]".
    """,
    tools=[check_prompt_safety],
)

# 2. Decision Agent (MODIFIED AS REQUESTED)
decision_agent = Agent(
    model=LiteLlm(model=PRO_MODEL), 
    name="decision_agent",
    description="Makes a decision based on the safety verdict.",
    instruction="""
    You will receive a JSON string containing "original_json_string" and "safety_verdict".
    
    1.  Parse this input JSON.
    2.  Parse the "original_json_string" to get the `prompt`, `user`, and `quality`.
    3.  Read the "safety_verdict" and follow these 3 cases.
    
    CASE 1 (verdict is "TOXIC" or "SAFETY_API_FAILED"):
    - Invent a new, safe, high-detail prompt. This prompt must be 
      **impressive, funny, or visually spectacular** for an AI video model.
    - Do not create a boring prompt.
    - Return the final JSON in this format:
      {"final_prompt": "[YOUR_NEW_IMPRESSIVE_PROMPT]", "display_message": "By [user] : prompt banned, replacement prompt here: [YOUR_NEW_IMPRESSIVE_PROMPT]", "quality": "[quality]"}

    CASE 2 (verdict is "BORDERLINE"):
    - Rewrite the original `prompt` to be completely family-friendly.
    - Return the final JSON in this format:
      {"final_prompt": "[rewritten_prompt]", "display_message": "By [user] (censored) : [rewritten_prompt]", "quality": "[quality]"}
      
    CASE 3 (verdict is "SAFE"):
    - Use the original `prompt`.
    - Return the final JSON in this format:
      {"final_prompt": "[original_prompt]", "display_message": "By [user] : [original_prompt]", "quality": "[quality]"}
    
    (Use the `user` and `quality` values from the parsed "original_json_string").
    """,
    tools=[],
)

# 3. Worker Agent (Unchanged)
video_worker_agent = Agent(
    model=LiteLlm(model=FLASH_MODEL),
    name="video_worker_agent",
    description="Calls the video generation tool.",
    instruction="""
    You are a video worker. You have ONE tool: `generate_video_and_prompt_file`.
    You MUST follow these rules:

    RULE 1: If your input is a JSON string (starting with '{"final_prompt":'):
    - Your job is to call the `generate_video_and_prompt_file` tool using the
      'final_prompt', 'display_message', and 'quality' arguments from that JSON.
    
    RULE 2: If your input is a tool output string (starting with 'gs://' or 'Video generation failed:'):
    - This is your final step.
    - Your ONLY job is to output this string *exactly one time*. Do not repeat it.
    - DO NOT call any tools.
    """,
    tools=[generate_video_and_prompt_file],
)

# 4. Confirmation Agent (Unchanged)
confirmation_agent = Agent(
    model=LiteLlm(model=FLASH_MODEL),
    name="confirmation_agent",
    description="Formats the final confirmation message.",
    instruction="""You will be given a GCS URI or an error message as input.
    If the input starts with 'gs://', your response MUST be in the following format:
    '''Task Complete: Video generation finished. The result is available at: [GCS_URI]'''
    (Replace [GS_URI] with the input URI).
    If the input starts with 'Video generation failed:', respond with 'Task Failed' and the error message.
    """,
    tools=[],
)

# 5. Orchestrator Agent (Unchanged)
orchestrator_agent = SequentialAgent(
    name="orchestrator_agent",
    sub_agents=[
        safety_check_agent,
        decision_agent,
        video_worker_agent,
        confirmation_agent
    ]
)

# Set the orchestrator as the root agent
root_agent = orchestrator_agent