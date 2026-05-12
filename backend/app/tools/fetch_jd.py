"""fetch_job_description: pull JD text from any job posting URL.

SSRF defense via scheme + resolved-IP guard, not domain allowlist.
Manual redirect loop revalidates each hop so a public URL cannot bounce
into the internal network. readability-lxml extracts main content.
"""
from __future__ import annotations

import asyncio
import ipaddress
import re
import socket
from urllib.parse import urlparse

import httpx
from readability import Document

from app.tools.registry import Tool, registry

REQUEST_TIMEOUT = 15.0
MAX_BYTES = 2 * 1024 * 1024
MAX_REDIRECTS = 5
ALLOWED_SCHEMES = {"http", "https"}
BLOCKED_HOSTS = {"localhost", "ip6-localhost", "ip6-loopback"}

# Hosts that render the JD client-side via JS/XHR. Static fetch returns
# only page chrome and template placeholders like {0}. Surface a clear
# error so the user pastes the JD text manually.
JS_RENDERED_HOSTS = (
    "taleo.net",
    "myworkdayjobs.com",
    "icims.com",
    "successfactors.com",
    "successfactors.eu",
    "smartrecruiters.com",
)
JS_RENDER_MSG = (
    "This site renders the job description with JavaScript, which the "
    "static fetcher cannot read. Please copy the description text from "
    "the page and paste it into the Job Description field."
)


def _ip_is_safe(ip: str) -> bool:
    try:
        addr = ipaddress.ip_address(ip)
    except ValueError:
        return False
    return not (
        addr.is_private
        or addr.is_loopback
        or addr.is_link_local
        or addr.is_reserved
        or addr.is_multicast
        or addr.is_unspecified
    )


async def _resolve_safe(host: str) -> tuple[bool, str]:
    if host.lower() in BLOCKED_HOSTS:
        return False, f"Blocked host: {host}"
    try:
        ipaddress.ip_address(host)
        if not _ip_is_safe(host):
            return False, f"Blocked IP literal: {host}"
        return True, host
    except ValueError:
        pass
    loop = asyncio.get_running_loop()
    try:
        infos = await loop.getaddrinfo(host, None)
    except socket.gaierror as e:
        return False, f"DNS error: {e}"
    for info in infos:
        ip = info[4][0]
        if not _ip_is_safe(ip):
            return False, f"Resolved to non-public IP: {host} -> {ip}"
    return True, host


async def _validate_url(url: str) -> tuple[bool, str]:
    p = urlparse(url)
    if p.scheme.lower() not in ALLOWED_SCHEMES:
        return False, f"Blocked scheme: {p.scheme}"
    host = (p.hostname or "").lower()
    if not host:
        return False, "Missing host"
    return await _resolve_safe(host)


def _is_js_rendered_host(url: str) -> bool:
    host = (urlparse(url).hostname or "").lower()
    return any(host == h or host.endswith("." + h) for h in JS_RENDERED_HOSTS)


async def _run(args: dict) -> dict:
    url = args["url"]
    if _is_js_rendered_host(url):
        return {"error": JS_RENDER_MSG, "ok": False, "js_rendered": True}
    ok, msg = await _validate_url(url)
    if not ok:
        return {"error": msg, "ok": False}
    try:
        async with httpx.AsyncClient(
            timeout=REQUEST_TIMEOUT,
            follow_redirects=False,
            headers={"User-Agent": "JobAssistant/0.1"},
        ) as client:
            current = url
            for _ in range(MAX_REDIRECTS + 1):
                r = await client.get(current)
                if r.is_redirect:
                    nxt = r.headers.get("location")
                    if not nxt:
                        return {"error": "Redirect without Location", "ok": False}
                    current = str(httpx.URL(current).join(nxt))
                    ok, msg = await _validate_url(current)
                    if not ok:
                        return {"error": f"Redirect blocked: {msg}", "ok": False}
                    continue
                r.raise_for_status()
                html = r.text[:MAX_BYTES]
                break
            else:
                return {"error": "Too many redirects", "ok": False}
    except (httpx.HTTPError, ValueError) as e:
        return {"error": str(e), "ok": False}

    doc = Document(html)
    summary_html = doc.summary(html_partial=True)
    text = _html_to_text(summary_html)
    # Some career portals (Taleo, custom ATS) defeat readability and yield
    # only label skeletons. Fall back to a stripped-body extraction that
    # drops scripts/styles/nav/footer and keeps the rest.
    if len(text) < 400 or _looks_like_label_skeleton(text):
        fallback = _body_text(html)
        if len(fallback) > len(text):
            text = fallback
    if _looks_js_rendered(text):
        return {"error": JS_RENDER_MSG, "ok": False, "js_rendered": True}
    return {"ok": True, "title": doc.short_title(), "text": text}


def _looks_js_rendered(text: str) -> bool:
    # Template placeholders ({0}, {1}) and label-only skeleton are
    # strong signals the real content is injected client-side.
    if re.search(r"\{\d+\}", text):
        return True
    if len(text) < 200 and _looks_like_label_skeleton(text):
        return True
    return False


def _html_to_text(html: str) -> str:
    text = re.sub(r"<[^>]+>", " ", html)
    return re.sub(r"\s+", " ", text).strip()


def _looks_like_label_skeleton(text: str) -> bool:
    # Heuristic: many ":" with very few words between them = label-only.
    colons = text.count(":")
    words = len(text.split())
    return colons >= 4 and words < 60


def _body_text(html: str) -> str:
    stripped = re.sub(
        r"<(script|style|noscript|nav|footer|header)[^>]*>.*?</\1>",
        " ",
        html,
        flags=re.DOTALL | re.IGNORECASE,
    )
    return _html_to_text(stripped)


fetch_jd_tool = registry.register(
    Tool(
        name="fetch_job_description",
        description="Fetch and clean the main text of a job description from any public job posting URL.",
        parameters={
            "type": "object",
            "properties": {
                "url": {"type": "string", "description": "Job posting URL"},
            },
            "required": ["url"],
        },
        run=_run,
    )
)
