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
        # Cast to float — exponents are negative ints, and `int ** negative-int`
        # raises in numpy/pandas. Float exponentiation handles it correctly.
        df["humanPrice"] = df["price"].astype(float) * 10.0 ** df["exponent"].astype(float)
        print(df[["priceFeedId", "humanPrice", "publisherCount"]])
        print("update timestamp (µs):", df.attrs.get("timestampUs"))


if __name__ == "__main__":
    main()
