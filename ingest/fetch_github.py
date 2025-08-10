import argparse, os, time
import httpx
from typing import List, Dict
from clean_text import md_to_text

BASE = "https://api.github.com"

def fetch_issues(repo: str, max_items: int = 200, token: str | None = None) -> List[Dict]:
    headers = {"Accept": "application/vnd.github+json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    items = []
    page = 1
    with httpx.Client(timeout=30.0, headers=headers) as client:
        while len(items) < max_items:
            r = client.get(f"{BASE}/repos/{repo}/issues", params={"state":"all","per_page":100,"page":page})
            r.raise_for_status()
            batch = [i for i in r.json() if "pull_request" not in i]
            if not batch:
                break
            for it in batch:
                num = it["number"]
                # fetch comments
                cr = client.get(f"{BASE}/repos/{repo}/issues/{num}/comments", params={"per_page":100})
                cr.raise_for_status()
                comments = cr.json()
                items.append({"issue": it, "comments": comments})
                if len(items) >= max_items:
                    break
            page += 1
            time.sleep(0.2)
    return items

if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--repo", required=True, help="owner/name")
    ap.add_argument("--max", type=int, default=200)
    args = ap.parse_args()

    token = os.getenv("GITHUB_TOKEN")
    data = fetch_issues(args.repo, max_items=args.max, token=token)

    os.makedirs(".data", exist_ok=True)
    out = f".data/{args.repo.replace('/','_')}_issues.jsonl"
    import json
    with open(out, "w", encoding="utf-8") as f:
        for item in data:
            f.write(json.dumps(item) + "\n")
    print(f"Wrote {len(data)} issues to {out}")