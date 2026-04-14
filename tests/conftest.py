"""Shared pytest fixtures."""

import pytest

from pyth_pandas import PythPandas


@pytest.fixture
def client() -> PythPandas:
    """Unauthenticated client for low-level error-handling tests."""
    return PythPandas(use_tqdm=False)


@pytest.fixture
def authed_client() -> PythPandas:
    """Client with stub credentials for endpoint tests."""
    return PythPandas(use_tqdm=False, api_key="test-api-key")
