# Forever Loot

Filterable loot browser for World of Warcraft: Forever. Filter equipment by stat, armor type,
slot, source and level, which Wowhead's own item database cannot do: it has no Spirit or Spell
Power filter at all.

## How the data is collected

Wowhead's item listing pages carry everything in the page itself. Each listing embeds the rows
(name, quality, item level, source) and a store of per-item stats keyed by item id. One page
load per equipment slot is the whole dataset.

The listing caps at 1000 rows, so a slot that hits the cap is re-fetched split by quality.

Stats come from Wowhead rather than the client data files on wago.tools, because Blizzard
hotfixes items on the beta servers without shipping a build. The 17 Sep build is missing 331 of
846 wrist items and disagrees on stats for roughly a quarter of the rest.

## Running it

The collector drives your own Chrome over CDP, because Wowhead blocks plain HTTP requests.

```bash
# Chrome with a throwaway profile
flatpak run com.google.Chrome --remote-debugging-port=9222 --user-data-dir=/tmp/claude-chrome

python collect/wowhead.py zones     # zone id -> name, for naming drop locations
python collect/wowhead.py           # every slot; pass slot numbers to limit it
python build/build.py               # data/raw -> docs/data/items.json
```

`collect/wago.py` downloads the same items from the client data files. It is a cross-check, not
a data source.

## Layout

| Path                | What it is                          |
| ------------------- | ----------------------------------- |
| `collect/`          | fetches into `data/raw/` (gitignored) |
| `build/build.py`    | raw sweep -> `docs/data/items.json` |
| `docs/`             | the site, served by GitHub Pages    |

## Known gaps

- Vanilla random-suffix items ("of the Eagle") carry no stats on their base row.
- The new PvP sets have no source data on Wowhead yet.
- Crafted items name the item rather than the profession.
- 3,286 of the 4,394 drops carry no zone on their listing row, so they show as
  "drop (zone unknown)" rather than splitting into world, dungeon and raid. Filling
  those in needs a second sweep, one listing per zone.
