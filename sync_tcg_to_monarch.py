import asyncio
import os
import re
import requests
from bs4 import BeautifulSoup
from monarchmoney import MonarchMoney

# Configuration
TCGCOLLECTOR_USER = os.getenv("TCGCOLLECTOR_USER")
MONARCH_EMAIL = os.getenv("MONARCH_EMAIL")
MONARCH_PASSWORD = os.getenv("MONARCH_PASSWORD")
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
    
    # 1. Check for standard metric/card stat blocks containing a dollar sign
    stat_items = soup.find_all(lambda tag: tag.name in ["div", "span", "p"] and "$" in tag.text)
    
    portfolio_value = None
    for item in stat_items:
        # Check if parent or neighboring text mentions "Value", "Price", or "Total"
        context = item.find_parent().get_text() if item.find_parent() else item.get_text()
        if any(term in context.lower() for term in ["value", "collection value", "market value"]):
            match = re.search(r"\$\s?([0-9,]+(?:\.[0-9]{2})?)", item.get_text())
            if match:
                portfolio_value = float(match.group(1).replace(",", ""))
                break
                
    # 2. Fallback: Search the full HTML if classes or layout change
    if portfolio_value is None:
        matches = re.findall(r"(?:collection|market)?\s*value.*?(\$\s?[0-9,]+(?:\.[0-9]{2})?)", response.text, re.IGNORECASE | re.DOTALL)
        if matches:
            clean_match = re.search(r"\$\s?([0-9,]+(?:\.[0-9]{2})?)", matches[0])
            if clean_match:
                portfolio_value = float(clean_match.group(1).replace(",", ""))

    if portfolio_value is None:
        raise ValueError("Could not extract collection value from the public dashboard page.")
        
    return portfolio_value


async def update_monarch_balance(new_balance: float):
    mm = MonarchMoney()
    await mm.login(email=MONARCH_EMAIL, password=MONARCH_PASSWORD)
    
    await mm.update_account_balance(
        account_id=MONARCH_ACCOUNT_ID,
        balance=new_balance
    )
    print(f"Successfully updated Monarch account {MONARCH_ACCOUNT_ID} to ${new_balance:,.2f}")


async def main():
    try:
        val = get_tcgcollector_portfolio_value(PUBLIC_TCG_URL)
        print(f"Found TCG Collector valuation: ${val:,.2f}")
        await update_monarch_balance(val)
    except Exception as e:
        print(f"Sync failed: {e}")
        raise e

if __name__ == "__main__":
    asyncio.run(main())