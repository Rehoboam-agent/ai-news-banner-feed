#!/usr/bin/env python3
"""Extract recent AI-newsletter candidates from the configured IMAP mailbox.

This script intentionally does not decide what is banner-worthy. It prints
structured JSON for the daily Rehoboam job, which then skims and edits feed.xml.

Configuration is read from /home/hermes/.hermes/.env:
  EMAIL_ADDRESS
  EMAIL_PASSWORD
  EMAIL_IMAP_HOST
"""
from __future__ import annotations

import email
import imaplib
import json
import os
import re
import sys
from datetime import datetime, timedelta, timezone
from email.header import decode_header, make_header
from email.message import Message
from pathlib import Path

from bs4 import BeautifulSoup

ENV_FILE = Path("/home/hermes/.hermes/.env")
SEEN_FILE = Path("data/seen_ids.json")

KEYWORDS = [
    "ai", "artificial intelligence", "openai", "anthropic", "claude",
    "deepmind", "gemini", "mistral", "meta ai", "xai", "grok",
    "nvidia", "perplexity", "llm", "model", "agent", "agents",
    "diffusion", "safety", "alignment", "regulation", "compute",
]

NEWSLETTER_HINTS = [
    "tldr ai", "tldr", "beehiiv", "substack", "newsletter", "the batch",
    "import ai", "ben's bites", "rundown", "superhuman", "neuron",
]


def load_env() -> None:
    if not ENV_FILE.exists():
        return
    for line in ENV_FILE.read_text(errors="ignore").splitlines():
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        os.environ.setdefault(key, value.strip().strip('"').strip("'"))


def decode_header_value(value: str | None) -> str:
    try:
        return str(make_header(decode_header(value or "")))
    except Exception:
        return value or ""


def message_text(msg: Message) -> str:
    chunks: list[str] = []
    parts = msg.walk() if msg.is_multipart() else [msg]
    for part in parts:
        content_type = part.get_content_type()
        disposition = (part.get("Content-Disposition") or "").lower()
        if "attachment" in disposition:
            continue
        if content_type not in {"text/plain", "text/html"}:
            continue
        payload = part.get_payload(decode=True)
        if not isinstance(payload, bytes):
            payload = b""
        charset = part.get_content_charset() or "utf-8"
        text = payload.decode(charset, errors="replace")
        if content_type == "text/html":
            text = BeautifulSoup(text, "html.parser").get_text("\n")
        chunks.append(text)
    text = "\n".join(chunks)
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text


def relevant_lines(text: str, limit: int = 80) -> list[str]:
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    selected: list[str] = []
    for line in lines:
        lower = line.lower()
        if any(keyword in lower for keyword in KEYWORDS):
            selected.append(line[:700])
        if len(selected) >= limit:
            break
    return selected


def load_seen() -> set[str]:
    if not SEEN_FILE.exists():
        return set()
    try:
        data = json.loads(SEEN_FILE.read_text())
        return set(data.get("message_ids", []))
    except Exception:
        return set()


def save_seen(ids: set[str]) -> None:
    SEEN_FILE.parent.mkdir(parents=True, exist_ok=True)
    SEEN_FILE.write_text(json.dumps({"message_ids": sorted(ids)}, indent=2) + "\n")


def main() -> int:
    days = int(os.environ.get("AI_NEWS_LOOKBACK_DAYS", sys.argv[1] if len(sys.argv) > 1 else "2"))
    mark_seen = os.environ.get("AI_NEWS_MARK_SEEN", "0") == "1"
    include_seen = os.environ.get("AI_NEWS_INCLUDE_SEEN", "0") == "1"

    load_env()
    address = os.environ.get("EMAIL_ADDRESS")
    password = os.environ.get("EMAIL_PASSWORD")
    host = os.environ.get("EMAIL_IMAP_HOST", "imap.gmail.com")
    if not address or not password:
        raise SystemExit("EMAIL_ADDRESS/EMAIL_PASSWORD not configured")

    seen = load_seen()
    since = (datetime.now(timezone.utc) - timedelta(days=days)).strftime("%d-%b-%Y")

    mail = imaplib.IMAP4_SSL(host)
    mail.login(address, password)
    mail.select("INBOX")
    typ, data = mail.search(None, f"(SINCE {since})")
    if typ != "OK":
        raise SystemExit(f"IMAP search failed: {typ}")

    results = []
    scanned_ids: set[str] = set()
    for raw_id in data[0].split()[-120:]:
        msg_id = raw_id.decode()
        if msg_id in seen and not include_seen:
            continue
        typ, fetched = mail.fetch(raw_id, "(BODY.PEEK[])")
        if typ != "OK":
            continue
        raw = next((part[1] for part in fetched if isinstance(part, tuple)), b"")
        if not raw:
            continue
        msg = email.message_from_bytes(raw)
        subject = decode_header_value(msg.get("Subject"))
        sender = decode_header_value(msg.get("From"))
        date = decode_header_value(msg.get("Date"))
        haystack = f"{subject} {sender}".lower()
        text = message_text(msg)
        text_lower = text[:8000].lower()
        if not (any(hint in haystack for hint in NEWSLETTER_HINTS) and any(keyword in text_lower or keyword in haystack for keyword in KEYWORDS)):
            continue
        scanned_ids.add(msg_id)
        results.append({
            "message_id": msg_id,
            "date": date,
            "from": sender,
            "subject": subject,
            "candidate_lines": relevant_lines(text),
        })

    mail.logout()
    if mark_seen:
        save_seen(seen | scanned_ids)

    print(json.dumps({
        "lookback_days": days,
        "count": len(results),
        "messages": results,
    }, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
