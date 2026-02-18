"""
Upstox token rotation helper.
Provides two helpers:
- request_access_token_via_api: tries to call Upstox Access Token Request API endpoints (best-effort).
- schedule_rotation_reminder: simple helper that can be used to notify operator or log reminder.

This is intentionally conservative: Upstox token issuance workflows vary by app type
so this helper tries known endpoints and returns the raw response for inspection.
"""

import httpx
from typing import Dict, Optional
from app.config import config


class UpstoxTokenManager:
    def __init__(self, client=None):
        # If provided, client should be an instance of UpstoxClient
        self.client = client
        self.base_v2 = "https://api.upstox.com/v2"

    async def request_access_token_via_api(self) -> Dict:
        """
        Best-effort call to Upstox Access Token Request API.
        Returns a dict with keys: success(bool), endpoint(str), response(dict or text), error(optional)

        Note: Upstox documentation refers to an Access Token Request flow for semi-automated
        tokens. The exact endpoint may depend on your app. This function attempts a couple
        of plausible endpoints and returns the result for you to inspect.
        """
        endpoints = [
            f"{self.base_v2}/access-token-request",
            f"{self.base_v2}/login/authorization/access-token-request",
        ]

        payload = {
            "client_id": config.UPSTOX_API_KEY,
            "redirect_uri": config.UPSTOX_REDIRECT_URI,
        }

        headers = {"Accept": "application/json"}

        async with httpx.AsyncClient(timeout=20.0) as http:
            for ep in endpoints:
                try:
                    resp = await http.post(ep, data=payload, headers=headers)
                    # Return status and body for inspection
                    try:
                        body = resp.json()
                    except Exception:
                        body = resp.text

                    return {"success": resp.status_code == 200, "endpoint": ep, "status_code": resp.status_code, "response": body}
                except Exception as e:
                    # Try next endpoint
                    last_error = str(e)

        return {"success": False, "endpoint_tried": endpoints, "error": last_error}

    def schedule_rotation_reminder(self):
        """Synchronous helper: caller can schedule this to notify operator daily.
        For a production setup integrate with email/SMS/webhook.
        This just returns a descriptive message (no external side-effects).
        """
        return {
            "message": "Upstox tokens expire daily. Use /upstox/auth-url and /upstox/callback or POST /upstox/request-rotation to initiate token request."
        }
