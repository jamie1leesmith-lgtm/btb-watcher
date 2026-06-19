# BTB Ticket Watcher

Watches the [Between The Bridges](https://www.eventbrite.co.uk/o/70305365543)
Eventbrite page and sends a Telegram alert the moment a new
`World Cup 2026: ... England ...` event is listed.

## How it works

- A GitHub Actions cron job runs `watcher.py` every 10 minutes.
- The script fetches the organiser page, extracts all World Cup 2026 event
  IDs from the HTML, and compares against `seen_events.json`.
- Any new event whose slug contains `england` triggers a Telegram message.
- The updated `seen_events.json` is committed back to the repo so we never
  alert on the same event twice.

## Local test

```bash
pip install -r requirements.txt
export TELEGRAM_BOT_TOKEN=...
export TELEGRAM_CHAT_ID=...
python watcher.py
```

## Secrets

Set in the GitHub repo (Settings → Secrets and variables → Actions):

- `TELEGRAM_BOT_TOKEN`
- `TELEGRAM_CHAT_ID`
