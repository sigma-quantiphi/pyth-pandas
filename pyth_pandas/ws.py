"""Sync WebSocket client for the Pyth Pro Router ``/v1/stream`` endpoint.

Built on the ``websocket-client`` library. Sessions are message-pulling:
call :meth:`PythWebSocketSession.recv` (or iterate the session) to drain
incoming frames as parsed JSON dicts.

Pyth Pro requires bearer-token authentication via the
``Authorization: Bearer <token>`` header on the upgrade request.
"""

from __future__ import annotations

import json
import os
import threading
import time
from collections.abc import Iterator
from dataclasses import dataclass, field
from queue import Empty, Queue
from typing import Self

import pandas as pd
from websocket import WebSocketApp

from pyth_pandas.utils import preprocess_dataframe as _preprocess_dataframe


@dataclass
class PythWebSocket:
    """Sync WebSocket factory. Use ``from_client(client)`` to share column config."""

    ws_url: str = "wss://pyth-lazer.dourolabs.app/v1/stream"
    api_key: str | None = None
    ping_interval: int = 20
    numeric_columns: tuple = ()
    str_datetime_columns: tuple = ()
    int_datetime_columns: tuple = ()
    ms_int_datetime_columns: tuple = ()
    us_int_datetime_columns: tuple = ()
    bool_columns: tuple = ()
    drop_columns: tuple = ()
    json_columns: tuple = ()

    def __post_init__(self) -> None:
        if self.api_key is None:
            self.api_key = os.getenv("PYTH_API_KEY")

    @classmethod
    def from_client(cls, client) -> Self:
        """Build a WS client that shares column-coercion config with an HTTP client."""
        sync = getattr(client, "_sync", client)
        return cls(
            api_key=sync.api_key,
            numeric_columns=tuple(sync._numeric_columns),
            str_datetime_columns=tuple(sync._str_datetime_columns),
            int_datetime_columns=tuple(sync._int_datetime_columns),
            ms_int_datetime_columns=tuple(sync._ms_int_datetime_columns),
            us_int_datetime_columns=tuple(sync._us_int_datetime_columns),
            bool_columns=tuple(sync._bool_columns),
            drop_columns=tuple(sync._drop_columns),
            json_columns=tuple(sync._json_columns),
        )

    def _preprocess(self, df: pd.DataFrame) -> pd.DataFrame:
        return _preprocess_dataframe(
            df,
            numeric_columns=list(self.numeric_columns),
            str_datetime_columns=list(self.str_datetime_columns),
            int_datetime_columns=list(self.int_datetime_columns),
            ms_int_datetime_columns=list(self.ms_int_datetime_columns),
            us_int_datetime_columns=list(self.us_int_datetime_columns),
            bool_columns=list(self.bool_columns),
            drop_columns=list(self.drop_columns),
            json_columns=list(self.json_columns),
        )

    def open(self) -> PythWebSocketSession:
        """Open a session that you can subscribe to one or more feeds on."""
        return PythWebSocketSession(
            ws_url=self.ws_url,
            api_key=self.api_key,
            ping_interval=self.ping_interval,
            preprocessor=self._preprocess,
        )


@dataclass
class PythWebSocketSession:
    """A sync WebSocket session.

    Use as a context manager. Call :meth:`subscribe` to start a feed
    subscription (server responds with ``subscribed`` / ``streamUpdated``
    frames), and iterate the session (or call :meth:`recv`) to drain
    parsed JSON messages.
    """

    ws_url: str
    api_key: str | None
    ping_interval: int
    preprocessor: object  # callable(pd.DataFrame) -> pd.DataFrame
    _app: WebSocketApp | None = field(default=None, init=False, repr=False)
    _queue: Queue = field(default_factory=Queue, init=False, repr=False)
    _connected: threading.Event = field(default_factory=threading.Event, init=False, repr=False)

    def __enter__(self) -> Self:
        headers = []
        if self.api_key:
            headers.append(f"Authorization: Bearer {self.api_key}")
        self._app = WebSocketApp(
            self.ws_url,
            header=headers,
            on_open=self._on_open,
            on_message=self._on_message,
        )
        threading.Thread(target=self._app.run_forever, daemon=True).start()
        threading.Thread(target=self._ping_loop, daemon=True).start()
        self._connected.wait(timeout=10)
        return self

    def __exit__(self, *_: object) -> None:
        if self._app is not None:
            self._app.close()

    def _on_open(self, _ws):
        self._connected.set()

    def _on_message(self, _ws, message):
        try:
            self._queue.put(json.loads(message))
        except Exception:
            self._queue.put({"type": "error", "raw": message})

    def _ping_loop(self):
        while self._app and self._app.sock and self._app.sock.connected:
            try:
                self._app.sock.ping()
            except Exception:
                break
            time.sleep(self.ping_interval)

    def subscribe(
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
        """Send a SubscribeRequest with the given subscription_id."""
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
        if self._app is None:
            raise RuntimeError("Session not open. Use as a context manager first.")
        self._app.send(json.dumps(body))

    def unsubscribe(self, *, subscription_id: int) -> None:
        """Send an UnsubscribeRequest for the given subscription_id."""
        if self._app is None:
            raise RuntimeError("Session not open. Use as a context manager first.")
        self._app.send(json.dumps({"type": "unsubscribe", "subscriptionId": subscription_id}))

    def recv(self, timeout: float | None = None) -> dict:
        """Pull the next parsed message off the queue."""
        try:
            return self._queue.get(timeout=timeout)
        except Empty as exc:
            raise TimeoutError("No WS message within timeout") from exc

    def __iter__(self) -> Iterator[dict]:
        while True:
            yield self.recv()
