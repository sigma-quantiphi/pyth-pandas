"""FastMCP server exposing pyth-pandas as MCP tools.

Run with: ``pyth-pandas-mcp`` (after ``uv pip install -e ".[mcp]"``).
"""

from __future__ import annotations

import inspect
from typing import Any

import pandas as pd
from fastmcp import FastMCP
from tabulate import tabulate  # type: ignore[import-untyped]

from pyth_pandas import PythPandas

mcp = FastMCP("pyth-pandas")
_client: PythPandas | None = None


def _get_client() -> PythPandas:
    global _client
    if _client is None:
        _client = PythPandas()
    return _client


def _format_result(result: Any) -> str:
    if isinstance(result, pd.DataFrame):
        if result.empty:
            return "(empty DataFrame)"
        return tabulate(result.head(50), headers="keys", tablefmt="pipe", showindex=False)
    if isinstance(result, dict):
        return tabulate(result.items(), headers=["key", "value"], tablefmt="pipe")
    return str(result)


def _register_tools() -> None:
    """Register every public method on PythPandas as an MCP tool."""
    client = _get_client()
    for name in dir(PythPandas):
        if name.startswith("_"):
            continue
        attr = getattr(PythPandas, name, None)
        if not callable(attr):
            continue

        sig = inspect.signature(attr)
        doc = inspect.getdoc(attr) or name

        def _make_tool(method_name: str, sig=sig, doc=doc):
            def _tool(**kwargs) -> str:
                fn = getattr(client, method_name)
                return _format_result(fn(**kwargs))

            _tool.__name__ = method_name
            _tool.__doc__ = doc
            _tool.__signature__ = sig.replace(  # type: ignore[attr-defined]
                parameters=[p for p in sig.parameters.values() if p.name != "self"]
            )
            return _tool

        mcp.tool(name=name, description=doc)(_make_tool(name))


def main() -> None:
    _register_tools()
    mcp.run()


if __name__ == "__main__":
    main()
