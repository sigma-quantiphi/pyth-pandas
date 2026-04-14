"""Async unit tests via pytest-asyncio."""

from __future__ import annotations

import pytest
from pytest_httpx import HTTPXMock

from pyth_pandas import AsyncPythPandas, ParsedFeedSchema, PythPandas

pytestmark = pytest.mark.asyncio


_LATEST_RESPONSE = {
    "parsed": {
        "timestampUs": "1700000000000000",
        "priceFeeds": [
            {"priceFeedId": 1, "price": "5000000000000", "exponent": -8},
        ],
    }
}


async def test_async_client_constructible():
    async with AsyncPythPandas() as client:
        assert client.base_url


async def test_async_methods_match_sync():
    """Every public method on the sync client must be reachable on the async one."""
    sync_methods = {
        m
        for m in dir(PythPandas)
        if not m.startswith("_") and callable(getattr(PythPandas, m, None))
    }
    async_methods = {
        m
        for m in dir(AsyncPythPandas)
        if not m.startswith("_") and callable(getattr(AsyncPythPandas, m, None))
    }
    missing = (
        sync_methods
        - async_methods
        - {
            "close",
            "preprocess_dataframe",
            "preprocess_dict",
        }
    )
    assert not missing, f"Missing async wrappers: {missing}"


async def test_async_fetch_latest_prices(httpx_mock: HTTPXMock):
    async with AsyncPythPandas(api_key="test", use_tqdm=False) as client:
        httpx_mock.add_response(
            url=f"{client.base_url}latest_price",
            method="POST",
            json=_LATEST_RESPONSE,
        )
        df = await client.fetch_latest_prices(
            symbols=["Crypto.BTC/USD"],
            properties=["price", "exponent"],
            formats=[],
        )
    ParsedFeedSchema.validate(df)
    assert df.iloc[0]["priceFeedId"] == 1
