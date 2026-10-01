from fastapi import APIRouter, Query, UploadFile, File
from pydantic import BaseModel
from typing import List
from typing import Optional
import psycopg2
import psycopg2.extras
import json
import csv
import io
from fastapi.responses import StreamingResponse

router = APIRouter(prefix="/api", tags=["Authentication"])

import os

DB_CONFIG = {
    "dbname": os.environ.get("DB_NAME", "fortisoar_logs"),
    "user": os.environ.get("DB_USER", "postgres"),
    "password": os.environ.get("DB_PASSWORD", "Varshi@10"),
    "host": os.environ.get("DB_HOST", "localhost"),
    "port": os.environ.get("DB_PORT", "5432"),
}



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

@router.get("/common-failures")
def get_common_failures():
    conn = get_connection()
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

    cur.execute("SELECT COUNT(*) AS total FROM playbook_requests;")
    total = cur.fetchone()["total"]

    cur.execute("SELECT COUNT(*) AS failed FROM playbook_requests WHERE status = 'failed';")
    failed = cur.fetchone()["failed"]

    cur.execute(
        "SELECT COUNT(DISTINCT requester_email) AS people "
        "FROM playbook_requests WHERE status = 'failed';"
    )
    people_affected = cur.fetchone()["people"]

    cur.execute(
        "SELECT requester_name, requester_email, request_text "
        "FROM playbook_requests WHERE status = 'failed';"
    )
    failed_rows = cur.fetchall()
    cur.close()
    conn.close()

    groups = {}
    for row in failed_rows:
        key = row["request_text"]
        if key not in groups:
            groups[key] = {}
        name = row["requester_name"]
        groups[key][name] = groups[key].get(name, 0) + 1

    patterns = []
    other_failures = []

    for request_text, people_counts in groups.items():
        if len(people_counts) >= 2:
            people_list = [{"name": n, "count": c} for n, c in people_counts.items()]
            total_failures = sum(people_counts.values())
            patterns.append({
                "request_text": request_text,
                "people": people_list,
                "total_failures": total_failures,
            })
        else:
            name = list(people_counts.keys())[0]
            count = people_counts[name]
            other_failures.append({
                "request_text": request_text,
                "name": name,
                "count": count,
            })

    patterns.sort(key=lambda p: -p["total_failures"])
    other_failures.sort(key=lambda o: -o["count"])

    return {
        "total": total,
        "failed": failed,
        "people_affected": people_affected,
        "shared_patterns": len(patterns),
        "patterns": patterns,
        "other_failures_count": len(other_failures),
        "other_failures": other_failures,
    }

@router.get("/forti-products")
def get_forti_products():

    conn = get_connection()
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    cur.execute("SELECT requester_name, request_text FROM playbook_requests;")
    rows = cur.fetchall()
    cur.close()
    conn.close()


    known_products = [
        "FortiGate-ips-signature", "FortiMAIL-demo", "FortiAnalyzer", "FortiAppSec",
        "FortiDeceptor", "FortiManager", "FortiRecon", "FortiSandbox", "FortiSIEM",
        "FortiSOAR", "FortiNDR", "FortiPAM", "FortiEDR", "FortiAIOPs", "FortiGate",
        "FortiGuard", "FortiOS", "Fortinet",
    ]

    product_to_names = {}
    for row in rows:
        text = row["request_text"] or ""
        name = row["requester_name"]
        remaining_text = text
        for product in known_products:
            if product.lower() in remaining_text.lower():
                product_to_names.setdefault(product, set()).add(name)
                idx = remaining_text.lower().find(product.lower())
                remaining_text = remaining_text[:idx] + remaining_text[idx + len(product):]

    result = [
        {"product": product, "requesters": sorted(names)}
        for product, names in sorted(product_to_names.items())
    ]

    return {"products": result}

