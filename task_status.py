# task_status.py
import os
import sys
import json
import urllib.parse
import requests

def escape_markdown(text):
    if not text:
        return ""
    # Critical markdown escaping to prevent table breaks
    for char in ["\\", "|", "*", "_", "[", "]", "#"]:
        text = text.replace(char, f"\\{char}")
    return text

def load_env_from_bashrc():
    bashrc_path = os.path.expanduser("~/.bashrc")
    if os.path.exists(bashrc_path):
        with open(bashrc_path, "r") as f:
            for line in f:
                if line.strip().startswith("export "):
                    parts = line.strip().split("export ", 1)[1].split("=", 1)
                    if len(parts) == 2:
                        key = parts[0].strip()
                        val = parts[1].strip().strip('"').strip("'")
                        if key not in os.environ:
                            os.environ[key] = val

def fetch_open_issues(base_url, token, jql):
    search_url = f"{base_url}/rest/api/2/search"
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }
    
    issues = []
    start_at = 0
    max_results = 50
    
    print(f"🚀 Fetching open issues for project 'NEETASOSS' from {base_url}...", file=sys.stderr)
    
    while True:
        payload = {
            "jql": jql,
            "startAt": start_at,
            "maxResults": max_results,
            "fields": ["summary", "status", "assignee", "issuetype", "priority"]
        }
        
        try:
            response = requests.post(search_url, json=payload, headers=headers)
            response.raise_for_status()
        except requests.exceptions.RequestException as e:
            print(f"❌ Error communicating with JIRA API: {e}", file=sys.stderr)
            return None
            
        try:
            data = response.json()
        except ValueError as e:
            print(f"❌ Error parsing JIRA response as JSON: {e}", file=sys.stderr)
            print(f"Status Code: {response.status_code}, Content-Type: {response.headers.get('Content-Type')}", file=sys.stderr)
            if "html" in response.headers.get("Content-Type", "").lower() or response.text.strip().startswith("<"):
                print("💡 Notice: The JIRA API returned an HTML page instead of JSON. This typically indicates that your JIRA_TOKEN is expired, invalid, or needs to be re-authenticated via WebSSO/PingFederate.", file=sys.stderr)
            return None
            
        batch = data.get("issues", [])
        if not batch:
            break
            
        issues.extend(batch)
        total = data.get("total", 0)
        print(f"   Downloaded {len(issues)} of {total} issues...", file=sys.stderr)
        
        if len(issues) >= total:
            break
            
        start_at += max_results
        
    return issues

def main():
    load_env_from_bashrc()
    
    jira_base_url = "https://rb-tracker.bosch.com/tracker19"
    jql_query = "project = NEETASOSS"
    
    # Load dynamic token from environment variables
    token = os.getenv("JIRA_TOKEN_TRACKER19") or os.getenv("JIRA_TOKEN")
    
    if not token:
        print("❌ Error: JIRA_TOKEN_TRACKER19 or JIRA_TOKEN environment variable is not configured.", file=sys.stderr)
        if os.path.exists("jira_stats.json"):
            print("⚠️ Warning: JIRA token is missing. Preserving the existing cached jira_stats.json file.", file=sys.stderr)
        else:
            stats = {
                "success": False,
                "issues": [],
                "todo": 0,
                "inprogress": 0,
                "blocked": 0,
                "done": 0
            }
            with open("jira_stats.json", "w") as f:
                json.dump(stats, f, indent=2)
        return
        
    raw_issues = fetch_open_issues(jira_base_url, token, jql_query)
    
    if raw_issues is not None:
        stats = {
            "success": True,
            "issues": []
        }
        for iss in raw_issues:
            key = iss.get("key")
            fields = iss.get("fields") or {}
            
            assignee_data = fields.get("assignee")
            assignee = assignee_data.get("displayName", "Unassigned") if assignee_data else "Unassigned"
            if " (" in assignee:
                assignee = assignee.split(" (")[0]
            
            stats["issues"].append({
                "key": key,
                "type": fields.get("issuetype", {}).get("name", "Task"),
                "summary": escape_markdown(fields.get("summary", "No Summary")),
                "status": fields.get("status", {}).get("name", "In Progress"),
                "assignee": assignee,
                "priority": fields.get("priority", {}).get("name", "Medium")
            })
            
        # Dynamically calculate stats counts
        todo_count = 0
        inprogress_count = 0
        blocked_count = 0
        done_count = 0
        
        issues_list = stats["issues"]
        for iss in issues_list:
            status = iss["status"]
            if "To Do" in status or "Open" in status:
                todo_count += 1
            elif "Progress" in status or "Active" in status:
                inprogress_count += 1
            elif "Hold" in status or "Blocked" in status:
                blocked_count += 1
            elif "Done" in status or "Closed" in status or "Resolved" in status:
                done_count += 1
                
        stats["todo"] = todo_count
        stats["inprogress"] = inprogress_count
        stats["blocked"] = blocked_count
        stats["done"] = done_count
            
        with open("jira_stats.json", "w") as f:
            json.dump(stats, f, indent=2)
        print("task_status.py completed: jira_stats.json updated successfully.")
    else:
        # Graceful fallback: keep any existing cached jira_stats.json file intact
        if os.path.exists("jira_stats.json"):
            print("⚠️ Warning: JIRA query failed. Preserving the existing cached jira_stats.json file.", file=sys.stderr)
        else:
            stats = {
                "success": False,
                "issues": [],
                "todo": 0,
                "inprogress": 0,
                "blocked": 0,
                "done": 0
            }
            with open("jira_stats.json", "w") as f:
                json.dump(stats, f, indent=2)
            print("task_status.py completed: Empty jira_stats.json created as fallback.", file=sys.stderr)

if __name__ == "__main__":
    main()
