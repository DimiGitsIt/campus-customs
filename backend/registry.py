"""One place to look up agents by name, populated after all five agent
modules finish constructing their Agent objects. Delegation tools call
get_agent() lazily so there's no import cycle between agent modules."""

from __future__ import annotations

from typing import Any

_REGISTRY: dict[str, Any] = {}


def register_agent(name: str, agent: Any) -> None:
    _REGISTRY[name] = agent


def get_agent(name: str):
    if not _REGISTRY:
        _populate()
    return _REGISTRY.get(name)


def _populate() -> None:
    """Import every agent module once so each registers itself."""
    from backend.agents import boss, inventory, accounting, facilities, customer_service  # noqa: F401
