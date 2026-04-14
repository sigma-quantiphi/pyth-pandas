"""Price-fetching endpoints (``/latest_price``, ``/price``, ``/reduce_price``)."""

from __future__ import annotations

from typing import cast

import pandas as pd
from pandera.typing import DataFrame

from pyth_pandas.schemas import ParsedFeedSchema
from pyth_pandas.types import JsonUpdate
from pyth_pandas.utils import to_unix_timestamp_us

# Type aliases for documentation
_Channel = str  # "real_time" | "fixed_rate@50ms" | "fixed_rate@200ms" | "fixed_rate@1000ms"
_Format = str  # "evm" | "solana" | "leEcdsa" | "leUnsigned"
_Property = str  # "price" | "confidence" | "exponent" | ... (see PriceFeedProperty)


class PricesMixin:
    """Price fetch endpoints that return one row per requested feed.

    Each ``fetch_*`` method returns a ``DataFrame`` of parsed feeds. The
    accompanying on-chain payloads (EVM, Solana, …) and the update
    timestamp are attached as ``df.attrs``. For the raw ``JsonUpdate``
    response, use the matching ``*_raw`` variant.
    """

    def _build_price_body(
        self,
        *,
        properties: list[_Property],
        formats: list[_Format],
        channel: _Channel,
        price_feed_ids: list[int] | None,
        symbols: list[str] | None,
        parsed: bool,
        json_binary_encoding: str | None,
        timestamp: int | None = None,
    ) -> dict:
        if (price_feed_ids is None) == (symbols is None):
            raise ValueError("Specify exactly one of price_feed_ids or symbols.")
        body: dict = {
            "properties": list(properties),
            "formats": list(formats),
            "channel": channel,
            "parsed": parsed,
            "priceFeedIds": price_feed_ids,
            "symbols": symbols,
        }
        if json_binary_encoding is not None:
            body["jsonBinaryEncoding"] = json_binary_encoding
        if timestamp is not None:
            body["timestamp"] = timestamp
        return body

    def _update_to_dataframe(self, payload: JsonUpdate) -> DataFrame[ParsedFeedSchema]:
        parsed = payload.get("parsed") if isinstance(payload, dict) else None
        feeds = parsed.get("priceFeeds", []) if parsed else []
        df = pd.DataFrame(feeds)
        df = self.preprocess_dataframe(df)  # type: ignore[attr-defined]
        df.attrs["timestampUs"] = parsed.get("timestampUs") if parsed else None
        for fmt in ("evm", "solana", "leEcdsa", "leUnsigned"):
            if isinstance(payload, dict) and payload.get(fmt) is not None:
                df.attrs[fmt] = payload[fmt]
        return cast(DataFrame[ParsedFeedSchema], df)

    # ── /latest_price ───────────────────────────────────────────────────

    def fetch_latest_prices_raw(
        self,
        *,
        properties: list[_Property],
        formats: list[_Format],
        channel: _Channel = "real_time",
        price_feed_ids: list[int] | None = None,
        symbols: list[str] | None = None,
        parsed: bool = True,
        json_binary_encoding: str | None = "hex",
    ) -> JsonUpdate:
        """Fetch the latest available update for the requested feeds.

        Args:
            properties: Feed properties to include
                (``price``, ``confidence``, ``exponent``, ...).
            formats: On-chain payload formats to include
                (``evm``, ``solana``, ``leEcdsa``, ``leUnsigned``).
            channel: Update channel — ``real_time`` or ``fixed_rate@*``.
            price_feed_ids: Numeric feed IDs. Mutually exclusive with ``symbols``.
            symbols: Feed symbols (e.g. ``["Crypto.BTC/USD"]``).
            parsed: Include the ``parsed`` block in the response.
            json_binary_encoding: ``"hex"`` or ``"base64"`` for binary payloads.

        Returns:
            The raw ``JsonUpdate`` dict.

        Raises:
            PythAPIError: For any non-2xx response from the upstream API.
        """
        body = self._build_price_body(
            properties=properties,
            formats=formats,
            channel=channel,
            price_feed_ids=price_feed_ids,
            symbols=symbols,
            parsed=parsed,
            json_binary_encoding=json_binary_encoding,
        )
        data = self._request_authed(  # type: ignore[attr-defined]
            path="latest_price", method="POST", data=body
        )
        return cast(JsonUpdate, data)

    def fetch_latest_prices(
        self,
        *,
        properties: list[_Property],
        formats: list[_Format] | None = None,
        channel: _Channel = "real_time",
        price_feed_ids: list[int] | None = None,
        symbols: list[str] | None = None,
        json_binary_encoding: str | None = "hex",
    ) -> DataFrame[ParsedFeedSchema]:
        """Fetch the latest update and return it as a parsed-feed DataFrame.

        Same arguments as :meth:`fetch_latest_prices_raw`. The returned
        DataFrame has one row per feed; the on-chain payloads and
        ``timestampUs`` are attached on ``df.attrs``.

        Args:
            properties: Feed properties to include.
            formats: On-chain payload formats. Defaults to ``[]`` (parsed only).
            channel: Update channel.
            price_feed_ids: Numeric feed IDs (mutually exclusive with ``symbols``).
            symbols: Feed symbols (e.g. ``["Crypto.BTC/USD"]``).
            json_binary_encoding: ``"hex"`` or ``"base64"``.

        Returns:
            DataFrame conforming to :class:`~pyth_pandas.schemas.ParsedFeedSchema`.
        """
        payload = self.fetch_latest_prices_raw(
            properties=properties,
            formats=formats or [],
            channel=channel,
            price_feed_ids=price_feed_ids,
            symbols=symbols,
            parsed=True,
            json_binary_encoding=json_binary_encoding,
        )
        return self._update_to_dataframe(payload)

    # ── /price (timestamped) ────────────────────────────────────────────

    def fetch_prices_raw(
        self,
        *,
        timestamp: int | float | str | pd.Timestamp,
        properties: list[_Property],
        formats: list[_Format],
        channel: _Channel = "real_time",
        price_feed_ids: list[int] | None = None,
        symbols: list[str] | None = None,
        parsed: bool = True,
        json_binary_encoding: str | None = "hex",
    ) -> JsonUpdate:
        """Fetch updates issued at a specific point in time.

        Args:
            timestamp: Microsecond-resolution Unix timestamp. Accepts an
                int (interpreted as µs if >= 10**14, else seconds), a
                ``pd.Timestamp``, or an ISO-8601 string.
            properties: Feed properties to include.
            formats: On-chain payload formats.
            channel: Update channel.
            price_feed_ids: Numeric feed IDs.
            symbols: Feed symbols.
            parsed: Include parsed block.
            json_binary_encoding: Binary payload encoding.

        Returns:
            The raw ``JsonUpdate`` dict.
        """
        ts_us = to_unix_timestamp_us(timestamp)
        body = self._build_price_body(
            properties=properties,
            formats=formats,
            channel=channel,
            price_feed_ids=price_feed_ids,
            symbols=symbols,
            parsed=parsed,
            json_binary_encoding=json_binary_encoding,
            timestamp=ts_us,
        )
        data = self._request_authed(path="price", method="POST", data=body)  # type: ignore[attr-defined]
        return cast(JsonUpdate, data)

    def fetch_prices(
        self,
        *,
        timestamp: int | float | str | pd.Timestamp,
        properties: list[_Property],
        formats: list[_Format] | None = None,
        channel: _Channel = "real_time",
        price_feed_ids: list[int] | None = None,
        symbols: list[str] | None = None,
        json_binary_encoding: str | None = "hex",
    ) -> DataFrame[ParsedFeedSchema]:
        """DataFrame variant of :meth:`fetch_prices_raw`.

        Returns:
            DataFrame conforming to :class:`~pyth_pandas.schemas.ParsedFeedSchema`.
        """
        payload = self.fetch_prices_raw(
            timestamp=timestamp,
            properties=properties,
            formats=formats or [],
            channel=channel,
            price_feed_ids=price_feed_ids,
            symbols=symbols,
            parsed=True,
            json_binary_encoding=json_binary_encoding,
        )
        return self._update_to_dataframe(payload)

    # ── /reduce_price ───────────────────────────────────────────────────

    def reduce_price_raw(
        self,
        *,
        payload: JsonUpdate,
        price_feed_ids: list[int],
    ) -> JsonUpdate:
        """Reduce an existing on-chain payload to only the listed feeds.

        Args:
            payload: A ``JsonUpdate`` previously received from
                ``fetch_latest_prices_raw``, ``fetch_prices_raw``, or the
                WebSocket stream.
            price_feed_ids: Subset of feed IDs to retain.

        Returns:
            A new ``JsonUpdate`` containing only the requested feeds.
        """
        body = {"payload": payload, "priceFeedIds": list(price_feed_ids)}
        data = self._request_authed(  # type: ignore[attr-defined]
            path="reduce_price", method="POST", data=body
        )
        return cast(JsonUpdate, data)

    def reduce_price(
        self,
        *,
        payload: JsonUpdate,
        price_feed_ids: list[int],
    ) -> DataFrame[ParsedFeedSchema]:
        """DataFrame variant of :meth:`reduce_price_raw`."""
        out = self.reduce_price_raw(payload=payload, price_feed_ids=price_feed_ids)
        return self._update_to_dataframe(out)
