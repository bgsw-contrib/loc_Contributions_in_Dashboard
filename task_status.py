# task_status.py
import os
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

def fetch_jira_search(instance, jql):
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
        
    encoded_jql = urllib.parse.quote(jql)
    url = f"https://rb-tracker.bosch.com/{instance}/rest/api/2/search?jql={encoded_jql}&maxResults=100"
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }
    try:
        response = requests.get(url, headers=headers)
        if response.status_code == 200:
            return response.json()
        else:
            print(f"Jira Search API returned status {response.status_code}")
            return None
    except Exception as e:
        print(f"Exception searching Jira: {e}")
        return None

def main():
    jql_query = 'project = NEETASOSS AND resolution is EMPTY'
    print(f"Executing JIRA search matching: {jql_query} in task_status.py...")
    search_data = fetch_jira_search("tracker19", jql_query)
    
    if search_data:
        # Extract dynamic values
        issues = search_data.get("issues", [])
        stats = {
            "success": True,
            "issues": []
        }
        for iss in issues:
            key = iss.get("key")
            fields = iss.get("fields", {})
            assignee_data = fields.get("assignee")
            assignee = assignee_data.get("displayName", "Unassigned") if assignee_data else "Unassigned"
            stats["issues"].append({
                "key": key,
                "type": fields.get("issuetype", {}).get("name", "Task"),
                "summary": escape_markdown(fields.get("summary", "No Summary")),
                "status": fields.get("status", {}).get("name", "In Progress"),
                "assignee": assignee,
                "priority": fields.get("priority", {}).get("name", "Medium")
            })
    else:
        # Rely strictly on dynamic JIRA system data without hardcoding fallback lists
        stats = {
            "success": False,
            "issues": []
        }
        
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
    print("task_status.py completed: jira_stats.json written.")

if __name__ == "__main__":
    main()