def normalize_row(row):
    """
    Accepts a row in either of two shapes and returns a single tuple:
    (row_id, name, email, timestamp, request_text, status, playbook_id, playbook_url)

    Shape 1 (old/simple exports): a list/tuple with exactly those 8 values, in order.

    Shape 2 (FortiSOAR AI-agent session exports, e.g. Gautam's files): a dict with
    keys like id, name, email, "FROM_UNIXTIME(created_at)", DESCRIPTION, signature
    (signature is a JSON string containing playbook_url / workflow_uuid when the
    playbook was actually generated, or empty/null when the request failed).
    Some exports from this same source only have id, DESCRIPTION, member_id,
    signature (no name/email/timestamp) - those are handled too, with a
    placeholder name and no timestamp, since that data simply isn't in the file.
    """
    if isinstance(row, (list, tuple)):
        row_id, name, email, timestamp, request_text, status, playbook_id, playbook_url = row
        return row_id, name, email, timestamp, request_text, status, playbook_id, playbook_url

    if isinstance(row, dict):
        row_id = row.get("id")
        name = row.get("name")
        email = row.get("email")
        timestamp = row.get("FROM_UNIXTIME(created_at)") or row.get("timestamp") or row.get("created_at")
        request_text = row.get("DESCRIPTION") or row.get("description") or row.get("request_text")

        if not name and row.get("member_id") is not None:
            name = f"Member {row.get('member_id')}"

        signature_raw = row.get("signature")
        playbook_id = None
        playbook_url = None

        if signature_raw:
            status = "success"
            try:
                sig = json.loads(signature_raw) if isinstance(signature_raw, str) else signature_raw
                playbook_url = sig.get("playbook_url")
                playbook_id = sig.get("workflow_uuid")
            except Exception:
                pass
        else:
            status = "failed"

        return row_id, name, email, timestamp, request_text, status, playbook_id, playbook_url

    raise ValueError(f"Unsupported row format: {type(row)}")


@router.post("/import-json")
async def import_json_upload(file: UploadFile = File(...)):
    content = await file.read()
    data = json.loads(content)
    rows = data["rows"]

    def clean(v):
        if isinstance(v, str):
            v = v.strip().strip('"')
            if v == "":
                return None
        return v

    conn = get_connection()
    cur = conn.cursor()

    added = 0
    updated = 0
    added_ids = []

    for row in rows:
        row_id, name, email, timestamp, request_text, status, playbook_id, playbook_url = normalize_row(row)

        name = clean(name)
        email = clean(email)
        timestamp = clean(timestamp)
        request_text = clean(request_text)
        status = clean(status)
        playbook_id = clean(playbook_id)
        playbook_url = clean(playbook_url)

        cur.execute("SELECT id FROM playbook_requests WHERE id = %s;", (row_id,))
        exists = cur.fetchone()

        if exists:
            cur.execute(
                """
                UPDATE playbook_requests
                SET requester_name = %s, requester_email = %s, requested_at = %s,
                    request_text = %s, status = %s, playbook_id = %s, playbook_url = %s
                WHERE id = %s;
                """,
                (name, email, timestamp, request_text, status, playbook_id, playbook_url, row_id),
            )
            updated += 1
        else:
            cur.execute(
                """
                INSERT INTO playbook_requests
                (id, requester_name, requester_email, requested_at, request_text, status, playbook_id, playbook_url)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s);
                """,
                (row_id, name, email, timestamp, request_text, status, playbook_id, playbook_url),
            )
            added += 1
            added_ids.append(row_id)

    conn.commit()
    cur.close()
    conn.close()

    return {"added": added, "updated": updated, "added_ids": added_ids}


class BulkDeleteRequest(BaseModel):
    ids: List[int]


@router.delete("/requests/bulk-delete")
def bulk_delete_requests(payload: BulkDeleteRequest):
    if not payload.ids:
        return {"deleted": 0}

    conn = get_connection()
    cur = conn.cursor()
    cur.execute("DELETE FROM playbook_requests WHERE id = ANY(%s);", (payload.ids,))
    deleted = cur.rowcount
    conn.commit()
    cur.close()
    conn.close()

    return {"deleted": deleted}
