# veo_tool.py
import os
import time
import re
from google import genai
from google.genai import types
from google.cloud import storage
from pathlib import Path
import google.cloud.logging
from google.adk.tools import ToolContext
from production_agent.tools.usage_guard import reserve_video_slot

client = google.cloud.logging.Client()
logger = client.logger("production-adk-agent-veo-tool")

# --- Environment Variables ---
# VEO_FAST_MODEL, VEO_HQ_MODEL, and GCS_BUCKET_NAME are expected.

def generate_video_and_prompt_file(final_prompt: str, display_message: str, quality: str, context: str, tool_context: ToolContext) -> str:
    """
    Generates a video AND uploads a corresponding .prompt.txt file.
    
    Args:
        final_prompt: The "clean" prompt to send to Veo.
        display_message: The "By JohnDoe: ..." text for the OBS overlay.
        quality: The quality ("fast" or "normal") to determine which model to use.
        context: The source of the request ("stream" or "admin") to determine the save folder.

    Returns:
        The GCS URI of the generated video.
    """
    project_id = os.environ.get("GOOGLE_CLOUD_PROJECT")
    location = os.environ.get("VEO_LOCATION", "us-central1")
    
    if quality == "fast":
        model_name = os.getenv("VEO_FAST_MODEL", "veo-3.1-fast-generate-001")
    else:
        model_name = os.getenv("VEO_HQ_MODEL", "veo-3.1-generate-001")
        
    bucket_name = os.environ.get("GCS_BUCKET_NAME")
    
    if not all([project_id, location, bucket_name]):
        raise EnvironmentError(
            "Missing required environment variables. "
            "Ensure GOOGLE_CLOUD_PROJECT, VEO_LOCATION, "
            "and GCS_BUCKET_NAME are set."
        )

    # Spending safeguard: must pass before any paid Veo call
    refusal = reserve_video_slot(tool_context.invocation_id)
    if refusal:
        logger.log_text(f"Video generation refused: {refusal}", severity="WARNING")
        return f"Video generation failed: {refusal}"

    # 1. Configure genai client
    client = genai.Client(project=project_id, location=location)

    # --- 2. PREPARE GCS PATHS ---
    timestamp = int(time.time())
    
    # Logic to decide the output folder
    if context == "admin":
        output_folder_prefix = "admin_videos"
    else:
        output_folder_prefix = "veo_output"
            
    logger.log_text(f"  Context: '{context}'. Saving to folder: '{output_folder_prefix}'", severity="INFO")
    
    # We generate in a temporary folder to keep things clean
    gcs_prefix = f"{output_folder_prefix}_temp/{timestamp}/" 
    output_gcs_uri_prefix = f"gs://{bucket_name}/{gcs_prefix}"
    logger.log_text(f"Configuring temporary output to GCS prefix: {output_gcs_uri_prefix}", severity="INFO")

    # 3. Start video generation
    logger.log_text(f"Starting video generation job for: '{final_prompt}' (Quality: {quality})", severity="INFO")
    operation = client.models.generate_videos(
        model=model_name,
        prompt=final_prompt,
        config=types.GenerateVideosConfig(
            output_gcs_uri=output_gcs_uri_prefix, 
            number_of_videos=1,
            aspect_ratio="16:9",
            duration_seconds=int(os.getenv("VIDEO_DURATION_SECONDS", "8")),
        )
    )

    # 4. Wait for completion
    logger.log_text(f"Waiting for operation {operation.name} to complete...", severity="INFO")
    while not operation.done:
        logger.log_text("  Polling... (checking status)", severity="INFO")
        time.sleep(10)
        operation = client.operations.get(operation)

    logger.log_text("Operation finished. Accessing response...", severity="INFO")
    
    # --- Your original error handling ---
    if not operation.result or not operation.result.generated_videos:
         error_details = "Unknown error or no videos generated (check safety filters)."
         if hasattr(operation, 'response') and operation.response:
             if hasattr(operation.response, 'error') and operation.response.error:
                 error_details = f"Operation error: {operation.response.error}"
             elif hasattr(operation.response, 'status') and operation.response.status:
                  error_details = f"Operation status: {operation.response.status}"
             elif hasattr(operation.response, 'details') and operation.response.details:
                  error_details = f"Operation details: {operation.response.details}"
         logger.log_text(f"Video generation failed: {error_details}", severity="ERROR")
         return f"Video generation failed: {error_details}"
    # --- End error handling ---
    
    final_video_gcs_uri_temp = operation.result.generated_videos[0].video.uri
    logger.log_text(f"  Successfully retrieved temporary GCS URI: {final_video_gcs_uri_temp}", severity="INFO")
    
    # --- 5. MOVE VIDEO TO FINAL PATH AND UPLOAD PROMPT ---
    final_video_gcs_uri = final_video_gcs_uri_temp # Default value in case of error
    try:
        logger.log_text(f"Moving video and uploading prompt to final destination...", severity="INFO")
        storage_client = storage.Client()
        gcs_bucket = storage_client.bucket(bucket_name)

        # --- 5a. Create the new filename base ---
        timestamp_str = time.strftime("%Y%m%d_%H%M%S", time.localtime(timestamp))
        safe_quality = quality.lower().strip()
        filename_base = f"{timestamp_str}_video_{safe_quality}"
        
        # --- 5b. Define final paths (using the correct folder) ---
        final_video_blob_name = f"{output_folder_prefix}/{filename_base}.mp4"
        final_prompt_blob_name = f"{output_folder_prefix}/{filename_base}.prompt.txt"
        
        # --- 5c. Move the generated video ---
        source_blob_name = final_video_gcs_uri_temp.replace(f"gs://{bucket_name}/", "")
        source_blob = gcs_bucket.blob(source_blob_name)

        logger.log_text(f"  Moving video from {source_blob_name} to {final_video_blob_name}", severity="INFO")
        gcs_bucket.rename_blob(source_blob, new_name=final_video_blob_name)
        
        # --- 5d. Upload the prompt file ---
        logger.log_text(f"  Uploading prompt file to: {final_prompt_blob_name}", severity="INFO")
        prompt_blob = gcs_bucket.blob(final_prompt_blob_name)
        prompt_blob.upload_from_string(display_message, content_type="text/plain")

        # --- 5e. Update the return URI ---
        final_video_gcs_uri = f"gs://{bucket_name}/{final_video_blob_name}"
        
    except Exception as e:
        logger.log_text(f"  WARNING: Failed to move video or upload prompt file. Error: {e}", severity="ERROR")
        # Non-critical, return the *temporary* path so the agent can at least confirm success
        pass
    
    # 6. Return the video URI (either the final one or the temporary one)
    return final_video_gcs_uri