"""Export public vacancy fields from the private Job Agent Google Sheet.

Requires GOOGLE_SERVICE_ACCOUNT_JSON secret. The sheet remains private and
must be explicitly shared with the service account's email (Viewer).
"""
import json
import os
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import quote

from google.auth.transport.requests import AuthorizedSession
from google.oauth2.service_account import Credentials

SPREADSHEET_ID = "1QvTor1ImDYxzmNfa-uVPqEu5rNAi4iwgGg7mQUNwZgc"
RANGE = "'Jobs'!A1:I1000"
FIELDS = ("Job ID", "Company", "Country", "Job title", "Official URL", "Match %", "Visa evidence", "Status", "Discovered")


def build_feed(values):
    if not values or tuple(values[0][:len(FIELDS)]) != FIELDS:
        raise ValueError("Unexpected Jobs sheet header; refusing to publish")
    jobs = []
    seen = set()
    for row in values[1:]:
        row = list(row) + [""] * (len(FIELDS) - len(row))
        job_id, company, country, title, url, _, _, status, _ = row[:len(FIELDS)]
        if not all(isinstance(x, str) and x.strip() for x in (job_id, company, country, title, url)):
            continue
        if not url.startswith("https://"):
            continue
        if url in seen:
            continue
        seen.add(url)
        jobs.append({"title": title, "company": company, "country": country,
                     "location": "", "url": url, "status": status or "discovered"})
    return {"schema_version": 1, "visibility": "public_jobs_only",
            "generated_at": datetime.now(timezone.utc).isoformat(), "jobs": jobs}


def main():
    info = json.loads(os.environ["GOOGLE_SERVICE_ACCOUNT_JSON"])
    credentials = Credentials.from_service_account_info(
        info, scopes=["https://www.googleapis.com/auth/spreadsheets.readonly"])
    session = AuthorizedSession(credentials)
    endpoint = f"https://sheets.googleapis.com/v4/spreadsheets/{SPREADSHEET_ID}/values/{quote(RANGE, safe='')}"
    response = session.get(endpoint, timeout=30)
    response.raise_for_status()
    feed = build_feed(response.json().get("values", []))
    Path("dashboard-data.json").write_text(
        json.dumps(feed, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Published public vacancy records: {len(feed['jobs'])}")


if __name__ == "__main__":
    main()
