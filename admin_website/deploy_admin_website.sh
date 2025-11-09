#!/bin/bash
# 1. Export variables

export PROJECT_ID="live-video-generation-tv"
export REGION="us-central1"
export VEO_SERVICE_URL="https://hackathon-adk-agent-362118722455.us-central1.run.app"
export FIRESTORE_DATABASE_ID="video-generation-users"                                                                                                                                                          
export SERVICE_NAME="hackaton-admin-website"

# This uses the $PROJECT_ID to build the service account email                                                                                                                                                 
export SERVICE_ACCOUNT_EMAIL="streamerbot-invoker@$PROJECT_ID.iam.gserviceaccount.com"                                                                                                                         
                                                                                                                                                                                                               
# A variable for the container image name base (without :latest)
export IMAGE_REPOSITORY="gcr.io/$PROJECT_ID/$SERVICE_NAME"                                                                                                                                                            
                                                                                                                                                                                                               
                                                                                                                                                                                                               
# 2. Submit the build (uses $PROJECT_ID and $IMAGE_REPOSITORY)                                                                                                                                                        
echo "--- Building container... ---"                                                                                                                                                                           
gcloud builds submit . --project $PROJECT_ID --tag $IMAGE_REPOSITORY:latest                                                                                                                                                                                      
                                                                                                                                                                                                               
# 3. Deploy to Cloud Run                                                                                                                                                                                       
echo "--- Deploying to Cloud Run... ---"                                                                                                                                                                       
gcloud run deploy $SERVICE_NAME \
    --project $PROJECT_ID \
    --image $IMAGE_REPOSITORY:latest \
    --region $REGION \
    --allow-unauthenticated \
    --service-account streamerbot-invoker@$PROJECT_ID.iam.gserviceaccount.com \
    --set-env-vars "SERVICE_ACCOUNT_EMAIL=$SERVICE_ACCOUNT_EMAIL,VEO_SERVICE_URL=$VEO_SERVICE_URL,FIRESTORE_DATABASE_ID=$FIRESTORE_DATABASE_ID" \
    --memory 512Mi \
    --cpu 1 \
    --max-instances 2 \
    --concurrency 80 \
    --timeout 600s

echo "--- Deployment complete. ---"