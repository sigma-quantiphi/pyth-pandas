# Getting started

```bash
uv pip install pyth-pandas
export PYTH_API_KEY=...     # your Pyth Pro access token
```

```python
from pyth_pandas import PythPandas

with PythPandas() as client:
    df = client.fetch_latest_prices(
        symbols=["Crypto.BTC/USD", "Crypto.ETH/USD"],
        properties=["price", "confidence", "exponent", "publisherCount"],
        formats=[],
    )
    print(df)
```

The `df` returned is a regular `pandas.DataFrame` whose columns conform to
[`ParsedFeedSchema`](api/schemas.rst). The on-chain payloads (EVM, Solana,
LeEcdsa, LeUnsigned) and the update timestamp are attached on `df.attrs`.
