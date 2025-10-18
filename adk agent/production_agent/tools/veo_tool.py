
import os
import time
import vertexai
from vertexai.preview.generative_models import GenerativeModel
from google.cloud import storage
import re

def generate_video_and_upload(prompt: str) -> str:
    """Generates a video using Vertex AI and uploads it to a GCS bucket.

    Args:
        prompt: The text prompt to generate the video from.
    
    Returns:
        The GCS URI of the uploaded video.
    """
    project_id = os.environ.get("GOOGLE_CLOUD_PROJECT")
    location = os.environ.get("GOOGLE_CLOUD_LOCATION")
    model_name = os.environ.get("VEO_MODEL_NAME")
    bucket_name = "ai-veo-videos"

    # Generate a unique blob name
    sanitized_prompt = re.sub(r'\W+', '_', prompt).lower()
    timestamp = int(time.time())
    destination_blob_name = f"{sanitized_prompt[:50]}_{timestamp}.mp4"

    vertexai.init(project=project_id, location=location)

    model = GenerativeModel(model_name)

    # Generate the video
    print("Generating video...")
    response = model.generate_content(prompt)
    
    # Assuming the first part of the response is the video
    video_part = response.parts[0]
    # Assuming the video is in the content_bytes
    video_bytes = video_part._raw_part.inline_data.data

    # Upload the video to GCS
    print(f"Uploading video to gs://{bucket_name}/{destination_blob_name}...")
    storage_client = storage.Client()
    bucket = storage_client.bucket(bucket_name)
    blob = bucket.blob(destination_blob_name)

    blob.upload_from_string(video_bytes, content_type='video/mp4')

    print("Video uploaded successfully.")
    
    return f"gs://{bucket_name}/{destination_blob_name}"
