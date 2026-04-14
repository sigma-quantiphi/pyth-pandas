# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [0.1.0] — 2026-04-14

### Added
- Initial release. Sync (`PythPandas`) and async (`AsyncPythPandas`) clients
  for the Pyth Pro Router (Pyth Lazer) REST API.
- DataFrame variants for `/latest_price`, `/price`, `/reduce_price`, plus
  raw `JsonUpdate` variants suffixed `_raw`.
- `get_guardian_set_upgrade()` for the Wormhole governance endpoint.
- `pandera` schema (`ParsedFeedSchema`) covering all parsed feed columns.
- `TypedDict` definitions for `JsonUpdate`, `SignedGuardianSetUpgrade`,
  `SignedMerkleRoot`, and supporting types.
- Sync + async WebSocket clients for `/v1/stream` (`ws` extra).
- FastMCP server entry point (`mcp` extra).
- Streamlit explorer (`explorer` extra).
- Sphinx docs, Binder configuration, GitHub Actions for CI / docs / release.

[Unreleased]: https://github.com/OWNER/pyth-pandas/compare/v0.1.0...HEAD
[0.1.0]: https://github.com/OWNER/pyth-pandas/releases/tag/v0.1.0
