"""Generic JSON fetcher driven entirely by config/sources.yaml.

Same contract as the upstream desk's `sources/http_source.py`, rewritten on
top of `requests` (already the signalling bot's only dependency) instead of
`httpx`, and synchronous instead of async.
"""
from __future__ import annotations
import logging
import re
from typing import Any
from urllib.parse import quote

import requests

from .config import settings

log = logging.getLogger("desk.http")
_IDX = re.compile(r"^(.*?)\[(\d+)\]$")

UA = {"User-Agent": "Mozilla/5.0 (compatible; metals-desk/1.0)",
      "Accept": "application/json, text/plain, */*"}

_FA_DIGITS = str.maketrans("۰۱۲۳۴۵۶۷۸۹٠١٢٣٤٥٦٧٨٩", "01234567890123456789")


def dig(obj: Any, path: str) -> Any:
    """dot/bracket path lookup: 'metals.gold', 'gold[0].price'."""
    cur = obj
    for part in path.split("."):
        if cur is None:
            return None
        m = _IDX.match(part)
        if m:
            key, idx = m.group(1), int(m.group(2))
            if key:
                cur = cur.get(key) if isinstance(cur, dict) else None
            if not isinstance(cur, (list, tuple)) or idx >= len(cur):
                return None
            cur = cur[idx]
        else:
            cur = cur.get(part) if isinstance(cur, dict) else None
    return cur


def num(v) -> float | None:
    if v is None:
        return None
    if isinstance(v, bool):
        return None
    if isinstance(v, (int, float)):
        return float(v)
    s = str(v).replace(",", "").replace("٬", "").strip()
    s = s.translate(_FA_DIGITS)
    try:
        return float(s)
    except ValueError:
        return None


def _url_for(name: str, spec: dict, relay_targets: list[str]) -> str:
    if settings.relay_url and name in relay_targets:
        return f"{settings.relay_url}/proxy?name={name}"
    return spec["url"]


def relay_wrap(url: str) -> tuple[str, dict]:
    """Route one arbitrary URL through the in-Iran relay, if one is set.

    `/proxy?name=` only works for sources with a single URL in sources.yaml.
    TSETMC needs three (search, price, NAV), so it uses the relay's generic
    `/get` passthrough instead. Returns the URL to call and extra headers.
    """
    if not settings.relay_url:
        return url, {}
    h = {"X-Relay-Token": settings.relay_token} if settings.relay_token else {}
    return f"{settings.relay_url}/get?url={quote(url, safe='')}", h


def get_json(url: str, *, params=None, timeout: int | None = None,
             headers: dict | None = None) -> tuple[Any, str]:
    """One GET. Returns (parsed_json, raw_text_truncated_for_/probe)."""
    h = dict(UA)
    h.update(headers or {})
    r = requests.get(url, params=params or None, headers=h,
                     timeout=timeout or settings.timeout)
    r.raise_for_status()
    return r.json(), r.text[:4000]


def extract(data: Any, spec: dict) -> dict[str, float]:
    """Apply the `fields:` mapping of a source spec to a parsed response."""
    out: dict[str, float] = {}
    locate_by = spec.get("locate_by")
    for field_name, fs in (spec.get("fields") or {}).items():
        val = None
        if locate_by and "container" in fs:
            items = dig(data, fs["container"]) or []
            want = str(fs.get("match", "")).strip().lower()
            for it in items:
                if not isinstance(it, dict):
                    continue
                if str(it.get(locate_by, "")).strip().lower() == want:
                    val = dig(it, fs.get("path", "price"))
                    break
        else:
            val = dig(data, fs["path"])
        n = num(val)
        if n is not None:
            out[field_name] = n * float(fs.get("scale", 1))
    return out


def fetch_http_source(name: str, spec: dict,
                      relay_targets: list[str]) -> tuple[dict, str]:
    """Returns (values, raw_text_for_probe). Raises on transport failure."""
    url = _url_for(name, spec, relay_targets)
    headers = {}
    if settings.relay_token and settings.relay_url and name in relay_targets:
        headers["X-Relay-Token"] = settings.relay_token
    data, raw = get_json(url, params=spec.get("params"),
                         timeout=spec.get("timeout"), headers=headers)
    return extract(data, spec), raw
