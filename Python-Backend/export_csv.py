"""
Exports all playbook requests into a CSV file with columns in this order:
Requester, Request, Status, Timestamp

USAGE:
    1. Put this file in your Python-Backend folder (same place as migrate_data.py)
    2. Make sure your backend is running (Terminal 1, uvicorn on port 8001)
    3. Run:
           python3 export_csv.py
    4. It creates: playbook_requests.csv in the same folder

The file is written with a UTF-8 BOM and proper comma-quoting, so double-clicking
it opens cleanly in Excel (no garbled text, no columns merging when a request
contains a comma).
"""

import csv
import urllib.request
import json

API_URL = "http://10.37.34.7:8001/api/requests"
OUTPUT_FILE = "playbook_requests.csv"


def main():
    print("Fetching data from backend...")
    with urllib.request.urlopen(API_URL) as response:
        data = json.loads(response.read().decode("utf-8"))

    print(f"Fetched {len(data)} records. Writing CSV...")

    print("\nFirst Record:")
    print(json.dumps(data[0], indent=4))

    with open(OUTPUT_FILE, "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.writer(f, quoting=csv.QUOTE_ALL)
        # Header row - exact order the manager asked for
        writer.writerow(["Requester", "Request", "Status", "Timestamp"])
        for row in data:
            writer.writerow([
                row.get("requester_name", ""),
                row.get("request_text", ""),
                row.get("status", ""),
                row.get("requested_at", ""),
            ])

    print(f"Done. Saved as: {OUTPUT_FILE}")
    print(f"Total rows written: {len(data)}")


if __name__ == "__main__":
    main()
