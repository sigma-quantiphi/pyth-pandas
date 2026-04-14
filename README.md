# pyth-pandas

> pandas-style client for the Pyth Pro Router (Pyth Lazer) REST + WebSocket API

[![PyPI](https://img.shields.io/pypi/v/pyth-pandas)](https://pypi.org/project/pyth-pandas/)
[![Python](https://img.shields.io/pypi/pyversions/pyth-pandas)](https://pypi.org/project/pyth-pandas/)
[![Downloads](https://img.shields.io/pypi/dm/pyth-pandas)](https://pypistats.org/packages/pyth-pandas)
[![License](https://img.shields.io/pypi/l/pyth-pandas)](https://github.com/sigma-quantiphi/pyth-pandas/blob/main/LICENSE)
[![CI](https://github.com/sigma-quantiphi/pyth-pandas/actions/workflows/ci.yml/badge.svg)](https://github.com/sigma-quantiphi/pyth-pandas/actions/workflows/ci.yml)
[![Code style: Ruff](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/ruff/main/assets/badge/v2.json)](https://github.com/astral-sh/ruff)
[![Docs](https://img.shields.io/badge/docs-sphinx-blue)](https://sigma-quantiphi.github.io/pyth-pandas/)
[![Binder](https://mybinder.org/badge_logo.svg)](https://mybinder.org/v2/gh/sigma-quantiphi/pyth-pandas/HEAD?labpath=examples)

Every list endpoint returns a `pandas.DataFrame`, every dict endpoint returns
a `TypedDict`, and every shape is enforced by a `pandera` schema. Sync + async,
plus optional WebSocket, Streamlit explorer, and FastMCP server extras.

This client targets **Pyth Pro Router API v1.0.0** (per the published OpenAPI
spec). The package version (`0.1.0`) is independent of the upstream API
version — see the `API_VERSION` / `SUPPORTED_API_VERSIONS` class attributes
on `PythPandas`.

## Install

```bash
uv pip install pyth-pandas              # core
uv pip install "pyth-pandas[ws]"        # + WebSocket
uv pip install "pyth-pandas[explorer]"  # + Streamlit dashboard
uv pip install "pyth-pandas[mcp]"       # + FastMCP server
uv pip install "pyth-pandas[dev]"       # + test/lint toolchain
```

## Quickstart

```python
from pyth_pandas import PythPandas

with PythPandas() as client:
    df = client.fetch_latest_prices(
        symbols=["Crypto.BTC/USD", "Crypto.ETH/USD"],
        properties=["price", "confidence", "exponent", "publisherCount"],
        formats=[],
    )
    df["humanPrice"] = df["price"] * 10 ** df["exponent"]
    print(df[["priceFeedId", "humanPrice", "publisherCount"]])
```

The DataFrame has one row per feed. The on-chain payloads (when
requested via `formats=["evm", ...]`) and the update timestamp are
attached on `df.attrs`. For the raw `JsonUpdate` dict, use
`fetch_latest_prices_raw(...)`.

### Async

```python
import asyncio
from pyth_pandas import AsyncPythPandas

async def main():
    async with AsyncPythPandas() as client:
        df = await client.fetch_latest_prices(
            symbols=["Crypto.BTC/USD"],
            properties=["price", "exponent"],
            formats=[],
        )
        print(df)

asyncio.run(main())
```

## Authentication

Pyth Pro requires a bearer access token. Set it via env var (recommended) or
constructor arg. Copy the shipped `.env.example` to `.env` and fill in your
key — examples and tests load it via `python-dotenv`:

```bash
cp .env.example .env
$EDITOR .env       # set PYTH_API_KEY=...
```

Or set it in your shell:

```bash
export PYTH_API_KEY=...
```

Or pass it directly:

```python
PythPandas(api_key="...")
```

## Endpoints

| Method | HTTP | Returns |
|---|---|---|
| `fetch_latest_prices(...)` | `POST /v1/latest_price` | `DataFrame[ParsedFeedSchema]` |
| `fetch_latest_prices_raw(...)` | `POST /v1/latest_price` | `JsonUpdate` (TypedDict) |
| `fetch_prices(timestamp=..., ...)` | `POST /v1/price` | `DataFrame[ParsedFeedSchema]` |
| `fetch_prices_raw(...)` | `POST /v1/price` | `JsonUpdate` |
| `reduce_price(payload=..., price_feed_ids=...)` | `POST /v1/reduce_price` | `DataFrame[ParsedFeedSchema]` |
| `reduce_price_raw(...)` | `POST /v1/reduce_price` | `JsonUpdate` |
| `get_guardian_set_upgrade()` | `GET /v1/guardian_set_upgrade` | `SignedGuardianSetUpgrade \| None` |

WebSocket: `PythWebSocket` / `AsyncPythWebSocket` (extra: `ws`) → connects
to `wss://pyth-lazer.dourolabs.app/v1/stream`.

## Compatibility

| pyth-pandas | Pyth Pro Router API |
|---|---|
| 0.1.x | 1.0.0 |

## Error handling

```python
from pyth_pandas import PythAuthError, PythRateLimitError, PythAPIError

try:
    df = client.fetch_latest_prices(symbols=["Crypto.BTC/USD"], properties=["price"])
except PythAuthError:
    ...  # 401/403 or missing PYTH_API_KEY
except PythRateLimitError:
    ...  # 429
except PythAPIError as e:
    print(e.status_code, e.url, e.detail)
```

## Development

```bash
uv pip install -e ".[dev,ws,explorer,mcp]"
uv run pytest tests/test_unit.py tests/test_async_unit.py -v
uv run ruff check pyth_pandas tests
uv run mypy pyth_pandas
```

CI runs the same checks on every push and PR via `.github/workflows/ci.yml`
across Python 3.11, 3.12, 3.13.

## Releasing

Releases are cut by pushing a `v*` tag. `.github/workflows/release.yml`:

1. Runs ruff + mypy + mocked pytest, then **live integration tests** against
   the real upstream API. If the test job fails, build / publish / release
   are all skipped.
2. Builds sdist + wheel via `uv build`.
3. Publishes to PyPI via [trusted publishing](https://docs.pypi.org/trusted-publishers/).
4. Creates a GitHub release.

**One-time setup:**

1. Reserve `pyth-pandas` on PyPI.
2. At <https://pypi.org/manage/account/publishing/>, add a pending publisher:
   - Project: `pyth-pandas`
   - Owner: your GitHub user/org
   - Repo: `pyth-pandas`
   - Workflow: `release.yml`
   - Environment: `pypi`
3. Create the `pypi` environment in GitHub repo settings.
4. Add `PYTH_API_KEY` as an environment secret on the `pypi` environment so
   live integration tests can run before publishing.
5. Enable GitHub Pages with source = "GitHub Actions" so `docs.yml` can
   deploy the Sphinx site.

**To force a release if the test infra is broken:**

```bash
gh workflow run release.yml -f tag=v0.1.1 -f skip_tests=true
```

## License

Apache-2.0
