"""
Google Play Billing purchase verification, via plain REST calls (httpx) +
the already-available PyJWT[crypto] for the service-account OAuth2
JWT-Bearer flow - same reasoning as premium_service's Razorpay calls: a
couple of well-documented REST endpoints, not worth pulling in
google-api-python-client for.

Needs a Google Cloud service account with API access to this app in Play
Console (Setup -> API access -> create/link a service account there,
grant it "View financial data" + release permissions, download its JSON
key). Set GOOGLE_PLAY_SERVICE_ACCOUNT_JSON to that key file's raw JSON
content and GOOGLE_PLAY_PACKAGE_NAME to the app's package name
(com.preppath.student). Unconfigured means the /premium/google-play/verify
route is hard-disabled - there's no dev-mode mock for this one, unlike
Razorpay's, since it only matters once a real Play Store build exists to
test against.
"""
import json
import time

import httpx
import jwt

from app.core.config import settings

TOKEN_URL = "https://oauth2.googleapis.com/token"
SCOPE = "https://www.googleapis.com/auth/androidpublisher"


def configured() -> bool:
    return bool(settings.GOOGLE_PLAY_SERVICE_ACCOUNT_JSON and settings.GOOGLE_PLAY_PACKAGE_NAME)


def _access_token() -> str:
    key = json.loads(settings.GOOGLE_PLAY_SERVICE_ACCOUNT_JSON)
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


def _product_url(product_id: str, purchase_token: str) -> str:
    return (
        f"https://androidpublisher.googleapis.com/androidpublisher/v3/applications/"
        f"{settings.GOOGLE_PLAY_PACKAGE_NAME}/purchases/products/{product_id}/tokens/{purchase_token}"
    )


def verify_purchase(product_id: str, purchase_token: str) -> bool:
    """True only if Google confirms this token is a genuine, completed
    purchase of `product_id` - purchaseState 0 means purchased (1 is
    canceled, 2 is pending, per the API's own enum)."""
    token = _access_token()
    resp = httpx.get(_product_url(product_id, purchase_token), headers={"Authorization": f"Bearer {token}"}, timeout=15)
    if resp.status_code != 200:
        return False
    return resp.json().get("purchaseState") == 0


def acknowledge_purchase(product_id: str, purchase_token: str) -> None:
    """Must happen within 3 days of purchase or Google auto-refunds it -
    done server-side here (rather than letting the app acknowledge
    client-side) so a purchase is only ever acknowledged after our own
    verify_purchase() has actually confirmed it."""
    token = _access_token()
    httpx.post(f"{_product_url(product_id, purchase_token)}:acknowledge", headers={"Authorization": f"Bearer {token}"}, timeout=15)
