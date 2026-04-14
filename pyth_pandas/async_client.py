"""Async wrapper for PythPandas.

Wraps the synchronous client via composition, running each method in a
``ThreadPoolExecutor`` for non-blocking behavior in asyncio contexts.
All public methods from ``PythPandas`` are auto-generated as async
wrappers — new mixin methods become available without changes here.

Usage:
    >>> async with AsyncPythPandas() as client:
    ...     df = await client.fetch_latest_prices(symbols=["Crypto.BTC/USD"], properties=["price"])
"""

from __future__ import annotations

import asyncio
import functools
from concurrent.futures import ThreadPoolExecutor
from typing import Self

from pyth_pandas.client import PythPandas

# Methods that are sync-only, properties, or internal — do not wrap.
_SKIP = frozenset(
    {
        "close",
        "preprocess_dataframe",
        "preprocess_dict",
    }
)


def _make_async_wrapper(method_name: str):
    async def wrapper(self, *args, **kwargs):
        loop = asyncio.get_running_loop()
        fn = getattr(self._sync, method_name)
        return await loop.run_in_executor(self._executor, functools.partial(fn, *args, **kwargs))

    wrapper.__name__ = method_name
    wrapper.__qualname__ = f"AsyncPythPandas.{method_name}"
    sync_method = getattr(PythPandas, method_name, None)
    if sync_method is not None:
        annotations = getattr(sync_method, "__annotations__", {})
        if "return" in annotations:
            wrapper.__annotations__ = {"return": annotations["return"]}
    return wrapper


class AsyncPythPandas:
    """Async version of :class:`~pyth_pandas.PythPandas`.

    Accepts the same constructor arguments. Internally creates a synchronous
    ``PythPandas`` instance and runs its methods in a thread pool.
    """

    def __init__(self, *, max_workers: int = 10, **kwargs):
        self._sync = PythPandas(**kwargs)
        self._executor = ThreadPoolExecutor(max_workers=max_workers)

    @property
    def base_url(self) -> str:
        return self._sync.base_url

    @property
    def api_key(self) -> str | None:
        return self._sync.api_key

    async def close(self) -> None:
        self._sync.close()
        self._executor.shutdown(wait=False)

    async def __aenter__(self) -> Self:
        return self

    async def __aexit__(self, *_: object) -> None:
        await self.close()

    def __repr__(self) -> str:
        return f"Async{self._sync!r}"


def _populate_async_methods() -> None:
    for name in dir(PythPandas):
        if name.startswith("_") or name in _SKIP:
            continue
        attr = getattr(PythPandas, name, None)
        # Use callable() not inspect.isfunction so cachetools.cachedmethod descriptors are caught
        if not callable(attr):
            continue
        if hasattr(AsyncPythPandas, name):
            continue
        wrapper = _make_async_wrapper(name)
        wrapper.__doc__ = getattr(attr, "__doc__", None)
        setattr(AsyncPythPandas, name, wrapper)


_populate_async_methods()
