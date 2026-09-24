import os
import datetime
from fastapi import FastAPI, Request, Response
from fastapi.responses import FileResponse, JSONResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel
import google.auth
from google.cloud import firestore
from google.cloud import storage
import google.auth.transport.requests
from google.oauth2 import id_token
import httpx
from fastapi.staticfiles import StaticFiles
import json 
import asyncio
from google.auth.transport.requests import Request as GAuthRequest
from google.auth import impersonated_credentials


HARDCODED_APP_VERSION = "v2.2 hackathon verrsion"

VEO_SERVICE_URL_FROM_ENV = os.environ.get("VEO_SERVICE_URL")
DATABASE_ID = os.environ.get("FIRESTORE_DATABASE_ID")

SERVICE_ACCOUNT_EMAIL = os.environ.get("SERVICE_ACCOUNT_EMAIL")


# Clean the URL to be robust
if VEO_SERVICE_URL_FROM_ENV:
    BASE_VEO_URL = VEO_SERVICE_URL_FROM_ENV.replace("/run", "")
    RUN_VEO_URL = f"{BASE_VEO_URL}/run"
else:
    BASE_VEO_URL = None
    RUN_VEO_URL = None


# Initialize FastAPI and templates
app = FastAPI()

# This will print to your Cloud Run logs as soon as the container starts
print(f"\n" + "="*50)
print(f"🚀 ADMIN WEBSITE SERVER IS STARTING")
print(f"🚀 VERSION: {HARDCODED_APP_VERSION}")
if SERVICE_ACCOUNT_EMAIL:
    print(f"🚀 Signing URLs as: {SERVICE_ACCOUNT_EMAIL}")
else:
    print(f"🔥 WARNING: SERVICE_ACCOUNT_EMAIL env var is NOT SET.")
print(f"="*50 + "\n")

templates = Jinja2Templates(directory="templates")

app.mount("/static", StaticFiles(directory="static"), name="static")


# Initialize Google clients
db = firestore.Client(database=DATABASE_ID)
storage_client = storage.Client()
http_client = httpx.AsyncClient()


# --- Models for receiving data ---

class AccessRequest(BaseModel):
    email: str

class PromptRequest(BaseModel):
    prompt: str

class StatusRequest(BaseModel):
    idToken: str


# --- Helper to Reserve a Generation Atomically ---
# Counting *before* the call (in a transaction) stops parallel requests
# from all passing the limit check while earlier videos are still generating.
@firestore.transactional
def reserve_generation(transaction, user_doc_ref) -> bool:
    user_data = user_doc_ref.get(transaction=transaction).to_dict() or {}
    if user_data.get("generation_count", 0) >= user_data.get("max_uses", 3):
        return False
    transaction.update(user_doc_ref, {"generation_count": firestore.Increment(1)})
    return True


# --- Helper Function to Verify Google ID Token ---

async def verify_google_token(token: str) -> dict | None:
    """Verifies a Google ID token and returns the user's info."""
    try:
        request = google.auth.transport.requests.Request()
        token_info = id_token.verify_oauth2_token(token, request)
        return token_info
    except Exception as e:
        print(f"Token verification failed: {e}")
        return None

# --- 1. Frontend Endpoints (Serving the Website) ---

@app.get("/")
async def get_homepage(request: Request):
    """Serves the main index.html file."""
    return templates.TemplateResponse("index.html", {"request": request})

# --- 2. Authentication & User Management Endpoints ---

@app.post("/request-access")
async def request_access(request: AccessRequest):
    """Handles a new user submitting their email for invite."""
    try:
        email = request.email.lower().strip()
        user_ref = db.collection("users").where("email", "==", email).limit(1).get()

        if len(user_ref) > 0:
            return JSONResponse({"status": "error", "message": "This email is already in the system."})

        # Create new user document
        new_user = {
            "email": email,
            "status": "pending",
            "requested_at": datetime.datetime.now(datetime.timezone.utc),
            "generation_count": 0,
            "max_uses": 3
        }
        db.collection("users").add(new_user)
        
        return JSONResponse({"status": "success", "message": "Access requested! To get approved, please send an email to brian.giann@gmail.com"})

    except Exception as e:
        return JSONResponse({"status": "error", "message": str(e)}, status_code=500)


@app.post("/check-status")
async def check_status(request: StatusRequest):
    """Checks if a signed-in user is approved, pending, or not found."""
    token_info = await verify_google_token(request.idToken)
    if not token_info:
        return JSONResponse({"status": "error", "message": "Invalid token."}, status_code=401)

    email = token_info.get("email")
    user_docs = db.collection("users").where("email", "==", email).limit(1).get()

    if not user_docs:
        return JSONResponse({"status": "not_found"})

    user_data = user_docs[0].to_dict()
    return JSONResponse({"status": user_data.get("status")})


