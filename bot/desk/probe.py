"""`/probeurl` — fetch an arbitrary URL from the Railway box and describe it.

The recurring question with Iranian data is not "what is the JSON shape", it
is "does this host answer a non-Iranian IP at all". Only the deployment can
answer that, and editing YAML, redeploying and reading logs is a slow way to
ask. This makes it one Telegram message.

It also does the tedious half: walks the response and prints the paths that
hold numbers, so you can paste one straight into `sources.yaml` instead of
reading four thousand characters of minified JSON on a phone.

Owner-gated in main.py, and guarded here as well — an arbitrary-URL fetcher
inside a service that can reach a private network is an SSRF hole if you let
it point anywhere.
"""
from __future__ import annotations
import ipaddress
import json
import re
import socket
from urllib.parse import urlparse

import requests

from .http_source import UA, num

MAX_PATHS = 40
# Most Iranian market sites are Next.js or Nuxt: the page is a shell and the
# numbers arrive either by XHR or baked into a JSON blob in the HTML. Digging
# that blob out means a page URL is often usable after all.
_EMBEDDED = (
    re.compile(r'<script[^>]+id="__NEXT_DATA__"[^>]*>(.*?)</script>', re.S),
    re.compile(r'<script[^>]+type="application/json"[^>]*>(.*?)</script>', re.S),
    re.compile(r'window\.__NUXT__\s*=\s*(\{.*?\});?\s*</script>', re.S),
)


def embedded_json(html: str):
    """Return (parsed, where) for the biggest JSON blob inside an HTML page."""
    best, where = None, ""
    for rx in _EMBEDDED:
        for m in rx.finditer(html):
            blob = m.group(1).strip()
            if len(blob) < 10:          # skip `{}` and other empty shells
                continue
            try:
                parsed = json.loads(blob)
            except ValueError:
                continue
            if best is None or len(blob) > best[0]:
                best, where = (len(blob), parsed), rx.pattern[:28]
    return (best[1], where) if best else (None, "")
MAX_BYTES = 400_000
TIMEOUT = 20


class ProbeRefused(ValueError):
    pass


def _check_public(url: str) -> str:
    """Only https, only a public address. Blocks the cloud metadata endpoint
    and anything else on Railway's internal network."""
    p = urlparse(url)
    if p.scheme != "https":
        raise ProbeRefused("https only")
    if not p.hostname:
        raise ProbeRefused("no host in that URL")
    try:
        infos = socket.getaddrinfo(p.hostname, p.port or 443, proto=socket.IPPROTO_TCP)
    except socket.gaierror as e:
        raise ProbeRefused(f"DNS did not resolve: {e}") from e
    for info in infos:
        ip = ipaddress.ip_address(info[4][0])
        if not ip.is_global:
            raise ProbeRefused(f"{p.hostname} resolves to non-public {ip}")
    return p.hostname


def numeric_paths(obj, prefix: str = "", out: list | None = None) -> list[tuple[str, float]]:
    """Every leaf that holds a number, as (dot/bracket path, value).

    The path is exactly what `sources.yaml` wants under `path:`.
    """
    out = [] if out is None else out
    if len(out) >= MAX_PATHS * 8:
        return out
    if isinstance(obj, dict):
        for k, v in obj.items():
            numeric_paths(v, f"{prefix}.{k}" if prefix else str(k), out)
    elif isinstance(obj, list):
        for i, v in enumerate(obj[:20]):
            numeric_paths(v, f"{prefix}[{i}]", out)
    else:
        n = num(obj)
        if n is not None and prefix:
            out.append((prefix, n))
    return out


def _fmt(v: float) -> str:
    """Prices are the point; `1.578e+06` is not a price you can read."""
    if v == int(v) and abs(v) < 1e15:
        return f"{int(v):,}"
    return f"{v:,.4f}".rstrip("0").rstrip(".")


def _label(name: str) -> str:
    """Nudge the eye toward the fields that matter for a fund."""
    low = name.lower()
    if "nav" in low:
        return " ← NAV?"
    if any(w in low for w in ("price", "last", "close", "pdrcot", "final")):
        return " ← price?"
    return ""


def probe_url(url: str, needle: str = "") -> str:
    """Fetch and describe. Returns Markdown ready for Telegram."""
    host = _check_public(url)
    r = requests.get(url, headers={**UA, "Referer": f"https://{host}/"},
                     timeout=TIMEOUT, allow_redirects=True, stream=True)
    # iter_content, not r.raw.read: r.raw is urllib3's and bypasses decoding.
    # Capped so a huge fund list cannot balloon the bot's memory.
    chunks, size = [], 0
    for chunk in r.iter_content(chunk_size=16384):
        chunks.append(chunk)
        size += len(chunk)
        if size >= MAX_BYTES:
            break
    r.close()
    body = b"".join(chunks)
    text = body.decode(r.encoding or "utf-8", errors="replace")
    ctype = (r.headers.get("Content-Type") or "?").split(";")[0]

    head = [f"`{r.status_code}` `{ctype}` · {len(body):,} bytes · `{host}`"]
    if r.status_code >= 400:
        head.append(f"\nHost answered, but with an error:\n```\n{text[:600]}\n```")
        return "\n".join(head)

    try:
        data = json.loads(text)
    except ValueError:
        data, where = embedded_json(text)
        if data is None:
            head.append("\n*Not JSON, and no JSON found inside the page.* The "
                        "numbers are fetched by the browser after load. Open the "
                        "site in a DESKTOP browser → DevTools → Network → "
                        "Fetch/XHR → reload, and probe the request that returns "
                        "them.")
            head.append(f"```\n{text[:400]}\n```")
            return "\n".join(head)
        head.append(f"_HTML page, but it embeds JSON (`{where}`) — reading that._")

    paths = numeric_paths(data)
    if needle:
        low = needle.lower()
        paths = [(p, v) for p, v in paths if low in p.lower()]
        # also surface the branch around a text match, e.g. a fund's name
        if not paths:
            head.append(f"\nNo numeric path matched `{needle}`. "
                        f"Try `/probeurl <url>` with no filter first.")
            return "\n".join(head)

    head.append(f"\n*{len(paths)} numeric field(s)*" +
                (f" matching `{needle}`" if needle else "") + ":")
    for p, v in paths[:MAX_PATHS]:
        key = p.split(".")[-1].split("[")[0]
        head.append(f"`{p}` = `{_fmt(v)}`{_label(key)}")
    if len(paths) > MAX_PATHS:
        head.append(f"_…{len(paths)-MAX_PATHS} more. Filter with "
                    f"`/probeurl <url> <text>`._")
    head.append("\nPaste a path into `sources.yaml` under `path:`. "
                "Add `scale: 0.1` if the site quotes rial.")
    return "\n".join(head)
