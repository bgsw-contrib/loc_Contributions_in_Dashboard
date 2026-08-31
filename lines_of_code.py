# lines_of_code.py
import os
import json
import requests
import time
from datetime import datetime

def get_gh_token():
    token = os.getenv("GITHUB_TOKEN")
    if token:
        return token
    try:
        hosts_path = os.path.expanduser("~/.config/gh/hosts.yml")
        if os.path.exists(hosts_path):
            with open(hosts_path, "r") as f:
                for line in f:
                    if "oauth_token:" in line:
                        return line.split("oauth_token:")[1].strip().strip('"').strip("'")
    except Exception:
        pass
    return None

def fetch_user_prs(username, org, headers):
    query = f"org:{org} author:{username} type:pr"
    url = f"https://api.github.com/search/issues?q={query}&per_page=100"
    try:
        response = requests.get(url, headers=headers)
        if response.status_code != 200:
            return []
        return response.json().get("items", [])
    except Exception:
        return []

def get_pr_details(pr_url, headers):
    try:
        response = requests.get(pr_url, headers=headers)
        if response.status_code != 200:
            return 0, 0, False
        data = response.json()
        return data.get("additions", 0), data.get("deletions", 0), data.get("merged", False)
    except Exception:
        return 0, 0, False

def run_loc_analysis(contributors, orgs, headers):
    stats = {}
    for org in orgs:
        stats[org] = {}
        print(f"Gathering LOC contribution metrics for organization: {org}...")
        for username in contributors:
            print(f"  Analyzing user: {username}...")
            prs = fetch_user_prs(username, org, headers)
            
            stats[org][username] = {
                "done": {"pr_count": 0, "additions": 0, "deletions": 0, "total_loc": 0},
                "in_progress": {"pr_count": 0, "additions": 0, "deletions": 0, "total_loc": 0}
            }
            
            for pr in prs:
                if "pull_request" in pr:
                    pr_detail_url = pr["pull_request"]["url"]
                    additions, deletions, merged = get_pr_details(pr_detail_url, headers)
                    state = pr.get("state", "closed")
                    
                    # Skip pull requests that were closed without being merged (rejected/cancelled)
                    if state == "closed" and not merged:
                        continue
                        
                    category = "in_progress" if state == "open" else "done"
                    
                    stats[org][username][category]["pr_count"] += 1
                    stats[org][username][category]["additions"] += additions
                    stats[org][username][category]["deletions"] += deletions
                    stats[org][username][category]["total_loc"] += additions + deletions
            time.sleep(1)
    return stats

def main():
    token = get_gh_token()
    if not token:
        print("Warning: GITHUB_TOKEN not found.")
        return
        
    headers = {
        "Authorization": f"token {token}",
        "Accept": "application/vnd.github.v3+json"
    }
    
    with open("users.json", "r") as f:
        contributors = json.load(f)
        
    stats = run_loc_analysis(contributors, ["bgsw-contrib", "eclipse-score"], headers)
    with open("loc_stats.json", "w") as f:
        json.dump(stats, f, indent=2)
    print("lines_of_code.py completed: loc_stats.json written.")

if __name__ == "__main__":
    main()
