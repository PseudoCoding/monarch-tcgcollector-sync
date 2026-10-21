import asyncio
import base64
import os
import re
import requests
from bs4 import BeautifulSoup
from monarchmoney import MonarchMoney, MonarchMoneyEndpoints

# Set the active API endpoint
MonarchMoneyEndpoints.BASE_URL = "https://api.monarch.com"

# Configuration
TCGCOLLECTOR_USER = os.getenv("TCGCOLLECTOR_USER")
MONARCH_SESSION_B64 = os.getenv("MONARCH_SESSION_B64")
MONARCH_ACCOUNT_ID = os.getenv("MONARCH_ACCOUNT_ID")

PUBLIC_TCG_URL = f"https://www.tcgcollector.com/dashboard/intl?viewUser={TCGCOLLECTOR_USER}"


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


async def update_monarch_balance(new_balance: float):
    mm = MonarchMoney()

    # Reconstitute and load saved session file
    session_bytes = base64.b64decode(MONARCH_SESSION_B64)
    with open("temp_session.pickle", "wb") as f:
        f.write(session_bytes)

    mm.load_session("temp_session.pickle")

    if os.path.exists("temp_session.pickle"):
        os.remove("temp_session.pickle")

    await mm.update_account(
		account_id=MONARCH_ACCOUNT_ID,
		account_balance=new_balance
	)
    
    print(f"Successfully updated Monarch account {MONARCH_ACCOUNT_ID} to ${new_balance:,.2f}")


async def main():
    if not MONARCH_SESSION_B64 or not MONARCH_ACCOUNT_ID:
        raise ValueError("Missing MONARCH_SESSION_B64 or MONARCH_ACCOUNT_ID environment variables.")

    val = get_tcgcollector_portfolio_value(PUBLIC_TCG_URL)
    print(f"Found TCG Collector valuation: ${val:,.2f}")
    await update_monarch_balance(val)


if __name__ == "__main__":
    asyncio.run(main())