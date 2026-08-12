from urllib.parse import urlencode

from google.auth.transport import requests as google_requests
from google.oauth2 import id_token

from core.config.config import settings
from core.http.http_client import http_client
from core.security.security import is_allowed_domain


class GoogleOAuthClient:
    auth_url = "https://accounts.google.com/o/oauth2/v2/auth"
    token_url = "https://oauth2.googleapis.com/token"

    def build_authorization_url(self, state: str, nonce: str) -> str:
        params = {
            "client_id": settings.GOOGLE_CLIENT_ID,
            "redirect_uri": settings.GOOGLE_REDIRECT_URI,
            "response_type": "code",
            "scope": "openid email profile",
            "state": state,
            "nonce": nonce,
            "prompt": "select_account",
            "access_type": "offline",
            "include_granted_scopes": "true",
        }
        return f"{self.auth_url}?{urlencode(params)}"

    async def exchange_code(self, code: str) -> dict:
        if http_client.client is None:
            await http_client.connect()

        response = await http_client.client.post(
            self.token_url,
            data={
                "code": code,
                "client_id": settings.GOOGLE_CLIENT_ID,
                "client_secret": settings.GOOGLE_CLIENT_SECRET,
                "redirect_uri": settings.GOOGLE_REDIRECT_URI,
                "grant_type": "authorization_code",
            },
        )

        if response.status_code != 200:
            try:
                error_data = response.json()
            except Exception:
                error_data = response.text
            raise ValueError(f"Falha na troca do token Google: {error_data}")

        return response.json()

    def verify_id_token(self, raw_id_token: str, expected_nonce: str) -> dict:
        payload = id_token.verify_oauth2_token(
            raw_id_token,
            google_requests.Request(),
            settings.GOOGLE_CLIENT_ID,
            clock_skew_in_seconds=settings.GOOGLE_OAUTH_CLOCK_SKEW_SECONDS,
        )

        if payload.get("iss") not in ("accounts.google.com", "https://accounts.google.com"):
            raise ValueError("Google issuer invalido")
        if payload.get("nonce") != expected_nonce:
            raise ValueError("Google nonce invalido")
        if payload.get("email_verified") is not True:
            raise ValueError("Email Google nao verificado")

        email = payload.get("email")
        if not email or not is_allowed_domain(email, payload.get("hd")):
            raise ValueError("Dominio de email nao permitido")

        return payload


google_oauth_client = GoogleOAuthClient()
