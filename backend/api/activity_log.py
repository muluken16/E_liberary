# core/activity_log.py

from collections import deque
from datetime import datetime

# Store only the latest 100 activities in memory
ACTIVITY_LOG = deque(maxlen=100)

def log_activity(user, action, model_name, object_id):
    ACTIVITY_LOG.appendleft({
        "user": user.username if user else "System",
        "action": action.lower(),
        "model": model_name.lower(),
        "object_id": object_id,
        "timestamp": datetime.utcnow().isoformat(),
        "text": f"{action.title()} {model_name.title()} with ID {object_id}"
    })

def get_recent_activities(limit=100):
    return list(ACTIVITY_LOG)[:limit]
