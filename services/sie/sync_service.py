import asyncpg

from integrations.sie_client import SIEClient
from repositories.sie.sie_repository import create_sync_run, deactivate_stale_permissions, finish_sync_run, upsert_project_bundle
from services.sie.normalizer import normalize_participation, normalize_project


async def synchronize_sie(
    pool: asyncpg.Pool,
    client: SIEClient,
    page_size: int,
) -> dict[str, int]:
    async with pool.acquire() as conn:
        sync_run_id = await create_sync_run(conn, page_size)

    pages = rows = projects = participants = 0
    try:
        token = await client.fetch_access_token()
        start = 0
        while True:
            payload = await client.fetch_page(token, start, start + page_size)
            page_rows = payload["data"]
            if not page_rows:
                break
            async with pool.acquire() as conn:
                async with conn.transaction():
                    for row in page_rows:
                        await upsert_project_bundle(
                            conn,
                            sync_run_id,
                            normalize_project(row),
                            normalize_participation(row),
                        )
                        projects += 1
                        participants += 1
            pages += 1
            rows += len(page_rows)
            if len(page_rows) < page_size:
                break
            start += page_size
    except Exception as error:
        async with pool.acquire() as conn:
            await finish_sync_run(conn, sync_run_id, "failed", pages, rows, projects, participants, str(error))
        raise

    async with pool.acquire() as conn:
        await deactivate_stale_permissions(conn, sync_run_id)
        await finish_sync_run(conn, sync_run_id, "success", pages, rows, projects, participants)
    return {"sync_run_id": sync_run_id, "pages": pages, "rows": rows, "projects": projects, "participants": participants}
