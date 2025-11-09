#!/bin/bash
# 1. Export your variables

export PROJECT_ID="sanguinax-playground"
export REGION="us-central1"
export VEO_SERVICE_URL="https://production-adk-agent-870622303377.us-central1.run.app"
export FIRESTORE_DATABASE_ID="video-generation-users"

# This uses the $PROJECT_ID to build the service account email
export SERVICE_ACCOUNT_EMAIL="streamerbot-invoker@$PROJECT_ID.iam.gserviceaccount.com"

# A variable for the container image name
export IMAGE_TAG="gcr.io/$PROJECT_ID/admin-website"


# 2. Submit the build (uses $PROJECT_ID and $IMAGE_TAG)
echo "--- Building container... ---"
gcloud builds submit \
    --project $PROJECT_ID \
    --tag $IMAGE_TAG

# 3. Deploy to Cloud Run (UPDATED)
# This now uses all your variables and has the correct env var names
echo "--- Deploying to Cloud Run... ---"
gcloud run deploy admin-website \
    --project $PROJECT_ID \
    --image gcr.io/$PROJECT_ID/admin-website:latest \
    --region us-central1 \
    --allow-unauthenticated \
    --service-account streamerbot-invoker@$PROJECT_ID.iam.gserviceaccount.com \
    --set-env-vars "SERVICE_ACCOUNT_EMAIL=$SERVICE_ACCOUNT_EMAIL,VEO_SERVICE_URL=$VEO_SERVICE_URL,FIRESTORE_DATABASE_ID=$FIRESTORE_DATABASE_ID" \
    --memory 512Mi \
    --cpu 1 \
    --max-instances 2 \
    --concurrency 80 \
    --timeout 600s

echo "--- Deployment complete. ---"