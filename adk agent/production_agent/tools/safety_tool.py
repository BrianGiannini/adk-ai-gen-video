# safety_tool.py
from google.cloud import language_v2

# Categories that are high-risk
# See all categories here: https://cloud.google.com/natural-language/docs/moderating-text#categories
HIGH_RISK_CATEGORIES = [
    "SEXUAL", "HATE_SPEECH", "HARASSMENT", "DANGEROUS_CONTENT"
]
# Categories that are borderline
BORDERLINE_CATEGORIES = [
    "TOXIC", "DEROGATORY", "VIOLENT", "INSULT", "PROFANITY"
]

def check_prompt_safety(prompt_text: str) -> str:
    """
    Checks prompt text using the Vertex AI Moderation API.
    
    Returns:
        A verdict string: "TOXIC", "BORDERLINE", or "SAFE".
    """
    try:
        client = language_v2.LanguageServiceClient()
        document = language_v2.Document(
            content=prompt_text,
            type_=language_v2.Document.Type.PLAIN_TEXT,
        )
        
        print(f"[Safety Tool] Checking prompt: '{prompt_text[:50]}...'")
        response = client.moderate_text(document=document)
        
        # Check for high-confidence TOXIC content first
        for category in response.moderation_categories:
            if category.name in HIGH_RISK_CATEGORIES and category.confidence > 0.7:
                print(f"[Safety Tool] Verdict: TOXIC (Category: {category.name}, Conf: {category.confidence})")
                return "TOXIC"
                
        # Check for medium-confidence BORDERLINE content
        for category in response.moderation_categories:
            if category.name in BORDERLINE_CATEGORIES and category.confidence > 0.5:
                print(f"[Safety Tool] Verdict: BORDERLINE (Category: {category.name}, Conf: {category.confidence})")
                return "BORDERLINE"

        print("[Safety Tool] Verdict: SAFE")
        return "SAFE"
        
    except Exception as e:
        print(f"[Safety Tool] ERROR: Could not moderate text. Error: {e}")
        # Return a specific error message so the next agent knows the API failed.
        return "SAFETY_API_FAILED"