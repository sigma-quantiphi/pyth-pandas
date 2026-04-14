"""PythPandas — core HTTP client dataclass with DataFrame preprocessing.

The client targets the Pyth Pro Router (Pyth Lazer) REST API. Endpoint
methods live in mixins; this class provides transport, authentication,
DataFrame preprocessing, and shared infrastructure.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from typing import ClassVar, Self

import httpx
import pandas as pd

from pyth_pandas.exceptions import PythAPIError, PythAuthError, PythRateLimitError
from pyth_pandas.mixins import GovernanceMixin, PricesMixin
from pyth_pandas.utils import (
    DEFAULT_BOOL_COLUMNS,
    DEFAULT_DROP_COLUMNS,
    DEFAULT_INT_DATETIME_COLUMNS,
    DEFAULT_JSON_COLUMNS,
    DEFAULT_MS_INT_DATETIME_COLUMNS,
    DEFAULT_NUMERIC_COLUMNS,
    DEFAULT_STR_DATETIME_COLUMNS,
    DEFAULT_US_INT_DATETIME_COLUMNS,
    expand_column_lists,
    filter_params,
)
from pyth_pandas.utils import preprocess_dataframe as _preprocess_dataframe
from pyth_pandas.utils import preprocess_dict as _preprocess_dict


@dataclass
class PythPandas(PricesMixin, GovernanceMixin):
    """HTTP client for the Pyth Pro Router that returns pandas DataFrames.

    Endpoint methods live in the mixins. This class provides the HTTP
    transport, bearer-token authentication, DataFrame preprocessing, and
    error-mapping infrastructure. Use as a context manager so the
    underlying connection pool is closed deterministically.

    Args:
        base_url: Pyth Pro Router base URL. Pyth runs multiple endpoints
            (numbered 0/1/2) for redundancy; supply whichever you have
            been onboarded onto.
        timeout: Per-request timeout in seconds.
        api_key: Bearer access token. Falls back to ``PYTH_API_KEY``
            from the environment (after any ``load_dotenv()`` call).
        use_tqdm: Whether progress bars are enabled for any future
            paginated helpers.

    Example:
        >>> from pyth_pandas import PythPandas
        >>> with PythPandas() as client:
        ...     df = client.fetch_latest_prices(
        ...         symbols=["Crypto.BTC/USD"],
        ...         properties=["price", "confidence", "exponent"],
        ...     )
    """

    #: Upstream API version this client targets (from the OpenAPI spec).
    API_VERSION: ClassVar[str] = "1.0.0"
    #: Upstream API versions this client is known to be compatible with.
    SUPPORTED_API_VERSIONS: ClassVar[tuple[str, ...]] = ("1.0.0",)

    base_url: str = "https://pyth-lazer.dourolabs.app/v1/"
    timeout: int = field(default=30, repr=False)
    api_key: str | None = field(default=None, repr=False)
    use_tqdm: bool = field(default=True, repr=True)
    tqdm_description: str = field(default="", repr=False)

    # Column-coercion defaults (override per-instance to extend)
    numeric_columns: tuple = field(default=DEFAULT_NUMERIC_COLUMNS, repr=False)
    str_datetime_columns: tuple = field(default=DEFAULT_STR_DATETIME_COLUMNS, repr=False)
    int_datetime_columns: tuple = field(default=DEFAULT_INT_DATETIME_COLUMNS, repr=False)
    ms_int_datetime_columns: tuple = field(default=DEFAULT_MS_INT_DATETIME_COLUMNS, repr=False)
    us_int_datetime_columns: tuple = field(default=DEFAULT_US_INT_DATETIME_COLUMNS, repr=False)
    bool_columns: tuple = field(default=DEFAULT_BOOL_COLUMNS, repr=False)
    drop_columns: tuple = field(default=DEFAULT_DROP_COLUMNS, repr=False)
    json_columns: tuple = field(default=DEFAULT_JSON_COLUMNS, repr=False)

    # ── Lifecycle ───────────────────────────────────────────────────────

    def __post_init__(self) -> None:
        if self.api_key is None:
            self.api_key = os.getenv("PYTH_API_KEY")

        if not self.base_url.endswith("/"):
            self.base_url = self.base_url + "/"

        self._client = httpx.Client(timeout=self.timeout)

        self._numeric_columns = expand_column_lists(self.numeric_columns)
        self._str_datetime_columns = expand_column_lists(self.str_datetime_columns)
        self._int_datetime_columns = expand_column_lists(self.int_datetime_columns)
        self._ms_int_datetime_columns = expand_column_lists(self.ms_int_datetime_columns)
        self._us_int_datetime_columns = expand_column_lists(self.us_int_datetime_columns)
        self._bool_columns = expand_column_lists(self.bool_columns)
        self._drop_columns = expand_column_lists(self.drop_columns)
        self._json_columns = expand_column_lists(self.json_columns)

    def close(self) -> None:
        """Close the underlying HTTP connection pool."""
        self._client.close()

    def __enter__(self) -> Self:
        return self

    def __exit__(self, *_: object) -> None:
        self.close()

    # ── Preprocessing helpers (bound to instance config) ────────────────

    def preprocess_dataframe(self, df: pd.DataFrame) -> pd.DataFrame:
        """Apply the client's column-coercion config to ``df``."""
        return _preprocess_dataframe(
            df,
            numeric_columns=self._numeric_columns,
            str_datetime_columns=self._str_datetime_columns,
            int_datetime_columns=self._int_datetime_columns,
            ms_int_datetime_columns=self._ms_int_datetime_columns,
            us_int_datetime_columns=self._us_int_datetime_columns,
            bool_columns=self._bool_columns,
            drop_columns=self._drop_columns,
            json_columns=self._json_columns,
        )

    def preprocess_dict(self, data: dict) -> dict:
        """Apply the client's column-coercion config to a single dict."""
        return _preprocess_dict(
            data,
            numeric_columns=self._numeric_columns,
            str_datetime_columns=self._str_datetime_columns,
            int_datetime_columns=self._int_datetime_columns,
            ms_int_datetime_columns=self._ms_int_datetime_columns,
            us_int_datetime_columns=self._us_int_datetime_columns,
            bool_columns=self._bool_columns,
            drop_columns=self._drop_columns,
            json_columns=self._json_columns,
        )

    # ── Auth guards ─────────────────────────────────────────────────────

    def _require_auth(self) -> None:
        if not self.api_key:
            raise PythAuthError(
                detail=(
                    "Pyth Pro access token not set. Provide api_key or set "
                    "PYTH_API_KEY in the environment."
                )
            )

    def _auth_headers(self) -> dict:
        return {"Authorization": f"Bearer {self.api_key}"}

    # ── Request helpers ─────────────────────────────────────────────────

    def _request(
        self,
        *,
        path: str,
        method: str = "GET",
        params: dict | None = None,
        data: dict | list | None = None,
        headers: dict | None = None,
    ) -> dict | list:
        """Send an unauthenticated request and return parsed JSON."""
        url = self.base_url + path.lstrip("/")
        response = self._client.request(
            method,
            url,
            params=filter_params(params),
            json=data,
            headers=headers,
        )
        return self._handle_response(response)

    def _request_authed(
        self,
        *,
        path: str,
        method: str = "GET",
        params: dict | None = None,
        data: dict | list | None = None,
    ) -> dict | list:
        """Send an authenticated request, raising before network if the token is missing."""
        self._require_auth()
        return self._request(
            path=path,
            method=method,
            params=params,
            data=data,
            headers=self._auth_headers(),
        )

    # ── Error handling ──────────────────────────────────────────────────

    def _handle_response(self, response: httpx.Response) -> dict | list:
        try:
            response.raise_for_status()
        except httpx.HTTPStatusError as exc:
            status = exc.response.status_code
            url = str(exc.request.url)
            try:
                detail: object = exc.response.json()
            except Exception:
                detail = exc.response.text
            if status in (401, 403):
                raise PythAuthError(status, url, detail) from exc
            if status == 429:
                raise PythRateLimitError(status, url, detail) from exc
            raise PythAPIError(status, url, detail) from exc
        if not response.content:
            return {}
        return response.json()
