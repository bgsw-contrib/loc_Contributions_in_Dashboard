import os
import json
import requests
from datetime import datetime, timedelta

# Environment variables
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")
ORG_NAME = "bgsw-contrib"
CONFIG_FILE = "users.json"
DASHBOARD_FILE = "README.md"

if not GITHUB_TOKEN:
    raise ValueError("GITHUB_TOKEN environment variable is required.")

headers = {
    "Authorization": f"token {GITHUB_TOKEN}",
    "Accept": "application/vnd.github.v3+json"
}

def load_config():
    with open(CONFIG_FILE, "r") as f:
        return json.load(f)

def fetch_user_prs(username, org):
    """
    Search for all Pull Requests created by the user in the specified organization.
    In this version, we fetch all historical PRs without any date filter.
    """
    query = f"org:{org} author:{username} type:pr"
    url = f"https://api.github.com/search/issues?q={query}"
    
    try:
        response = requests.get(url, headers=headers)
        if response.status_code != 200:
            try:
                error_msg = response.json().get("message", "Unknown error")
            except Exception:
                error_msg = response.text
            print(f"Error fetching PRs for {username}: {error_msg}")
            return []
        return response.json().get("items", [])
    except Exception as e:
        print(f"Exception fetching PRs for {username}: {e}")
        return []

def get_pr_details(pr_url):
    """
    Fetches additions and deletions from the specific PR API endpoint.
    """
    try:
        response = requests.get(pr_url, headers=headers)
        if response.status_code != 200:
            return 0, 0
        data = response.json()
        return data.get("additions", 0), data.get("deletions", 0)
    except Exception as e:
        print(f"Exception fetching PR details from {pr_url}: {e}")
        return 0, 0

def main():
    config = load_config()
    contributors = config.get("contributors", {})
    
    user_stats = {}
    group_stats = {}
    
    print("Gathering contribution metrics...")
    
    for username, info in contributors.items():
        name = info["name"]
        group = info["group"]
        
        print(f"Analyzing user: {username} ({name})...")
        prs = fetch_user_prs(username, ORG_NAME)
        
        total_additions = 0
        total_deletions = 0
        pr_count = len(prs)
        
        for pr in prs:
            # The search endpoint returns issue items; we need the actual pull_request API URL
            if "pull_request" in pr:
                pr_detail_url = pr["pull_request"]["url"]
                additions, deletions = get_pr_details(pr_detail_url)
                total_additions += additions
                total_deletions += deletions
        
        user_stats[username] = {
            "name": name,
            "group": group,
            "pr_count": pr_count,
            "additions": total_additions,
            "deletions": total_deletions,
            "total_loc": total_additions + total_deletions
        }
        
        # Aggregate by group
        if group not in group_stats:
            group_stats[group] = {
                "members": 0,
                "pr_count": 0,
                "additions": 0,
                "deletions": 0,
                "total_loc": 0
            }
        
        group_stats[group]["members"] += 1
        group_stats[group]["pr_count"] += pr_count
        group_stats[group]["additions"] += total_additions
        group_stats[group]["deletions"] += total_deletions
        group_stats[group]["total_loc"] += (total_additions + total_deletions)

    # Generate Markdown Dashboard Content
    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    markdown = f"""# Lines of Code Contributions Dashboard

Automated dashboard tracking active contributions within the **{ORG_NAME}** organization.

> **Last Updated:** `{now_str} (UTC)`  
> *Note: Metrics represent total historical Pull Request contributions.*

---

## 📊 Team & Group Summary

| Role Group | Members Tracked | Total PRs | Lines Added (+) | Lines Deleted (-) | Total LOC Changed |
| :--- | :---: | :---: | :---: | :---: | :---: |
"""
    for group, stats in sorted(group_stats.items(), key=lambda x: x[1]["total_loc"], reverse=True):
        markdown += f"| **{group}** | {stats['members']} | {stats['pr_count']} | {stats['additions']:,} | {stats['deletions']:,} | **{stats['total_loc']:,}** |\n"

    markdown += """
---

## 👤 Individual Contributor Standings

| Contributor | Role Group | PRs Created | Lines Added (+) | Lines Deleted (-) | Total LOC Changed |
| :--- | :--- | :---: | :---: | :---: | :---: |
"""
    for username, stats in sorted(user_stats.items(), key=lambda x: x[1]["total_loc"], reverse=True):
        markdown += f"| **{stats['name']}** ({username}) | {stats['group']} | {stats['pr_count']} | {stats['additions']:,} | {stats['deletions']:,} | **{stats['total_loc']:,}** |\n"

    markdown += """
---

## 🛠️ How it Works
This dashboard is fully automated. Every day, a GitHub Action workflow runs the tracking script, queries the GitHub API for activity within the organization, aggregates the LOC metrics, and updates this page.

To manage the list of tracked contributors and their groups, modify the `users.json` file.
"""

    with open(DASHBOARD_FILE, "w") as f:
        f.write(markdown)
    
    print("Dashboard updated successfully!")

if __name__ == "__main__":
    main()
