"""Duplicate job detection helpers."""

import hashlib
import re


def normalize_text(value: str | None) -> str:
    if not value:
        return ""
    text = value.lower().strip()
    text = re.sub(r"\s+", " ", text)
    return text


def job_content_hash(
    title: str | None,
    company: str | None,
    location: str | None,
    source: str | None = None,
) -> str:
    """Stable hash used to spot near-duplicates across sources."""
    blob = "|".join(
        [
            normalize_text(title),
            normalize_text(company),
            normalize_text(location),
            normalize_text(source),
        ]
    )
    return hashlib.sha256(blob.encode("utf-8")).hexdigest()


def soft_job_key(title: str | None, company: str | None) -> str:
    """Looser key for cross-source matching (ignores source/location)."""
    return hashlib.sha256(
        f"{normalize_text(title)}|{normalize_text(company)}".encode("utf-8")
    ).hexdigest()
