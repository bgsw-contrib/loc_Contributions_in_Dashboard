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
        # Use exact live JIRA project dataset provided by user
        stats = {
            "success": False,
            "issues": [
                # --- IN PROGRESS (24) ---
                {
                    "key": "NEETASOSS-78",
                    "type": "User Story",
                    "summary": escape_markdown("https://github.com/eclipse-score/tooling/issues/82"),
                    "assignee": "Ramakrishnan P K",
                    "priority": "High",
                    "status": "In Progress"
                },
                {
                    "key": "NEETASOSS-77",
                    "type": "User Story",
                    "summary": escape_markdown("(INTERNAL) Dashboard on LOC (lines of code) for S-Core Contributions"),
                    "assignee": "Srinivasu Kandukuri",
                    "priority": "High",
                    "status": "In Progress"
                },
                {
                    "key": "NEETASOSS-76",
                    "type": "Task",
                    "summary": escape_markdown("https://github.com/eclipse-score/lifecycle/issues/448"),
                    "assignee": "Srinivasu Kandukuri",
                    "priority": "High",
                    "status": "In Progress"
                },
                {
                    "key": "NEETASOSS-75",
                    "type": "Task",
                    "summary": escape_markdown("https://github.com/eclipse-score/baselibs/issues/455"),
                    "assignee": "Srinivasu Kandukuri",
                    "priority": "High",
                    "status": "In Progress"
                },
                {
                    "key": "NEETASOSS-74",
                    "type": "User Story",
                    "summary": escape_markdown("https://github.com/eclipse-score/score/issues/1837"),
                    "assignee": "Ramakrishnan P K",
                    "priority": "High",
                    "status": "In Progress"
                },
                {
                    "key": "NEETASOSS-73",
                    "type": "User Story",
                    "summary": escape_markdown("https://github.com/eclipse-score/module_template/issues/130"),
                    "assignee": "Panne Naveena",
                    "priority": "Medium",
                    "status": "In Progress"
                },
                {
                    "key": "NEETASOSS-72",
                    "type": "User Story",
                    "summary": escape_markdown("https://github.com/eclipse-score/bazel_registry/issues/485"),
                    "assignee": "Nanda Purna Chandra",
                    "priority": "Medium",
                    "status": "In Progress"
                },
                {
                    "key": "NEETASOSS-70",
                    "type": "Task",
                    "summary": escape_markdown("https://github.com/eclipse-score/docs-as-code/issues/595"),
                    "assignee": "Kumar Mv Vinodha",
                    "priority": "Medium",
                    "status": "In Progress"
                },
                {
                    "key": "NEETASOSS-67",
                    "type": "User Story",
                    "summary": escape_markdown("https://github.com/eclipse-score/.eclipsefdn/issues/210"),
                    "assignee": "Ramakrishnan P K",
                    "priority": "Medium",
                    "status": "In Progress"
                },
                {
                    "key": "NEETASOSS-53",
                    "type": "User Story",
                    "summary": escape_markdown("Joystick Reader integration - New Project Conan Cmake"),
                    "assignee": "Ramakrishnan P K",
                    "priority": "Medium",
                    "status": "In Progress"
                },
                {
                    "key": "NEETASOSS-51",
                    "type": "User Story",
                    "summary": escape_markdown("https://github.com/eclipse-score/scrample/issues/27"),
                    "assignee": "Amulya Doma",
                    "priority": "Medium",
                    "status": "In Progress"
                },
                {
                    "key": "NEETASOSS-46",
                    "type": "User Story",
                    "summary": escape_markdown("https://github.com/eclipse-score/cicd-workflows/issues/135"),
                    "assignee": "Parthiban Kuppudurai",
                    "priority": "Medium",
                    "status": "In Progress"
                },
                {
                    "key": "NEETASOSS-43",
                    "type": "Epic",
                    "summary": escape_markdown("mw::com Data Provider for Kuksa Databroker (Rust, QM)"),
                    "assignee": "Prashanth Manje Gowda",
                    "priority": "High",
                    "status": "In Progress"
                },
                {
                    "key": "NEETASOSS-39",
                    "type": "User Story",
                    "summary": escape_markdown("mw::comDataProvider - Signal conversion & broker ingest"),
                    "assignee": "Patil Rutuja Milind",
                    "priority": "Medium",
                    "status": "In Progress"
                },
                {
                    "key": "NEETASOSS-38",
                    "type": "User Story",
                    "summary": escape_markdown("mw::comDataProvider - JSON + config generator"),
                    "assignee": "Patil Rutuja Milind",
                    "priority": "Medium",
                    "status": "In Progress"
                },
                {
                    "key": "NEETASOSS-37",
                    "type": "User Story",
                    "summary": escape_markdown("mw::comDataProvider - Rust bindings for mw::com using codegen"),
                    "assignee": "Patil Rutuja Milind",
                    "priority": "Medium",
                    "status": "In Progress"
                },
                {
                    "key": "NEETASOSS-36",
                    "type": "User Story",
                    "summary": escape_markdown("mw::comDataProvider - Provider skeleton and data provider trait implementation"),
                    "assignee": "Prashanth Manje Gowda",
                    "priority": "Medium",
                    "status": "In Progress"
                },
                {
                    "key": "NEETASOSS-35",
                    "type": "User Story",
                    "summary": escape_markdown("mw::comDataProvider - Analysis and design"),
                    "assignee": "Prashanth Manje Gowda",
                    "priority": "Medium",
                    "status": "In Progress"
                },
                {
                    "key": "NEETASOSS-34",
                    "type": "New Feature",
                    "summary": escape_markdown("mw::com Data Provider for Kuksa Databroker (Rust, QM)"),
                    "assignee": "Prashanth Manje Gowda",
                    "priority": "High",
                    "status": "In Progress"
                },
                {
                    "key": "NEETASOSS-32",
                    "type": "User Story",
                    "summary": escape_markdown("https://github.com/eclipse-score/cicd-workflows/issues/126"),
                    "assignee": "Divya Priya Gopal",
                    "priority": "Medium",
                    "status": "In Progress"
                },
                {
                    "key": "NEETASOSS-28",
                    "type": "Subtask",
                    "summary": escape_markdown("Part 1: Split Bridge Management functionality"),
                    "assignee": "Patil Rutuja Milind",
                    "priority": "Medium",
                    "status": "In Progress"
                },
                {
                    "key": "NEETASOSS-27",
                    "type": "User Story",
                    "summary": escape_markdown("https://github.com/eclipse-score/inc_someip_gateway/issues/79"),
                    "assignee": "Patil Rutuja Milind",
                    "priority": "Medium",
                    "status": "In Progress"
                },
                {
                    "key": "NEETASOSS-22",
                    "type": "Epic",
                    "summary": escape_markdown("S-CORE Demo Kit"),
                    "assignee": "Ramakrishnan P K",
                    "priority": "High",
                    "status": "In Progress"
                },
                {
                    "key": "NEETASOSS-20",
                    "type": "User Story",
                    "summary": escape_markdown("https://github.com/eclipse-score/communication/issues/449"),
                    "assignee": "Patil Rutuja Milind",
                    "priority": "Medium",
                    "status": "In Progress"
                },
                
                # --- TO DO (36) ---
                {
                    "key": "NEETASOSS-69",
                    "type": "Task",
                    "summary": escape_markdown("https://github.com/eclipse-score/cicd-workflows/issues/121"),
                    "assignee": "Divya Priya Gopal",
                    "priority": "Medium",
                    "status": "To Do"
                },
                {
                    "key": "NEETASOSS-66",
                    "type": "Epic",
                    "summary": escape_markdown("Parthiban Kuppudurai: S-Core Contributions: improvements, Bugs and test cases"),
                    "assignee": "Parthiban Kuppudurai",
                    "priority": "High",
                    "status": "To Do"
                },
                {
                    "key": "NEETASOSS-65",
                    "type": "Epic",
                    "summary": escape_markdown("Srinivasu Kandukuri: S-Core Contributions: improvements, Bugs and test cases"),
                    "assignee": "Srinivasu Kandukuri",
                    "priority": "High",
                    "status": "To Do"
                },
                {
                    "key": "NEETASOSS-64",
                    "type": "Epic",
                    "summary": escape_markdown("Nanda Purna Chandra: S-Core Contributions: improvements, Bugs and test cases"),
                    "assignee": "Nanda Purna Chandra",
                    "priority": "High",
                    "status": "To Do"
                },
                {
                    "key": "NEETASOSS-63",
                    "type": "Epic",
                    "summary": escape_markdown("Logeshwari Sithan: S-Core Contributions: improvements, Bugs and test cases"),
                    "assignee": "Logeshwari Sithan",
                    "priority": "High",
                    "status": "To Do"
                },
                {
                    "key": "NEETASOSS-62",
                    "type": "Epic",
                    "summary": escape_markdown("Deepak Pk Shetty: S-Core Contributions: improvements, Bugs and test cases"),
                    "assignee": "Deepak Pk Shetty",
                    "priority": "High",
                    "status": "To Do"
                },
                {
                    "key": "NEETASOSS-61",
                    "type": "Epic",
                    "summary": escape_markdown("Gnana Prakash N R: S-Core Contributions: improvements, Bugs and test cases"),
                    "assignee": "Gnana Prakash N R",
                    "priority": "High",
                    "status": "To Do"
                },
                {
                    "key": "NEETASOSS-59",
                    "type": "User Story",
                    "summary": escape_markdown("Android App update for Motor Control Demo"),
                    "assignee": "Ramakrishnan P K",
                    "priority": "Medium",
                    "status": "To Do"
                },
                {
                    "key": "NEETASOSS-58",
                    "type": "User Story",
                    "summary": escape_markdown("Velocitas App for Motor Control Demo"),
                    "assignee": "Ramakrishnan P K",
                    "priority": "Medium",
                    "status": "To Do"
                },
                {
                    "key": "NEETASOSS-57",
                    "type": "User Story",
                    "summary": escape_markdown("Motor Control Sources - CAN support"),
                    "assignee": "Ramakrishnan P K",
                    "priority": "Medium",
                    "status": "To Do"
                },
                {
                    "key": "NEETASOSS-56",
                    "type": "User Story",
                    "summary": escape_markdown("Sync Middleware SOMEIP configurations"),
                    "assignee": "Ramakrishnan P K",
                    "priority": "Medium",
                    "status": "To Do"
                },
                {
                    "key": "NEETASOSS-55",
                    "type": "User Story",
                    "summary": escape_markdown("VSS signal update - RC car controls"),
                    "assignee": "Ramakrishnan P K",
                    "priority": "Medium",
                    "status": "To Do"
                },
                {
                    "key": "NEETASOSS-54",
                    "type": "User Story",
                    "summary": escape_markdown("Kuksa Databroker feeder Integration"),
                    "assignee": "Ramakrishnan P K",
                    "priority": "Medium",
                    "status": "To Do"
                },
                {
                    "key": "NEETASOSS-52",
                    "type": "User Story",
                    "summary": escape_markdown("Joystick Reader and Databroker sender Integration for RaspberryPI"),
                    "assignee": "Ramakrishnan P K",
                    "priority": "High",
                    "status": "To Do"
                },
                {
                    "key": "NEETASOSS-49",
                    "type": "Epic",
                    "summary": escape_markdown("Amulya Doma: S-Core Contributions: improvements, Bugs and test cases"),
                    "assignee": "Amulya Doma",
                    "priority": "High",
                    "status": "To Do"
                },
                {
                    "key": "NEETASOSS-47",
                    "type": "Epic",
                    "summary": escape_markdown("Panne Naveena: S-Core Contributions: improvements, Bugs and test cases"),
                    "assignee": "Panne Naveena",
                    "priority": "High",
                    "status": "To Do"
                },
                {
                    "key": "NEETASOSS-45",
                    "type": "Epic",
                    "summary": escape_markdown("Patil Kamesh Shambhurao: S-Core Contributions: improvements, Bugs and test cases"),
                    "assignee": "Patil Kamesh Shambhurao",
                    "priority": "High",
                    "status": "To Do"
                },
                {
                    "key": "NEETASOSS-44",
                    "type": "Epic",
                    "summary": escape_markdown("Akhila Thapliyal: S-Core Contributions: improvements, Bugs and test cases"),
                    "assignee": "Akhila Thapliyal",
                    "priority": "High",
                    "status": "To Do"
                },
                {
                    "key": "NEETASOSS-42",
                    "type": "User Story",
                    "summary": escape_markdown("mw::comDataProvider - Delivery & OSS contribution"),
                    "assignee": "Patil Rutuja Milind",
                    "priority": "Medium",
                    "status": "To Do"
                },
                {
                    "key": "NEETASOSS-41",
                    "type": "User Story",
                    "summary": escape_markdown("mw::comDataProvider - Testing and validation"),
                    "assignee": "Patil Rutuja Milind",
                    "priority": "Medium",
                    "status": "To Do"
                },
                {
                    "key": "NEETASOSS-40",
                    "type": "User Story",
                    "summary": escape_markdown("mw::comDataProvider - QM <-> ASIL-B boundary & robustness"),
                    "assignee": "Prashanth Manje Gowda",
                    "priority": "Medium",
                    "status": "To Do"
                },
                {
                    "key": "NEETASOSS-33",
                    "type": "Epic",
                    "summary": escape_markdown("Divya: S-Core Contributions: improvements, Bugs and test cases"),
                    "assignee": "Divya Priya Gopal",
                    "priority": "High",
                    "status": "To Do"
                },
                {
                    "key": "NEETASOSS-30",
                    "type": "Epic",
                    "summary": escape_markdown("Vrinda: S-Core Contributions: improvements, Bugs and test cases"),
                    "assignee": "Vrinda A M",
                    "priority": "High",
                    "status": "To Do"
                },
                {
                    "key": "NEETASOSS-29",
                    "type": "Epic",
                    "summary": escape_markdown("Prashanth MG: S-Core Contributions: improvements, Bugs and test cases"),
                    "assignee": "Prashanth Manje Gowda",
                    "priority": "High",
                    "status": "To Do"
                },
                {
                    "key": "NEETASOSS-25",
                    "type": "Epic",
                    "summary": escape_markdown("Vinodha: S-Core Contributions: improvements, Bugs and test cases"),
                    "assignee": "Kumar Mv Vinodha",
                    "priority": "High",
                    "status": "To Do"
                },
                {
                    "key": "NEETASOSS-24",
                    "type": "Epic",
                    "summary": escape_markdown("KiranHV: S-Core Contributions: improvements, Bugs and test cases"),
                    "assignee": "Kiran Kumar Hoskere",
                    "priority": "High",
                    "status": "To Do"
                },
                {
                    "key": "NEETASOSS-23",
                    "type": "Epic",
                    "summary": escape_markdown("RamPK: S-Core Contributions: Improvements, Bugs and test cases"),
                    "assignee": "Ramakrishnan P K",
                    "priority": "High",
                    "status": "To Do"
                },
                {
                    "key": "NEETASOSS-19",
                    "type": "Bug",
                    "summary": escape_markdown("FIX the below error due to FIL"),
                    "assignee": "Amulya Doma",
                    "priority": "Medium",
                    "status": "To Do"
                },
                {
                    "key": "NEETASOSS-10",
                    "type": "Epic",
                    "summary": escape_markdown("S-Core RBC Demo feature"),
                    "assignee": "Ramakrishnan P K",
                    "priority": "High",
                    "status": "To Do"
                },
                {
                    "key": "NEETASOSS-8",
                    "type": "User Story",
                    "summary": escape_markdown("Architecture & Design"),
                    "assignee": "Patil Rutuja Milind",
                    "priority": "Medium",
                    "status": "To Do"
                },
                {
                    "key": "NEETASOSS-7",
                    "type": "Epic",
                    "summary": escape_markdown("KUKSA Databroker Integration with Eclipse S-CORE"),
                    "assignee": "Joshi Mayank",
                    "priority": "High",
                    "status": "To Do"
                },
                {
                    "key": "NEETASOSS-6",
                    "type": "New Feature",
                    "summary": escape_markdown("S-Core: Suitcase demo (RBC App)"),
                    "assignee": "Ramakrishnan P K",
                    "priority": "High",
                    "status": "To Do"
                },
                {
                    "key": "NEETASOSS-4",
                    "type": "Epic",
                    "summary": escape_markdown("Rutuja: S-Core Contributions: Improvements, Bugs and test cases"),
                    "assignee": "Patil Rutuja Milind",
                    "priority": "High",
                    "status": "To Do"
                },
                {
                    "key": "NEETASOSS-3",
                    "type": "Epic",
                    "summary": escape_markdown("Score-Demo with Read and write"),
                    "assignee": "Joshi Mayank",
                    "priority": "High",
                    "status": "To Do"
                },
                {
                    "key": "NEETASOSS-2",
                    "type": "Epic",
                    "summary": escape_markdown("Drag and drop epics to reorder"),
                    "assignee": "Joshi Mayank",
                    "priority": "High",
                    "status": "To Do"
                },
                {
                    "key": "NEETASOSS-1",
                    "type": "Epic",
                    "summary": escape_markdown("Click here to edit this epic's name"),
                    "assignee": "Joshi Mayank",
                    "priority": "High",
                    "status": "To Do"
                },
                
                # --- ON HOLD (2) ---
                {
                    "key": "NEETASOSS-18",
                    "type": "Task",
                    "summary": escape_markdown("Prepare the New development board"),
                    "assignee": "Amulya Doma",
                    "priority": "Medium",
                    "status": "On Hold"
                },
                {
                    "key": "NEETASOSS-17",
                    "type": "Task",
                    "summary": escape_markdown("Cleanup initrd with unwanted binaries."),
                    "assignee": "Amulya Doma",
                    "priority": "Medium",
                    "status": "On Hold"
                }
            ]
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
