"""Governance endpoints (``/guardian_set_upgrade``)."""

from __future__ import annotations

from typing import cast

from pyth_pandas.types import SignedGuardianSetUpgrade


class GovernanceMixin:
    """Wormhole-related governance endpoints exposed by the Pyth Pro Router."""

    def get_guardian_set_upgrade(self) -> SignedGuardianSetUpgrade | None:
        """Get the signed Wormhole guardian set upgrade VAA body, if any.

        Active when both the current and next guardian sets are present
        in router state, indicating that a guardian set upgrade is in
        progress. Returns ``None`` when no upgrade is in progress.

        Returns:
            The signed upgrade dict, or ``None`` if not in progress.
        """
        data = self._request_authed(path="guardian_set_upgrade", method="GET")  # type: ignore[attr-defined]
        if not data:
            return None
        return cast(SignedGuardianSetUpgrade, data)
