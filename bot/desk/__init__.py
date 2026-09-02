"""Metals Desk — the Two Engines Handbook, bolted onto the signalling bot.

Import is side-effect free and cheap. Nothing here starts a thread, touches
the network, or writes to the volume until `Desk(...)` is constructed, which
`main.py` only does when `ENABLE_DESK=1`.
"""
from .config import ConfigError, settings          # noqa: F401
from .service import Desk, HELP                    # noqa: F401

__all__ = ["Desk", "HELP", "settings", "ConfigError"]
