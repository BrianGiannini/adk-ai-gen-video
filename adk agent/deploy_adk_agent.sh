#!/bin/bash
# 1. Export variables

export PROJECT_ID="live-video-generation-tv"
export REGION="us-central1"
export GCS_BUCKET_NAME="ai-veo-videos-us-storage"
export VEO_FAST_MODEL="veo-3.1-fast-generate-001"
export VEO_HQ_MODEL="veo-3.1-generate-001"
export PRO_MODEL="gemini-3.1-pro-preview"
export FLASH_MODEL="gemini-3.8-flash"                                                                                                                                                                          
export SERVICE_NAME="hackathon-adk-agent"

# Spending safeguards (enforced before every Veo call, see usage_guard.py)
export VIDEO_GENERATION_ENABLED="false"  # kill switch: "true" to allow videos, "false" blocks them all
export DAILY_VIDEO_LIMIT="10"            # max videos per UTC day, all users and callers combined
export VIDEO_DURATION_SECONDS="8"        # Veo bills per second of video: 4, 6 or 8
export FIRESTORE_DATABASE_ID="video-generation-users"


# A variable for the container image name                                                                                                                                                                      
export IMAGE_TAG="gcr.io/$PROJECT_ID/$SERVICE_NAME"                                                                                                                                                      
                                                                                                                                                                                                               
                                                                                                                                                                                                               
# 2. Submit the build (uses $PROJECT_ID and $IMAGE_TAG)                                                                                                                                                        
echo "--- Building container... ---"                                                                                                                                                                           
gcloud builds submit \                                                                                                                                                                                         
    --project $PROJECT_ID \                                                                                                                                                                                    
    --tag $IMAGE_TAG                                                                                                                                                                                           
                                                                                                                                                                                                               
# 3. Deploy to Cloud Run                                                                                                                                                                                   
echo "--- Deploying to Cloud Run... ---"                                                                                                                                                                       
gcloud run deploy $SERVICE_NAME \
    --project $PROJECT_ID \
    --image $IMAGE_TAG \
    --region $REGION \
    --no-allow-unauthenticated \
    --memory 4Gi \
    --cpu 2 \
    --max-instances 1 \
    --concurrency 50 \
    --timeout 500 \
    --set-env-vars="GOOGLE_CLOUD_PROJECT=$PROJECT_ID,GOOGLE_CLOUD_LOCATION=global,VEO_LOCATION=$REGION,GCS_BUCKET_NAME=$GCS_BUCKET_NAME,VEO_FAST_MODEL=$VEO_FAST_MODEL,VEO_HQ_MODEL=$VEO_HQ_MODEL,PRO_MODEL=$PRO_MODEL,FLASH_MODEL=$FLASH_MODEL,VIDEO_GENERATION_ENABLED=$VIDEO_GENERATION_ENABLED,DAILY_VIDEO_LIMIT=$DAILY_VIDEO_LIMIT,VIDEO_DURATION_SECONDS=$VIDEO_DURATION_SECONDS,FIRESTORE_DATABASE_ID=$FIRESTORE_DATABASE_ID"

echo "--- Deployment complete. ---"
