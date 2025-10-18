import os
from pathlib import Path
from dotenv import load_dotenv
from google.cloud import aiplatform

# Load environment variables from .env file in root directory
root_dir = Path(__file__).parent.parent
dotenv_path = root_dir / ".env"
print(f"Attempting to load .env file from: {dotenv_path}")
load_dotenv(dotenv_path=dotenv_path)

def list_available_models():
    """Lists the available models in the project and location."""
    project_id = "adk-video-gen"
    location = "us-central1"

    print(f"Listing models for project: {project_id} in location: {location}")

    aiplatform.init(project=project_id, location=location)

    models = aiplatform.Model.list()

    if not models:
        print("No models found in this project and region.")
    else:
        for model in models:
            print(f"Model Display Name: {model.display_name}, Model ID: {model.name}")

if __name__ == "__main__":
    list_available_models()