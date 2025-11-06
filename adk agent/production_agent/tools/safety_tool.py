# production_agent/tools/safety_tool.py
from google.cloud import language_v2

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
        
        print(f"[Safety Tool] Checking prompt: '{prompt_text[:50]}...'")
        response = client.moderate_text(document=document)
        
        print(f"[Safety Tool] RAW API RESPONSE: {response}")
        
        if not response.moderation_categories:
            print("[Safety Tool] WARNING: API returned no categories.")
            return "SAFETY_API_FAILED"

        # Pass 1: Check for HIGHLY-CONFIDENT high-risk content
        for category in response.moderation_categories:
            if category.name.upper() in HIGH_RISK_CATEGORIES and category.confidence > 0.3:
                print(f"[Safety Tool] Verdict: TOXIC (High-Risk Category: {category.name}, Conf: {category.confidence})")
                return "TOXIC"
        
        # Pass 2:  Check for HIGHLY-CONFIDENT borderline content
        # (Your rule: > 0.8 on 'TOXIC', 'VIOLENT', etc. should be banned)
        for category in response.moderation_categories:
            if category.name.upper() in BORDERLINE_CATEGORIES and category.confidence > 0.8:
                print(f"[Safety Tool] Verdict: TOXIC (Escalated Borderline: {category.name}, Conf: {category.confidence})")
                return "TOXIC"

        # Pass 3: Check for LOW-CONFIDENT high-risk content
        for category in response.moderation_categories:
            if category.name.upper() in HIGH_RISK_CATEGORIES and category.confidence > 0.15:
                print(f"[Safety Tool] Verdict: BORDERLINE (High-Risk Category: {category.name}, Conf: {category.confidence})")
                return "BORDERLINE"

        # Pass 4: Check for REGULAR borderline content
        for category in response.moderation_categories:
            if category.name.upper() in BORDERLINE_CATEGORIES and category.confidence > 0.5:
                print(f"[Safety Tool] Verdict: BORDERLINE (Category: {category.name}, Conf: {category.confidence})")
                return "BORDERLINE"

        # Pass 5: If nothing was found, it's SAFE
        print("[Safety Tool] Verdict: SAFE")
        return "SAFE"
        
    except Exception as e:
        print(f"[Safety Tool] ERROR: Could not moderate text. Error: {e}")
        return "SAFETY_API_FAILED"