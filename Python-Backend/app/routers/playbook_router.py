from fastapi import APIRouter, Query
from typing import Optional
import psycopg2
import psycopg2.extras
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
                # remove matched part so a shorter overlapping name isn't double counted
                idx = remaining_text.lower().find(product.lower())
                remaining_text = remaining_text[:idx] + remaining_text[idx + len(product):]

    result = [
        {"product": product, "requesters": sorted(names)}
        for product, names in sorted(product_to_names.items())
    ]

    return {"products": result}