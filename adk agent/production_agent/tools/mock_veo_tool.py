# mock_veo_tool.py
import time
import re

def generate_video_and_prompt_file(final_prompt: str, display_message: str, quality: str) -> str:
    """
    MOCK/SIMULATED version of the Veo tool.
    
    - It does NOT generate a video or call any Google APIs.
    - It returns a fake GCS URI almost instantly.
    - If the prompt contains the word "FAIL", it simulates a failure.
    """
    
    print("\n" + "="*30)
    print("--- MOCK VEO TOOL (SIMULATION) ---")
    print(f"  [MOCK] Received Final Prompt: {final_prompt}")
    print(f"  [MOCK] Received Display Message: {display_message}")
    print(f"  [MOCK] Received Quality: {quality}")

    # --- Simulation Logic ---
    # Check for the magic "FAIL" keyword to test error paths
    if "FAIL" in final_prompt.upper():
        print("  [MOCK] Detected 'FAIL' in prompt. Simulating a generation error.")
        print("="*30 + "\n")
        
        # This error string MUST match what the real tool returns
        # and what the 'video_worker_agent' expects in Phase 2
        return "Video generation failed: Mock error triggered by 'FAIL' keyword."

    # If not failing, simulate a short "generation" time
    print("  [MOCK] Simulating video generation (taking 2 seconds)...")
    time.sleep(2) # To feel like it's "doing" something

    # Create a fake, believable GCS URI
    sanitized_prompt = re.sub(r'\W+', '_', final_prompt).lower()
    timestamp = int(time.time())
    
    fake_gcs_path = f"gs://MOCK_BUCKET/veo_output/{sanitized_prompt[:50]}_{timestamp}/mock_video.mp4"
    
    print(f"  [MOCK] Simulation complete. Returning fake URI: {fake_gcs_path}")
    print(f"  [MOCK] It *would* have uploaded '{display_message}' to a .prompt.txt file.")
    print("="*30 + "\n")

    return fake_gcs_path