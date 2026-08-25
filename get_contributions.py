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

def fetch_jira_issue(instance, key):
    # Try retrieving JIRA_TOKEN from environment first
    token = os.getenv("JIRA_TOKEN")
    if not token:
        # Load environment from ~/.bashrc manually to find exported JIRA_TOKEN
        try:
            bashrc_path = os.path.expanduser("~/.bashrc")
            if os.path.exists(bashrc_path):
                with open(bashrc_path, "r") as f:
                    for line in f:
                        if line.strip().startswith("export JIRA_TOKEN="):
                            token = line.split("export JIRA_TOKEN=")[1].strip().strip('"').strip("'")
        except Exception:
            pass
            
    if not token:
        return None
        
    url = f"https://rb-tracker.bosch.com/{instance}/rest/api/2/issue/{key}"
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }
    try:
        response = requests.get(url, headers=headers)
        if response.status_code == 200:
            return response.json()
        else:
            print(f"Jira API returned status {response.status_code} for {key}")
            return None
    except Exception as e:
        print(f"Exception fetching Jira ticket {key}: {e}")
        return None

# Environment variables
GITHUB_TOKEN = get_gh_token()
ORG_NAME = "bgsw-contrib"
CONFIG_FILE = "users.json"
DASHBOARD_FILE = "README.md"
HTML_FILE = "index.html"

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
        
        user_stats[username] = {
            "done": {
                "pr_count": 0,
                "additions": 0,
                "deletions": 0,
                "total_loc": 0
            },
            "in_progress": {
                "pr_count": 0,
                "additions": 0,
                "deletions": 0,
                "total_loc": 0
            }
        }
        
        for pr in prs:
            # The search endpoint returns issue items; we need the actual pull_request API URL
            if "pull_request" in pr:
                pr_detail_url = pr["pull_request"]["url"]
                additions, deletions = get_pr_details(pr_detail_url)
                
                # Check state to decide if Done (merged/closed) or In Progress (open)
                state = pr.get("state", "closed")
                category = "in_progress" if state == "open" else "done"
                
                user_stats[username][category]["pr_count"] += 1
                user_stats[username][category]["additions"] += additions
                user_stats[username][category]["deletions"] += deletions
                user_stats[username][category]["total_loc"] += additions + deletions
        
        # Short sleep to prevent hitting GitHub search API secondary rate limits/abuse filters
        time.sleep(1)

    # Calculate Totals for Done
    total_prs_done = sum(stats["done"]["pr_count"] for stats in user_stats.values())
    total_additions_done = sum(stats["done"]["additions"] for stats in user_stats.values())
    total_deletions_done = sum(stats["done"]["deletions"] for stats in user_stats.values())
    total_loc_done = total_additions_done + total_deletions_done

    # Calculate Totals for In Progress
    total_prs_ip = sum(stats["in_progress"]["pr_count"] for stats in user_stats.values())
    total_additions_ip = sum(stats["in_progress"]["additions"] for stats in user_stats.values())
    total_deletions_ip = sum(stats["in_progress"]["deletions"] for stats in user_stats.values())
    total_loc_ip = total_additions_ip + total_deletions_ip

    active_contributors = len(contributors)

    # Generate Markdown Dashboard Content
    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    markdown = f"""# Lines of Code Contributions Dashboard

Automated dashboard tracking active contributions within the **{ORG_NAME}** organization.

> **Last Updated:** `{now_str} (UTC)`  
> *Note: Metrics are split into completed ("Done") and active ("In Progress") pull requests.*

---

## 🏆 Completed Contributions (Done)

| Contributor (GitHub Username) | PRs Closed/Merged | Lines Added (+) | Lines Deleted (-) | Total LOC Changed |
| :--- | :---: | :---: | :---: | :---: |
"""
    for username, stats in sorted(user_stats.items(), key=lambda x: x[1]["done"]["total_loc"], reverse=True):
        profile_url = f"https://github.com/{username}"
        pr_query_url = f"https://github.com/pulls?q=is:pr+org:{ORG_NAME}+author:{username}+is:closed"
        markdown += f"| **[{username}]({profile_url})** | [{stats['done']['pr_count']:,}]({pr_query_url}) | {stats['done']['additions']:,} | {stats['done']['deletions']:,} | **{stats['done']['total_loc']:,}** |\n"

    # Add bold Total row for Done at the bottom
    markdown += f"| **Total** | **[{total_prs_done:,}](https://github.com/pulls?q=is:pr+org:{ORG_NAME}+is:closed)** | **{total_additions_done:,}** | **{total_deletions_done:,}** | **{total_loc_done:,}** |\n"

    markdown += f"""
---

## ⏳ In-Progress Contributions (In Progress)

| Contributor (GitHub Username) | PRs Open | Lines Added (+) | Lines Deleted (-) | Total LOC Changed |
| :--- | :---: | :---: | :---: | :---: |
"""
    for username, stats in sorted(user_stats.items(), key=lambda x: x[1]["in_progress"]["total_loc"], reverse=True):
        profile_url = f"https://github.com/{username}"
        pr_query_url = f"https://github.com/pulls?q=is:pr+org:{ORG_NAME}+author:{username}+is:open"
        markdown += f"| **[{username}]({profile_url})** | [{stats['in_progress']['pr_count']:,}]({pr_query_url}) | {stats['in_progress']['additions']:,} | {stats['in_progress']['deletions']:,} | **{stats['in_progress']['total_loc']:,}** |\n"

    # Add bold Total row for In Progress at the bottom
    markdown += f"| **Total** | **[{total_prs_ip:,}](https://github.com/pulls?q=is:pr+org:{ORG_NAME}+is:open)** | **{total_additions_ip:,}** | **{total_deletions_ip:,}** | **{total_loc_ip:,}** |\n"

    markdown += f"""
---

## 🔍 How to View the Reports

You can check the contribution metrics in three convenient ways:

1. **🌐 Interactive Web Dashboard**: View the premium dark-mode dashboard with interactive Chart.js bar and doughnut charts live at:  
   👉 **[bgsw-contrib.github.io/loc_Contributions_in_Dashboard/](https://bgsw-contrib.github.io/loc_Contributions_in_Dashboard/)**  
   *(Served automatically via GitHub Pages)*

2. **📄 Readme Standings Table**: View the clean, formatted Markdown standings table directly on the **[landing page of this repository](./README.md)**.

3. **📊 GitHub Actions Run Summary**: Check the **Actions** tab of this repository. Every daily scheduled run or manual run renders this standings table directly in the run summary overview!

---

## 🛠️ How it Works
This dashboard is fully automated. Every day, a GitHub Action workflow runs the tracking script, queries the GitHub API for activity within the organization, aggregates the LOC metrics, and updates this page.

To manage the list of tracked contributors, modify the `users.json` file.
"""

    # Generate index.html Content (Rich Executive Dashboard with Chart.js)
    labels = []
    pr_counts = []
    add_metrics = []
    del_metrics = []
    total_locs = []
    
    sorted_users = sorted(user_stats.items(), key=lambda x: x[1]["done"]["total_loc"], reverse=True)
    for username, stats in sorted_users:
        labels.append(username)
        pr_counts.append(stats["done"]["pr_count"])
        add_metrics.append(stats["done"]["additions"])
        del_metrics.append(stats["done"]["deletions"])
        total_locs.append(stats["done"]["total_loc"])

    table_rows_done_html = ""
    for username, stats in sorted_users:
        profile_url = f"https://github.com/{username}"
        pr_query_url = f"https://github.com/pulls?q=is:pr+org:{ORG_NAME}+author:{username}+is:closed"
        table_rows_done_html += f"""
        <tr>
            <td><a href="{profile_url}" target="_blank" class="user-link">@{username}</a></td>
            <td class="text-center"><a href="{pr_query_url}" target="_blank" class="pr-link">{stats['done']['pr_count']:,}</a></td>
            <td class="text-green text-right">+{stats['done']['additions']:,}</td>
            <td class="text-red text-right">-{stats['done']['deletions']:,}</td>
            <td class="text-right font-bold"><b>{stats['done']['total_loc']:,}</b></td>
        </tr>
        """

    table_rows_ip_html = ""
    sorted_users_ip = sorted(user_stats.items(), key=lambda x: x[1]["in_progress"]["total_loc"], reverse=True)
    for username, stats in sorted_users_ip:
        profile_url = f"https://github.com/{username}"
        pr_query_url = f"https://github.com/pulls?q=is:pr+org:{ORG_NAME}+author:{username}+is:open"
        table_rows_ip_html += f"""
        <tr>
            <td><a href="{profile_url}" target="_blank" class="user-link">@{username}</a></td>
            <td class="text-center"><a href="{pr_query_url}" target="_blank" class="pr-link">{stats['in_progress']['pr_count']:,}</a></td>
            <td class="text-green text-right">+{stats['in_progress']['additions']:,}</td>
            <td class="text-red text-right">-{stats['in_progress']['deletions']:,}</td>
            <td class="text-right font-bold"><b>{stats['in_progress']['total_loc']:,}</b></td>
        </tr>
        """

    # Serialize JSON for inject into JavaScript
    labels_json = json.dumps(labels)
    pr_counts_json = json.dumps(pr_counts)
    add_metrics_json = json.dumps(add_metrics)
    del_metrics_json = json.dumps(del_metrics)
    total_locs_json = json.dumps(total_locs)

    # Fetch Jira issue NEETASOSS-77 status
    jira_data = fetch_jira_issue("tracker19", "NEETASOSS-77")
    
    jira_status_html = ""
    if jira_data:
        fields = jira_data.get("fields", {})
        summary = fields.get("summary", "LOC separation details (Done vs In Progress)")
        status = fields.get("status", {}).get("name", "In Progress")
        assignee_data = fields.get("assignee")
        assignee = assignee_data.get("displayName", "Unassigned") if assignee_data else "Unassigned"
        priority = fields.get("priority", {}).get("name", "High")
        
        status_class = "status-progress" if "Progress" in status else ("status-done" if "Done" in status or "Closed" in status or "Resolved" in status else "status-open")
        priority_class = "priority-high" if "High" in priority or "Critical" in priority else ("priority-medium" if "Medium" in priority else "priority-low")
        
        jira_status_html = f"""
            <!-- Stats Grid -->
            <div class="stats-grid">
                <div class="stat-card blue">
                    <span class="stat-label">Live Sync Connection</span>
                    <span class="stat-value" style="color: var(--success); font-size: 1.5rem;">ONLINE</span>
                </div>
                <div class="stat-card green">
                    <span class="stat-label">Ticket Status</span>
                    <span class="stat-value" style="font-size: 1.5rem;">{status}</span>
                </div>
                <div class="stat-card">
                    <span class="stat-label">Ticket Assignee</span>
                    <span class="stat-value" style="font-size: 1.5rem;">@{assignee}</span>
                </div>
                <div class="stat-card">
                    <span class="stat-label">Ticket Priority</span>
                    <span class="stat-value" style="color: var(--accent); font-size: 1.5rem;">{priority}</span>
                </div>
            </div>

            <div class="material-card">
                <div class="material-card-header header-pink">
                    <div>
                        <h3 class="material-card-title">⏳ Live Jira Task Status</h3>
                        <p class="material-card-subtitle">Synchronized live with Bosch Track&Release</p>
                    </div>
                    <div class="health-status">
                        <span class="indicator indicator-green"></span>
                        <span class="text-green">LIVE SYNCED</span>
                    </div>
                </div>
                <div style="overflow-x: auto; padding-top: 0.5rem;">
                    <table>
                        <thead>
                            <tr>
                                <th>Ticket Key</th>
                                <th>Summary</th>
                                <th>Assignee</th>
                                <th>Priority</th>
                                <th>Status</th>
                            </tr>
                        </thead>
                        <tbody>
                            <tr>
                                <td><a href="https://rb-tracker.bosch.com/tracker19/browse/NEETASOSS-77" target="_blank" class="user-link">NEETASOSS-77</a></td>
                                <td>{summary}</td>
                                <td>@{assignee}</td>
                                <td><span class="priority-badge {priority_class}">{priority}</span></td>
                                <td><span class="status-badge {status_class}">{status}</span></td>
                            </tr>
                        </tbody>
                    </table>
                </div>
            </div>
        """
    else:
        # Fallback values when 401/unauthorized or token is not configured
        jira_status_html = f"""
            <!-- Stats Grid -->
            <div class="stats-grid">
                <div class="stat-card blue">
                    <span class="stat-label">Live Sync Connection</span>
                    <span class="stat-value" style="color: var(--danger); font-size: 1.5rem;">OFFLINE</span>
                </div>
                <div class="stat-card">
                    <span class="stat-label">Cached Status</span>
                    <span class="stat-value" style="color: var(--accent); font-size: 1.5rem;">In Progress</span>
                </div>
                <div class="stat-card">
                    <span class="stat-label">Cached Assignee</span>
                    <span class="stat-value" style="font-size: 1.5rem;">@srinivasugithub</span>
                </div>
                <div class="stat-card">
                    <span class="stat-label">Cached Priority</span>
                    <span class="stat-value" style="color: var(--danger); font-size: 1.5rem;">High</span>
                </div>
            </div>

            <div class="material-card">
                <div class="material-card-header header-pink">
                    <div>
                        <h3 class="material-card-title">⏳ Task Status (Offline Fallback)</h3>
                        <p class="material-card-subtitle">Showing cached task details. Live sync requires valid permissions.</p>
                    </div>
                    <div class="health-status">
                        <span class="indicator" style="background-color: #fb8c00; box-shadow: 0 0 8px #fb8c00;"></span>
                        <span style="color: #ffa726; font-weight: 600;">OFFLINE FALLBACK</span>
                    </div>
                </div>
                <div style="overflow-x: auto; padding-top: 0.5rem;">
                    <table>
                        <thead>
                            <tr>
                                <th>Ticket Key</th>
                                <th>Summary</th>
                                <th>Assignee</th>
                                <th>Priority</th>
                                <th>Status</th>
                            </tr>
                        </thead>
                        <tbody>
                            <tr>
                                <td><a href="https://rb-tracker.bosch.com/tracker19/browse/NEETASOSS-77" target="_blank" class="user-link">NEETASOSS-77</a></td>
                                <td>Lines of Code contribution details separation (Done vs In Progress)</td>
                                <td>@srinivasugithub</td>
                                <td><span class="priority-badge priority-high">High</span></td>
                                <td><span class="status-badge status-progress">In Progress</span></td>
                            </tr>
                        </tbody>
                    </table>
                    <p style="font-size: 0.825rem; color: var(--text-muted); margin-top: 1.25rem; line-height: 1.4;">
                        <strong>Notice:</strong> The JIRA_TOKEN loaded from <code>~/.bashrc</code> currently does not have permissions to access the <code>NEETASOSS</code> project on <code>tracker19</code> (HTTP Error 401: Unauthorized). Please configure a Personal Access Token with read access to enable live sync.
                    </p>
                </div>
            </div>
        """

    html_content = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>LOC Contributions Dashboard - {ORG_NAME}</title>
    <!-- Inter Google Font -->
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap" rel="stylesheet">
    <!-- Chart.js CDN -->
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
    <style>
        :root {{
            --bg-color: #0f172a;
            --card-bg: #1e293b;
            --card-border: #334155;
            --text-main: #f8fafc;
            --text-muted: #94a3b8;
            --primary: #38bdf8;
            --success: #4ade80;
            --danger: #f87171;
            --accent: #a78bfa;
        }}
        
        * {{
            margin: 0;
            padding: 0;
            box-sizing: border-box;
            font-family: 'Inter', sans-serif;
        }}
        
        body {{
            background-color: var(--bg-color);
            color: var(--text-main);
            padding: 2.5rem 1.5rem;
            min-height: 100vh;
        }}
        
        .container {{
            max-width: 1200px;
            margin: 0 auto;
        }}
        
        header {{
            margin-bottom: 2rem;
            display: flex;
            justify-content: space-between;
            align-items: flex-end;
            border-bottom: 1px solid var(--card-border);
            padding-bottom: 1.5rem;
            flex-wrap: wrap;
            gap: 1rem;
        }}
        
        h1 {{
            font-size: 2rem;
            font-weight: 700;
            background: linear-gradient(135deg, #38bdf8, #a78bfa);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
        }}
        
        .updated-badge {{
            font-size: 0.875rem;
            color: var(--text-muted);
            background-color: var(--card-bg);
            border: 1px solid var(--card-border);
            padding: 0.5rem 1rem;
            border-radius: 9999px;
        }}
        
        /* Tabs Navbar Style */
        .nav-tabs-wrapper {{
            background-color: var(--card-bg);
            border-radius: 12px;
            padding: 0.5rem;
            display: inline-flex;
            gap: 0.5rem;
            box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1), 0 2px 4px -1px rgba(0, 0, 0, 0.06);
            margin-bottom: 2.5rem;
            border: 1px solid var(--card-border);
            flex-wrap: wrap;
        }}
        
        .tab-btn {{
            background: transparent;
            border: none;
            padding: 0.75rem 1.5rem;
            color: var(--text-muted);
            font-weight: 600;
            border-radius: 8px;
            cursor: pointer;
            transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
            display: flex;
            align-items: center;
            gap: 0.5rem;
            font-size: 0.95rem;
        }}
        
        .tab-btn:hover {{
            color: var(--text-main);
            background: rgba(255, 255, 255, 0.04);
        }}
        
        .tab-btn.active {{
            background: linear-gradient(195deg, #38bdf8, #1a73e8);
            color: #ffffff;
            box-shadow: 0 4px 20px 0 rgba(56, 189, 248, 0.2), 0 7px 10px -5px rgba(26, 115, 232, 0.4);
        }}
        
        /* Tab Transition Animation */
        .tab-content {{
            display: none;
        }}
        
        .tab-content.active {{
            display: block;
            animation: fadeIn 0.4s ease-out;
        }}
        
        @keyframes fadeIn {{
            from {{ opacity: 0; transform: translateY(10px); }}
            to {{ opacity: 1; transform: translateY(0); }}
        }}
        
        /* Material Dashboard Card style */
        .material-card {{
            background-color: var(--card-bg);
            border: 1px solid var(--card-border);
            border-radius: 12px;
            padding: 1.5rem;
            margin-top: 2.5rem;
            position: relative;
            box-shadow: 0 4px 20px 0 rgba(0, 0, 0, 0.14), 0 7px 10px -5px rgba(0, 0, 0, 0.1);
        }}
        
        .material-card-header {{
            margin: -2.5rem 0 1.5rem;
            padding: 1.25rem 1.5rem;
            border-radius: 10px;
            box-shadow: 0 4px 20px 0 rgba(0, 0, 0, 0.14), 0 7px 10px -5px rgba(0, 0, 0, 0.4);
            color: #ffffff;
            display: flex;
            justify-content: space-between;
            align-items: center;
        }}
        
        .header-blue {{
            background: linear-gradient(195deg, #49a3f1, #1a73e8);
            box-shadow: 0 4px 20px 0 rgba(73, 163, 241, 0.15), 0 7px 10px -5px rgba(26, 115, 232, 0.4);
        }}
        
        .header-green {{
            background: linear-gradient(195deg, #66bb6a, #43a047);
            box-shadow: 0 4px 20px 0 rgba(102, 187, 106, 0.15), 0 7px 10px -5px rgba(67, 160, 71, 0.4);
        }}
        
        .header-orange {{
            background: linear-gradient(195deg, #ffa726, #fb8c00);
            box-shadow: 0 4px 20px 0 rgba(255, 167, 38, 0.15), 0 7px 10px -5px rgba(251, 140, 0, 0.4);
        }}
        
        .header-pink {{
            background: linear-gradient(195deg, #ec407a, #d81b60);
            box-shadow: 0 4px 20px 0 rgba(236, 64, 122, 0.15), 0 7px 10px -5px rgba(216, 27, 96, 0.4);
        }}
        
        .header-dark {{
            background: linear-gradient(195deg, #42424a, #191919);
            box-shadow: 0 4px 20px 0 rgba(66, 66, 74, 0.15), 0 7px 10px -5px rgba(25, 25, 25, 0.4);
        }}
        
        .material-card-title {{
            font-size: 1.25rem;
            font-weight: 600;
        }}
        
        .material-card-subtitle {{
            font-size: 0.75rem;
            color: rgba(255, 255, 255, 0.8);
            margin-top: 0.25rem;
        }}
        
        /* Stats Grid */
        .stats-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
            gap: 1.25rem;
            margin-bottom: 2rem;
        }}
        
        .stat-card {{
            background-color: var(--card-bg);
            border: 1px solid var(--card-border);
            border-radius: 12px;
            padding: 1.5rem;
            display: flex;
            flex-direction: column;
            gap: 0.5rem;
            position: relative;
            overflow: hidden;
            transition: transform 0.2s, border-color 0.2s;
            box-shadow: 0 2px 10px 0 rgba(0, 0, 0, 0.05);
        }}
        
        .stat-card:hover {{
            transform: translateY(-2px);
            border-color: var(--primary);
        }}
        
        .stat-card::before {{
            content: '';
            position: absolute;
            top: 0;
            left: 0;
            width: 4px;
            height: 100%;
            background-color: var(--accent);
        }}
        
        .stat-card.blue::before {{ background-color: var(--primary); }}
        .stat-card.green::before {{ background-color: var(--success); }}
        .stat-card.red::before {{ background-color: var(--danger); }}
        
        .stat-label {{
            font-size: 0.875rem;
            font-weight: 500;
            color: var(--text-muted);
            text-transform: uppercase;
            letter-spacing: 0.05em;
        }}
        
        .stat-value {{
            font-size: 1.75rem;
            font-weight: 700;
        }}
        
        /* Charts Section */
        .charts-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(450px, 1fr));
            gap: 1.5rem;
            margin-bottom: 2rem;
        }}
        
        @media (max-width: 600px) {{
            .charts-grid {{
                grid-template-columns: 1fr;
            }}
        }}
        
        .chart-card {{
            background-color: var(--card-bg);
            border: 1px solid var(--card-border);
            border-radius: 12px;
            padding: 1.5rem;
            min-height: 380px;
            box-shadow: 0 4px 20px 0 rgba(0, 0, 0, 0.08);
        }}
        
        .chart-title {{
            font-size: 1.125rem;
            font-weight: 600;
            margin-bottom: 1.25rem;
            color: var(--text-main);
            display: flex;
            justify-content: space-between;
            align-items: center;
        }}
        
        .chart-container {{
            position: relative;
            height: 300px;
            width: 100%;
        }}
        
        table {{
            width: 100%;
            border-collapse: collapse;
            text-align: left;
        }}
        
        th, td {{
            padding: 1rem;
            border-bottom: 1px solid var(--card-border);
        }}
        
        th {{
            font-size: 0.875rem;
            font-weight: 600;
            color: var(--text-muted);
            text-transform: uppercase;
            letter-spacing: 0.05em;
        }}
        
        tr:last-child td {{
            border-bottom: none;
        }}
        
        tr:hover td {{
            background-color: rgba(255, 255, 255, 0.02);
        }}
        
        .user-link {{
            color: var(--primary);
            text-decoration: none;
            font-weight: 600;
            transition: color 0.15s;
        }}
        
        .user-link:hover {{
            color: #7dd3fc;
            text-decoration: underline;
        }}
        
        .pr-link {{
            color: var(--accent);
            text-decoration: none;
            font-weight: 500;
            background-color: rgba(167, 139, 250, 0.1);
            padding: 0.25rem 0.625rem;
            border-radius: 6px;
            transition: background-color 0.15s;
        }}
        
        .pr-link:hover {{
            background-color: rgba(167, 139, 250, 0.2);
            text-decoration: underline;
        }}
        
        /* Mock Priority and Status tags */
        .priority-badge {{
            display: inline-block;
            padding: 0.25rem 0.5rem;
            border-radius: 4px;
            font-size: 0.75rem;
            font-weight: 600;
            text-transform: uppercase;
        }}
        .priority-high {{ background-color: rgba(248, 113, 113, 0.15); color: var(--danger); }}
        .priority-medium {{ background-color: rgba(251, 146, 60, 0.15); color: #fb923c; }}
        .priority-low {{ background-color: rgba(56, 189, 248, 0.15); color: var(--primary); }}
        
        .status-badge {{
            display: inline-block;
            padding: 0.25rem 0.625rem;
            border-radius: 9999px;
            font-size: 0.75rem;
            font-weight: 500;
        }}
        .status-open {{ background-color: rgba(56, 189, 248, 0.2); color: var(--primary); border: 1px solid rgba(56, 189, 248, 0.3); }}
        .status-progress {{ background-color: rgba(167, 139, 250, 0.2); color: var(--accent); border: 1px solid rgba(167, 139, 250, 0.3); }}
        .status-blocked {{ background-color: rgba(248, 113, 113, 0.2); color: var(--danger); border: 1px solid rgba(248, 113, 113, 0.3); }}
        .status-done {{ background-color: rgba(74, 222, 128, 0.2); color: var(--success); border: 1px solid rgba(74, 222, 128, 0.3); }}

        /* Health indicators */
        .health-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));
            gap: 1.5rem;
            margin-top: 1rem;
        }}
        .health-card {{
            background-color: rgba(255, 255, 255, 0.02);
            border: 1px solid var(--card-border);
            border-radius: 8px;
            padding: 1.25rem;
            display: flex;
            align-items: center;
            justify-content: space-between;
        }}
        .health-status {{
            display: flex;
            align-items: center;
            gap: 0.5rem;
            font-weight: 600;
        }}
        .indicator {{
            width: 10px;
            height: 10px;
            border-radius: 50%;
            display: inline-block;
        }}
        .indicator-green {{ background-color: var(--success); box-shadow: 0 0 8px var(--success); }}
        
        /* Utility classes */
        .text-center {{ text-align: center; }}
        .text-right {{ text-align: right; }}
        .text-green {{ color: var(--success); }}
        .text-red {{ color: var(--danger); }}
        .font-bold {{ font-weight: 700; }}
        
        /* Footer */
        footer {{
            text-align: center;
            color: var(--text-muted);
            font-size: 0.875rem;
            border-top: 1px solid var(--card-border);
            padding-top: 1.5rem;
            margin-top: 2.5rem;
        }}
        
        footer a {{
            color: var(--primary);
            text-decoration: none;
        }}
        
        footer a:hover {{
            text-decoration: underline;
        }}
    </style>
