# mock_veo_tool.py
import time
import re
import google.cloud.logging
client = google.cloud.logging.Client()
logger = client.logger("production-adk-agent-veo-tool")

def generate_video_and_prompt_file(final_prompt: str, display_message: str, quality: str) -> str:
    """
    MOCK/SIMULATED version of the Veo tool.
    
    - It does NOT generate a video or call any Google APIs.
    - It returns a fake GCS URI almost instantly.
    - If the prompt contains the word "FAIL", it simulates a failure.
    """
    
    logger.log_text("\n" + "="*30, severity="INFO")
    logger.log_text("--- MOCK VEO TOOL (SIMULATION) ---", severity="INFO")
    logger.log_text(f"  [MOCK] Received Final Prompt: {final_prompt}", severity="INFO")
    logger.log_text(f"  [MOCK] Received Display Message: {display_message}", severity="INFO")
    logger.log_text(f"  [MOCK] Received Quality: {quality}", severity="INFO")

    # --- Simulation Logic ---
    # Check for the magic "FAIL" keyword to test error paths
    if "FAIL" in final_prompt.upper():
        logger.log_text("  [MOCK] Detected 'FAIL' in prompt. Simulating a generation error.", severity="INFO")
        logger.log_text("="*30 + "\n", severity="INFO")
        
        # This error string MUST match what the real tool returns
        # and what the 'video_worker_agent' expects in Phase 2
        return "Video generation failed: Mock error triggered by 'FAIL' keyword."

    # If not failing, simulate a short "generation" time
    logger.log_text("  [MOCK] Simulating video generation (taking 2 seconds)...", severity="INFO")
    time.sleep(2) # To feel like it's "doing" something

    # Create a fake, believable GCS URI
    sanitized_prompt = re.sub(r'\W+', '_', final_prompt).lower()
    timestamp = int(time.time())
    
    fake_gcs_path = f"gs://MOCK_BUCKET/veo_output/{sanitized_prompt[:50]}_{timestamp}/mock_video.mp4"
    
    logger.log_text(f"  [MOCK] Simulation complete. Returning fake URI: {fake_gcs_path}", severity="INFO")
    logger.log_text(f"  [MOCK] It *would* have uploaded '{display_message}' to a .prompt.txt file.", severity="INFO")
    logger.log_text("="*30 + "\n", severity="INFO")

    return fake_gcs_path