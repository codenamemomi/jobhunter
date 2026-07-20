"""Extract how a candidate can apply (email vs external URL) from job text."""

from __future__ import annotations

import re
from dataclasses import dataclass
from html import unescape
from typing import Any
from urllib.parse import unquote, urlparse

EMAIL_RE = re.compile(
    r"(?:mailto:)?([a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,})",
    re.I,
)

# Phrases that suggest the address is for applications
APPLY_CONTEXT_RE = re.compile(
    r"(?:apply|application|resume|cv|cover\s*letter|send\s+(?:your|us|a)|email\s+(?:your|us)|"
    r"careers?@|jobs?@|recruit(?:ing|er)?|hiring|talent@)",
    re.I,
)

JUNK_EMAIL_PARTS = (
    "example.com",
    "sentry.io",
    "wixpress.com",
    "schema.org",
    "domain.com",
    "email.com",
    "yourdomain",
    "company.com",
    "github.com",
    "gitlab.com",
    "googleapis.com",
    "cloudflare",
    "w3.org",
    "png",
    "jpg",
    "jpeg",
    "gif",
    "svg",
    "noreply",
    "no-reply",
    "donotreply",
    "mailer-daemon",
)

APPLY_URL_HINTS = (
    "greenhouse.io",
    "lever.co",
    "workable.com",
    "ashbyhq.com",
    "myworkdayjobs.com",
    "smartrecruiters.com",
    "jobvite.com",
    "bamboohr.com",
    "recruitee.com",
    "applytojob.com",
    "boards.eu.greenhouse.io",
)


@dataclass
class ApplyInfo:
    apply_method: str  # email | url | unknown
    apply_email: str | None = None
    apply_url: str | None = None


def extract_apply_info(
    description: str | None,
    listing_url: str | None = None,
    raw: dict[str, Any] | None = None,
) -> ApplyInfo:
    """
    Detect email-apply vs external URL apply from description / raw scraper payload.
    Prefer real application emails; fall back to listing or ATS URL.
    """
    chunks: list[str] = []
    if description:
        chunks.append(description)
    if raw:
        for key in (
            "description",
            "how_to_apply",
            "apply_url",
            "url",
            "application_url",
            "instructions",
        ):
            val = raw.get(key)
            if isinstance(val, str):
                chunks.append(val)
            elif isinstance(val, dict):
                chunks.append(str(val))

    blob = "\n".join(chunks)
    plain = _strip_html(blob)

    email = _best_email(plain, blob)
    apply_url = _best_apply_url(plain, listing_url, raw)

    if email:
        return ApplyInfo(apply_method="email", apply_email=email, apply_url=apply_url or listing_url)
    if apply_url or listing_url:
        return ApplyInfo(
            apply_method="url",
            apply_email=None,
            apply_url=apply_url or listing_url,
        )
    return ApplyInfo(apply_method="unknown", apply_email=None, apply_url=None)


def _strip_html(text: str) -> str:
    text = unescape(text or "")
    text = re.sub(r"(?is)<script.*?>.*?</script>", " ", text)
    text = re.sub(r"(?is)<style.*?>.*?</style>", " ", text)
    text = re.sub(r"(?i)<br\s*/?>", "\n", text)
    text = re.sub(r"(?i)</p>", "\n", text)
    text = re.sub(r"<[^>]+>", " ", text)
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def _is_junk_email(email: str) -> bool:
    lower = email.lower()
    if any(j in lower for j in JUNK_EMAIL_PARTS):
        return True
    local, _, domain = lower.partition("@")
    if not domain or "." not in domain:
        return True
    if local in {"email", "name", "user", "username", "test"}:
        return True
    # image / asset fake emails
    if re.search(r"\.(png|jpe?g|gif|svg|webp)$", domain):
        return True
    return False


def _best_email(plain: str, original: str) -> str | None:
    candidates: list[tuple[int, str]] = []
    for match in EMAIL_RE.finditer(original + "\n" + plain):
        email = unquote(match.group(1)).strip().rstrip(".,;)>\"'")
        if _is_junk_email(email):
            continue
        # score by nearby apply context
        start = max(0, match.start() - 80)
        end = min(len(original) + len(plain), match.end() + 80)
        window = (original + plain)[start:end]
        score = 10
        if APPLY_CONTEXT_RE.search(window):
            score += 50
        if email.lower().startswith(("jobs@", "careers@", "apply@", "hr@", "recruiting@", "talent@")):
            score += 40
        if email.lower().startswith(("hello@", "info@", "contact@")):
            score += 5
        candidates.append((score, email.lower()))

    if not candidates:
        return None
    candidates.sort(key=lambda x: (-x[0], x[1]))
    return candidates[0][1]


def _best_apply_url(
    plain: str,
    listing_url: str | None,
    raw: dict[str, Any] | None,
) -> str | None:
    if raw:
        for key in ("apply_url", "application_url", "url"):
            val = raw.get(key)
            if isinstance(val, str) and val.startswith("http"):
                return val

    urls = re.findall(r"https?://[^\s<>\"']+", plain)
    for url in urls:
        cleaned = url.rstrip(").,;\"'")
        host = urlparse(cleaned).netloc.lower()
        if any(h in host for h in APPLY_URL_HINTS):
            return cleaned
        if any(tok in cleaned.lower() for tok in ("/apply", "application", "jobs/")):
            return cleaned

    return listing_url
