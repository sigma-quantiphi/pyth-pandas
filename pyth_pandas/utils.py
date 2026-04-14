"""Stateless helpers shared across the pyth-pandas client.

This module is intentionally identical in shape across all api-pandas
generated packages. Add API-specific column names by extending the
``DEFAULT_*`` tuples in your client's dataclass fields, not here.
"""

from __future__ import annotations

import time
from datetime import datetime
from functools import wraps

import orjson
import pandas as pd

__all__ = [
    "DEFAULT_BOOL_COLUMNS",
    "DEFAULT_DROP_COLUMNS",
    "DEFAULT_INT_DATETIME_COLUMNS",
    "DEFAULT_JSON_COLUMNS",
    "DEFAULT_MS_INT_DATETIME_COLUMNS",
    "DEFAULT_NUMERIC_COLUMNS",
    "DEFAULT_STR_DATETIME_COLUMNS",
    "DEFAULT_US_INT_DATETIME_COLUMNS",
    "expand_column_lists",
    "filter_params",
    "instance_cache",
    "preprocess_dataframe",
    "preprocess_dict",
    "snake_columns_to_camel",
    "snake_to_camel",
    "to_unix_timestamp",
    "to_unix_timestamp_us",
]


# ── Defaults for Pyth Pro ────────────────────────────────────────────
# Pyth uses microsecond integer timestamps (TimestampUs) and large mantissa
# integers for prices/confidence (with separate exponent). We keep the
# default coercion narrow — just the obvious mantissa/numeric fields. The
# raw integer mantissas are NOT auto-divided by 10^exponent; that's left
# to the caller (use df["price"] * 10 ** df["exponent"]).
DEFAULT_NUMERIC_COLUMNS: tuple = (
    "price",
    "bestBidPrice",
    "bestAskPrice",
    "confidence",
    "emaPrice",
    "emaConfidence",
    "fundingRate",
    "exponent",
    "publisherCount",
    "fundingRateInterval",
    "priceFeedId",
)
DEFAULT_STR_DATETIME_COLUMNS: tuple = ()
DEFAULT_INT_DATETIME_COLUMNS: tuple = ()  # second-resolution Unix timestamps
DEFAULT_MS_INT_DATETIME_COLUMNS: tuple = ()
# Pyth-specific: microsecond-resolution Unix timestamps appear as integers
# in many feed fields. We coerce them in a dedicated pass below.
DEFAULT_US_INT_DATETIME_COLUMNS: tuple = (
    "timestampUs",
    "feedUpdateTimestamp",
    "fundingTimestamp",
)
DEFAULT_BOOL_COLUMNS: tuple = ()
DEFAULT_DROP_COLUMNS: tuple = ()
DEFAULT_JSON_COLUMNS: tuple = ()


# ── Conversions ──────────────────────────────────────────────────────


def to_unix_timestamp(value: int | float | str | pd.Timestamp | datetime) -> int:
    """Convert a datetime-like value to a Unix timestamp in seconds."""
    if isinstance(value, (int, float)):
        return int(value)
    if isinstance(value, str):
        value = pd.Timestamp(value, tz="UTC")
    if isinstance(value, pd.Timestamp):
        if value.tzinfo is None:
            value = value.tz_localize("UTC")
        return int(value.timestamp())
    if isinstance(value, datetime):
        if value.tzinfo is None:
            from zoneinfo import ZoneInfo

            value = value.replace(tzinfo=ZoneInfo("UTC"))
        return int(value.timestamp())
    raise TypeError(f"Cannot convert {type(value).__name__} to Unix timestamp")


