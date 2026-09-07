"""OPTIONAL tiny relay to run INSIDE Iran when Railway's IP is blocked.

    pip install fastapi uvicorn requests pyyaml
    RELAY_TOKEN=secret python bot/desk/relay.py      # listens on :8080

Then on Railway set IRAN_RELAY_URL=https://your-relay.example and
IRAN_RELAY_TOKEN=secret. Only the sources listed under `relay.applies_to`
in config/sources.yaml are routed through it.

Two endpoints, because the sources come in two shapes:

  /proxy?name=brsapi_gold   single-URL sources, resolved from sources.yaml
  /get?url=<encoded>        multi-URL sources (TSETMC needs search, price
                            and NAV), restricted to hosts that appear in
                            sources.yaml so this cannot be used as an open
                            proxy by anyone who learns the address.

This file is never imported by the bot — it has its own dependencies and
runs on your own machine, not on Railway.
"""
from __future__ import annotations
import os
import sys
from pathlib import Path
from urllib.parse import urlparse

sys.path.insert(0, str(Path(__file__).resolve().parent))

import requests
from fastapi import FastAPI, Header, HTTPException

from config import load_yaml

app = FastAPI()
TOKEN = os.getenv("RELAY_TOKEN", "")
CFG = load_yaml("sources.yaml")["sources"]

UA = {"User-Agent": "Mozilla/5.0"}


def _allowed_hosts() -> set[str]:
    hosts: set[str] = set()
    for spec in CFG.values():
        if not isinstance(spec, dict):
            continue
        for k, v in spec.items():
            if isinstance(v, str) and k.endswith("url") and v.startswith("http"):
                h = urlparse(v.replace("{symbol}", "x").replace("{code}", "1")).hostname
                if h:
                    hosts.add(h.lower())
    return hosts


ALLOWED = _allowed_hosts()


def _auth(token: str) -> None:
    if TOKEN and token != TOKEN:
        raise HTTPException(401, "bad token")


@app.get("/health")
def health():
    return {"ok": True, "sources": list(CFG), "hosts": sorted(ALLOWED)}


@app.get("/proxy")
def proxy(name: str, x_relay_token: str = Header(default="")):
    _auth(x_relay_token)
    spec = CFG.get(name)
    if not spec or "url" not in spec:
        raise HTTPException(404, "unknown source")
    r = requests.get(spec["url"], params=spec.get("params") or None,
                     headers=UA, timeout=spec.get("timeout", 20))
    return r.json()


@app.get("/get")
def get(url: str, x_relay_token: str = Header(default="")):
    _auth(x_relay_token)
    host = (urlparse(url).hostname or "").lower()
    if host not in ALLOWED:
        raise HTTPException(403, f"host not in sources.yaml: {host}")
    r = requests.get(url, headers={**UA, "Referer": f"https://{host}/"}, timeout=25)
    return r.json()


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=int(os.getenv("PORT", "8080")))
