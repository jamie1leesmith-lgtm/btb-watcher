#!/usr/bin/env python3
"""Watch the Between The Bridges organiser page on Eventbrite for new
World Cup 2026 events featuring England, and send a Telegram alert when
one appears.
"""
from __future__ import annotations

import json
import os
import re
import sys
from pathlib import Path

import httpx

ORGANIZER_URL = "https://www.eventbrite.co.uk/o/70305365543"
STATE_FILE = Path(__file__).parent / "seen_events.json"
USER_AGENT = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0 Safari/537.36"
)

EVENT_RE = re.compile(
    r"https://www\.eventbrite\.co\.uk/e/"
    r"(?P<slug>world-cup-2026-[a-z0-9-]+?)"
    r"-tickets-(?P<id>\d+)"
)


def fetch_events() -> list[dict]:
    r = httpx.get(
        ORGANIZER_URL,
        headers={"User-Agent": USER_AGENT},
        timeout=30,
        follow_redirects=True,
    )
    r.raise_for_status()
    events: dict[str, dict] = {}
    for m in EVENT_RE.finditer(r.text):
        eid = m.group("id")
        if eid in events:
            continue
        slug = m.group("slug")
        events[eid] = {
            "id": eid,
            "slug": slug,
            "title": slug.replace("-", " ").title().replace(" Vs ", " vs "),
            "url": f"https://www.eventbrite.co.uk/e/{slug}-tickets-{eid}",
        }
    return list(events.values())


def load_seen() -> set[str]:
    if STATE_FILE.exists():
        return set(json.loads(STATE_FILE.read_text()))
    return set()


def save_seen(ids: set[str]) -> None:
    STATE_FILE.write_text(json.dumps(sorted(ids), indent=2) + "\n")


def is_england_match(event: dict) -> bool:
    return "england" in event["slug"].lower()


def notify(token: str, chat_id: str, text: str) -> None:
    r = httpx.post(
        f"https://api.telegram.org/bot{token}/sendMessage",
        data={
            "chat_id": chat_id,
            "text": text,
            "parse_mode": "HTML",
            "disable_web_page_preview": "false",
        },
        timeout=15,
    )
    r.raise_for_status()


def main() -> int:
    token = os.environ["TELEGRAM_BOT_TOKEN"]
    chat_id = os.environ["TELEGRAM_CHAT_ID"]

    events = fetch_events()
    seen = load_seen()

    new_england = [
        e for e in events if is_england_match(e) and e["id"] not in seen
    ]

    for e in new_england:
        notify(
            token,
            chat_id,
            (
                "🏴󠁧󠁢󠁥󠁮󠁧󠁿 <b>New England match listed at Between The Bridges</b>\n\n"
                f"<b>{e['title']}</b>\n"
                f'<a href="{e["url"]}">Open on Eventbrite</a>'
            ),
        )
        print(f"NOTIFIED: {e['title']} ({e['id']})", file=sys.stderr)

    all_ids = seen | {e["id"] for e in events}
    save_seen(all_ids)

    print(
        f"Checked {len(events)} world-cup events; "
        f"{len(new_england)} new England match(es); "
        f"{len(all_ids)} total tracked."
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
