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
    
    # --- UPDATED: Quality-based model selection with defaults ---
    if quality == "fast":
        model_name = os.getenv("VEO_FAST_MODEL", "veo-3.1-fast-generate-preview")
    else:
        model_name = os.getenv("VEO_HQ_MODEL", "veo-3.1-generate-preview")
    # --- END UPDATE ---
        
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
    sanitized_prompt = re.sub(r'\W+', '_', final_prompt).lower()
    timestamp = int(time.time())
    gcs_prefix = f"veo_output/{sanitized_prompt[:50]}_{timestamp}/" 
    output_gcs_uri_prefix = f"gs://{bucket_name}/{gcs_prefix}"
    print(f"Configuring output to GCS prefix: {output_gcs_uri_prefix}")

    # 3. Start video generation
    print(f"Starting video generation job for: '{final_prompt}' (Quality: {quality})")
    operation = client.models.generate_videos(
        model=model_name, # <-- Uses the quality-based model name
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
         print(f"Video generation failed: {error_details}")
         return f"Video generation failed: {error_details}"
    # --- End error handling ---
    
    final_video_gcs_uri = operation.result.generated_videos[0].video.uri
    print(f"  Successfully retrieved GCS URI: {final_video_gcs_uri}")
    
    # --- 5. UPLOAD THE PROMPT FILE ---
    try:
        print(f"Uploading prompt file to match video...")
        storage_client = storage.Client()
        gcs_bucket = storage_client.bucket(bucket_name)
        
        video_filename = Path(final_video_gcs_uri).name
        # Create a .prompt.txt file with the same name as the video
        prompt_filename = video_filename.replace(".mp4", ".prompt.txt")
        prompt_gcs_path = f"{gcs_prefix}{prompt_filename}"
        
        prompt_blob = gcs_bucket.blob(prompt_gcs_path)
        # Upload the "By JohnDoe: ..." message
        prompt_blob.upload_from_string(display_message)
        print(f"  Successfully uploaded prompt file: gs://{bucket_name}/{prompt_gcs_path}")
        
    except Exception as e:
        print(f"  WARNING: Failed to upload prompt file. Error: {e}")
        # Non-critical error, we still want to return the video URI
    
    # 6. Return the video URI
    return final_video_gcs_uri