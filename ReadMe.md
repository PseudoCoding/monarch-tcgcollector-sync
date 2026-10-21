# TCG Collector to Monarch Money Sync

An automated pipeline that scrapes your Pokémon card collection valuation from [TCG Collector](https://www.tcgcollector.com/) and syncs it daily into a manual Collectibles asset account in [Monarch Money](https://www.monarchmoney.com/) using GitHub Actions.

---

## Features

* **No Official API Token Needed:** Parses portfolio valuation directly from your public TCG Collector dashboard.
* **Bypasses Cloudflare Restrictions:** Uses a base64-encoded, persistent session pickle to avoid login bot blocks and `HTTP 429: Too Many Requests` errors on CI/CD runners.
* **Automated Daily Sync:** Scheduled via GitHub Actions cron with on-demand manual trigger support (`workflow_dispatch`).
* **Supports API Domain Routing:** Configured to point directly to Monarch's current API gateway (`api.monarch.com`).

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
└── README.md

```

---

## Prerequisites

1. **Monarch Money Account:** Create a manual account under **Accounts → + Add Account → Manual Account**. Set the category to **Asset → Collectibles** (e.g., `Pokémon Cards`).
2. **Monarch Account UUID:** Open your manual account in a desktop browser. Copy the UUID from the URL:
`[https://app.monarchmoney.com/accounts/](https://app.monarchmoney.com/accounts/)<ACCOUNT_ID>`
3. **TCG Collector Public Dashboard:** Ensure your collection is visible publicly (or accessible via your user ID link: `[https://www.tcgcollector.com/dashboard/intl?viewUser=](https://www.tcgcollector.com/dashboard/intl?viewUser=)<USER_ID>`).

---

## Setup & Configuration

### 1. Generate Monarch Session Locally

Monarch blocks automated logins from cloud data centers (like GitHub Actions). To bypass this, log in once on your local machine to export your session.

1. Install dependencies locally:
```bash
pip install monarchmoney beautifulsoup4 requests

```


2. Run `save_session.py`:
```python
import asyncio
from monarchmoney import MonarchMoney, MonarchMoneyEndpoints

# Point to active API host
MonarchMoneyEndpoints.BASE_URL = "https://api.monarch.com"

async def main():
    mm = MonarchMoney()
    await mm.interactive_login()
    mm.save_session("monarch_session.pickle")
    print("\nSession saved to monarch_session.pickle!")

if __name__ == "__main__":
    asyncio.run(main())

```


3. Follow the terminal prompt to enter your Monarch email, password, and MFA code.

### 2. Encode the Session File to Base64

Encode `monarch_session.pickle` to a single base64 string:

* **macOS:**
```bash
base64 -i monarch_session.pickle | pbcopy

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
| `MONARCH_SESSION_B64` | `gASV...` | The entire base64 string generated from `monarch_session.pickle` |
| `MONARCH_ACCOUNT_ID` | `xxxxxxxx-xxxx-...` | Your manual Collectibles account UUID in Monarch |

---

## Automation Workflow

The workflow file located at `.github/workflows/sync.yml` automatically executes the sync:

```yaml
name: Sync TCG Collector to Monarch

on:
  schedule:
    # Runs daily at 06:00 UTC
    - cron: '0 6 * * *'
  workflow_dispatch: # Allows manual trigger from Actions tab

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
          MONARCH_SESSION_B64: ${{ secrets.MONARCH_SESSION_B64 }}
          MONARCH_ACCOUNT_ID: ${{ secrets.MONARCH_ACCOUNT_ID }}
        run: |
          python sync_tcg_to_monarch.py

```

---

## Troubleshooting

* **`HTTP Code 405: Method Not Allowed`:** Ensure `MonarchMoneyEndpoints.BASE_URL = "[https://api.monarch.com](https://api.monarch.com)"` is defined before instantiating `MonarchMoney()`.
* **`AttributeError: 'MonarchMoney' object has no attribute 'update_account_balance'`:** Use `mm.update_account(account_id=..., account_balance=...)` instead.
* **Session Expiration:** Monarch sessions generally remain valid for several months. If the Action fails with an unauthorized or authentication error, run `save_session.py` locally again and update the `MONARCH_SESSION_B64` secret in GitHub.