"""Async WebSocket client for the Pyth Pro Router ``/v1/stream`` endpoint."""

from __future__ import annotations

import asyncio
import json
import os
from dataclasses import dataclass, field
from typing import Any, Self

import websockets


@dataclass
class AsyncPythWebSocket:
    """Async WebSocket factory."""

    ws_url: str = "wss://pyth-lazer.dourolabs.app/v1/stream"
    api_key: str | None = None
    ping_interval: int = 20
    reconnect_max_backoff: float = 30.0

    def __post_init__(self) -> None:
        if self.api_key is None:
            self.api_key = os.getenv("PYTH_API_KEY")

    @classmethod
    def from_client(cls, client) -> Self:
        sync = getattr(client, "_sync", client)
        return cls(api_key=sync.api_key)

    def open(self) -> AsyncPythWebSocketSession:
        return AsyncPythWebSocketSession(
            ws_url=self.ws_url,
            api_key=self.api_key,
            ping_interval=self.ping_interval,
            reconnect_max_backoff=self.reconnect_max_backoff,
        )


@dataclass
class AsyncPythWebSocketSession:
    ws_url: str
    api_key: str | None
    ping_interval: int
    reconnect_max_backoff: float
    _ws: Any = field(default=None, init=False, repr=False)
    _ping_task: asyncio.Task | None = field(default=None, init=False, repr=False)

    async def __aenter__(self) -> Self:
        await self._connect()
        return self

    async def __aexit__(self, *_: object) -> None:
        await self.close()

    async def _connect(self) -> None:
        backoff = 1.0
        headers = {}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
        while True:
            try:
                self._ws = await websockets.connect(self.ws_url, additional_headers=headers)
                self._ping_task = asyncio.create_task(self._ping_loop())
                return
            except Exception:
                await asyncio.sleep(backoff)
                backoff = min(backoff * 2, self.reconnect_max_backoff)

    async def _ping_loop(self) -> None:
        while self._ws is not None:
            try:
                pong = await self._ws.ping()
                await pong
            except Exception:
                return
            await asyncio.sleep(self.ping_interval)

    async def close(self) -> None:
        if self._ping_task:
            self._ping_task.cancel()
        if self._ws is not None:
            await self._ws.close()

    async def subscribe(
        self,
        *,
        subscription_id: int,
        properties: list[str],
        formats: list[str],
        channel: str = "real_time",
        price_feed_ids: list[int] | None = None,
        symbols: list[str] | None = None,
        parsed: bool = True,
        delivery_format: str = "json",
        json_binary_encoding: str = "hex",
        ignore_invalid_feeds: bool = False,
    ) -> None:
        if (price_feed_ids is None) == (symbols is None):
            raise ValueError("Specify exactly one of price_feed_ids or symbols.")
        body = {
            "type": "subscribe",
            "subscriptionId": subscription_id,
            "properties": properties,
            "formats": formats,
            "channel": channel,
            "parsed": parsed,
            "deliveryFormat": delivery_format,
            "jsonBinaryEncoding": json_binary_encoding,
            "ignoreInvalidFeeds": ignore_invalid_feeds,
            "priceFeedIds": price_feed_ids,
            "symbols": symbols,
        }
        body = {k: v for k, v in body.items() if v is not None}
        if self._ws is None:
            raise RuntimeError("Session not connected.")
        await self._ws.send(json.dumps(body))

    async def unsubscribe(self, *, subscription_id: int) -> None:
        if self._ws is None:
            raise RuntimeError("Session not connected.")
        await self._ws.send(json.dumps({"type": "unsubscribe", "subscriptionId": subscription_id}))

    def __aiter__(self) -> AsyncPythWebSocketSession:
        return self

    async def __anext__(self) -> dict:
        while True:
            if self._ws is None:
                await self._connect()
            try:
                raw = await self._ws.recv()
            except websockets.ConnectionClosed:
                await self._connect()
                continue
            return json.loads(raw)
