## 🚀 Lab Overview

### Part 1: Understanding the Production Agent (10 minutes)

Let's first explore the agent we'll be deploying:

#### Agent Architecture

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│ Stream Donation │ -> │    Streambot    │ -> │   ADK Agent     │ -> │  Gemini API     │
│                 │    │                 │    │  (Cloud Run)    │    │                 │
└─────────────────┘    └─────────────────┘    └─────────────────┘    └─────────────────┘

┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   User Request  │ -> │  Admin Website  │ -> │   ADK Agent     │ -> │  Gemini API     │
│                 │    │  (Cloud Run)    │    │  (Cloud Run)    │    │                 │
└─────────────────┘    └─────────────────┘    └─────────────────┘    └─────────────────┘
```

#### Key Components

## Prerequisites

```bash
# Authenticate with Google Cloud
gcloud auth login

# Set your Google Cloud project
export PROJECT_ID="your-project-id"
gcloud config set project $PROJECT_ID
gcloud config set run/region us-central1

# Enable APIs
gcloud services enable run.googleapis.com cloudbuild.googleapis.com aiplatform.googleapis.com
```

## Run the Agent Locally

You can run the ADK agent locally for development and testing. The agent uses Google Cloud services and needs to be configured with the correct project and model information.

### 1. Using a `.env` file

Create a `.env` file in the `adk agent` directory and add the following variables:

```
GOOGLE_CLOUD_PROJECT="your-project-id"
GOOGLE_CLOUD_LOCATION="global"
VEO_LOCATION="us-central1"
PRO_MODEL="gemini-3.1-pro-preview"
FLASH_MODEL="gemini-3.8-flash"
VEO_FAST_MODEL="veo-3.1-fast-generate-001"
VEO_HQ_MODEL="veo-3.1-generate-001"
GCS_BUCKET_NAME="your-gcs-bucket-name"
```

### 2. Run the server

```bash
python "adk agent/server.py"
```

The agent will automatically load the environment variables from the `.env` file.

### Test Local Agent API Endpoints

```bash
curl -X POST http://127.0.0.1:8080/apps/production_agent/users/local_test_user/sessions/session-12345 \
-H "Content-Type: application/json" \
-d '{}'

curl -X POST http://172.17.0.1:8080/run \
-H "Content-Type: application/json" \
-d '{
    "app_name": "production_agent",
    "user_id": "local_test_user",
    "session_id": "session-12345",
    "new_message": {
        "parts": [
            {
                "text": "{\"prompt\": \"A test prompt from curl\", \"user\": \"curl_user\", \"quality\": \"normal\"}"
            }
        ],
        "role": "user"
    }
}'
```

## Deploy ADK Cloud Run Agent

```bash
# go to the ADK agent directory
cd "adk agent"

# run the deployment script
./deploy_adk_agent.sh
```

## Test Your Agent's health (need to upload your agent in allow unauthenticated)

```bash
# Get service URL                                                                                                                                                                                              
export ADK_AGENT_SERVICE_NAME="hackathon-adk-agent"
export SERVICE_URL=$(gcloud run services describe $ADK_AGENT_SERVICE_NAME \
    --region=us-central1 \
    --format='value(status.url)')
# Test health endpoint
curl $SERVICE_URL/health
```

## 🎉 Test your Agent with the ADK WebUI

Your production ADK agent is now running on Cloud Run!

Interact with your agent by entering the SERVICE_URL above for your $ADK_AGENT_SERVICE_NAME into a new browser tab. You should see the ADK web interface.

## Admin Website

The admin website provides a simple interface to view the generated videos.

### Run the Admin Website Locally

```bash
# Go to the admin_website directory
cd admin_website

# Install dependencies
pip install -r requirements.txt

# Set the Flask app
export FLASK_APP=server.py

# Run the server
flask run
```

### Deploy the Admin Website


This will deploy the admin website as a private service.

```bash
# Go to the admin_website directory
cd admin_website

# run the deployment script
./deploy_admin_website.sh
```

  ## Clean up
Follow these steps to delete the resources you created in this lab to avoid incurring further charges.

```bash
#Delete the ADK agent Cloud Run service:                                                                                                                                                                       
gcloud run services delete $ADK_AGENT_SERVICE_NAME --region us-central1```
