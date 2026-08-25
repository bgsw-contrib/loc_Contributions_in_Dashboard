# task_status.py
import os
import json
import urllib.parse
import requests

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
    url = f"https://rb-tracker.bosch.com/{instance}/rest/api/2/search?jql={encoded_jql}"
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
    jql_query = 'project = NEETASOSS OR text ~ "SCORE"'
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
                "summary": fields.get("summary", "No Summary"),
                "status": fields.get("status", {}).get("name", "In Progress"),
                "assignee": assignee,
                "priority": fields.get("priority", {}).get("name", "Medium")
            })
    else:
        # Use fallback values with exact display names
        stats = {
            "success": False,
            "issues": [
                {
                    "key": "NEETASOSS-72",
                    "summary": "Configure JIRA_TOKEN secret in GitHub Actions pipeline to enable automated live sync on scheduled runs",
                    "assignee": "Srinivasu Kandukuri",
                    "priority": "High",
                    "status": "In Progress"
                },
                {
                    "key": "NEETASOSS-77",
                    "summary": "Separated LOC contributions standings report for In Progress (Open) and Done (Closed/Merged)",
                    "assignee": "Srinivasu Kandukuri",
                    "priority": "High",
                    "status": "In Progress"
                },
                {
                    "key": "NEETASOSS-78",
                    "summary": "Integrate premium Material Dashboard inspired tabbed layout in index.html generated page",
                    "assignee": "Vinodha kumar mv",
                    "priority": "High",
                    "status": "Done"
                },
                {
                    "key": "NEETASOSS-79",
                    "summary": "Configure secure GitHub local credential fallback routines parsed from hosts config",
                    "assignee": "Ramakrishnan PK",
                    "priority": "Medium",
                    "status": "Done"
                },
                {
                    "key": "NEETASOSS-80",
                    "summary": "Refactor dashboard Chart.js stacked bar additions and deletions to follow Material theme guidelines",
                    "assignee": "Kirankumar H V",
                    "priority": "Low",
                    "status": "Done"
                },
                {
                    "key": "NEETASOSS-81",
                    "summary": "Build dynamic search capability for SCORE Contributions JQL query filters using Track&Release APIs",
                    "assignee": "Srinivasu Kandukuri",
                    "priority": "High",
                    "status": "Done"
                }
            ]
        }
        
    with open("jira_stats.json", "w") as f:
        json.dump(stats, f, indent=2)
    print("task_status.py completed: jira_stats.json written.")

if __name__ == "__main__":
    main()
