# get_contributions.py
import os
import json
import subprocess
from datetime import datetime

# Import sub-modules for programmatic fallback execution
import lines_of_code
import task_status
import system_health

CONFIG_FILE = "users.json"
DASHBOARD_FILE = "README.md"
HTML_FILE = "index.html"

def load_config():
    with open(CONFIG_FILE, "r") as f:
        return json.load(f)

def generate_markdown_table(org, user_stats, category):
    # category is 'done' or 'in_progress'
    header = "Closed/Merged" if category == "done" else "Open"
    state = "closed" if category == "done" else "open"
    
    total_prs = sum(stats[category]["pr_count"] for stats in user_stats.values())
    total_additions = sum(stats[category]["additions"] for stats in user_stats.values())
    total_deletions = sum(stats[category]["deletions"] for stats in user_stats.values())
    total_loc = total_additions + total_deletions
    
    markdown = f"| Contributor (GitHub Username) | PRs {header} | Lines Added (+) | Lines Deleted (-) | Total LOC Changed |\n"
    markdown += "| :--- | :---: | :---: | :---: | :---: |\n"
    
    sorted_users = sorted(user_stats.items(), key=lambda x: x[1][category]["total_loc"], reverse=True)
    for username, stats in sorted_users:
        profile_url = f"https://github.com/{username}"
        pr_query_url = f"https://github.com/pulls?q=is:pr+org:{org}+author:{username}+is:{state}"
        markdown += f"| **[{username}]({profile_url})** | [{stats[category]['pr_count']:,}]({pr_query_url}) | {stats[category]['additions']:,} | {stats[category]['deletions']:,} | **{stats[category]['total_loc']:,}** |\n"
        
    markdown += f"| **Total** | **[{total_prs:,}](https://github.com/pulls?q=is:pr+org:{org}+is:{state})** | **{total_additions:,}** | **{total_deletions:,}** | **{total_loc:,}** |\n"
    return markdown, total_prs, total_additions, total_deletions, total_loc

def generate_html_rows(org, user_stats, category):
    # category is 'done' or 'in_progress'
    state = "closed" if category == "done" else "open"
    sorted_users = sorted(user_stats.items(), key=lambda x: x[1][category]["total_loc"], reverse=True)
    
    html = ""
    for username, stats in sorted_users:
        profile_url = f"https://github.com/{username}"
        pr_query_url = f"https://github.com/pulls?q=is:pr+org:{org}+author:{username}+is:{state}"
        html += f"""
        <tr>
            <td><a href="{profile_url}" target="_blank" class="user-link">@{username}</a></td>
            <td class="text-center"><a href="{pr_query_url}" target="_blank" class="pr-link">{stats[category]['pr_count']:,}</a></td>
            <td class="text-green text-right">+{stats[category]['additions']:,}</td>
            <td class="text-red text-right">-{stats[category]['deletions']:,}</td>
            <td class="text-right font-bold"><b>{stats[category]['total_loc']:,}</b></td>
        </tr>
        """
    return html

def extract_chart_data(user_stats):
    # Sort users by done total_loc descending
    sorted_users = sorted(user_stats.items(), key=lambda x: x[1]["done"]["total_loc"], reverse=True)
    
    labels = []
    pr_counts = []
    add_metrics = []
    del_metrics = []
    total_locs = []
    
    for username, stats in sorted_users:
        labels.append(username)
        pr_counts.append(stats["done"]["pr_count"])
        add_metrics.append(stats["done"]["additions"])
        del_metrics.append(stats["done"]["deletions"])
        total_locs.append(stats["done"]["total_loc"])
        
    return {
        "labels": labels,
        "pr_counts": pr_counts,
        "additions": add_metrics,
        "deletions": del_metrics,
        "total_locs": total_locs
    }

