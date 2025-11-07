# veo_tool.py
import os
import time
import re
from google import genai
from google.genai import types
from google.cloud import storage
from pathlib import Path

# --- Environment Variables ---
# VEO_FAST_MODEL, VEO_HQ_MODEL, and GCS_BUCKET_NAME are expected.

def generate_video_and_prompt_file(final_prompt: str, display_message: str, quality: str) -> str:
    """
    Generates a video AND uploads a corresponding .prompt.txt file.
    
    Args:
        final_prompt: The "clean" prompt to send to Veo.
        display_message: The "By JohnDoe: ..." text for the OBS overlay.
        quality: The quality ("fast" or "normal") to determine which model to use.

    Returns:
        The GCS URI of the generated video.
    """
    project_id = os.environ.get("GOOGLE_CLOUD_PROJECT")
    location = os.environ.get("GOOGLE_CLOUD_LOCATION")
    
    if quality == "fast":
        model_name = os.getenv("VEO_FAST_MODEL", "veo-3.1-fast-generate-preview")
    else:
        model_name = os.getenv("VEO_HQ_MODEL", "veo-3.1-generate-preview")
        
    bucket_name = os.environ.get("GCS_BUCKET_NAME")
    
    if not all([project_id, location, bucket_name]):
        raise EnvironmentError(
            "Missing required environment variables. "
            "Ensure GOOGLE_CLOUD_PROJECT, GOOGLE_CLOUD_LOCATION, "
            "and GCS_BUCKET_NAME are set."
        )

    # 1. Configure genai client
    client = genai.Client(project=project_id, location=location)

    # 2. Prepare GCS prefix
    timestamp = int(time.time())
    gcs_prefix = f"veo_temp/{timestamp}/" 
    output_gcs_uri_prefix = f"gs://{bucket_name}/{gcs_prefix}"
    print(f"Configuring temporary output to GCS prefix: {output_gcs_uri_prefix}")

    # 3. Start video generation
    print(f"Starting video generation job for: '{final_prompt}' (Quality: {quality})")
    operation = client.models.generate_videos(
        model=model_name,
        prompt=final_prompt,
        config=types.GenerateVideosConfig(
            output_gcs_uri=output_gcs_uri_prefix, 
            number_of_videos=1,
            aspect_ratio="16:9",
        )
    )

    # 4. Wait for completion
    print(f"Waiting for operation {operation.name} to complete...")
    while not operation.done:
        print("  Polling... (checking status)")
        time.sleep(10)
        operation = client.operations.get(operation)

    print("Operation finished. Accessing response...")
    
    # --- Error handling ---
    if not operation.result or not operation.result.generated_videos:
         error_details = "Unknown error or no videos generated (check safety filters)."
         if hasattr(operation, 'response') and operation.response:
             if hasattr(operation.response, 'error') and operation.response.error:
                 error_details = f"Operation error: {operation.response.error}"
             elif hasattr(operation.response, 'status') and operation.response.status:
                  error_details = f"Operation status: {operation.response.status}"
             elif hasattr(operation.response, 'details') and operation.response.details:
                  error_details = f"Operation details: {operation.response.details}"
         print(f"Video generation failed: {error_details}")
         return f"Video generation failed: {error_details}"
    # --- End error handling ---
    
    final_video_gcs_uri = operation.result.generated_videos[0].video.uri
    print(f"  Successfully retrieved GCS URI: {final_video_gcs_uri}")
    
    # --- 5. MOVE VIDEO TO FINAL PATH AND UPLOAD PROMPT ---
    try:
        print(f"Moving video and uploading prompt to final destination...")
        storage_client = storage.Client()
        gcs_bucket = storage_client.bucket(bucket_name)

        # --- 5a. Create the new filename base ---
        timestamp_str = time.strftime("%Y%m%d_%H%M%S", time.localtime(timestamp))
        safe_quality = quality.lower().strip()
        filename_base = f"{timestamp_str}_video_{safe_quality}"
        
        # --- 5b. Define final paths (no sub-folder) ---
        final_video_blob_name = f"veo_output/{filename_base}.mp4"
        final_prompt_blob_name = f"veo_output/{filename_base}.prompt.txt"
        
        # --- 5c. Move the generated video ---
        source_blob_name = final_video_gcs_uri.replace(f"gs://{bucket_name}/", "")
        source_blob = gcs_bucket.blob(source_blob_name)

        print(f"  Moving video from {source_blob_name} to {final_video_blob_name}")
        gcs_bucket.rename_blob(source_blob, new_name=final_video_blob_name)
        
        # --- 5d. Upload the prompt file ---
        print(f"  Uploading prompt file to: {final_prompt_blob_name}")
        prompt_blob = gcs_bucket.blob(final_prompt_blob_name)
        prompt_blob.upload_from_string(display_message, content_type="text/plain")

        # --- 5e. Update the return URI ---
        final_video_gcs_uri = f"gs://{bucket_name}/{final_video_blob_name}"
        
    except Exception as e:
        print(f"  WARNING: Failed to move video or upload prompt file. Error: {e}")
        pass
    
    # 6. Return the video URI
    return final_video_gcs_uri