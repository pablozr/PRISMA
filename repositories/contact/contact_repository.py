import json
from typing import Optional

import asyncpg


async def create_contact_email_request(
    conn: asyncpg.Connection,
    requested_by_user_id: int,
    project_id: int,
    subject: str,
    body: str,
    payload: dict,
) -> Optional[dict]:
    query = """
            WITH target_project AS (
                SELECT id,
                       contact_email
                FROM projects
                WHERE id = $2
                  AND is_active = TRUE
                  AND status = 'published'
                  AND published_at IS NOT NULL
            )
            INSERT INTO email_dispatch_requests (
                requested_by_user_id,
                project_id,
                to_email,
                subject,
                body,
                payload,
                status,
                next_attempt_at
            )
            SELECT $1,
                   target_project.id,
                   target_project.contact_email,
                   $3,
                   $4,
                   $5::jsonb,
                   'queued',
                   NOW()
            FROM target_project
            RETURNING id AS request_id,
                      project_id,
                      to_email,
                      subject,
                      body,
                      status,
                      attempt_count,
                      next_attempt_at,
                      last_error,
                      sent_at;
            """

    row = await conn.fetchrow(
        query,
        requested_by_user_id,
        project_id,
        subject,
        body,
        json.dumps(payload),
    )
    return dict(row) if row else None


async def get_contact_email_request_status(
    conn: asyncpg.Connection,
    request_id: int,
    user_id: int,
    user_role: str,
) -> Optional[dict]:
    query = """
            SELECT id AS request_id,
                   status,
                   attempt_count,
                   next_attempt_at,
                   last_error,
                   sent_at
            FROM email_dispatch_requests
            WHERE id = $1
              AND ($3::TEXT = 'admin' OR requested_by_user_id = $2)
            LIMIT 1;
            """

    row = await conn.fetchrow(query, request_id, user_id, user_role)
    return dict(row) if row else None


async def get_contact_email_sent_by_me(
    conn: asyncpg.Connection,
    user_id: int,
) -> list:
    query = """
            SELECT id AS request_id,
                   project_id,
                   to_email,
                   subject,
                   body,
                   status,
                   attempt_count,
                   next_attempt_at,
                   last_error,
                   sent_at
            FROM email_dispatch_requests
            WHERE requested_by_user_id = $1
            ORDER BY created_at DESC;
            """

    rows = await conn.fetch(query, user_id)
    return [dict(row) for row in rows]


async def mark_contact_email_request_as_sent(
    conn: asyncpg.Connection,
    request_id: int,
) -> bool:
    query = """
            UPDATE email_dispatch_requests
            SET status = 'sent',
                sent_at = NOW()
            WHERE id = $1
              AND status IN ('queued', 'failed')
            RETURNING id;
            """

    row = await conn.fetchrow(query, request_id)
    return bool(row)


async def mark_contact_email_request_as_failed(
    conn: asyncpg.Connection,
    request_id: int,
    error_message: str,
) -> bool:
    query = """
            UPDATE email_dispatch_requests
            SET status = 'failed',
                last_error = $2,
                next_attempt_at = NOW() + INTERVAL '15 minutes'
            WHERE id = $1
              AND status IN ('queued', 'failed')
            RETURNING id;
            """

    row = await conn.fetchrow(query, request_id, error_message)
    return bool(row)
