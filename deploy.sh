#!/bin/bash
# 1. Export your variables

export PROJECT_ID="sanguinax-playground"
export REGION="us-central1"
export GCS_BUCKET_NAME="ai-veo-videos-us"
export VEO_FAST_MODEL="veo-3.1-fast-generate-preview"
export VEO_HQ_MODEL="veo-3.1-generate-preview"
export PRO_MODEL="gemini-2.5-pro"
export FLASH_MODEL="gemini-2.5-flash"

# A variable for the container image name
export IMAGE_TAG="gcr.io/$PROJECT_ID/production-adk-agent"


# 2. Submit the build (uses $PROJECT_ID and $IMAGE_TAG)
echo "--- Building container... ---"
gcloud builds submit \
    --project $PROJECT_ID \
    --tag $IMAGE_TAG

# 3. Deploy to Cloud Run (UPDATED)
# This now uses all your variables and has the correct env var names
echo "--- Deploying to Cloud Run... ---"
gcloud run deploy production-adk-agent \
    --project $PROJECT_ID \
    --image $IMAGE_TAG \
    --region $REGION \
    --allow-unauthenticated \
    --memory 4Gi \
    --cpu 2 \
    --max-instances 1 \
    --concurrency 50 \
    --timeout 500 \
    --set-env-vars="GOOGLE_CLOUD_PROJECT=$PROJECT_ID,GOOGLE_CLOUD_LOCATION=$REGION,GCS_BUCKET_NAME=$GCS_BUCKET_NAME,VEO_FAST_MODEL=$VEO_FAST_MODEL,VEO_HQ_MODEL=$VEO_HQ_MODEL,PRO_MODEL=$PRO_MODEL,FLASH_MODEL=$FLASH_MODEL"

echo "--- Deployment complete. ---"