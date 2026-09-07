"""Desk settings + YAML config loading.

Differences from the upstream metals-desk `src/config.py`:

  * no `python-dotenv` — Railway injects variables into the environment
    directly, and the signalling bot already reads them with `os.getenv`.
  * `PyYAML` is imported lazily. If it is somehow missing the desk reports
    itself unavailable and the signalling bot carries on untouched, rather
    than the whole process dying on an ImportError at boot.
  * state lives on the same volume as the rest of the bot (`DATA_DIR`), so
    it survives a redeploy exactly like `prices.csv` does.
"""
from __future__ import annotations
import os
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent
CONFIG_DIR = ROOT / "config"
_ENV_RE = re.compile(r"\$\{([A-Z0-9_]+)\}")


class ConfigError(RuntimeError):
    pass


def _expand(obj):
    if isinstance(obj, str):
        return _ENV_RE.sub(lambda m: os.getenv(m.group(1), ""), obj)
    if isinstance(obj, dict):
        return {k: _expand(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_expand(v) for v in obj]
    return obj


def load_yaml(name: str) -> dict:
    """Read `config/<name>`, expanding ${ENV_VAR} placeholders."""
    try:
        import yaml
    except ImportError as e:                              # pragma: no cover
        raise ConfigError(
            "PyYAML is not installed — add `PyYAML` to requirements.txt") from e
    with open(CONFIG_DIR / name, encoding="utf-8") as f:
        return _expand(yaml.safe_load(f))


def _flag(name: str, default: str = "0") -> bool:
    return os.getenv(name, default).strip().lower() in ("1", "true", "yes", "on")


class Settings:
    """Reads env once, at import. Everything has a working default."""

    def __init__(self) -> None:
        # The desk is OFF unless explicitly switched on, so adding this file
        # to the repo cannot change what a running deployment does.
        self.enabled = _flag("ENABLE_DESK", "0")
        self.poll_seconds = max(60, int(os.getenv("DESK_POLL_SECONDS", "900")))
        self.alerts = _flag("DESK_ALERTS", "1")
        self.quiet = os.getenv("DESK_QUIET_HOURS", "01:00-07:00")
        self.relay_url = os.getenv("IRAN_RELAY_URL", "").rstrip("/")
        self.relay_token = os.getenv("IRAN_RELAY_TOKEN", "")
        self.timeout = int(os.getenv("DESK_HTTP_TIMEOUT", "20"))

    def quiet_window(self):
        if not self.quiet or "-" not in self.quiet:
            return None
        a, b = self.quiet.split("-", 1)
        try:
            return (tuple(int(x) for x in a.split(":")),
                    tuple(int(x) for x in b.split(":")))
        except ValueError:
            return None


settings = Settings()
