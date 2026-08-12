import sys
import json
import psycopg2

DB_CONFIG = {
    "dbname": "fortisoar_logs",
    "user": "postgres",
    "password": "Varshi@10",
    "host": "localhost",
    "port": "5432",
}


def clean_value(value):
    
    if isinstance(value, str):
        value = value.strip().strip('"')
        if value == "":
            return None
    return value


def load_json_rows(filepath):
    with open(filepath, "r") as f:
        data = json.load(f)
    return data["rows"]


def import_data(filepath, sync_mode=False):
    rows = load_json_rows(filepath)
    json_ids = set()

    conn = psycopg2.connect(**DB_CONFIG)
    cur = conn.cursor()

    added = 0
    updated = 0

    for row in rows:
        row_id, name, email, timestamp, request_text, status, playbook_id, playbook_url = row
        json_ids.add(row_id)

        
        playbook_id = clean_value(playbook_id)
        playbook_url = clean_value(playbook_url)
        name = clean_value(name)
        email = clean_value(email)
        request_text = clean_value(request_text)
        status = clean_value(status)

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

    removed = 0
    if sync_mode:
        cur.execute("SELECT id FROM playbook_requests;")
        db_ids = {r[0] for r in cur.fetchall()}
        ids_to_remove = db_ids - json_ids
        for rid in ids_to_remove:
            cur.execute("DELETE FROM playbook_requests WHERE id = %s;", (rid,))
            removed += 1

    conn.commit()
    cur.close()
    conn.close()

    print("Import complete.")
    print(f"  Added:   {added}")
    print(f"  Updated: {updated}")
    if sync_mode:
        print(f"  Removed: {removed} (sync mode was on)")
    else:
        print("  Removed: 0 (sync mode was off - nothing deleted)")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python3 import_json.py <filename.json> [--sync]")
        sys.exit(1)

    json_file = sys.argv[1]
    sync_flag = "--sync" in sys.argv

    import_data(json_file, sync_mode=sync_flag)