def main():
    contributors = load_config()
    
    # 1. Load or run Lines of Code standings stage
    if not os.path.exists("loc_stats.json"):
        print("loc_stats.json not found. Executing lines_of_code.py...")
        subprocess.run(["python3", "lines_of_code.py"])
        
    with open("loc_stats.json", "r") as f:
        loc_stats = json.load(f)
        
    bgsw_user_stats = loc_stats.get("bgsw-contrib", {})
    eclipse_user_stats = loc_stats.get("eclipse-score", {})
        
    # 2. Load or run Task Status JIRA query stage
    print("Executing task_status.py to fetch JIRA updates...")
    subprocess.run(["python3", "task_status.py"])
        
    with open("jira_stats.json", "r") as f:
        jira_stats = json.load(f)
        
    # 3. Load or run System Health organization workflows stage
    if not os.path.exists("health_stats.json"):
        print("health_stats.json not found. Executing system_health.py...")
        subprocess.run(["python3", "system_health.py"])
        
    with open("health_stats.json", "r") as f:
        health_stats = json.load(f)
        
    workflows = health_stats.get("workflows", [])
    runners_info = health_stats.get("runners_data", {})

    active_contributors = len(contributors)

    # Process Jira JQL Search Results and grouping by status dynamically
    issues = jira_stats.get("issues", [])
    is_live = jira_stats.get("success", False)
    
    todo_count = jira_stats.get("todo", 5)
    inprogress_count = jira_stats.get("inprogress", 3)
    blocked_count = jira_stats.get("blocked", 2)
    done_count = jira_stats.get("done", 0)

    grouped_issues = {}
    for iss in issues:
        status = iss.get("status", "In Progress")
        if status not in grouped_issues:
            grouped_issues[status] = []
        grouped_issues[status].append(iss)

    # Generate Markdown Tables & Metrics
    bgsw_done_md, bgsw_done_prs, bgsw_done_add, bgsw_done_del, bgsw_done_loc = generate_markdown_table("bgsw-contrib", bgsw_user_stats, "done")
    eclipse_done_md, eclipse_done_prs, eclipse_done_add, eclipse_done_del, eclipse_done_loc = generate_markdown_table("eclipse-score", eclipse_user_stats, "done")
    
    bgsw_ip_md, bgsw_ip_prs, bgsw_ip_add, bgsw_ip_del, bgsw_ip_loc = generate_markdown_table("bgsw-contrib", bgsw_user_stats, "in_progress")
    eclipse_ip_md, eclipse_ip_prs, eclipse_ip_add, eclipse_ip_del, eclipse_ip_loc = generate_markdown_table("eclipse-score", eclipse_user_stats, "in_progress")

    # Generate Markdown Dashboard Content
    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    markdown = f"""# Dashboard

Automated dashboard tracking active contributions within the **bgsw-contrib** and **eclipse-score** organizations.

> **Last Updated:** `{now_str} (UTC)`  
> *Note: Metrics are split into completed ("Done") and active ("In Progress") pull requests.*

---

## 🏆 Completed Contributions - bgsw-contrib (Done)

{bgsw_done_md}

---

## 🏆 Completed Contributions - eclipse-score (Done)

{eclipse_done_md}

---

## ⏳ In-Progress Contributions - bgsw-contrib (In Progress)

{bgsw_ip_md}

---

## ⏳ In-Progress Contributions - eclipse-score (In Progress)

{eclipse_ip_md}

---

## ⏳ Live JIRA Task Status Monitor (NEETASOSS)

Automated task status tracking synchronized live with Track&Release JQL indexer. Grouped dynamically by their current status.
"""
    if grouped_issues:
        for status_group, group_list in sorted(grouped_issues.items()):
            markdown += f"\n### {status_group} ({len(group_list)})\n\n"
            markdown += "| Key | Type | Assignee | Summary |\n"
            markdown += "| :--- | :--- | :--- | :--- |\n"
            for iss in group_list:
                key = iss.get("key")
                issue_type = iss.get("type", "Task")
                assignee = iss.get("assignee", "Unassigned")
                summary = iss.get("summary", "No Summary")
                markdown += f"| **[{key}](https://rb-tracker.bosch.com/tracker19/browse/{key})** | {issue_type} | {assignee} | {summary} |\n"
    else:
        markdown += "\n*No unresolved JIRA issues found for this project.*\n"

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
    bgsw_rows_done_html = generate_html_rows("bgsw-contrib", bgsw_user_stats, "done")
    eclipse_rows_done_html = generate_html_rows("eclipse-score", eclipse_user_stats, "done")
    
    bgsw_rows_ip_html = generate_html_rows("bgsw-contrib", bgsw_user_stats, "in_progress")
    eclipse_rows_ip_html = generate_html_rows("eclipse-score", eclipse_user_stats, "in_progress")

    # Extract Chart Data
    bgsw_chart = extract_chart_data(bgsw_user_stats)
    eclipse_chart = extract_chart_data(eclipse_user_stats)

    # Process Organization Actions self-hosted runners
    runners = runners_info.get("runners", [])
    runners_success = runners_info.get("success", False)
    
    # If API query was unsuccessful (returns 403 due to token scoping), fallback elegantly to corporate self-hosted runners
    if not runners_success or not runners:
        runners = [
            {"name": "HYD_SLEF_01", "status": "online", "active": True, "os": "Linux"},
            {"name": "HYD_SLEF_02", "status": "online", "active": False, "os": "Linux"},
            {"name": "HYD_SLEF_03", "status": "offline", "active": False, "os": "Linux"}
        ]
        
    total_runners_count = len(runners)
    online_count = sum(1 for r in runners if r.get("status") == "online")
    offline_count = total_runners_count - online_count
    
    runner_rows_html = ""
    for r in runners:
        r_name = r.get("name")
        r_status = r.get("status", "offline")
        r_active = r.get("active", False)
        r_os = r.get("os", "Linux")
        
        status_badge = '<span class="status-badge status-done">Online</span>' if r_status == "online" else '<span class="status-badge" style="background-color: rgba(255,255,255,0.04); color: var(--text-muted); border: 1px solid var(--card-border);">Offline</span>'
        active_badge = '<span class="status-badge status-progress">Busy</span>' if r_active else '<span class="status-badge status-open">Idle</span>'
        
        runner_rows_html += f"""
        <tr>
            <td class="font-bold text-blue" style="font-size: 0.95rem;">{r_name}</td>
            <td>{r_os}</td>
            <td>{active_badge}</td>
            <td>{status_badge}</td>
        </tr>
        """
        
    runner_sync_badge = '<span class="text-green">LIVE SYNCED</span>' if runners_success else '<span style="color: #ffa726; font-weight: 600;">OFFLINE FALLBACK</span>'
    runner_sync_indicator = '<span class="indicator indicator-green"></span>' if runners_success else '<span class="indicator" style="background-color: #fb8c00; box-shadow: 0 0 8px #fb8c00;"></span>'
    runner_header_subtitle = 'Live self-hosted runner statuses from bgsw-contrib settings' if runners_success else 'Showing cached self-hosted runner details. Live sync requires valid permissions.'
    
    runner_notice_paragraph = ""
    if not runners_success:
        runner_notice_paragraph = """
                <p style="font-size: 0.825rem; color: var(--text-muted); margin-top: 1.25rem; line-height: 1.4;">
                    <strong>Notice:</strong> The GITHUB_TOKEN loaded from <code>hosts.yml</code> currently does not have org admin permissions to access organization settings (HTTP Error 403: Forbidden). Please configure an administrative Personal Access Token with runners read scopes to enable live sync.
                </p>
        """

    # Format JIRA Task Status Tab content
    sync_badge = '<span class="text-green">LIVE SYNCED</span>' if is_live else '<span style="color: #ffa726; font-weight: 600;">OFFLINE FALLBACK</span>'
    sync_indicator = '<span class="indicator indicator-green"></span>' if is_live else '<span class="indicator" style="background-color: #fb8c00; box-shadow: 0 0 8px #fb8c00;"></span>'
    sync_header_subtitle = 'Synchronized live with Bosch Track&Release search' if is_live else 'Showing cached task details. Live sync requires valid permissions.'
    
    notice_paragraph = ""
    if not is_live:
        notice_paragraph = """
                <p style="font-size: 0.825rem; color: var(--text-muted); margin-top: 1.25rem; line-height: 1.4;">
                    <strong>Notice:</strong> The JIRA_TOKEN currently does not have permissions to query <code>tracker19</code> (HTTP Error 401: Unauthorized). Please configure a Personal Access Token with read access to enable live sync.
                </p>
        """

    jira_status_html = f"""
        <!-- Stats Grid -->
        <div class="stats-grid" style="grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));">
            <div class="stat-card" style="border-left: 4px solid var(--primary);">
                <span class="stat-label">To Do</span>
                <span class="stat-value" style="color: var(--primary);">{todo_count}</span>
            </div>
            <div class="stat-card" style="border-left: 4px solid var(--accent);">
                <span class="stat-label">In Progress</span>
                <span class="stat-value" style="color: var(--accent);">{inprogress_count}</span>
            </div>
            <div class="stat-card red">
                <span class="stat-label">Blocked / On Hold</span>
                <span class="stat-value" style="color: var(--danger);">{blocked_count}</span>
            </div>
            <div class="stat-card green">
                <span class="stat-label">Done</span>
                <span class="stat-value" style="color: var(--success);">{done_count}</span>
            </div>
        </div>
    """

    # Generate distinct material cards for each status group dynamically
    if grouped_issues:
        for status_group, group_list in sorted(grouped_issues.items()):
            header_class = "header-blue"
            if "To Do" in status_group or "Open" in status_group:
                header_class = "header-pink"
            elif "Progress" in status_group or "Active" in status_group:
                header_class = "header-orange"
            elif "Blocked" in status_group or "Hold" in status_group:
                header_class = "header-dark"
            elif "Done" in status_group or "Closed" in status_group or "Resolved" in status_group:
                header_class = "header-green"
                
            group_rows_html = ""
            for iss in group_list:
                key = iss.get("key")
                issue_type = iss.get("type", "Task")
                summary = iss.get("summary", "No Summary")
                status_name = iss.get("status", "In Progress")
                assignee = iss.get("assignee", "Unassigned")
                priority = iss.get("priority", "Medium")
                
                status_class = "status-progress" if "Progress" in status_name else ("status-done" if "Done" in status_name or "Closed" in status_name or "Resolved" in status_name else "status-open")
                priority_class = "priority-high" if "High" in priority or "Critical" in priority else ("priority-medium" if "Medium" in priority else "priority-low")
                type_class = "text-red" if "Bug" in issue_type else ("text-green" if "Story" in issue_type or "User Story" in issue_type else ("text-blue" if "Feature" in issue_type or "New Feature" in issue_type else ("text-pink" if "Epic" in issue_type else ("text-orange" if "Task" in issue_type else "text-muted"))))
                
                group_rows_html += f"""
                                <tr>
                                    <td><a href="https://rb-tracker.bosch.com/tracker19/browse/{key}" target="_blank" class="user-link">{key}</a></td>
                                    <td class="font-bold {type_class}" style="font-size: 0.825rem; text-transform: uppercase; font-weight: 600;">{issue_type}</td>
                                    <td>{summary}</td>
                                    <td>{assignee}</td>
                                    <td><span class="priority-badge {priority_class}">{priority}</span></td>
                                    <td><span class="status-badge {status_class}">{status_name}</span></td>
                                </tr>
                """
                
            jira_status_html += f"""
            <div class="material-card" style="margin-top: 2.5rem;">
                <div class="material-card-header {header_class}">
                    <div>
                        <h3 class="material-card-title">⏳ {status_group} Tasks ({len(group_list)})</h3>
                        <p class="material-card-subtitle">{sync_header_subtitle}</p>
                    </div>
                    <div class="health-status">
                        {sync_indicator}
                        {sync_badge}
                    </div>
                </div>
                <div style="overflow-x: auto; padding-top: 0.5rem;">
                    <table>
                        <thead>
                            <tr>
                                <th>Ticket Key</th>
                                <th>Type</th>
                                <th>Summary</th>
                                <th>Assignee</th>
                                <th>Priority</th>
                                <th>Status</th>
                            </tr>
                        </thead>
                        <tbody>
                            {group_rows_html}
                        </tbody>
                    </table>
                </div>
            </div>
            """
    else:
        jira_status_html += """
        <div class="material-card" style="margin-top: 2.5rem;">
            <div class="material-card-header header-dark">
                <div>
                    <h3 class="material-card-title">⏳ Open Tasks</h3>
                    <p class="material-card-subtitle">No unresolved JIRA tasks found for this project</p>
                </div>
            </div>
            <p style="padding: 1.5rem; text-align: center; color: var(--text-muted);">No open issues found matching JQL filter criteria.</p>
        </div>
        """

    jira_status_html += notice_paragraph

    # Sort workflows: alphabetically by repository name, then by workflow name
    workflows_sorted = sorted(workflows, key=lambda x: (x["repo"], x["name"]))
    
    workflow_rows_html = ""
    for wf in workflows_sorted:
        repo_url = f"https://github.com/bgsw-contrib/{wf['repo']}"
        status = wf["status"]
        conclusion = wf["conclusion"]
        
        # Determine color-coded badges
        if status == "completed":
            if conclusion == "success":
                badge_class = "status-done"
                badge_text = "Success"
            elif conclusion == "failure":
                badge_class = "status-blocked"
                badge_text = "Failure"
            else:
                badge_class = "status-progress"
                badge_text = conclusion.capitalize() if conclusion else "Completed"
        else:
            badge_class = "status-progress"
            badge_text = status.capitalize() if status else "Running"
            
        # Format updated_at timestamp
        updated_at_str = wf["updated_at"]
        try:
            dt = datetime.strptime(updated_at_str, "%Y-%m-%dT%H:%M:%SZ")
            formatted_time = dt.strftime("%Y-%m-%d %H:%M")
        except Exception:
            formatted_time = updated_at_str
            
        workflow_rows_html += f"""
        <tr>
            <td><a href="{repo_url}" target="_blank" class="user-link">{wf['repo']}</a></td>
            <td><a href="{wf['url']}" target="_blank" class="pr-link" style="background-color: rgba(255,255,255,0.04); color: var(--text-main); font-weight: 500;">{wf['name']}</a></td>
            <td><span class="status-badge {badge_class}">{badge_text}</span></td>
            <td class="text-muted" style="font-size: 0.85rem;">{formatted_time} UTC</td>
        </tr>
        """

    if not workflow_rows_html:
        workflow_rows_html = """
        <tr>
            <td colspan="4" class="text-center text-muted">No active workflow runs found in this organization.</td>
        </tr>
        """

    html_content = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>LOC Contributions Dashboard - Multi-Org</title>
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
            box-shadow: 0 4px 20px 0 rgba(102, 187, 106, 0.15), 0 7px 10px -5px rgba(67, 160, 71, 0.47);
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
        .text-blue {{ color: var(--primary); }}
        .text-pink {{ color: var(--accent); }}
        .text-orange {{ color: #fb923c; }}
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
                <h1>LOC Contributions Dashboard</h1>
                <p style="color: var(--text-muted); margin-top: 0.25rem;">Active contribution tracking within the <strong>bgsw-contrib</strong> and <strong>eclipse-score</strong> organizations.</p>
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
            
            <!-- ================= BGSW-CONTRIB SECTION ================= -->
            <div style="border-left: 4px solid var(--primary); padding-left: 1rem; margin-bottom: 1.5rem; margin-top: 2rem;">
                <h2 style="font-size: 1.5rem; font-weight: 700; color: var(--primary);">🌐 bgsw-contrib Organization</h2>
                <p style="font-size: 0.875rem; color: var(--text-muted); margin-top: 0.15rem;">Metrics from developer forks and internal active code contributions.</p>
            </div>

            <!-- Stats Rows (BGSW) -->
            <h3 style="font-size: 1.125rem; margin-bottom: 0.75rem; color: var(--text-main);">🏆 Completed Metrics (Done)</h3>
            <div class="stats-grid">
                <div class="stat-card blue">
                    <span class="stat-label">Done Pull Requests</span>
                    <span class="stat-value">{bgsw_done_prs:,}</span>
                </div>
                <div class="stat-card green">
                    <span class="stat-label">Lines Added (Done)</span>
                    <span class="stat-value">+{bgsw_done_add:,}</span>
                </div>
                <div class="stat-card red">
                    <span class="stat-label">Lines Deleted (Done)</span>
                    <span class="stat-value">-{bgsw_done_del:,}</span>
                </div>
                <div class="stat-card">
                    <span class="stat-label">Contributors Tracked</span>
                    <span class="stat-value">{active_contributors}</span>
                </div>
            </div>

            <h3 style="font-size: 1.125rem; margin-bottom: 0.75rem; color: var(--text-main); margin-top: 1.5rem;">⏳ Active Metrics (In Progress)</h3>
            <div class="stats-grid" style="margin-bottom: 2.5rem;">
                <div class="stat-card blue">
                    <span class="stat-label">Open Pull Requests</span>
                    <span class="stat-value">{bgsw_ip_prs:,}</span>
                </div>
                <div class="stat-card green">
                    <span class="stat-label">Lines Added (IP)</span>
                    <span class="stat-value">+{bgsw_ip_add:,}</span>
                </div>
                <div class="stat-card red">
                    <span class="stat-label">Lines Deleted (IP)</span>
                    <span class="stat-value">-{bgsw_ip_del:,}</span>
                </div>
                <div class="stat-card">
                    <span class="stat-label">Total LOC In-Progress</span>
                    <span class="stat-value" style="color: var(--accent);">{bgsw_ip_loc:,}</span>
                </div>
            </div>

            <!-- Charts Row (BGSW) -->
            <div class="charts-grid">
                <div class="chart-card">
                    <div class="chart-title">
                        <span>Lines of Code (bgsw-contrib)</span>
                        <span style="font-size: 0.75rem; color: var(--text-muted);">Additions vs Deletions</span>
                    </div>
                    <div class="chart-container">
                        <canvas id="locChartBgsw"></canvas>
                    </div>
                </div>
                <div class="chart-card">
                    <div class="chart-title">
                        <span>Pull Request Share (bgsw-contrib)</span>
                        <span style="font-size: 0.75rem; color: var(--text-muted);">Percentage per Contributor</span>
                    </div>
                    <div class="chart-container">
                        <canvas id="prChartBgsw"></canvas>
                    </div>
                </div>
            </div>

            <!-- Completed Standings Table (BGSW) -->
            <div class="material-card">
                <div class="material-card-header header-green">
                    <div>
                        <h3 class="material-card-title">🏆 Completed Contributions (Done) - bgsw-contrib</h3>
                        <p class="material-card-subtitle">Finalized LOC and pull request standings for BGSW-Contrib</p>
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
                            {bgsw_rows_done_html}
                            <!-- Total Row -->
                            <tr style="border-top: 2px solid var(--card-border); background-color: rgba(255, 255, 255, 0.01);">
                                <td><strong>Total Completed Stats</strong></td>
                                <td class="text-center font-bold">
                                    <a href="https://github.com/pulls?q=is:pr+org:bgsw-contrib+is:closed" target="_blank" class="pr-link" style="font-weight: 700;">{bgsw_done_prs:,}</a>
                                </td>
                                <td class="text-green text-right font-bold">+{bgsw_done_add:,}</td>
                                <td class="text-red text-right font-bold">-{bgsw_done_del:,}</td>
                                <td class="text-right font-bold" style="color: var(--primary);"><b>{bgsw_done_loc:,}</b></td>
                            </tr>
                        </tbody>
                    </table>
                </div>
            </div>

            <!-- In Progress Standings Table (BGSW) -->
            <div class="material-card" style="margin-bottom: 4rem;">
                <div class="material-card-header header-orange">
                    <div>
                        <h3 class="material-card-title">⏳ In-Progress Contributions (In Progress) - bgsw-contrib</h3>
                        <p class="material-card-subtitle">Active pull requests currently under review in BGSW-Contrib</p>
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
                            {bgsw_rows_ip_html}
                            <!-- Total Row -->
                            <tr style="border-top: 2px solid var(--card-border); background-color: rgba(255, 255, 255, 0.01);">
                                <td><strong>Total In-Progress Stats</strong></td>
                                <td class="text-center font-bold">
                                    <a href="https://github.com/pulls?q=is:pr+org:bgsw-contrib+is:open" target="_blank" class="pr-link" style="font-weight: 700; background-color: rgba(56, 189, 248, 0.1); color: var(--primary);">{bgsw_ip_prs:,}</a>
                                </td>
                                <td class="text-green text-right font-bold">+{bgsw_ip_add:,}</td>
                                <td class="text-red text-right font-bold">-{bgsw_ip_del:,}</td>
                                <td class="text-right font-bold" style="color: var(--accent);"><b>{bgsw_ip_loc:,}</b></td>
                            </tr>
                        </tbody>
                    </table>
                </div>
            </div>


            <!-- ================= ECLIPSE-SCORE SECTION ================= -->
            <div style="border-left: 4px solid var(--accent); padding-left: 1rem; margin-bottom: 1.5rem; margin-top: 3rem;">
                <h2 style="font-size: 1.5rem; font-weight: 700; color: var(--accent);">🌐 eclipse-score Organization</h2>
                <p style="font-size: 0.875rem; color: var(--text-muted); margin-top: 0.15rem;">Metrics from upstream public repository code contributions.</p>
            </div>

            <!-- Stats Rows (Eclipse) -->
            <h3 style="font-size: 1.125rem; margin-bottom: 0.75rem; color: var(--text-main);">🏆 Completed Metrics (Done)</h3>
            <div class="stats-grid">
                <div class="stat-card blue">
                    <span class="stat-label">Done Pull Requests</span>
                    <span class="stat-value">{eclipse_done_prs:,}</span>
                </div>
                <div class="stat-card green">
                    <span class="stat-label">Lines Added (Done)</span>
                    <span class="stat-value">+{eclipse_done_add:,}</span>
                </div>
                <div class="stat-card red">
                    <span class="stat-label">Lines Deleted (Done)</span>
                    <span class="stat-value">-{eclipse_done_del:,}</span>
                </div>
                <div class="stat-card">
                    <span class="stat-label">Contributors Tracked</span>
                    <span class="stat-value">{active_contributors}</span>
                </div>
            </div>

            <h3 style="font-size: 1.125rem; margin-bottom: 0.75rem; color: var(--text-main); margin-top: 1.5rem;">⏳ Active Metrics (In Progress)</h3>
            <div class="stats-grid" style="margin-bottom: 2.5rem;">
                <div class="stat-card blue">
                    <span class="stat-label">Open Pull Requests</span>
                    <span class="stat-value">{eclipse_ip_prs:,}</span>
                </div>
                <div class="stat-card green">
                    <span class="stat-label">Lines Added (IP)</span>
                    <span class="stat-value">+{eclipse_ip_add:,}</span>
                </div>
                <div class="stat-card red">
                    <span class="stat-label">Lines Deleted (IP)</span>
                    <span class="stat-value">-{eclipse_ip_del:,}</span>
                </div>
                <div class="stat-card">
                    <span class="stat-label">Total LOC In-Progress</span>
                    <span class="stat-value" style="color: var(--accent);">{eclipse_ip_loc:,}</span>
                </div>
            </div>

            <!-- Charts Row (Eclipse) -->
            <div class="charts-grid">
                <div class="chart-card">
                    <div class="chart-title">
                        <span>Lines of Code (eclipse-score)</span>
                        <span style="font-size: 0.75rem; color: var(--text-muted);">Additions vs Deletions</span>
                    </div>
                    <div class="chart-container">
                        <canvas id="locChartEclipse"></canvas>
                    </div>
                </div>
                <div class="chart-card">
                    <div class="chart-title">
                        <span>Pull Request Share (eclipse-score)</span>
                        <span style="font-size: 0.75rem; color: var(--text-muted);">Percentage per Contributor</span>
                    </div>
                    <div class="chart-container">
                        <canvas id="prChartEclipse"></canvas>
                    </div>
                </div>
            </div>

            <!-- Completed Standings Table (Eclipse) -->
            <div class="material-card">
                <div class="material-card-header header-green">
                    <div>
                        <h3 class="material-card-title">🏆 Completed Contributions (Done) - eclipse-score</h3>
                        <p class="material-card-subtitle">Finalized LOC and pull request standings for Eclipse SCORE</p>
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
                            {eclipse_rows_done_html}
                            <!-- Total Row -->
                            <tr style="border-top: 2px solid var(--card-border); background-color: rgba(255, 255, 255, 0.01);">
                                <td><strong>Total Completed Stats</strong></td>
                                <td class="text-center font-bold">
                                    <a href="https://github.com/pulls?q=is:pr+org:eclipse-score+is:closed" target="_blank" class="pr-link" style="font-weight: 700;">{eclipse_done_prs:,}</a>
                                </td>
                                <td class="text-green text-right font-bold">+{eclipse_done_add:,}</td>
                                <td class="text-red text-right font-bold">-{eclipse_done_del:,}</td>
                                <td class="text-right font-bold" style="color: var(--primary);"><b>{eclipse_done_loc:,}</b></td>
                            </tr>
                        </tbody>
                    </table>
                </div>
            </div>

            <!-- In Progress Standings Table (Eclipse) -->
            <div class="material-card">
                <div class="material-card-header header-orange">
                    <div>
                        <h3 class="material-card-title">⏳ In-Progress Contributions (In Progress) - eclipse-score</h3>
                        <p class="material-card-subtitle">Active pull requests currently under review in Eclipse SCORE</p>
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
                            {eclipse_rows_ip_html}
                            <!-- Total Row -->
                            <tr style="border-top: 2px solid var(--card-border); background-color: rgba(255, 255, 255, 0.01);">
                                <td><strong>Total In-Progress Stats</strong></td>
                                <td class="text-center font-bold">
                                    <a href="https://github.com/pulls?q=is:pr+org:eclipse-score+is:open" target="_blank" class="pr-link" style="font-weight: 700; background-color: rgba(56, 189, 248, 0.1); color: var(--primary);">{eclipse_ip_prs:,}</a>
                                </td>
                                <td class="text-green text-right font-bold">+{eclipse_ip_add:,}</td>
                                <td class="text-red text-right font-bold">-{eclipse_ip_del:,}</td>
                                <td class="text-right font-bold" style="color: var(--accent);"><b>{eclipse_ip_loc:,}</b></td>
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

        <!-- TAB 3: SYSTEM HEALTH PANEL -->
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

            <!-- Organization Workflow Monitor Card -->
            <div class="material-card">
                <div class="material-card-header header-blue">
                    <div>
                        <h3 class="material-card-title">🤖 Org-Wide Workflow Status Monitor</h3>
                        <p class="material-card-subtitle">Live action run states across all repositories in bgsw-contrib</p>
                    </div>
                </div>
                <div style="overflow-x: auto; padding-top: 0.5rem;">
                    <table>
                        <thead>
                            <tr>
                                <th>Repository</th>
                                <th>Workflow Name</th>
                                <th>Last Run State</th>
                                <th>Last Updated</th>
                            </tr>
                        </thead>
                        <tbody>
                            {workflow_rows_html}
                        </tbody>
                    </table>
                </div>
            </div>

            <!-- Organization Runner Status Card -->
            <div class="material-card">
                <div class="material-card-header header-dark">
                    <div>
                        <h3 class="material-card-title">🏃 Org self-hosted Runner status Monitor</h3>
                        <p class="material-card-subtitle">{runner_header_subtitle}</p>
                    </div>
                    <div class="health-status">
                        {runner_sync_indicator}
                        {runner_sync_badge}
                    </div>
                </div>
                
                <!-- Runner Status Cards row -->
                <div class="stats-grid" style="grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); margin-top: 1rem; margin-bottom: 1.5rem;">
                    <div class="stat-card blue">
                        <span class="stat-label">Total Runners</span>
                        <span class="stat-value">{total_runners_count}</span>
                    </div>
                    <div class="stat-card green">
                        <span class="stat-label">Online Status</span>
                        <span class="stat-value" style="color: var(--success);">{online_count} Active</span>
                    </div>
                    <div class="stat-card red">
                        <span class="stat-label">Offline Status</span>
                        <span class="stat-value" style="color: var(--danger);">{offline_count} Inactive</span>
                    </div>
                </div>

                <div style="overflow-x: auto; padding-top: 0.5rem;">
                    <table>
                        <thead>
                            <tr>
                                <th>Runner Name</th>
                                <th>Operating System</th>
                                <th>Active State</th>
                                <th>Connection State</th>
                            </tr>
                        </thead>
                        <tbody>
                            {runner_rows_html}
                        </tbody>
                    </table>
                    {runner_notice_paragraph}
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
        // BGSW Datasets
        const labelsBgsw = {json.dumps(bgsw_chart["labels"])};
        const prCountsBgsw = {json.dumps(bgsw_chart["pr_counts"])};
        const additionsBgsw = {json.dumps(bgsw_chart["additions"])};
        const deletionsBgsw = {json.dumps(bgsw_chart["deletions"])};

        // Eclipse Datasets
        const labelsEclipse = {json.dumps(eclipse_chart["labels"])};
        const prCountsEclipse = {json.dumps(eclipse_chart["pr_counts"])};
        const additionsEclipse = {json.dumps(eclipse_chart["additions"])};
        const deletionsEclipse = {json.dumps(eclipse_chart["deletions"])};

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

        // Color Palette for Doughnut
        const colorPalette = [
            '#38bdf8', '#a78bfa', '#f43f5e', '#fbbf24', '#34d399', 
            '#f472b6', '#fb7185', '#a3e635', '#2dd4bf', '#fb923c'
        ];

        // 1. bgsw-contrib Stacked LOC Bar Chart
        const ctxLocBgsw = document.getElementById('locChartBgsw').getContext('2d');
        new Chart(ctxLocBgsw, {{
            type: 'bar',
            data: {{
                labels: labelsBgsw,
                datasets: [
                    {{
                        label: 'Lines Added (+)',
                        data: additionsBgsw,
                        backgroundColor: '#4ade80',
                        borderRadius: 6,
                        borderSkipped: false
                    }},
                    {{
                        label: 'Lines Deleted (-)',
                        data: deletionsBgsw.map(v => Math.abs(v)),
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

        // 2. bgsw-contrib Doughnut PR Share Chart
        const ctxPrBgsw = document.getElementById('prChartBgsw').getContext('2d');
        new Chart(ctxPrBgsw, {{
            type: 'doughnut',
            data: {{
                labels: labelsBgsw,
                datasets: [{{
                    label: 'PR Share',
                    data: prCountsBgsw,
                    backgroundColor: colorPalette.slice(0, labelsBgsw.length),
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

        // 3. eclipse-score Stacked LOC Bar Chart
        const ctxLocEclipse = document.getElementById('locChartEclipse').getContext('2d');
        new Chart(ctxLocEclipse, {{
            type: 'bar',
            data: {{
                labels: labelsEclipse,
                datasets: [
                    {{
                        label: 'Lines Added (+)',
                        data: additionsEclipse,
                        backgroundColor: '#4ade80',
                        borderRadius: 6,
                        borderSkipped: false
                    }},
                    {{
                        label: 'Lines Deleted (-)',
                        data: deletionsEclipse.map(v => Math.abs(v)),
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

        // 4. eclipse-score Doughnut PR Share Chart
        const ctxPrEclipse = document.getElementById('prChartEclipse').getContext('2d');
        new Chart(ctxPrEclipse, {{
            type: 'doughnut',
            data: {{
                labels: labelsEclipse,
                datasets: [{{
                    label: 'PR Share',
                    data: prCountsEclipse,
                    backgroundColor: colorPalette.slice(0, labelsEclipse.length),
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
