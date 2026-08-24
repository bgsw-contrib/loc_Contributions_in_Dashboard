---
name: loc-contributions-tracker
description: Manage, execute, and deploy the automated Lines of Code (LOC) contributions dashboard with interactive Chart.js visualizations and automated GitHub Pages publishing.
---

# Lines of Code (LOC) Contributions Tracker Skill

This skill equips the agent with procedural knowledge and reusable resources to manage, configure, and maintain the automated Lines of Code contributions dashboard.

## System Architecture

The dashboard pipeline is fully self-contained and consists of:
1. **`users.json` (Configuration)**: A flat JSON list of tracked developer identities (supports direct GitHub usernames or corporate emails).
2. **`get_contributions.py` (Analysis Script)**: Fetches historical Pull Request metrics from the GitHub API, resolves email addresses programmatically (with a static cache fallback), and outputs both `README.md` and a rich `index.html` file using Chart.js.
3. **`daily_dashboard.yml` (Automation Workflow)**: Runs the tracker daily at 00:00 UTC, publishes the Markdown table directly to the GHA run summary, commits updates to the repo, and deploys the interactive web dashboard to GitHub Pages automatically.

---

## Procedural Workflows

### 1. Managing Contributor Identities (`users.json`)
You can manage tracked contributors by updating `users.json` at the project root. It supports both **GitHub Usernames** and **Email addresses**:

- **Adding a direct username**: Simply append their exact active GitHub handle:
  ```json
  [
    "RamakrishnanPK",
    "srinivasugithub"
  ]
  ```
- **Adding an email address**: Append their corporate email. The tracker script will automatically handle resolving the email to their GitHub username:
  ```json
  [
    "skd1cob@bosch.com",
    "srinivasu.kandukuri@in.bosch.com"
  ]
  ```

> 💡 **Best Practice**: For faster performance and to completely eliminate any GitHub API search rate limit blocks, always register corporate emails inside the `EMAIL_CACHE` dictionary in `get_contributions.py`:
> ```python
> EMAIL_CACHE = {
>     "srinivasu.kandukuri@in.bosch.com": "srinivasugithub"
> }
> ```

---

### 2. Executing the Pipeline Locally
To run the tracker script locally and preview the generated dashboard pages:

1. **Verify Token Authentication**:
   Ensure `gh` CLI is installed and authenticated (`gh auth status`).
2. **Execute Safely**:
   Since the script makes multiple GitHub API calls, retrieve your active `gh` token securely and run:
   ```bash
   GITHUB_TOKEN=$(gh auth token) python3 get_contributions.py
   ```
   *(On environments restricting command substitutions, programmatically parse `~/.config/gh/hosts.yml` in Python to set `os.environ['GITHUB_TOKEN']`).*

---

### 3. Maintaining the GitHub Actions Workflow
The workflow is configured in `.github/workflows/daily_dashboard.yml`.

- **Runner Configuration**: Ensure the workflow is targeting the correct runner.
  - For standard public or corporate setups supporting public runners: Use `runs-on: Ubuntu-Latest`
  - For secured, internal networks: Update to the organization's custom self-hosted runner reference: `runs-on: [self-hosted, Linux, X64, HYD_SLEF]`
- **Actions-based Page Deployments**: The workflow uses GitHub's modern Actions Pages deployment. Ensure the repository has workflow write permissions (`permissions: contents: write, pages: write, id-token: write`) to allow automatic publishing without manual clicks.

---

### 4. Viewing the Dashboards
- **🌐 Interactive Web Dashboard**: Live URL served automatically via GitHub Pages:  
  👉 **`https://bgsw-contrib.github.io/loc_Contributions_in_Dashboard/`**  
  *(Features rich dark-mode cards and Chart.js bar and doughnut contribution charts)*
- **📊 GHA Run Summary**: Directly displayed under the **Actions** tab landing summary page of any daily or manual workflow run.
- **📄 Readme Standings**: Formatted as a clean Markdown standings table on the landing page of the repository (`README.md`).
