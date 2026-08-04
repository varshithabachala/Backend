"""
Local PostgreSQL -> Render PostgreSQL migration script.
Bypasses pg_dump/pg_restore entirely (avoids SNI / client-version issues)
by using psycopg2 directly (same library your FastAPI backend already uses).

USAGE:
    1. Activate your venv:
         source venv/bin/activate      (Linux/Mac)
    2. Run:
         python migrate_data.py

It will:
    - Connect to your LOCAL fortisoar_logs database
    - Read the exact column structure of playbook_requests
    - Create the same table on RENDER (if it doesn't exist)
    - Copy every row across
    - Verify row counts match
"""

import psycopg2
import psycopg2.extras

TABLE_NAME = "playbook_requests"

LOCAL_CONFIG = {
    "dbname": "fortisoar_logs",
    "user": "postgres",
    "password": "Varshi@10",
    "host": "localhost",
    "port": "5432",
}

# Render external DB URL + sslmode=require
RENDER_URL = (
    "postgresql://fortisoar_db_user:2U8spKKQNVepVWvnx7x54PV9XFaxg8De@"
    "dpg-d9oof5qd0e5s73c1rkl0-a.singapore-postgres.render.com/fortisoar_db"
    "?sslmode=require"
)


def get_column_defs(local_conn):
    """Read column names + types from the local table."""
    cur = local_conn.cursor()
    cur.execute(
        """
        SELECT column_name, data_type, character_maximum_length
        FROM information_schema.columns
        WHERE table_name = %s
        ORDER BY ordinal_position
        """,
        (TABLE_NAME,),
    )
    cols = cur.fetchall()
    cur.close()
    if not cols:
        raise RuntimeError(
            f"Table '{TABLE_NAME}' not found locally. Check the table name."
        )
    return cols


def build_create_table_sql(cols):
    parts = []
    for name, dtype, maxlen in cols:
        if dtype == "character varying" and maxlen:
            coltype = f"VARCHAR({maxlen})"
        elif dtype == "character varying":
            coltype = "VARCHAR"
        elif dtype == "timestamp without time zone":
            coltype = "TIMESTAMP"
        elif dtype == "integer":
            coltype = "INTEGER"
        elif dtype == "text":
            coltype = "TEXT"
        else:
            coltype = "TEXT"  # safe fallback
        parts.append(f'"{name}" {coltype}')
    cols_sql = ", ".join(parts)
    return f'CREATE TABLE IF NOT EXISTS {TABLE_NAME} ({cols_sql});'


def main():
    print("Connecting to LOCAL database...")
    local_conn = psycopg2.connect(**LOCAL_CONFIG)

    print("Reading table structure...")
    cols = get_column_defs(local_conn)
    col_names = [c[0] for c in cols]
    print(f"Columns found: {col_names}")

    create_sql = build_create_table_sql(cols)

    print("Connecting to RENDER database...")
    render_conn = psycopg2.connect(RENDER_URL)
    render_cur = render_conn.cursor()

    print("Creating table on Render (if not exists)...")
    render_cur.execute(create_sql)
    render_conn.commit()

    print("Fetching all rows from local table...")
    local_cur = local_conn.cursor()
    local_cur.execute(f"SELECT {', '.join(col_names)} FROM {TABLE_NAME}")
    rows = local_cur.fetchall()
    print(f"Found {len(rows)} rows locally.")

    if rows:
        print("Clearing existing rows on Render (avoid duplicates on re-run)...")
        render_cur.execute(f"DELETE FROM {TABLE_NAME}")

        placeholders = ", ".join(["%s"] * len(col_names))
        insert_sql = f'INSERT INTO {TABLE_NAME} ({", ".join(col_names)}) VALUES ({placeholders})'

        print("Inserting rows into Render...")
        psycopg2.extras.execute_batch(render_cur, insert_sql, rows, page_size=200)
        render_conn.commit()

    render_cur.execute(f"SELECT COUNT(*) FROM {TABLE_NAME}")
    render_count = render_cur.fetchone()[0]

    print(f"\nDONE. Local rows: {len(rows)} | Render rows now: {render_count}")

    local_cur.close()
    render_cur.close()
    local_conn.close()
    render_conn.close()


if __name__ == "__main__":
    main()