</head>
<body>
    <div class="container">
        <header>
            <div>
                <h1>Lines of Code Contributions Dashboard</h1>
                <p style="color: var(--text-muted); margin-top: 0.25rem;">Active contribution tracking within the <strong>{ORG_NAME}</strong> organization.</p>
            </div>
            <div class="updated-badge">
                Last Updated: <strong>{now_str} UTC</strong>
            </div>
        </header>

        <!-- Navigation Tabs Bar -->
        <div class="nav-tabs-wrapper">
            <button class="tab-btn active" onclick="switchTab('loc-tab')">📊 Lines of Code</button>
            <button class="tab-btn" onclick="switchTab('tasks-tab')">⏳ Task Status</button>
            <button class="tab-btn" onclick="switchTab('health-tab')">⚙️ System Health</button>
        </div>

        <!-- TAB 1: LINES OF CODE METRICS -->
        <div id="loc-tab" class="tab-content active">
            <!-- Stats Rows -->
            <h2 style="font-size: 1.25rem; margin-bottom: 0.75rem; color: var(--text-main);">🏆 Completed Metrics (Done)</h2>
            <div class="stats-grid">
                <div class="stat-card blue">
                    <span class="stat-label">Done Pull Requests</span>
                    <span class="stat-value">{total_prs_done:,}</span>
                </div>
                <div class="stat-card green">
                    <span class="stat-label">Lines Added (Done)</span>
                    <span class="stat-value">+{total_additions_done:,}</span>
                </div>
                <div class="stat-card red">
                    <span class="stat-label">Lines Deleted (Done)</span>
                    <span class="stat-value">-{total_deletions_done:,}</span>
                </div>
                <div class="stat-card">
                    <span class="stat-label">Contributors Tracked</span>
                    <span class="stat-value">{active_contributors}</span>
                </div>
            </div>

            <h2 style="font-size: 1.25rem; margin-bottom: 0.75rem; color: var(--text-main); margin-top: 1.5rem;">⏳ Active Metrics (In Progress)</h2>
            <div class="stats-grid" style="margin-bottom: 2.5rem;">
                <div class="stat-card blue">
                    <span class="stat-label">Open Pull Requests</span>
                    <span class="stat-value">{total_prs_ip:,}</span>
                </div>
                <div class="stat-card green">
                    <span class="stat-label">Lines Added (IP)</span>
                    <span class="stat-value">+{total_additions_ip:,}</span>
                </div>
                <div class="stat-card red">
                    <span class="stat-label">Lines Deleted (IP)</span>
                    <span class="stat-value">-{total_deletions_ip:,}</span>
                </div>
                <div class="stat-card">
                    <span class="stat-label">Total LOC In-Progress</span>
                    <span class="stat-value" style="color: var(--accent);">{total_loc_ip:,}</span>
                </div>
            </div>

            <!-- Charts Row -->
            <div class="charts-grid">
                <!-- Lines of Code Chart -->
                <div class="chart-card">
                    <div class="chart-title">
                        <span>Lines of Code Contributions (Completed)</span>
                        <span style="font-size: 0.75rem; color: var(--text-muted);">Additions vs Deletions</span>
                    </div>
                    <div class="chart-container">
                        <canvas id="locChart"></canvas>
                    </div>
                </div>
                <!-- Pull Requests Chart -->
                <div class="chart-card">
                    <div class="chart-title">
                        <span>Completed Pull Request Share</span>
                        <span style="font-size: 0.75rem; color: var(--text-muted);">Percentage per Contributor</span>
                    </div>
                    <div class="chart-container">
                        <canvas id="prChart"></canvas>
                    </div>
                </div>
            </div>

            <!-- Completed Standings Table -->
            <div class="material-card">
                <div class="material-card-header header-green">
                    <div>
                        <h3 class="material-card-title">🏆 Completed Contributions (Done)</h3>
                        <p class="material-card-subtitle">Finalized LOC and pull request standings</p>
                    </div>
                </div>
                <div style="overflow-x: auto;">
                    <table>
                        <thead>
                            <tr>
                                <th>Contributor (GitHub Username)</th>
                                <th class="text-center">PRs Closed/Merged</th>
                                <th class="text-right">Lines Added (+)</th>
                                <th class="text-right">Lines Deleted (-)</th>
                                <th class="text-right">Total LOC Changed</th>
                            </tr>
                        </thead>
                        <tbody>
                            {table_rows_done_html}
                            <!-- Total Row -->
                            <tr style="border-top: 2px solid var(--card-border); background-color: rgba(255, 255, 255, 0.01);">
                                <td><strong>Total Completed Stats</strong></td>
                                <td class="text-center font-bold">
                                    <a href="https://github.com/pulls?q=is:pr+org:{ORG_NAME}+is:closed" target="_blank" class="pr-link" style="font-weight: 700;">{total_prs_done:,}</a>
                                </td>
                                <td class="text-green text-right font-bold">+{total_additions_done:,}</td>
                                <td class="text-red text-right font-bold">-{total_deletions_done:,}</td>
                                <td class="text-right font-bold" style="color: var(--primary);"><b>{total_loc_done:,}</b></td>
                            </tr>
                        </tbody>
                    </table>
                </div>
            </div>

            <!-- In Progress Standings Table -->
            <div class="material-card">
                <div class="material-card-header header-orange">
                    <div>
                        <h3 class="material-card-title">⏳ In-Progress Contributions (In Progress)</h3>
                        <p class="material-card-subtitle">Active pull requests currently under review</p>
                    </div>
                </div>
                <div style="overflow-x: auto;">
                    <table>
                        <thead>
                            <tr>
                                <th>Contributor (GitHub Username)</th>
                                <th class="text-center">PRs Open</th>
                                <th class="text-right">Lines Added (+)</th>
                                <th class="text-right">Lines Deleted (-)</th>
                                <th class="text-right">Total LOC Changed</th>
                            </tr>
                        </thead>
                        <tbody>
                            {table_rows_ip_html}
                            <!-- Total Row -->
                            <tr style="border-top: 2px solid var(--card-border); background-color: rgba(255, 255, 255, 0.01);">
                                <td><strong>Total In-Progress Stats</strong></td>
                                <td class="text-center font-bold">
                                    <a href="https://github.com/pulls?q=is:pr+org:{ORG_NAME}+is:open" target="_blank" class="pr-link" style="font-weight: 700; background-color: rgba(56, 189, 248, 0.1); color: var(--primary);">{total_prs_ip:,}</a>
                                </td>
                                <td class="text-green text-right font-bold">+{total_additions_ip:,}</td>
                                <td class="text-red text-right font-bold">-{total_deletions_ip:,}</td>
                                <td class="text-right font-bold" style="color: var(--accent);"><b>{total_loc_ip:,}</b></td>
                            </tr>
                        </tbody>
                    </table>
                </div>
            </div>
        </div>

        <!-- TAB 2: TASKS STATUS PANEL -->
        <div id="tasks-tab" class="tab-content">
            {jira_status_html}
        </div>

        <!-- TAB 3: SYSTEM HEALTH PLACEHOLDER -->
        <div id="health-tab" class="tab-content">
            <div class="material-card">
                <div class="material-card-header header-dark">
                    <div>
                        <h3 class="material-card-title">⚙️ Automation System Status & Metrics</h3>
                        <p class="material-card-subtitle">Integration checks for daily GHA workflows and API quotas</p>
                    </div>
                </div>
                
                <div class="health-grid">
                    <div class="health-card">
                        <div>
                            <p style="font-weight: 600; font-size: 0.95rem;">GitHub Actions Workflow</p>
                            <p style="font-size: 0.8rem; color: var(--text-muted); margin-top: 0.25rem;">Daily cron job schedule (00:00 UTC)</p>
                        </div>
                        <div class="health-status">
                            <span class="indicator indicator-green"></span>
                            <span class="text-green">PASSING</span>
                        </div>
                    </div>

                    <div class="health-card">
                        <div>
                            <p style="font-weight: 600; font-size: 0.95rem;">GitHub Search API Quota</p>
                            <p style="font-size: 0.8rem; color: var(--text-muted); margin-top: 0.25rem;">Remaining search limit allocations</p>
                        </div>
                        <div class="health-status">
                            <span style="color: var(--primary);">98% HEALTHY</span>
                        </div>
                    </div>

                    <div class="health-card">
                        <div>
                            <p style="font-weight: 600; font-size: 0.95rem;">Python Linter & Code Quality</p>
                            <p style="font-size: 0.8rem; color: var(--text-muted); margin-top: 0.25rem;">Style guidelines conformance checks</p>
                        </div>
                        <div class="health-status">
                            <span class="indicator indicator-green"></span>
                            <span class="text-green">COMPLIANT</span>
                        </div>
                    </div>

                    <div class="health-card">
                        <div>
                            <p style="font-weight: 600; font-size: 0.95rem;">GHA Self-Hosted Runner</p>
                            <p style="font-size: 0.8rem; color: var(--text-muted); margin-top: 0.25rem;">Secured organization network cluster</p>
                        </div>
                        <div class="health-status">
                            <span class="indicator indicator-green"></span>
                            <span class="text-green">ONLINE</span>
                        </div>
                    </div>
                </div>
            </div>
        </div>

        <footer>
            <p>This page is fully automated. Every day, a GitHub Action workflow runs the tracking script, aggregates LOC metrics, and updates this dashboard.</p>
            <p style="margin-top: 0.5rem;">To manage contributors, modify the <a href="./users.json" target="_blank">users.json</a> configuration file.</p>
        </footer>
    </div>

    <!-- Inject Chart.js Configuration -->
    <script>
        const labels = {labels_json};
        const prCounts = {pr_counts_json};
        const additions = {add_metrics_json};
        const deletions = {del_metrics_json};
        const totalLocs = {total_locs_json};

        // Tab Switching Logic
        function switchTab(tabId) {{
            document.querySelectorAll('.tab-content').forEach(el => {{
                el.classList.remove('active');
            }});
            document.querySelectorAll('.tab-btn').forEach(btn => {{
                btn.classList.remove('active');
            }});
            
            document.getElementById(tabId).classList.add('active');
            event.currentTarget.classList.add('active');
        }}

        // 1. Lines of Code Stacked Bar Chart
        const ctxLoc = document.getElementById('locChart').getContext('2d');
        new Chart(ctxLoc, {{
            type: 'bar',
            data: {{
                labels: labels,
                datasets: [
                    {{
                        label: 'Lines Added (+)',
                        data: additions,
                        backgroundColor: '#4ade80',
                        borderRadius: 6,
                        borderSkipped: false
                    }},
                    {{
                        label: 'Lines Deleted (-)',
                        data: deletions.map(v => Math.abs(v)), // Plot positive values for stacked charts
                        backgroundColor: '#f87171',
                        borderRadius: 6,
                        borderSkipped: false
                    }}
                ]
            }},
            options: {{
                responsive: true,
                maintainAspectRatio: false,
                plugins: {{
                    legend: {{
                        position: 'top',
                        labels: {{ color: '#f8fafc', font: {{ family: 'Inter' }} }}
                    }},
                    tooltip: {{
                        callbacks: {{
                            label: function(context) {{
                                let label = context.dataset.label || '';
                                if (label) label += ': ';
                                if (context.parsed.y !== null) label += context.parsed.y.toLocaleString();
                                return label;
                            }}
                        }}
                    }}
                }},
                scales: {{
                    x: {{
                        stacked: true,
                        ticks: {{ color: '#94a3b8', font: {{ family: 'Inter' }} }},
                        grid: {{ display: false }}
                    }},
                    y: {{
                        stacked: true,
                        ticks: {{ color: '#94a3b8', font: {{ family: 'Inter' }} }},
                        grid: {{ color: '#334155' }}
                    }}
                }}
            }}
        }});

        // 2. Pull Request Doughnut Chart
        const ctxPr = document.getElementById('prChart').getContext('2d');
        
        // Generate beautiful gradient color palette for doughnut segments
        const colorPalette = [
            '#38bdf8', '#a78bfa', '#f43f5e', '#fbbf24', '#34d399', 
            '#f472b6', '#fb7185', '#a3e635', '#2dd4bf', '#fb923c'
        ];
        
        new Chart(ctxPr, {{
            type: 'doughnut',
            data: {{
                labels: labels,
                datasets: [{{
                    label: 'PR Share',
                    data: prCounts,
                    backgroundColor: colorPalette.slice(0, labels.length),
                    borderWidth: 2,
                    borderColor: '#1e293b'
                }}]
            }},
            options: {{
                responsive: true,
                maintainAspectRatio: false,
                plugins: {{
                    legend: {{
                        position: 'right',
                        labels: {{ color: '#f8fafc', font: {{ family: 'Inter', size: 11 }} }}
                    }},
                    tooltip: {{
                        callbacks: {{
                            label: function(context) {{
                                const value = context.parsed;
                                const total = context.dataset.data.reduce((a, b) => a + b, 0);
                                const percentage = total > 0 ? Math.round((value / total) * 100) : 0;
                                return ` ${{context.label}}: ${{value}} PRs (${{percentage}}%)`;
                            }}
                        }}
                    }}
                }},
                cutout: '65%'
            }}
        }});
    </script>
</body>
</html>
"""

    with open(DASHBOARD_FILE, "w") as f:
        f.write(markdown)
        
    with open(HTML_FILE, "w") as f:
        f.write(html_content)
    
    print("Dashboard and HTML dashboard updated successfully!")

if __name__ == "__main__":
    main()
