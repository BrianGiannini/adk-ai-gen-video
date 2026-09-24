# usage_guard.py
# Hard spending limits, checked *before* any paid Veo call.
# Budget alerts arrive hours late, so these are the real protection.
import os
import datetime
from google.cloud import firestore
import google.cloud.logging

client = google.cloud.logging.Client()
logger = client.logger("production-adk-agent-usage-guard")

# --- Environment Variables ---
# VIDEO_GENERATION_ENABLED: kill switch, anything other than "true" blocks all videos.
# DAILY_VIDEO_LIMIT: max videos per UTC day, across all users and all callers.
# FIRESTORE_DATABASE_ID: database holding the daily counters.
DAILY_VIDEO_LIMIT = int(os.getenv("DAILY_VIDEO_LIMIT", "10"))

_db = None
# Invocations that already got a video: stops an LLM loop from paying for several.
_invocations_with_video = set()


def _get_db():
    global _db
    if _db is None:
        _db = firestore.Client(database=os.getenv("FIRESTORE_DATABASE_ID", "(default)"))
    return _db


@firestore.transactional
def _increment_if_below_limit(transaction, counter_ref) -> bool:
    snapshot = counter_ref.get(transaction=transaction)
    count = snapshot.get("count") if snapshot.exists else 0
    if count >= DAILY_VIDEO_LIMIT:
        return False
    transaction.set(counter_ref, {"count": count + 1, "updated_at": firestore.SERVER_TIMESTAMP})
    return True


def reserve_video_slot(invocation_id: str) -> str | None:
    """
    Reserves one video from today's budget.

    Returns:
        None if the video may be generated, otherwise the reason it was refused.
        Fails closed: if the counter can't be checked, the video is refused.
    """
    if os.getenv("VIDEO_GENERATION_ENABLED", "true").lower() != "true":
        return "video generation is disabled (VIDEO_GENERATION_ENABLED)."

    if invocation_id in _invocations_with_video:
        return "a video was already generated for this request."

    today = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%d")
    try:
        db = _get_db()
        counter_ref = db.collection("video_usage").document(today)
        if not _increment_if_below_limit(db.transaction(), counter_ref):
            return f"daily limit of {DAILY_VIDEO_LIMIT} videos reached."
    except Exception as e:
        logger.log_text(f"[Usage Guard] Could not check daily limit, refusing: {e}", severity="ERROR")
        return "usage limit could not be verified."

    _invocations_with_video.add(invocation_id)
    logger.log_text(f"[Usage Guard] Slot reserved for {today} (limit {DAILY_VIDEO_LIMIT}).", severity="INFO")
    return None
