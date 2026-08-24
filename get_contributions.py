import os
import json
import requests
import time
from datetime import datetime

# Environment variables
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")
ORG_NAME = "bgsw-contrib"
CONFIG_FILE = "users.json"
DASHBOARD_FILE = "README.md"
REPORT_FILE = "report.md"

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
    contributors = load_config()
    
    user_stats = {}
    
    print("Gathering contribution metrics...")
    
    for username in contributors:
        print(f"Analyzing user: {username}...")
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
            "pr_count": pr_count,
            "additions": total_additions,
            "deletions": total_deletions,
            "total_loc": total_additions + total_deletions
        }
        
        # Short sleep to prevent hitting GitHub search API secondary rate limits/abuse filters
        time.sleep(1)

    # Calculate Totals
    total_prs = sum(stats["pr_count"] for stats in user_stats.values())
    total_additions = sum(stats["additions"] for stats in user_stats.values())
    total_deletions = sum(stats["deletions"] for stats in user_stats.values())
    total_loc = total_additions + total_deletions

    # Generate Markdown Dashboard Content
    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    markdown = f"""# Lines of Code Contributions Dashboard

Automated dashboard tracking active contributions within the **{ORG_NAME}** organization.

> **Last Updated:** `{now_str} (UTC)`  
> *Note: Metrics represent total historical Pull Request contributions.*

---

## 👤 Contributor Standings

| Contributor (GitHub Username) | PRs Created | Lines Added (+) | Lines Deleted (-) | Total LOC Changed |
| :--- | :---: | :---: | :---: | :---: |
"""
    for username, stats in sorted(user_stats.items(), key=lambda x: x[1]["total_loc"], reverse=True):
        profile_url = f"https://github.com/{username}"
        pr_query_url = f"https://github.com/pulls?q=is:pr+org:{ORG_NAME}+author:{username}"
        markdown += f"| **[{username}]({profile_url})** | [{stats['pr_count']:,}]({pr_query_url}) | {stats['additions']:,} | {stats['deletions']:,} | **{stats['total_loc']:,}** |\n"

    # Add bold Total row at the bottom
    markdown += f"| **Total** | **[{total_prs:,}](https://github.com/pulls?q=is:pr+org:{ORG_NAME})** | **{total_additions:,}** | **{total_deletions:,}** | **{total_loc:,}** |\n"

    markdown += """
---

## 🛠️ How it Works
This dashboard is fully automated. Every day, a GitHub Action workflow runs the tracking script, queries the GitHub API for activity within the organization, aggregates the LOC metrics, and updates this page.

To manage the list of tracked contributors, modify the `users.json` file.
"""

    with open(DASHBOARD_FILE, "w") as f:
        f.write(markdown)
        
    with open(REPORT_FILE, "w") as f:
        f.write(markdown)
    
    print("Dashboard and report updated successfully!")

if __name__ == "__main__":
    main()
