# production_agent/tools/safety_tool.py
from google.cloud import language_v2
import google.cloud.logging

client = google.cloud.logging.Client()
logger = client.logger("production-adk-agent-safety-tool")

# Our lists are in UPPER_CASE and match the API's output
HIGH_RISK_CATEGORIES = [
    "SEXUAL", 
    "HATE SPEECH", 
    "HARASSMENT", 
    "DANGEROUS CONTENT"
]

BORDERLINE_CATEGORIES = [
    "TOXIC", 
    "DEROGATORY", 
    "VIOLENT", 
    "INSULT", 
    "PROFANITY",
    "RELIGION & BELIEF",
    "WAR & CONFLICT",
    "DEATH, HARM & TRAGEDY",
    "POLITICS"
]

def check_prompt_safety(prompt_text: str) -> str:
    """
    Checks prompt text using the Cloud Natural Language API.
    
    Returns:
        A verdict string: "TOXIC", "BORDERLINE", "SAFE", or "SAFETY_API_FAILED".
    """
    try:
        client = language_v2.LanguageServiceClient()
        document = language_v2.Document(
            content=prompt_text,
            type_=language_v2.Document.Type.PLAIN_TEXT,
        )
        
        logger.log_text(f"[Safety Tool] Checking prompt: '{prompt_text[:50]}...'", severity="INFO")
        response = client.moderate_text(document=document)
        
        # Log the raw protobuf response as a string
        logger.log_text(f"[Safety Tool] RAW API RESPONSE: {response._pb}", severity="INFO")
        
        if not response.moderation_categories:
            logger.log_text("[Safety Tool] WARNING: API returned no categories.", severity="WARNING")
            return "SAFETY_API_FAILED"

        # Pass 1: Check for HIGHLY-CONFIDENT high-risk content
        for category in response.moderation_categories:
            if category.name.upper() in HIGH_RISK_CATEGORIES and category.confidence > 0.3:
                logger.log_text(f"[Safety Tool] Verdict: TOXIC (High-Risk Category: {category.name}, Conf: {category.confidence})", severity="INFO")
                return "TOXIC"
        
        # Pass 2:  Check for HIGHLY-CONFIDENT borderline content
        for category in response.moderation_categories:
            if category.name.upper() in BORDERLINE_CATEGORIES and category.confidence > 0.8:
                logger.log_text(f"[Safety Tool] Verdict: TOXIC (Escalated Borderline: {category.name}, Conf: {category.confidence})", severity="INFO")
                return "TOXIC"

        # Pass 3: Check for LOW-CONFIDENT high-risk content
        for category in response.moderation_categories:
            if category.name.upper() in HIGH_RISK_CATEGORIES and category.confidence > 0.15:
                logger.log_text(f"[Safety Tool] Verdict: BORDERLINE (High-Risk Category: {category.name}, Conf: {category.confidence})", severity="INFO")
                return "BORDERLINE"

        # Pass 4: Check for REGULAR borderline content
        for category in response.moderation_categories:
            if category.name.upper() in BORDERLINE_CATEGORIES and category.confidence > 0.5:
                logger.log_text(f"[Safety Tool] Verdict: BORDERLINE (Category: {category.name}, Conf: {category.confidence})", severity="INFO")
                return "BORDERLINE"

        # Pass 5: If nothing was found, it's SAFE
        logger.log_text("[Safety Tool] Verdict: SAFE", severity="INFO")
        return "SAFE"
        
    except Exception as e:
        logger.log_text(f"[Safety Tool] ERROR: Could not moderate text. Error: {e}", severity="ERROR")
        return "SAFETY_API_FAILED"