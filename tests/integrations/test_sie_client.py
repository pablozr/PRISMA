import asyncio

from integrations.sie_client import SIEClient


class Response:
    def __init__(self, payload):
        self.payload = payload

    def raise_for_status(self):
        return None

    def json(self):
        return self.payload


class HTTPClient:
    async def post(self, *args, **kwargs):
        return Response({"access": "token"})

    async def get(self, *args, **kwargs):
        return Response({"data": [], "subset": [1, 10]})


def test_sie_client_authenticates_and_fetches_page():
    client = SIEClient(HTTPClient(), "https://api.unirio.br/api/v2", "x", "y")
    token = asyncio.run(client.fetch_access_token())
    payload = asyncio.run(client.fetch_page(token, 0, 10))
    assert token == "token"
    assert payload["data"] == []
