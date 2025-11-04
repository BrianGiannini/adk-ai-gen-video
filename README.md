## 🚀 Lab Overview

### Part 1: Understanding the Production Agent (10 minutes)

Let's first explore the agent we'll be deploying:

#### Agent Architecture

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   User Request  │ -> │   ADK Agent     │ -> │  Gemma Backend  │
│                 │    │  (Cloud Run)    │    │ (Cloud Run+GPU) │
└─────────────────┘    └─────────────────┘    └─────────────────┘
                              │
                              v
                       ┌─────────────────┐
                       │ FastAPI Server  │
                       │ Health Checks   │
                       │─────────────────┘
```

#### Key Components

## Prerequisites 

```bash
# Set your Google Cloud project
export PROJECT_ID="your-project-id"
gcloud config set project $PROJECT_ID
gcloud config set run/region us-central1

# Enable APIs
gcloud services enable run.googleapis.com cloudbuild.googleapis.com aiplatform.googleapis.com
```

## Run the Agent Locally

You can run the ADK agent locally for development and testing. The agent needs to know the URL of your Ollama server, which can be configured in two ways:

### 1. Using an environment variable

You can set the `OLLAMA_API_BASE` environment variable when you run the server.

```bash
OLLAMA_API_BASE="<your_ollama_server_url>" python "adk agent/server.py"
```

If this variable is not set, the agent will default to `http://localhost:10010`.

### 2. Using a `.env` file

Alternatively, you can create a `.env` file in the root of the project directory and add the server URL there.

1.  Create a file named `.env` in the project root.
2.  Add the following line to the file:

    ```
    OLLAMA_API_BASE="<your_ollama_server_url>"
    ```

3.  Run the server:

    ```bash
    python "adk agent/server.py"
    ```

The agent will automatically load the URL from the `.env` file.

## Deploy Gemma Backend

```bash
cd hackathon-cloudrun/ollama-backend

gcloud run deploy ollama-gemma3-4b-gpu \
  --source . \
  --concurrency 4 \
  --cpu 8 \
  --set-env-vars OLLAMA_NUM_PARALLEL=4 \
  --gpu 1 \
  --gpu-type nvidia-l4 \
  --max-instances 1 \
  --memory 32Gi \
  --allow-unauthenticated \
  --no-cpu-throttling \
  --no-gpu-zonal-redundancy \
  --timeout=600


## download ollama utility and test the Cloud Run GPU service that is created
curl -fsSL https://ollama.com/install.sh
OLLAMA_HOST=<Cloud Run SERVICE URL generated above> ollama run gemma3:4b
```

## Deploy ADK Cloud Run Agent that calls the Gemma Backend

```bash
# go to the ADK agent directory
cd hackathon-cloudrun/adk-agent

export OLLAMA_URL=$(gcloud run services describe ollama-gemma3-4b-gpu \
  --region us-central1 \
  --format='value(status.url)')

# Create environment file

cat > .env << EOF
GOOGLE_CLOUD_PROJECT=$PROJECT_ID
GOOGLE_CLOUD_LOCATION=us-central1
GEMMA_MODEL_NAME=gemma3:4b
OLLAMA_API_BASE=$OLLAMA_URL
EOF

# Deploy the ADK based AI agent to Cloud Run with ADK webUI 
export PROJECT_ID="sanguinax-playground"

# Build with correct project
gcloud builds submit \
    --project $PROJECT_ID \
    --tag gcr.io/$PROJECT_ID/production-adk-agent

# Deploy
gcloud run deploy production-adk-agent \
    --project sanguinax-playground \
    --image gcr.io/sanguinax-playground/production-adk-agent \
    --region us-central1 \
    --allow-unauthenticated \
    --memory 4Gi \
    --cpu 2 \
    --max-instances 1 \
    --concurrency 50 \
    --timeout 500 \
    --set-env-vars GOOGLE_CLOUD_PROJECT=sanguinax-playground,GOOGLE_CLOUD_LOCATION=us-central1,GEMMA_MODEL_NAME=gemma3:4b,VEO_MODEL_NAME=veo-3.1-fast-generate-preview,OLLAMA_API_BASE=https://ollama-gemma3-4b-gpu-870622303377.us-central1.run.app,GCS_BUCKET_NAME=ai-veo-videos-us
```

## Test Your Agent's health

```bash
# Get service URL
export SERVICE_URL=$(gcloud run services describe production-adk-agent \
    --region=us-central1 \
    --format='value(status.url)')

# Test health endpoint
curl $SERVICE_URL/health

```

## 🎉 Test your Agent with the ADK WebUI

Your production ADK agent is now running on Cloud Run with GPU acceleration!

Interact with your agent by entering the SERVICE_URL above for your production-adk-agent into a new browser tab. You should see the ADK web interface.

  ## Clean up
Follow these steps to delete the resources you created in this lab to avoid incurring further charges.

Examples of how to delete the two Cloud Run services that were deployed in this repo. You can also delete them in the Cloud Run Web Console page. 
Please also remember to delete other Google Cloud resources you may have used. 

```bash
#Delete the ADK agent Cloud Run service:
gcloud run services delete production-adk-agent -region europe-west1
# Delete the Gemma backend Cloud Run service: 
gcloud run services delete ollama-gemma3-4b-gpu --region europe-west1

```
