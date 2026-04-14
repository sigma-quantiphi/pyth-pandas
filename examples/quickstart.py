"""Sync quickstart for pyth-pandas.

Run with::

    cp .env.example .env  # then edit, fill in PYTH_API_KEY
    uv run python examples/quickstart.py
"""

from __future__ import annotations

from dotenv import load_dotenv

from pyth_pandas import PythPandas

load_dotenv()


def main() -> None:
    with PythPandas() as client:
        df = client.fetch_latest_prices(
            symbols=["Crypto.BTC/USD", "Crypto.ETH/USD"],
            properties=["price", "confidence", "exponent", "publisherCount"],
            formats=[],
        )
        # Convert raw mantissa to a human-readable price.
        df["humanPrice"] = df["price"] * 10 ** df["exponent"]
        print(df[["priceFeedId", "humanPrice", "publisherCount"]])
        print("update timestamp (µs):", df.attrs.get("timestampUs"))


if __name__ == "__main__":
    main()
