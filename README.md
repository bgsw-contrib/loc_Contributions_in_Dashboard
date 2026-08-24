# Lines of Code Contributions Dashboard

Automated dashboard tracking active contributions within the **bgsw-contrib** organization.

This repository tracks and displays statistics on Pull Request activity and lines of code (LOC) additions and deletions per user and per team/role group within the organization.

---

## 📊 Dashboard

The dashboard below is updated automatically every day.

> **Last Updated:** `Not run yet`  
> *Note: Metrics represent Pull Request contributions created in the last 30 days.*

---

## 👤 Tracked Contributors & Role Groups

This project tracks contributions from key members grouped by their operational focus:
- **S-Core & AUTOSAR Technical Lead**
- **Infrastructure & Coordination**
- **S-Core Architecture & QNX-Rust**
- **GenAI & Innovation Strategy**
- **QNX-RUST POC Lead**

You can configure and manage the list of tracked contributors and their groups by editing [users.json](./users.json).

---

## 🛠️ How it Works

1. **Daily Tracker Execution:**
   Every day, a scheduled GitHub Actions workflow runs the [get_contributions.py](./get_contributions.py) Python script.
2. **API Data Collection:**
   The script queries the GitHub Search API for all Pull Requests created by the specified users in the `bgsw-contrib` organization over the last 30 days.
3. **Metric Calculation:**
   For each PR, the script retrieves detailed contribution metrics (lines of code added and deleted) from the GitHub REST API.
4. **Aggregation:**
   Metrics are aggregated by individual contributor and group role.
5. **Dashboard Generation:**
   The script updates this `README.md` file with a beautifully formatted table representing the up-to-date metrics.
6. **Automatic Commit:**
   The GitHub Actions runner commits and pushes the updated `README.md` back to the repository.

---

## 🚀 Running Locally

To run the script locally and preview the generated dashboard tables:

### 1. Prerequisites
Ensure you have Python 3.8+ installed. Install the required dependencies:
```bash
pip install requests
```

### 2. Configure GitHub Token
Generate a personal access token (PAT) with repository read permissions, and export it as an environment variable:
```bash
export GITHUB_TOKEN="your_personal_access_token"
```

### 3. Run the Script
Execute the analysis script:
```bash
python get_contributions.py
```

This will output:
```text
Gathering contribution metrics...
Analyzing user: srinivasu-kandukuri (Srinivasu Kandukuri)...
...
Dashboard updated successfully!
```

Once successful, your local `README.md` will have the fresh stats tables!

---

## 📂 Repository Structure

```tree
loc_Contributions_in_Dashboard/
├── .github/
│   └── workflows/
│       └── daily_dashboard.yml   # Scheduled GitHub Action workflow
├── get_contributions.py           # Metrics calculation and report script
├── users.json                     # Contributors configuration
└── README.md                      # This dashboard and guide
```
