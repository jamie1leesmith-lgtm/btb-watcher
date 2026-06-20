#!/usr/bin/env python3
"""Watch Between The Bridges listings on Eventbrite and Dice for World Cup
matches featuring England, and send a Telegram alert when one appears.
"""
from __future__ import annotations

import json
import os
import re
import sys
from pathlib import Path

import httpx

STATE_FILE = Path(__file__).parent / "seen_events.json"
USER_AGENT = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0 Safari/537.36"
)

EVENTBRITE_URL = "https://www.eventbrite.co.uk/o/70305365543"
DICE_URL = "https://dice.fm/venue/between-the-bridges-vaol"

EVENTBRITE_RE = re.compile(
    r"https://www\.eventbrite\.co\.uk/e/"
    r"(?P<slug>[a-z0-9-]+?)"
    r"-tickets-(?P<id>\d+)"
)

DICE_RE = re.compile(
    r"https://dice\.fm/event/"
    r"(?P<id>[a-z0-9]{6,})"
    r"-(?P<slug>[a-z0-9-]+?)-tickets"
)


def fetch(url: str) -> str:
    r = httpx.get(
        url,
        headers={"User-Agent": USER_AGENT},
        timeout=30,
        follow_redirects=True,
    )
    r.raise_for_status()
    return r.text


def parse_eventbrite(html: str) -> list[dict]:
    events: dict[str, dict] = {}
    for m in EVENTBRITE_RE.finditer(html):
        eid = m.group("id")
        if eid in events:
            continue
        slug = m.group("slug")
        events[eid] = {
            "id": f"eb:{eid}",
            "slug": slug,
            "title": slug.replace("-", " ").title().replace(" Vs ", " vs "),
            "url": f"https://www.eventbrite.co.uk/e/{slug}-tickets-{eid}",
            "source": "Eventbrite",
        }
    return list(events.values())


def parse_dice(html: str) -> list[dict]:
    events: dict[str, dict] = {}
    for m in DICE_RE.finditer(html):
        eid = m.group("id")
        if eid in events:
            continue
        slug = m.group("slug")
        # Trim trailing venue + date for a tidier title
        name_part = slug.split("-between-the-bridges-")[0]
        name_part = re.sub(r"-\d+(?:st|nd|rd|th)-[a-z]+$", "", name_part)
        title = " ".join(
            w.upper() if w == "fifa" else w.capitalize()
            for w in name_part.split("-")
        )
        events[eid] = {
            "id": f"dice:{eid}",
            "slug": slug,
            "title": title,
            "url": f"https://dice.fm/event/{eid}-{slug}-tickets",
            "source": "Dice",
        }
    return list(events.values())


SOURCES = [
    (EVENTBRITE_URL, parse_eventbrite),
    (DICE_URL, parse_dice),
]


def is_england_match(event: dict) -> bool:
    slug = event["slug"].lower()
    return "england" in slug and ("world-cup" in slug or "fifa" in slug)


def load_seen() -> set[str]:
    if STATE_FILE.exists():
        return set(json.loads(STATE_FILE.read_text()))
    return set()


def save_seen(ids: set[str]) -> None:
    STATE_FILE.write_text(json.dumps(sorted(ids), indent=2) + "\n")


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

    all_events: list[dict] = []
    for url, parser in SOURCES:
        try:
            all_events.extend(parser(fetch(url)))
        except Exception as e:
            print(f"WARN: failed source {url}: {e}", file=sys.stderr)

    seen = load_seen()
    new_england = [
        e for e in all_events if is_england_match(e) and e["id"] not in seen
    ]

    for e in new_england:
        notify(
            token,
            chat_id,
            (
                f"🏴󠁧󠁢󠁥󠁮󠁧󠁿 <b>New England match at Between The Bridges</b> "
                f"({e['source']})\n\n"
                f"<b>{e['title']}</b>\n"
                f'<a href="{e["url"]}">Open on {e["source"]}</a>'
            ),
        )
        print(f"NOTIFIED: {e['title']} ({e['id']})", file=sys.stderr)

    all_ids = seen | {e["id"] for e in all_events}
    save_seen(all_ids)

    print(
        f"Checked {len(all_events)} events across {len(SOURCES)} sources; "
        f"{len(new_england)} new England match(es); "
        f"{len(all_ids)} total tracked."
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
