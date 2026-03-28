from datetime import datetime, timedelta

PENDING_EXPIRE_MINUTES = 10
_pending_submissions = {}


def set_pending(openid: str, data: dict):
    _pending_submissions[openid] = {
        **data,
        "created_at": datetime.now(),
    }


def get_pending(openid: str):
    item = _pending_submissions.get(openid)
    if not item:
        return None

    created_at = item["created_at"]
    if datetime.now() - created_at > timedelta(minutes=PENDING_EXPIRE_MINUTES):
        _pending_submissions.pop(openid, None)
        return None

    return item


def clear_pending(openid: str):
    _pending_submissions.pop(openid, None)