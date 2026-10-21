import asyncio
from monarchmoney import MonarchMoney, MonarchMoneyEndpoints

# Redirect to the active Monarch API domain
MonarchMoneyEndpoints.BASE_URL = "https://api.monarch.com"

async def main():
    mm = MonarchMoney()
    # This will now hit https://api.monarch.com/auth/login/ without returning a 405
    await mm.interactive_login()
    mm.save_session("monarch_session.pickle")
    print("\nSession saved successfully as monarch_session.pickle!")

if __name__ == "__main__":
    asyncio.run(main())