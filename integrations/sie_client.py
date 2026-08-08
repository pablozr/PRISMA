from typing import Any


class SIEClient:
    report_name = "V_RELATORIO_110499010113"

    def __init__(self, http_client: Any, base_url: str, email: str, password: str):
        self._http_client = http_client
        self._base_url = base_url.rstrip("/")
        self._email = email
        self._password = password

    async def fetch_access_token(self) -> str:
        response = await self._http_client.post(
            f"{self._base_url}/api_auth/token/",
            json={"email": self._email, "password": self._password},
        )
        response.raise_for_status()
        token = response.json().get("access")
        if not token:
            raise RuntimeError("SIE authentication response has no access token")
        return token

    async def fetch_page(self, token: str, start: int, end: int) -> dict:
        response = await self._http_client.get(
            f"{self._base_url}/acesso_sie/acesso/{self.report_name}",
            headers={"Authorization": f"Bearer {token}"},
            params={"min": start, "max": end},
        )
        response.raise_for_status()
        payload = response.json()
        if not isinstance(payload.get("data"), list):
            raise RuntimeError("SIE report response has no data list")
        return payload
