# TCG Collector to Monarch Money Sync

An automated pipeline that scrapes your Pokémon card collection valuation from [TCG Collector](https://www.tcgcollector.com/) and syncs it daily into a manual Collectibles asset account in [Monarch Money](https://www.monarchmoney.com/) using GitHub Actions.

---

## Features

* **No Official API Token Needed:** Parses portfolio valuation directly from your public TCG Collector dashboard.
* **Session-based authentication:** Uses a locally exported Monarch session stored as a GitHub Actions secret. Treat it as account access and never commit it.
* **Automated Daily Sync:** Scheduled via GitHub Actions cron with on-demand manual trigger support (`workflow_dispatch`).
* **Supports API Domain Routing:** Configured to point directly to Monarch's current API gateway (`api.monarch.com`).

Released under the [MIT License](LICENSE).

---

## Project Structure

```text
.
├── .github/
│   └── workflows/
│       └── sync.yml              # Scheduled GitHub Actions runner
├── sync_tcg_to_monarch.py        # Main extraction & sync script
├── save_session.py               # One-time local helper to export session
├── requirements.txt              # Python dependencies
├── LICENSE                       # MIT License
├── ReadMe.md
└── tests/
  └── test_sync_tcg_to_monarch.py

```

---

## Prerequisites

1. **Monarch Money Account:** Create a manual account under **Accounts → + Add Account → Manual Account**. Set the category to **Asset → Collectibles** (e.g., `Pokémon Cards`).
2. **Monarch Account UUID:** Open your manual account in a desktop browser. Copy the UUID from the URL:
`[https://app.monarchmoney.com/accounts/](https://app.monarchmoney.com/accounts/)<ACCOUNT_ID>`
3. **TCG Collector Public Dashboard:** Ensure your collection is visible publicly via **Share my collection → Copy link** (or accessible via your user ID link: `[https://www.tcgcollector.com/dashboard/intl?viewUser=](https://www.tcgcollector.com/dashboard/intl?viewUser=)<USER_ID>`).

The public dashboard makes your collection visible to others. Before running this automation, review the current terms and access policies of both services and use only access methods they permit. This project is not affiliated with either service.

---

## Setup & Configuration

### 1. Export a Monarch Session Locally

The session is sensitive account-access data. Do not commit the session file or share its encoded value. If it is exposed, revoke or replace the session where supported and update the GitHub secret.

1. Install the pinned dependencies:
```bash
python -m pip install -r requirements.txt
```

2. Run the included helper and follow its login prompts:
```bash
python save_session.py
```

Enter your Monarch credentials and MFA code only in the trusted local terminal prompt.

### 2. Encode the Session File to Base64

Encode `monarch_session.pickle` to a single base64 string:

* **macOS:**
```bash
base64 -i monarch_session.pickle | tr -d '\n' | pbcopy
```


* **Linux:**
```bash
base64 -w 0 monarch_session.pickle
```


* **Windows (PowerShell):**
```powershell
[Convert]::ToBase64String([IO.File]::ReadAllBytes("monarch_session.pickle")) | Set-Clipboard

```



### 3. Configure GitHub Repository Secrets

In your GitHub repository, navigate to **Settings → Secrets and variables → Actions → New repository secret** and add:

| Secret Name | Value | Description |
| --- | --- | --- |
| `TCGCOLLECTOR_USER_ID` | `12345` | User ID for TCG Collector Public Page
| `MONARCH_SESSION_B64` | `gASV...` | The entire base64 string generated from `monarch_session.pickle` |
| `MONARCH_ACCOUNT_ID` | `xxxxxxxx-xxxx-...` | Your manual Collectibles account UUID in Monarch |

Also add the repository **variable** `MAX_BALANCE_CHANGE` with the largest dollar change you will allow between the current Monarch balance and the scraped value. Choose a conservative limit; the script stops without updating when the difference exceeds it. This variable is required, including for the first sync.

---

## Automation Workflow

The workflow file located at `.github/workflows/sync.yml` automatically executes the sync:

```yaml
name: Sync TCG Collector to Monarch

on:
  schedule:
    # Runs daily at 06:00 UTC
    - cron: '0 6 * * *'
  workflow_dispatch:
    inputs:
      dry_run:
        description: Validate the value without updating Monarch
        required: false
        type: boolean
        default: true

permissions:
  contents: read

jobs:
  sync:
    runs-on: ubuntu-latest

    steps:
      - name: Check out repository
        uses: actions/checkout@v4

      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: '3.11'
          cache: 'pip'

      - name: Install dependencies
        run: |
          python -m pip install --upgrade pip
          pip install -r requirements.txt

      - name: Run sync script
        env:
          TCGCOLLECTOR_USER_ID: ${{ secrets.TCGCOLLECTOR_USER_ID }}
          MONARCH_SESSION_B64: ${{ secrets.MONARCH_SESSION_B64 }}
          MONARCH_ACCOUNT_ID: ${{ secrets.MONARCH_ACCOUNT_ID }}
          MAX_BALANCE_CHANGE: ${{ vars.MAX_BALANCE_CHANGE }}
          DRY_RUN: ${{ inputs.dry_run || false }}
        run: |
          python sync_tcg_to_monarch.py

```

Manual workflow runs default to dry-run. Set `dry_run` to `false` only when ready to update Monarch. Scheduled runs update the account, subject to the configured balance-change limit.

---

## Troubleshooting

* **`HTTP Code 405: Method Not Allowed`:** Ensure `MonarchMoneyEndpoints.BASE_URL = "[https://api.monarch.com](https://api.monarch.com)"` is defined before instantiating `MonarchMoney()`.
* **`AttributeError: 'MonarchMoney' object has no attribute 'update_account_balance'`:** Use `mm.update_account(account_id=..., account_balance=...)` instead.
* **Session Expiration:** If the Action fails with an authentication error, run `save_session.py` locally again and replace the `MONARCH_SESSION_B64` secret in GitHub.
* **Balance-change limit:** If a legitimate change exceeds `MAX_BALANCE_CHANGE`, review the scraped value and current account balance before raising the repository variable.