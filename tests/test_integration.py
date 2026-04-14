"""Live integration tests. Skipped unless ``PYTEST_LIVE=1``.

Run with::

    PYTEST_LIVE=1 uv run pytest tests/test_integration.py -v

Live tests require a real ``PYTH_API_KEY`` (Pyth Pro access token) and
network reachability of the Pyth Pro Router endpoint.
"""

from __future__ import annotations

import os
import time

import pandas as pd
import pytest

from pyth_pandas import ParsedFeedSchema, PythAuthError, PythPandas

pytestmark = pytest.mark.skipif(
    not os.getenv("PYTEST_LIVE"),
    reason="Live tests disabled. Set PYTEST_LIVE=1 to enable.",
)

_THROTTLE_SECONDS = float(os.getenv("PYTH_TEST_THROTTLE", "1"))


@pytest.fixture(autouse=True)
def _throttle_between_live_calls():
    time.sleep(_THROTTLE_SECONDS)
    yield


@pytest.fixture(scope="module")
def live_client() -> PythPandas:
    return PythPandas(use_tqdm=False)


def test_fetch_latest_prices_live(live_client: PythPandas):
    df = live_client.fetch_latest_prices(
        symbols=["Crypto.BTC/USD", "Crypto.ETH/USD"],
        properties=["price", "confidence", "exponent", "publisherCount"],
        formats=[],
    )
    assert isinstance(df, pd.DataFrame)
    assert len(df) >= 1
    ParsedFeedSchema.validate(df)


def test_get_guardian_set_upgrade_live(live_client: PythPandas):
    # Returns SignedGuardianSetUpgrade dict or None — both are valid.
    # The governance endpoint is entitled separately from price feeds; a
    # price-feed-only token will get 403 here, which is expected.
    try:
        result = live_client.get_guardian_set_upgrade()
    except PythAuthError as exc:
        pytest.skip(f"Token not entitled for /guardian_set_upgrade: {exc}")
    assert result is None or "new_guardian_set_index" in result
