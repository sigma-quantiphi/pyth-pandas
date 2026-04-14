"""Unit tests — no live API calls; HTTP interactions mocked via pytest-httpx."""

from __future__ import annotations

import pandas as pd
import pytest
from pytest_httpx import HTTPXMock

from pyth_pandas import (
    ParsedFeedSchema,
    PythAPIError,
    PythAuthError,
    PythPandas,
    PythRateLimitError,
)
from pyth_pandas.utils import filter_params, snake_to_camel, to_unix_timestamp_us

# ── Utility tests ────────────────────────────────────────────────────


def test_snake_to_camel():
    assert snake_to_camel("price_feed_id") == "priceFeedId"
    assert snake_to_camel("already") == "already"


def test_filter_params_removes_none():
    assert filter_params({"a": 1, "b": None}) == {"a": 1}


def test_filter_params_removes_empty_lists():
    assert filter_params({"a": [], "b": [1]}) == {"b": [1]}


def test_to_unix_timestamp_us_int_seconds():
    assert to_unix_timestamp_us(1_700_000_000) == 1_700_000_000_000_000


def test_to_unix_timestamp_us_int_already_us():
    assert to_unix_timestamp_us(1_700_000_000_000_000) == 1_700_000_000_000_000


def test_to_unix_timestamp_us_iso_string():
    assert to_unix_timestamp_us("2024-01-01T00:00:00Z") == 1_704_067_200_000_000


# ── Error handling ───────────────────────────────────────────────────


def test_auth_error_on_401(client: PythPandas, httpx_mock: HTTPXMock):
    httpx_mock.add_response(status_code=401, json={"error": "unauthorized"})
    with pytest.raises(PythAuthError):
        client._request(path="anything")


def test_rate_limit_error_on_429(client: PythPandas, httpx_mock: HTTPXMock):
    httpx_mock.add_response(status_code=429, json={"error": "rate limited"})
    with pytest.raises(PythRateLimitError):
        client._request(path="anything")


def test_api_error_on_500(client: PythPandas, httpx_mock: HTTPXMock):
    httpx_mock.add_response(status_code=500, json={"error": "boom"})
    with pytest.raises(PythAPIError):
        client._request(path="anything")


def test_missing_credentials_raises_before_request(httpx_mock: HTTPXMock):
    c = PythPandas(use_tqdm=False, api_key=None)
    with pytest.raises(PythAuthError):
        c._request_authed(path="latest_price")
    assert not httpx_mock.get_requests()


# ── Endpoint tests ───────────────────────────────────────────────────


_LATEST_RESPONSE = {
    "parsed": {
        "timestampUs": "1700000000000000",
        "priceFeeds": [
            {
                "priceFeedId": 1,
                "price": "5000000000000",
                "confidence": 1000,
                "exponent": -8,
                "publisherCount": 12,
            },
            {
                "priceFeedId": 2,
                "price": "300000000000",
                "confidence": 500,
                "exponent": -8,
                "publisherCount": 10,
            },
        ],
    },
    "evm": {"encoding": "hex", "data": "0xdeadbeef"},
}


def test_fetch_latest_prices_returns_dataframe(authed_client: PythPandas, httpx_mock: HTTPXMock):
    httpx_mock.add_response(
        url=f"{authed_client.base_url}latest_price",
        method="POST",
        json=_LATEST_RESPONSE,
    )
    df = authed_client.fetch_latest_prices(
        symbols=["Crypto.BTC/USD", "Crypto.ETH/USD"],
        properties=["price", "confidence", "exponent", "publisherCount"],
        formats=["evm"],
    )
    assert isinstance(df, pd.DataFrame)
    assert len(df) == 2
    assert {"priceFeedId", "price", "confidence", "exponent"}.issubset(df.columns)
    assert df.attrs["timestampUs"] == "1700000000000000"
    assert df.attrs["evm"]["data"] == "0xdeadbeef"
    ParsedFeedSchema.validate(df)


def test_fetch_latest_prices_raw_returns_dict(authed_client: PythPandas, httpx_mock: HTTPXMock):
    httpx_mock.add_response(
        url=f"{authed_client.base_url}latest_price",
        method="POST",
        json=_LATEST_RESPONSE,
    )
    payload = authed_client.fetch_latest_prices_raw(
        symbols=["Crypto.BTC/USD"],
        properties=["price"],
        formats=["evm"],
    )
    assert payload["parsed"]["timestampUs"] == "1700000000000000"
    assert payload["evm"]["data"] == "0xdeadbeef"


def test_fetch_latest_prices_requires_ids_or_symbols(authed_client: PythPandas):
    with pytest.raises(ValueError):
        authed_client.fetch_latest_prices(
            properties=["price"], formats=[], price_feed_ids=None, symbols=None
        )
    with pytest.raises(ValueError):
        authed_client.fetch_latest_prices(
            properties=["price"],
            formats=[],
            price_feed_ids=[1],
            symbols=["Crypto.BTC/USD"],
        )


def test_fetch_prices_sends_microsecond_timestamp(authed_client: PythPandas, httpx_mock: HTTPXMock):
    httpx_mock.add_response(
        url=f"{authed_client.base_url}price",
        method="POST",
        json=_LATEST_RESPONSE,
    )
    df = authed_client.fetch_prices(
        timestamp=1_700_000_000,  # seconds — should be promoted to µs
        symbols=["Crypto.BTC/USD"],
        properties=["price"],
        formats=[],
    )
    ParsedFeedSchema.validate(df)
    sent = httpx_mock.get_requests()[-1].read()
    assert b'"timestamp":1700000000000000' in sent


def test_reduce_price_returns_dataframe(authed_client: PythPandas, httpx_mock: HTTPXMock):
    httpx_mock.add_response(
        url=f"{authed_client.base_url}reduce_price",
        method="POST",
        json=_LATEST_RESPONSE,
    )
    df = authed_client.reduce_price(payload=_LATEST_RESPONSE, price_feed_ids=[1])
    assert isinstance(df, pd.DataFrame)
    ParsedFeedSchema.validate(df)


def test_get_guardian_set_upgrade_none(authed_client: PythPandas, httpx_mock: HTTPXMock):
    httpx_mock.add_response(
        url=f"{authed_client.base_url}guardian_set_upgrade",
        method="GET",
        json=None,
    )
    assert authed_client.get_guardian_set_upgrade() is None


def test_get_guardian_set_upgrade_present(authed_client: PythPandas, httpx_mock: HTTPXMock):
    body = {
        "current_guardian_set_index": 4,
        "new_guardian_set_index": 5,
        "new_guardian_keys": [[1, 2, 3]],
        "body": "0xdead",
        "signature": "0xbeef",
    }
    httpx_mock.add_response(
        url=f"{authed_client.base_url}guardian_set_upgrade",
        method="GET",
        json=body,
    )
    out = authed_client.get_guardian_set_upgrade()
    assert out is not None
    assert out["new_guardian_set_index"] == 5