def to_unix_timestamp_us(value: int | float | str | pd.Timestamp | datetime) -> int:
    """Convert a datetime-like value to a Unix timestamp in microseconds.

    Pyth Pro uses microsecond-resolution timestamps (`TimestampUs`) throughout
    its API. Prefer this over ``to_unix_timestamp`` when calling endpoints
    such as ``fetch_prices``.
    """
    if isinstance(value, int):
        # Heuristic: values >= 10**14 are already microsecond timestamps.
        return int(value) if value >= 10**14 else int(value) * 1_000_000
    if isinstance(value, float):
        return int(value * 1_000_000) if value < 10**13 else int(value)
    if isinstance(value, str):
        value = pd.Timestamp(value, tz="UTC")
    if isinstance(value, pd.Timestamp):
        if value.tzinfo is None:
            value = value.tz_localize("UTC")
        return int(value.value // 1000)  # ns → µs
    if isinstance(value, datetime):
        if value.tzinfo is None:
            from zoneinfo import ZoneInfo

            value = value.replace(tzinfo=ZoneInfo("UTC"))
        return int(value.timestamp() * 1_000_000)
    raise TypeError(f"Cannot convert {type(value).__name__} to microsecond timestamp")


def snake_to_camel(value: str) -> str:
    """Convert snake_case (or kebab-case) to lowerCamelCase."""
    if "_" in value:
        parts = value.split("_")
        value = parts[0] + "".join(p[:1].upper() + p[1:] for p in parts[1:] if p)
    return value


def snake_columns_to_camel(data: pd.DataFrame) -> pd.DataFrame:
    """Return a copy of df with camelCase column names."""
    data = data.copy()
    data.columns = [snake_to_camel(col) for col in data.columns]
    return data


# ── Caching ──────────────────────────────────────────────────────────


def instance_cache(method=None, *, ttl: float | None = None, maxsize: int = 256):
    """Cache results of an instance method, keyed by arguments.

    Wraps :func:`cachetools.cachedmethod`, storing a per-method cache on the
    instance as ``_cache_{method_name}``.
    """
    from cachetools import Cache, TTLCache, cachedmethod

    def decorator(fn):
        attr = f"_cache_{fn.__name__}"

        def _get_cache(self):
            cache = getattr(self, attr, None)
            if cache is None:
                cache = TTLCache(maxsize=maxsize, ttl=ttl) if ttl else Cache(maxsize=maxsize)
                setattr(self, attr, cache)
            return cache

        return cachedmethod(_get_cache)(fn)

    if method is not None:
        return decorator(method)
    return decorator


# ── Param filtering ──────────────────────────────────────────────────


def filter_params(params: dict | None) -> dict:
    """Remove None values and empty lists; convert Timestamps to Unix seconds."""
    if params is None:
        return {}
    new_params = {}
    for key, value in params.items():
        if isinstance(value, list):
            if len(value) > 0:
                new_params[key] = value
        elif value is None:
            continue
        else:
            if isinstance(value, (pd.Timestamp, datetime)):
                value = int(value.timestamp())
            new_params[key] = value
    return new_params


# ── Preprocessing ────────────────────────────────────────────────────


def preprocess_dataframe(
    df: pd.DataFrame,
    *,
    numeric_columns: list,
    str_datetime_columns: list,
    int_datetime_columns: list,
    ms_int_datetime_columns: list,
    bool_columns: list,
    drop_columns: list,
    json_columns: list,
    us_int_datetime_columns: list | None = None,
    int_datetime_unit: str = "s",
) -> pd.DataFrame:
    """Apply column renaming and type coercion to a raw API DataFrame."""
    if us_int_datetime_columns is None:
        us_int_datetime_columns = []
    df = snake_columns_to_camel(df)
    df = df.drop(columns=drop_columns, errors="ignore")
    columns = df.columns

    numeric_to_convert = [
        x
        for x in columns
        if x
        in numeric_columns
        + int_datetime_columns
        + ms_int_datetime_columns
        + us_int_datetime_columns
    ]
    int_datetime_to_convert = [x for x in columns if x in int_datetime_columns]
    ms_int_datetime_to_convert = [x for x in columns if x in ms_int_datetime_columns]
    us_int_datetime_to_convert = [x for x in columns if x in us_int_datetime_columns]
    str_datetime_to_convert = [x for x in columns if x in str_datetime_columns]
    bool_to_convert = [x for x in columns if x in bool_columns]
    json_to_convert = [x for x in columns if x in json_columns]

    if numeric_to_convert:
        df[numeric_to_convert] = df[numeric_to_convert].apply(pd.to_numeric, errors="coerce")
    if int_datetime_to_convert:
        df[int_datetime_to_convert] = df[int_datetime_to_convert].apply(
            pd.to_datetime, utc=True, unit=int_datetime_unit, errors="coerce"
        )
    if ms_int_datetime_to_convert:
        df[ms_int_datetime_to_convert] = df[ms_int_datetime_to_convert].apply(
            pd.to_datetime, utc=True, unit="ms", errors="coerce"
        )
    if us_int_datetime_to_convert:
        df[us_int_datetime_to_convert] = df[us_int_datetime_to_convert].apply(
            pd.to_datetime, utc=True, unit="us", errors="coerce"
        )
    for col in str_datetime_to_convert:
        df[col] = pd.to_datetime(df[col], utc=True, errors="coerce")

    _bool_map = {
        "true": True,
        "True": True,
        "1": True,
        True: True,
        "false": False,
        "False": False,
        "0": False,
        "": False,
        False: False,
    }
    for col in bool_to_convert:
        df[col] = df[col].map(_bool_map).astype("boolean")
    for column in json_to_convert:
        df[column] = df[column].apply(lambda x: orjson.loads(x) if pd.notnull(x) else x)
    return df


def preprocess_dict(
    data: dict,
    *,
    numeric_columns: list,
    str_datetime_columns: list,
    int_datetime_columns: list,
    ms_int_datetime_columns: list,
    bool_columns: list,
    drop_columns: list,
    json_columns: list,
    us_int_datetime_columns: list | None = None,
) -> dict:
    """Apply the same coercion as preprocess_dataframe to a single dict."""
    if us_int_datetime_columns is None:
        us_int_datetime_columns = []
    data = {snake_to_camel(k): v for k, v in data.items()}
    for key in drop_columns:
        data.pop(key, None)

    for key, val in list(data.items()):
        if not isinstance(val, str):
            continue
        if key in json_columns:
            try:
                data[key] = orjson.loads(val)
            except Exception:
                pass
        elif key in (
            *numeric_columns,
            *int_datetime_columns,
            *ms_int_datetime_columns,
            *us_int_datetime_columns,
        ):
            try:
                data[key] = float(val)
            except (ValueError, TypeError):
                pass
        elif key in str_datetime_columns:
            try:
                data[key] = pd.Timestamp(val, tz="UTC")
            except Exception:
                pass
        elif key in bool_columns:
            data[key] = val.lower() not in ("false", "0", "")

    for key in int_datetime_columns:
        val = data.get(key)
        if isinstance(val, (int, float)):
            try:
                data[key] = pd.Timestamp(val, unit="s", tz="UTC")
            except Exception:
                pass
    for key in ms_int_datetime_columns:
        val = data.get(key)
        if isinstance(val, (int, float)):
            try:
                data[key] = pd.Timestamp(val, unit="ms", tz="UTC")
            except Exception:
                pass
    for key in us_int_datetime_columns:
        val = data.get(key)
        if isinstance(val, (int, float)):
            try:
                data[key] = pd.Timestamp(val, unit="us", tz="UTC")
            except Exception:
                pass
    return data


# ── Nested expansion ─────────────────────────────────────────────────


_DEFAULT_EXPAND_PREFIXES: tuple = ()


def expand_column_lists(base: tuple, prefixes: tuple = _DEFAULT_EXPAND_PREFIXES) -> list:
    """Return base columns plus prefixed camelCase variants for nested expand fields."""
    result = [snake_to_camel(x) for x in base]
    for prefix in prefixes:
        result += [snake_to_camel(f"{prefix}_{x}") for x in base]
    return result


# ── Decorator: declarative offset auto-pagination (unused but available) ─────


def autopage(param_limit: str = "limit", param_offset: str = "offset"):
    """Decorator that adds an `_all` autopaging wrapper using offset pagination."""
    import inspect

    def _decorator(func):
        sig = inspect.signature(func)
        default_limit = (
            sig.parameters[param_limit].default if param_limit in sig.parameters else 100
        )
        default_offset = (
            sig.parameters[param_offset].default if param_offset in sig.parameters else 0
        )

        @wraps(func)
        def _all(self, *args, **kwargs) -> pd.DataFrame:
            limit = kwargs.get(param_limit, default_limit)
            offset = kwargs.get(param_offset, default_offset)
            max_pages = kwargs.pop("max_pages", None)
            sleep_s = kwargs.pop("sleep_s", 0.0)
            pages = []
            done = 0
            while True:
                kwargs[param_limit] = limit
                kwargs[param_offset] = offset
                df = func(self, *args, **kwargs)
                if not isinstance(df, pd.DataFrame) or df.empty:
                    break
                pages.append(df)
                if len(df) < limit:
                    break
                done += 1
                if max_pages and done >= max_pages:
                    break
                offset += limit
                if sleep_s:
                    time.sleep(sleep_s)
            return pd.concat(pages, ignore_index=True) if pages else pd.DataFrame()

        return _all

    return _decorator
