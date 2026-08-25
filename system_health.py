# system_health.py
import os
import json
import requests
import time

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

def fetch_org_workflows(org, headers):
    url = f"https://api.github.com/orgs/{org}/repos?per_page=100"
    try:
        response = requests.get(url, headers=headers)
        if response.status_code != 200:
            return []
        repos = response.json()
        
        workflow_runs = []
        for r in repos:
            repo_name = r.get("name")
            runs_url = f"https://api.github.com/repos/{org}/{repo_name}/actions/runs?per_page=3"
            try:
                runs_res = requests.get(runs_url, headers=headers)
                if runs_res.status_code == 200:
                    runs_data = runs_res.json().get("workflow_runs", [])
                    # Group by workflow_id to get only the latest run for each distinct workflow
                    seen_workflows = set()
                    for run in runs_data:
                        wf_id = run.get("workflow_id")
                        if wf_id not in seen_workflows:
                            seen_workflows.add(wf_id)
                            workflow_runs.append({
                                "repo": repo_name,
                                "name": run.get("name", "Unnamed Workflow"),
                                "status": run.get("status"),
                                "conclusion": run.get("conclusion"),
                                "url": run.get("html_url"),
                                "updated_at": run.get("updated_at")
                            })
                time.sleep(0.1)  # Polite pause
            except Exception as e:
                print(f"Exception fetching runs for {repo_name}: {e}")
        return workflow_runs
    except Exception as e:
        print(f"Exception fetching org repos: {e}")
        return []

def main():
    token = get_gh_token()
    if not token:
        print("Warning: GITHUB_TOKEN not found.")
        return
        
    headers = {
        "Authorization": f"token {token}",
        "Accept": "application/vnd.github.v3+json"
    }
    
    workflows = fetch_org_workflows("bgsw-contrib", headers)
    with open("health_stats.json", "w") as f:
        json.dump(workflows, f, indent=2)
    print("system_health.py completed: health_stats.json written.")

if __name__ == "__main__":
    main()