# --- 3. The Core Video Generation Endpoint ---

@app.post("/submit-prompt")
async def submit_prompt(request: Request, prompt_data: PromptRequest):
    """
    The main, secure endpoint that:
    1. Verifies the user's Google ID Token.
    2. Checks their status and 3-time-limit.
    3. Calls the Veo Service (Cloud Run #1).
    4. Generates a Signed URL for the video.
    """
    
    print(f"--- /submit-prompt initiated (Version: {HARDCODED_APP_VERSION}) ---")
    
    # Initialize gcs_path to fix UnboundLocalError
    gcs_path = "" 
    
    # 1. Verify the Google ID Token
    try:
        auth_header = request.headers.get("Authorization")
        if not auth_header or not auth_header.startswith("Bearer "):
            print("ERROR: Missing Authorization header")
            return JSONResponse({"error": "Missing or invalid Authorization header"}, status_code=401)
        
        token = auth_header.split("Bearer ")[1]
        token_info = await verify_google_token(token)
        
        if not token_info:
            print("ERROR: Invalid Google ID Token")
            return JSONResponse({"error": "Invalid Google ID Token"}, status_code=401)
        
        email = token_info.get("email")
        user_id = token_info.get("sub") 
        print(f"Token verified for user: {email}")

    except Exception as e:
        print(f"ERROR during token verification: {e}")
        return JSONResponse({"error": f"Token verification failed: {e}"}, status_code=500)

    # 2. Check User Status and Limit
    try:
        user_docs = list(db.collection("users").where("email", "==", email).limit(1).get())

        if not user_docs:
            print(f"ERROR: User not found in invite list: {email}")
            return JSONResponse({"error": "User not found in invite list."}, status_code=403)
        
        user_doc_ref = user_docs[0].reference
        user_data = user_docs[0].to_dict()

        if user_data.get("status") != "approved":
            print(f"ERROR: User not approved: {email}")
            return JSONResponse({"error": "Your account is not yet approved."}, status_code=403)

        if not reserve_generation(db.transaction(), user_doc_ref):
            print(f"ERROR: User has no generations left: {email}")
            return JSONResponse({"error": "You have used all your generations."}, status_code=429)
        
        print(f"User {email} authorized. Generation reserved (count before: {user_data.get('generation_count', 0)})")
    
    except Exception as e:
        print(f"ERROR during Firestore check: {e}")
        return JSONResponse({"error": f"Database check failed: {e}"}, status_code=500)


    if not RUN_VEO_URL:
        print("ERROR: VEO_SERVICE_URL is not configured on server.")
        return JSONResponse({"error": "Backend Veo service is not configured."}, status_code=500)
        
    if not SERVICE_ACCOUNT_EMAIL:
        print("ERROR: SERVICE_ACCOUNT_EMAIL is not configured on server.")
        return JSONResponse({"error": "Backend signing service is not configured."}, status_code=500)

    # 3. Call the Veo Service (Cloud Run #1)
    try:
        auth_req = google.auth.transport.requests.Request()
        audience = BASE_VEO_URL 
        service_token = google.oauth2.id_token.fetch_id_token(auth_req, audience)
        print("Successfully fetched service-to-service auth token.")
        
    except Exception as e:
        print(f"ERROR: Could not get service account token: {e}")
        return JSONResponse({"error": f"Could not get service account token: {e}"}, status_code=500)


    # Build the payloads
    inner_payload = {
        "prompt": prompt_data.prompt,
        "user": email, 
        "quality": "fast",
        "context": "admin"
    }
    inner_payload_string = json.dumps(inner_payload)

    # The app_name is the Python path to the file: "production_agent.agent"
    app_name = "production_agent.agent" 
    
    session_id = str(user_id) 
    
    veo_payload = {
        "app_name": app_name, 
        "user_id": user_id,
        "session_id": session_id,
        "new_message": {
            "parts": [
                {"text": inner_payload_string}
            ],
            "role": "user"
        }
    }
    
    headers = {
        "Authorization": f"Bearer {service_token}",
        "Content-Type": "application/json"
    }

    MAX_RETRIES = 3
    RETRY_DELAY_SECONDS = 5
    SESSION_TIMEOUT_SECONDS = 30 

    try:
        # --- PRE-WARM / SESSION CREATE CALL (with retry) ---
        session_created = False
        print(f"Attempting to create session / pre-warm agent...")
        session_create_url = f"{BASE_VEO_URL}/apps/{app_name}/users/{user_id}/sessions/{session_id}"
        
        for attempt in range(MAX_RETRIES):
            try:
                print(f"  Attempt {attempt + 1} of {MAX_RETRIES}...")
                await http_client.post(
                    session_create_url, 
                    headers=headers, 
                    json={}, 
                    timeout=SESSION_TIMEOUT_SECONDS
                )
                session_created = True
                print(f"  Session created successfully (agent is warm).")
                break # Exit loop on success
            except httpx.ReadTimeout:
                print(f"  Attempt {attempt + 1} timed out (cold start).")
                if attempt < MAX_RETRIES - 1:
                    await asyncio.sleep(RETRY_DELAY_SECONDS)
            except Exception as e:
                print(f"  Attempt {attempt + 1} failed: {e}")
                if attempt < MAX_RETRIES - 1:
                    await asyncio.sleep(RETRY_DELAY_SECONDS)
        
        if not session_created:
            print("ERROR: Failed to create session after all retries.")
            return JSONResponse({"error": "Failed to wake up the generation service. Please try again in a moment."}, status_code=504) # 504 Gateway Timeout
        
        # --- /RUN CALL (VIDEO GENERATION) ---
        print(f"Calling Veo service at: {RUN_VEO_URL}")
        response = await http_client.post(
            RUN_VEO_URL, 
            headers=headers, 
            json=veo_payload, 
            timeout=600.0 # Long timeout for video gen
        )
        
        response.raise_for_status() 
        print(f"Veo service responded with status: {response.status_code}")
        
    except httpx.HTTPStatusError as e:
        print(f"ERROR: Veo service returned an error: {e.response.text}")
        return JSONResponse({"error": f"Failed to call Veo service: {e.response.text}"}, status_code=502)
    except Exception as e:
        print(f"ERROR: Exception while calling Veo service: {e}")
        return JSONResponse({"error": f"Error calling Veo service: {e}"}, status_code=500)


    # 4. Create a Signed URL for the Video
    try:
        veo_response_data_list = response.json()
        print(f"Received full response list from Veo service. Count: {len(veo_response_data_list)}")

        final_agent_message = veo_response_data_list[-1] 
        print(f"Final agent message: {final_agent_message}")

        # The text is nested inside the 'content' key
        gcs_uri_text = final_agent_message["content"]["parts"][0]["text"]
        
        print(f"Extracted GCS URI text: {gcs_uri_text}")

        # Check if the agent returned a failure message instead of a GCS path
        if "Video generation failed" in gcs_uri_text or "Task Failed" in gcs_uri_text:
            print(f"ERROR: The ADK agent reported a failure: {gcs_uri_text}")
            return JSONResponse({"error": gcs_uri_text}, status_code=500)

        # Check for the expected "gs://" prefix
        if "gs://" not in gcs_uri_text:
            print(f"ERROR: Final message was not a GCS path: {gcs_uri_text}")
            return JSONResponse({"error": f"Agent returned an unexpected final message: {gcs_uri_text}"}, status_code=500)
            
        # If we get here, it's a success, so parse the path
        gcs_path = "gs://" + gcs_uri_text.split("gs://")[1]
        print(f"Parsed GCS path: {gcs_path}")

        bucket_name = gcs_path.split("/")[2]
        blob_name = "/".join(gcs_path.split("/")[3:])
        
        bucket = storage_client.bucket(bucket_name)
        blob = bucket.blob(blob_name)
        
        
        # 1. Get the ambient (source) credentials from Cloud Run
        source_credentials, project = google.auth.default(
            scopes=["https://www.googleapis.com/auth/iam"]
        )
        
        # 2. Create new "impersonated" credentials.
        signing_credentials = impersonated_credentials.Credentials(
            source_credentials=source_credentials,
            target_principal=SERVICE_ACCOUNT_EMAIL,
            target_scopes=["https://www.googleapis.com/auth/devstorage.read_only"],
            lifetime=300 # 5 minutes
        )
        
        # 3. Refresh the credentials to get an access token
        signing_credentials.refresh(GAuthRequest())

        # 4. Set the download filename
        download_filename = "generated_video.mp4"
        
        # 5. Pass credentials AND the response_disposition to force download
        signed_url = blob.generate_signed_url(
            version="v4",
            expiration=datetime.timedelta(minutes=10),
            method="GET",
            credentials=signing_credentials,
            response_disposition=f'attachment; filename="{download_filename}"'
        )
        
        print(f"Successfully created signed URL: {signed_url}")
        
        # 6. Send the Signed URL back to the user's browser
        return JSONResponse({
            "status": "success",
            "video_url": signed_url
        })
        
    except Exception as e:
        print(f"ERROR: Failed to create signed URL or parse response: {e}")
        # Updated error message to not use gcs_path if it's not defined
        error_message = f"Failed to create signed URL or parse response: {e}."
        if gcs_path:
             error_message += f" Raw GCS path was: {gcs_path}"
        return JSONResponse({"error": error_message}, status_code=500)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8080)