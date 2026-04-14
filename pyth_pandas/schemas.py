"""Pandera DataFrameModel schemas for pyth-pandas DataFrame-returning endpoints.

Convention:
    Every public method that returns a ``pd.DataFrame`` MUST have a
    corresponding ``DataFrameModel`` schema defined here and annotated as
    ``DataFrame[SomeSchema]`` in its return type. Integration tests
    validate live API responses against these schemas.

All schemas use ``strict=False`` (extra columns allowed) and ``coerce=True``
to avoid breaking when the upstream API adds new fields.

Column names reflect the post-preprocessing camelCase convention.
"""

from __future__ import annotations

import pandas as pd  # noqa: F401  — required for `pd.Timestamp` annotations
import pandera.pandas as pa


class _Lenient(pa.DataFrameModel):
    """Base config: allow extra columns, coerce types."""

    class Config:
        strict = False
        coerce = True


class ParsedFeedSchema(_Lenient):
    """Schema for one row of a parsed Pyth Pro feed update.

    Source:
        ``POST /v1/latest_price``, ``POST /v1/price``, ``POST /v1/reduce_price``
        — specifically the ``parsed.priceFeeds[]`` array of each response.

    Columns are post-preprocessing camelCase names. All numeric fields are
    raw mantissas — multiply by ``10 ** exponent`` to get the human value.
    """

    priceFeedId: int = pa.Field(nullable=False, ge=0)
    price: float | None = pa.Field(nullable=True)
    bestBidPrice: float | None = pa.Field(nullable=True)
    bestAskPrice: float | None = pa.Field(nullable=True)
    confidence: float | None = pa.Field(nullable=True)
    exponent: float | None = pa.Field(nullable=True)
    publisherCount: float | None = pa.Field(nullable=True)
    fundingRate: float | None = pa.Field(nullable=True)
    fundingRateInterval: float | None = pa.Field(nullable=True)
    marketSession: str | None = pa.Field(nullable=True)
    emaPrice: float | None = pa.Field(nullable=True)
    emaConfidence: float | None = pa.Field(nullable=True)
    feedUpdateTimestamp: pd.Timestamp | None = pa.Field(nullable=True)
    fundingTimestamp: pd.Timestamp | None = pa.Field(nullable=True)
