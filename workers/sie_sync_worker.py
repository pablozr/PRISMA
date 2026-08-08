import asyncio

import httpx

from core.config.config import settings
from core.postgresql.postgresql import postgresql
from integrations.sie_client import SIEClient
from services.sie.sync_service import synchronize_sie


async def run_forever() -> None:
    if not settings.SIE_EMAIL or not settings.SIE_PASSWORD:
        raise RuntimeError("SIE_EMAIL and SIE_PASSWORD are required")
    await postgresql.connect()
    try:
        async with httpx.AsyncClient(timeout=settings.HTTP_CLIENT_TIMEOUT_SECONDS) as http_client:
            client = SIEClient(http_client, settings.SIE_API_BASE_URL, settings.SIE_EMAIL, settings.SIE_PASSWORD)
            while True:
                await synchronize_sie(postgresql.pool, client, settings.SIE_SYNC_PAGE_SIZE)
                await asyncio.sleep(settings.SIE_SYNC_INTERVAL_DAYS * 24 * 60 * 60)
    finally:
        await postgresql.disconnect()


if __name__ == "__main__":
    asyncio.run(run_forever())
