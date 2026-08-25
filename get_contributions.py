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
        
        /* Stats Grid */
        .stats-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
            gap: 1.25rem;
            margin-bottom: 1.5rem;
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
            margin-bottom: 2.5rem;
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
        
        /* Table Card */
        .table-card {{
            background-color: var(--card-bg);
            border: 1px solid var(--card-border);
            border-radius: 12px;
            padding: 1.5rem;
            overflow-x: auto;
            margin-bottom: 2.5rem;
        }}
        
        .table-title {{
            font-size: 1.25rem;
            font-weight: 600;
            margin-bottom: 1.25rem;
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
            margin-top: 1.5rem;
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
        <div class="table-card">
            <h2 class="table-title">🏆 Completed Contributions (Done)</h2>
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

        <!-- In Progress Standings Table -->
        <div class="table-card">
            <h2 class="table-title">⏳ In-Progress Contributions (In Progress)</h2>
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
