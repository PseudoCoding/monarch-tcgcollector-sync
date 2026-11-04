import asyncio
import base64
import math
import os
import re
import requests
import tempfile
from typing import Optional
from bs4 import BeautifulSoup
from monarchmoney import MonarchMoney, MonarchMoneyEndpoints

# Set the active API endpoint
MonarchMoneyEndpoints.BASE_URL = "https://api.monarch.com"

# Configuration
TCGCOLLECTOR_USER_ID = os.getenv("TCGCOLLECTOR_USER_ID")
MONARCH_SESSION_B64 = os.getenv("MONARCH_SESSION_B64")
MONARCH_ACCOUNT_ID = os.getenv("MONARCH_ACCOUNT_ID")
MAX_BALANCE_CHANGE = os.getenv("MAX_BALANCE_CHANGE")

PUBLIC_TCG_URL = f"https://www.tcgcollector.com/dashboard/intl?viewUser={TCGCOLLECTOR_USER_ID}"


def get_tcgcollector_portfolio_value(url: str) -> float:
    """Scrapes the total market/collection value from the public dashboard page."""
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/120.0.0.0 Safari/537.36"
        ),
        "Accept-Language": "en-US,en;q=0.9",
    }

    response = requests.get(url, headers=headers, timeout=15)
    response.raise_for_status()

    soup = BeautifulSoup(response.text, "html.parser")

    # Look for metrics containing dollar signs
    stat_items = soup.find_all(lambda tag: tag.name in ["div", "span", "p"] and "$" in tag.text)

    portfolio_value = None
    for item in stat_items:
        context = item.find_parent().get_text() if item.find_parent() else item.get_text()
        if any(term in context.lower() for term in ["value", "collection value", "market value"]):
            match = re.search(r"\$\s?([0-9,]+(?:\.[0-9]{2})?)", item.get_text())
            if match:
                portfolio_value = float(match.group(1).replace(",", ""))
                break

    # Fallback regex if layout changes
    if portfolio_value is None:
        matches = re.findall(
            r"(?:collection|market)?\s*value.*?(\$\s?[0-9,]+(?:\.[0-9]{2})?)",
            response.text,
            re.IGNORECASE | re.DOTALL,
        )
        if matches:
            clean_match = re.search(r"\$\s?([0-9,]+(?:\.[0-9]{2})?)", matches[0])
            if clean_match:
                portfolio_value = float(clean_match.group(1).replace(",", ""))

    if portfolio_value is None:
        raise ValueError("Could not extract collection value from the public dashboard page.")

    return portfolio_value


def validate_balance_change(
    current_balance: float,
    new_balance: float,
    max_balance_change: Optional[float],
) -> None:
    values = (current_balance, new_balance)
    if not all(math.isfinite(value) for value in values):
        raise ValueError("Balance values must be finite numbers.")
    if current_balance < 0 or new_balance < 0:
        raise ValueError("Balances must not be negative.")
    if max_balance_change is None:
        return
    if not math.isfinite(max_balance_change) or max_balance_change < 0:
        raise ValueError("MAX_BALANCE_CHANGE must be a finite, non-negative number.")
    if abs(new_balance - current_balance) > max_balance_change:
        raise ValueError(
            "The scraped balance differs from the current Monarch balance by more "
            "than MAX_BALANCE_CHANGE; no update was made."
        )


def parse_dry_run(value: Optional[str]) -> bool:
    if value is None:
        return True
    normalized_value = value.strip().lower()
    if normalized_value in {"1", "true", "yes"}:
        return True
    if normalized_value in {"0", "false", "no"}:
        return False
    raise ValueError("DRY_RUN must be set to true or false.")


async def update_monarch_balance(
    new_balance: float, max_balance_change: Optional[float], dry_run: bool
) -> None:
    mm = MonarchMoney()

    session_path = None
    try:
        session_bytes = base64.b64decode(
            "".join(MONARCH_SESSION_B64.split()), validate=True
        )
        with tempfile.NamedTemporaryFile(suffix=".pickle", delete=False) as session_file:
            session_path = session_file.name
            session_file.write(session_bytes)
        mm.load_session(session_path)
    finally:
        if session_path and os.path.exists(session_path):
            os.remove(session_path)

    accounts_response = await mm.get_accounts()
    accounts = accounts_response.get("accounts")
    if not isinstance(accounts, list):
        raise ValueError("Could not read Monarch accounts; no balance update was made.")

    account = next(
        (item for item in accounts if item.get("id") == MONARCH_ACCOUNT_ID), None
    )
    if account is None:
        raise ValueError("The configured Monarch account was not found.")

    current_balance = float(account["currentBalance"])
    validate_balance_change(current_balance, new_balance, max_balance_change)

    if dry_run:
        print("Dry run passed; no Monarch account was updated.")
        return

    await mm.update_account(
        account_id=MONARCH_ACCOUNT_ID,
        account_balance=new_balance,
    )
    print("Monarch account balance updated successfully.")


async def main():
    required_environment_variables = {
        "TCGCOLLECTOR_USER_ID": TCGCOLLECTOR_USER_ID,
        "MONARCH_SESSION_B64": MONARCH_SESSION_B64,
        "MONARCH_ACCOUNT_ID": MONARCH_ACCOUNT_ID,
    }
    missing_variables = [
        name for name, value in required_environment_variables.items() if not value
    ]
    if missing_variables:
        raise ValueError("Missing required configuration: " + ", ".join(missing_variables))

    max_balance_change = None
    if MAX_BALANCE_CHANGE and MAX_BALANCE_CHANGE.strip():
        try:
            max_balance_change = float(MAX_BALANCE_CHANGE)
        except ValueError as error:
            raise ValueError("MAX_BALANCE_CHANGE must be a non-negative number.") from error
        if not math.isfinite(max_balance_change) or max_balance_change < 0:
            raise ValueError("MAX_BALANCE_CHANGE must be a finite, non-negative number.")

    dry_run = parse_dry_run(os.getenv("DRY_RUN"))
    portfolio_value = get_tcgcollector_portfolio_value(PUBLIC_TCG_URL)
    if not math.isfinite(portfolio_value) or portfolio_value < 0:
        raise ValueError("The scraped collection value is invalid; no update was made.")
    await update_monarch_balance(portfolio_value, max_balance_change, dry_run)


if __name__ == "__main__":
    asyncio.run(main())