"""Sweep Wowhead's Forever item database, one page load per equipment slot.

Each listing page embeds two things we need: the listview rows (name, quality,
item level, source) and a gathered-data store keyed by item id holding the stats
shown in the hover tooltip. Together they are the whole dataset, so no per-item
requests are needed.

Wowhead caps a listing at 1000 rows, so a slot that hits the cap is re-fetched
split by quality.
"""

import json
import time
from datetime import datetime, timezone
from pathlib import Path

from playwright.sync_api import TimeoutError as PlaywrightTimeout
from playwright.sync_api import sync_playwright

BASE = "https://www.wowhead.com/forever/items"
CDP = "http://127.0.0.1:9222"
RAW = Path(__file__).resolve().parent.parent / "data" / "raw" / "wowhead"
PAGE_CAP = 1000
QUALITIES = [2, 3, 4, 5]  # uncommon and above
PAUSE = 4.0

EXTRACT = """() => ({
  rows: (window.g_listviews && window.g_listviews.items || {}).data || [],
  gathered: window.g_gathered_types ? (window.g_gathered_types[3] || {}) : {},
})"""

SLOTS = """() => {
  const s = [...document.querySelectorAll('select')].find(x => (x.name || x.id) === 'slot');
  return s ? [...s.options].filter(o => o.value).map(o => [Number(o.value), o.text.trim()]) : [];
}"""


def _load(page, url: str) -> dict:
    page.goto(url, wait_until="domcontentloaded", timeout=60000)
    try:
        page.wait_for_function(
            "() => window.g_listviews && window.g_listviews.items", timeout=20000
        )
    except PlaywrightTimeout:
        # a filter that matches nothing renders no listview at all
        return {"rows": [], "gathered": {}}
    page.wait_for_timeout(1500)
    return page.evaluate(EXTRACT)


def _write(name: str, url: str, payload: dict) -> int:
    n = len(payload["rows"])
    out = RAW / f"{name}.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(
        json.dumps(
            {
                "url": url,
                "fetched_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
                "rows": payload["rows"],
                "gathered": payload["gathered"],
            }
        )
    )
    print(f"  {name}: {n} rows -> {out.name}")
    return n


def sweep(slots: list[int] | None = None, resume: bool = False) -> None:
    with sync_playwright() as pw:
        page = pw.chromium.connect_over_cdp(CDP).contexts[0].pages[0]

        page.goto(BASE, wait_until="domcontentloaded", timeout=60000)
        page.wait_for_timeout(2500)
        catalogue = dict(page.evaluate(SLOTS))
        if not catalogue:
            raise SystemExit("could not read the slot list from the filter form")
        (RAW / "slots.json").parent.mkdir(parents=True, exist_ok=True)
        (RAW / "slots.json").write_text(json.dumps(catalogue, indent=2))

        targets = slots or sorted(catalogue)
        for slot in targets:
            if resume and list(RAW.glob(f"slot-{slot}.json")) + list(RAW.glob(f"slot-{slot}-q*.json")):
                print(f"slot {slot}: already collected, skipping")
                continue
            print(f"slot {slot} ({catalogue.get(slot, '?')})")
            url = f"{BASE}/slot:{slot}"
            payload = _load(page, url)
            if len(payload["rows"]) < PAGE_CAP:
                _write(f"slot-{slot}", url, payload)
                time.sleep(PAUSE)
                continue

            print(f"  hit the {PAGE_CAP} cap, splitting by quality")
            for quality in QUALITIES:
                time.sleep(PAUSE)
                url = f"{BASE}/quality:{quality}/slot:{slot}"
                payload = _load(page, url)
                n = _write(f"slot-{slot}-q{quality}", url, payload)
                if n >= PAGE_CAP:
                    print(f"  WARNING: quality {quality} also hit the cap")
            time.sleep(PAUSE)


def zones() -> None:
    """Zone id -> name and instance type, used to name drop locations."""
    with sync_playwright() as pw:
        page = pw.chromium.connect_over_cdp(CDP).contexts[0].pages[0]
        page.goto(
            "https://www.wowhead.com/forever/zones",
            wait_until="domcontentloaded",
            timeout=60000,
        )
        page.wait_for_function(
            "() => window.g_listviews && window.g_listviews.zones", timeout=30000
        )
        rows = page.evaluate("() => g_listviews.zones.data || []")
    RAW.mkdir(parents=True, exist_ok=True)
    (RAW / "zones.json").write_text(json.dumps(rows))
    print(f"zones: {len(rows)} -> zones.json")


if __name__ == "__main__":
    import sys

    args = sys.argv[1:]
    resume = "--resume" in args
    args = [a for a in args if a != "--resume"]
    if args[:1] == ["zones"]:
        zones()
    else:
        sweep([int(a) for a in args] or None, resume=resume)
