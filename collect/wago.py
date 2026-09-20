"""Fetch Forever (wow_classic_titan) game data tables from wago.tools.

The build number is the change proxy: if it has not moved, no item in the game
has changed and there is nothing to download.
"""

import json
import sys
import urllib.request
from pathlib import Path

PRODUCT = "wow_classic_titan"
TABLES = ["ItemSparse", "Item"]
RAW = Path(__file__).resolve().parent.parent / "data" / "raw"
STATE = RAW / "wago_state.json"


USER_AGENT = "wow-forever-loot (https://github.com/; personal loot browser)"


def _get(url: str) -> bytes:
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(req, timeout=180) as r:
        return r.read()


def latest_build() -> dict:
    builds = json.loads(_get("https://wago.tools/api/builds"))[PRODUCT]
    return builds[0] if isinstance(builds, list) else builds


def fetch(force: bool = False) -> dict:
    build = latest_build()
    version = build["version"]
    state = json.loads(STATE.read_text()) if STATE.exists() else {}

    out = RAW / "wago" / version
    have = state.get("version") == version and all(
        (out / f"{t}.csv").exists() for t in TABLES
    )
    if have and not force:
        print(f"build {version} unchanged, nothing to fetch")
        return state

    out.mkdir(parents=True, exist_ok=True)
    for table in TABLES:
        path = out / f"{table}.csv"
        if path.exists() and not force:
            continue
        data = _get(f"https://wago.tools/db2/{table}/csv?build={version}")
        path.write_bytes(data)
        print(f"{table}: {len(data) // 1024} KiB -> {path}")

    state = {"version": version, "created_at": build["created_at"]}
    STATE.write_text(json.dumps(state, indent=2) + "\n")
    print(f"build {version} ({build['created_at']})")
    return state


if __name__ == "__main__":
    fetch(force="--force" in sys.argv)
