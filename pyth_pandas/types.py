"""TypedDict models for dict-returning endpoints.

These are structural subtypes of ``dict`` — existing code using
``result["key"]`` or ``result.get("key")`` continues to work unchanged.
"""

from __future__ import annotations

from typing import NotRequired, TypedDict

import pandas as pd  # noqa: F401  — used in attached docstrings

# ── Building blocks ───────────────────────────────────────────────────


class JsonBinaryData(TypedDict):
    """A signed/binary payload returned alongside a parsed price update."""

    encoding: str  # "base64" | "hex"
    data: str


class ParsedFeedPayload(TypedDict, total=False):
    """One feed entry inside ``ParsedPayload.priceFeeds``."""

    priceFeedId: int
    price: NotRequired[str | None]
    bestBidPrice: NotRequired[str | None]
    bestAskPrice: NotRequired[str | None]
    confidence: NotRequired[int | None]
    exponent: NotRequired[int | None]
    publisherCount: NotRequired[int | None]
    fundingRate: NotRequired[int | None]
    fundingRateInterval: NotRequired[int | None]
    marketSession: NotRequired[str | None]
    emaPrice: NotRequired[str | None]
    emaConfidence: NotRequired[int | None]
    feedUpdateTimestamp: NotRequired[int | None]
    fundingTimestamp: NotRequired[int | None]


class ParsedPayload(TypedDict):
    """Top-level parsed price update across multiple feeds."""

    timestampUs: str
    priceFeeds: list[ParsedFeedPayload]


class JsonUpdate(TypedDict, total=False):
    """Full price update returned by ``/latest_price``, ``/price``, ``/reduce_price``."""

    parsed: NotRequired[ParsedPayload | None]
    evm: NotRequired[JsonBinaryData | None]
    solana: NotRequired[JsonBinaryData | None]
    leEcdsa: NotRequired[JsonBinaryData | None]
    leUnsigned: NotRequired[JsonBinaryData | None]


class SignedGuardianSetUpgrade(TypedDict):
    """Wormhole guardian set upgrade VAA body + this router's ECDSA signature."""

    current_guardian_set_index: int
    new_guardian_set_index: int
    new_guardian_keys: list[list[int]]
    body: str
    signature: str


class SignedMerkleRoot(TypedDict):
    """Signed merkle root frame from the ``/merkle/root/stream`` WebSocket."""

    root: str
    slot: int
    timestamp: int
    channel: str
    signature: str
    messages: list[str]
