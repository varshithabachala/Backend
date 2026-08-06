"""
FastAPI router that serves playbook_requests data from PostgreSQL.

Place this file at: app/routers/playbook_router.py
(next to your existing auth_router.py and user_router.py)

Then in main.py, add:
    from app.routers import playbook_router
    app.include_router(playbook_router.router)
"""

from fastapi import APIRouter, Query
from typing import Optional
import psycopg2
import psycopg2.extras
import csv
import io
from fastapi.responses import StreamingResponse

router = APIRouter(prefix="/api", tags=["Authentication"])

# ---- adjust these to match your setup ----
import os

DB_CONFIG = {
    "dbname": os.environ.get("DB_NAME", "fortisoar_logs"),
    "user": os.environ.get("DB_USER", "postgres"),
    "password": os.environ.get("DB_PASSWORD", "Varshi@10"),
    "host": os.environ.get("DB_HOST", "localhost"),
    "port": os.environ.get("DB_PORT", "5432"),
}
# -------------------------------------------


def get_connection():
    return psycopg2.connect(**DB_CONFIG)


@router.get("/requests")
def get_requests(
    status: Optional[str] = Query(None, description="Filter by status: success or failed"),
    search: Optional[str] = Query(None, description="Search requester name, email, or request text"),
):
    query = (
        "SELECT id, requester_name, requester_email, requested_at, "
        "request_text, status, playbook_id, playbook_url FROM playbook_requests"
    )
    conditions = []
    params = []

    if status and status in ("success", "failed"):
        conditions.append("status = %s")
        params.append(status)

    if search:
        conditions.append(
            "(requester_name ILIKE %s OR requester_email ILIKE %s OR request_text ILIKE %s)"
        )
        like = f"%{search}%"
        params.extend([like, like, like])

    if conditions:
        query += " WHERE " + " AND ".join(conditions)

    query += " ORDER BY requested_at DESC"

    conn = get_connection()
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    cur.execute(query, params)
    rows = cur.fetchall()
    cur.close()
    conn.close()

    for r in rows:
        if r["requested_at"] is not None:
            r["requested_at"] = r["requested_at"].isoformat(sep=" ")

    return rows


@router.get("/stats")
def get_stats():
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT COUNT(*) FROM playbook_requests;")
    total = cur.fetchone()[0]
    cur.execute("SELECT COUNT(*) FROM playbook_requests WHERE status = 'success';")
    success = cur.fetchone()[0]
    cur.execute("SELECT COUNT(DISTINCT requester_email) FROM playbook_requests;")
    unique_users = cur.fetchone()[0]
    cur.close()
    conn.close()

    return {
        "total": total,
        "success": success,
        "failed": total - success,
        "unique_requesters": unique_users,
    }

@router.get("/requests/csv")
def download_requests_csv():
    conn = get_connection()
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    cur.execute(
        "SELECT requester_name, request_text, requester_email, status, requested_at "
        "FROM playbook_requests ORDER BY requested_at DESC"
    )
    rows = cur.fetchall()
    cur.close()
    conn.close()

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["Requester", "Request", "Status", "Email", "Timestamp"])

    for r in rows:
        timestamp = r["requested_at"].isoformat(sep=" ") if r["requested_at"] else ""
        writer.writerow([r["requester_name"], r["request_text"], r["status"], r["requester_email"], timestamp])

    output.seek(0)
    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=playbook_requests.csv"}
    )