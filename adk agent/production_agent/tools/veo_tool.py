# main.py
import os
import time
import re
# google-cloud-storage is no longer needed here as the API writes directly
# from google.cloud import storage 
from google import genai
from google.genai import types

# --- Environment Variables ---
# GOOGLE_CLOUD_PROJECT, GOOGLE_CLOUD_LOCATION,
# VEO_MODEL_NAME, GCS_BUCKET_NAME are expected to be set in the environment.

def generate_video_and_upload(prompt: str) -> str:
    """Generates a video using Veo on Vertex AI directly into a GCS bucket.

    Args:
        prompt: The text prompt to generate the video from.
    
    Returns:
        The GCS URI of the generated video.
    """
    project_id = os.environ.get("GOOGLE_CLOUD_PROJECT")
    location = os.environ.get("GOOGLE_CLOUD_LOCATION")
    model_name = os.environ.get("VEO_MODEL_NAME")
    bucket_name = os.environ.get("GCS_BUCKET_NAME")

    # Check for all required environment variables
    if not all([project_id, location, model_name, bucket_name]):
        raise EnvironmentError(
            "Missing required environment variables. "
            "Ensure GOOGLE_CLOUD_PROJECT, GOOGLE_CLOUD_LOCATION, "
            "VEO_MODEL_NAME, and GCS_BUCKET_NAME are set."
        )

    # 1. Configure and create the genai client for Vertex AI
    client = genai.Client(
        project=project_id,
        location=location
    )

    # 2. Prepare the GCS output URI
    sanitized_prompt = re.sub(r'\W+', '_', prompt).lower()
    timestamp = int(time.time())
    # Ensure the path ends with a '/' for the API to generate filename(s) within it
    gcs_prefix = f"veo_output/{sanitized_prompt[:50]}_{timestamp}/" 
    output_gcs_uri_prefix = f"gs://{bucket_name}/{gcs_prefix}"
    print(f"Configuring output to GCS prefix: {output_gcs_uri_prefix}")

    # 3. Start the asynchronous video generation job with GCS output config
    print(f"Starting video generation job for: '{prompt}'")
    operation = client.models.generate_videos(
        model=model_name,
        prompt=prompt,
        config=types.GenerateVideosConfig(
            # Tell the API to write the output directly to GCS
            output_gcs_uri=output_gcs_uri_prefix, 
            # You can still set other params like aspect_ratio or duration here
            # aspect_ratio="16:9", 
            # duration=8,
        )
    )

    # 4. Poll the operation until it's complete
    print(f"Waiting for operation {operation.name} to complete...")
    while not operation.done:
        print("  Polling... (checking status)")
        time.sleep(10)  # Wait 10 seconds before polling again
        # The operation object re-fetches its state
        operation = client.operations.get(operation)

    # 5. Access the response.
    # If the operation failed, accessing .response will raise an exception.
    print("Operation finished. Accessing response...")
    
    # The response object is technically operation.result when using output_gcs_uri
    # It contains the URIs of the generated videos in GCS
    # We access .result instead of .response when using GCS output
    if not operation.result or not operation.result.generated_videos:
         # Handle cases where the result might be empty even if done (e.g., safety filters)
         # Accessing operation.response might show error details if operation.result is empty
         error_details = "Unknown error or no videos generated (check safety filters)."
         if hasattr(operation, 'response') and operation.response:
             # Try to get more specific error info if available
             # Note: The exact structure for errors in this SDK operation might vary.
             # This attempts to capture common patterns.
             if hasattr(operation.response, 'error') and operation.response.error:
                 error_details = f"Operation error: {operation.response.error}"
             elif hasattr(operation.response, 'status') and operation.response.status:
                  error_details = f"Operation status: {operation.response.status}"
             elif hasattr(operation.response, 'details') and operation.response.details:
                  error_details = f"Operation details: {operation.response.details}"
         raise Exception(f"Video generation operation completed but no result found. {error_details}")


    # Get the GCS URI from the result object's video attribute
    # Assuming we only care about the first generated video
    final_gcs_uri = operation.result.generated_videos[0].video.uri
    
    print(f"  Successfully retrieved GCS URI: {final_gcs_uri}")

    # 6. No download or upload needed - video is already in GCS.
    # 7. No File API resource to delete.

    return final_gcs_uri

# Example usage (this part won't run in Cloud Run, only locally)
if __name__ == "__main__":
    try:
        # For local testing, ensure env vars are set:
        # export GOOGLE_CLOUD_PROJECT="..."
        # export GOOGLE_CLOUD_LOCATION="..."
        # export VEO_MODEL_NAME="..."
        # export GCS_BUCKET_NAME="..."
        # And ensure you are authenticated:
        # gcloud auth application-default login
        
        gcs_uri = generate_video_and_upload(
            prompt="A majestic cinematic shot of a red panda performing a backflip"
        )
        print(f"\nFinal GCS URI: {gcs_uri}")
    except Exception as e:
        print(f"\nAn error occurred: {e}")

