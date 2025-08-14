"""Fetch GitHub issues (excluding PRs) and their comments into JSONL.

Prints progress updates while paging through issues and collecting comments.
"""
import argparse
import json
import os
import time
from typing import Any

import httpx

BASE = "https://api.github.com"


def fetch_issues(repo: str, max_items: int = 200, token: str | None = None) -> list[dict[str, Any]]:
    """Fetch up to `max_items` issues (no PRs) and their comments for a repo.

    Args:
        repo: Repository in the form "owner/name".
        max_items: Maximum number of issues to fetch.
        token: Optional GitHub token for higher rate limits.
    Returns:
        A list of dicts with shape: {"issue": <issue_json>, "comments": <list>}.
    """
    headers = {
        "Accept": "application/vnd.github+json",
        "User-Agent": "issue-triage-fetcher",
    }
    if token:
        headers["Authorization"] = f"Bearer {token}"

    items: list[dict[str, Any]] = []
    page = 1
    per_page = 100

    print(f"Fetching up to {max_items} issues from {repo}...")

    with httpx.Client(timeout=30.0, headers=headers, base_url=BASE) as client:
        while len(items) < max_items:
            params = {"state": "all", "per_page": per_page, "page": page}

            print(f"• Page {page}: requesting issues…", flush=True)
            r = client.get(f"/repos/{repo}/issues", params=params)
            r.raise_for_status()
            all_items = r.json()
            batch = [it for it in all_items if "pull_request" not in it]
            if not batch:
                print("No more issues found; stopping.")
                break

            print(f"  ↳ Received {len(batch)} issues (excluding PRs). Collecting comments…")
            for it in batch:
                num = it["number"]
                cr = client.get(f"/repos/{repo}/issues/{num}/comments", params={"per_page": 100})
                cr.raise_for_status()
                comments = cr.json()
                items.append({"issue": it, "comments": comments})

                if len(items) % 25 == 0 or len(items) >= max_items:
                    print(f"  Collected {len(items)}/{max_items} issues so far…", flush=True)

                if len(items) >= max_items:
                    break

            page += 1
            time.sleep(0.2)

    print(f"Done. Total issues collected: {len(items)}")
    return items


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--repo", required=True, help="owner/name")
    ap.add_argument("--max", type=int, default=200)
    args = ap.parse_args()

    token = os.getenv("GITHUB_TOKEN")
    data = fetch_issues(args.repo, max_items=args.max, token=token)

    os.makedirs(".data", exist_ok=True)
    out = f".data/{args.repo.replace('/', '_')}_issues.jsonl"
    print(f"Writing {len(data)} records to {out}…")
    with open(out, "w", encoding="utf-8") as f:
        for item in data:
            f.write(json.dumps(item) + "\n")
    print(f"Wrote {len(data)} issues to {out}")