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
