"""Async quickstart for pyth-pandas."""

from __future__ import annotations

import asyncio

from dotenv import load_dotenv

from pyth_pandas import AsyncPythPandas

load_dotenv()


async def main() -> None:
    async with AsyncPythPandas() as client:
        df = await client.fetch_latest_prices(
            symbols=["Crypto.BTC/USD"],
            properties=["price", "exponent"],
            formats=[],
        )
        print(df)


if __name__ == "__main__":
    asyncio.run(main())
