"""
Firebase Cloud Messaging (push notifications to the Android app), via the
FCM HTTP v1 API - same reasoning as google_play_service.py: a service
account JWT-Bearer OAuth2 flow + plain REST calls (httpx), not worth
pulling in the firebase-admin SDK for one endpoint.

Needs a Firebase service account (Firebase Console -> Project Settings ->
Service accounts -> Generate new private key). Set
FCM_SERVICE_ACCOUNT_JSON to that key file's raw JSON content. Unconfigured
means send_push() is a silent no-op - a push failing to send should never
break whatever triggered it (e.g. publishing a job posting).
"""
import json
import time

import httpx
import jwt

from app.core.config import settings

TOKEN_URL = "https://oauth2.googleapis.com/token"
SCOPE = "https://www.googleapis.com/auth/firebase.messaging"


def configured() -> bool:
    return bool(settings.FCM_SERVICE_ACCOUNT_JSON)


def _access_token() -> str:
    key = json.loads(settings.FCM_SERVICE_ACCOUNT_JSON)
    now = int(time.time())
    assertion = jwt.encode(
        {"iss": key["client_email"], "scope": SCOPE, "aud": TOKEN_URL, "iat": now, "exp": now + 3600},
        key["private_key"],
        algorithm="RS256",
    )
    resp = httpx.post(
        TOKEN_URL,
        data={"grant_type": "urn:ietf:params:oauth:grant-type:jwt-bearer", "assertion": assertion},
        timeout=15,
    )
    resp.raise_for_status()
    return resp.json()["access_token"]


def send_push(device_token: str, title: str, body: str, data: dict[str, str] | None = None) -> bool:
    """Best-effort - logs and swallows any failure (an invalid/expired
    device token, Firebase being down, etc.) rather than raising, since
    nothing calling this should ever fail because a push didn't go out."""
    if not configured():
        return False
    try:
        key = json.loads(settings.FCM_SERVICE_ACCOUNT_JSON)
        token = _access_token()
        resp = httpx.post(
            f"https://fcm.googleapis.com/v1/projects/{key['project_id']}/messages:send",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "message": {
                    "token": device_token,
                    "notification": {"title": title, "body": body},
                    "data": data or {},
                    "android": {"priority": "high"},
                }
            },
            timeout=15,
        )
        return resp.status_code == 200
    except Exception:
        return False
