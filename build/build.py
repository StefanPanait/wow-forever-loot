"""Turn the raw Wowhead sweep into the flat item list the site loads."""

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
RAW = ROOT / "data" / "raw" / "wowhead"
OUT = ROOT / "docs" / "data"

QUALITY = {0: "Poor", 1: "Common", 2: "Uncommon", 3: "Rare", 4: "Epic", 5: "Legendary"}

# item class -> subclass -> what you filter on
ARMOR = {1: "Cloth", 2: "Leather", 3: "Mail", 4: "Plate", 6: "Shield", 0: "Misc"}
WEAPON = {
    0: "Axe", 1: "Two-handed Axe", 2: "Bow", 3: "Gun", 4: "Mace",
    5: "Two-handed Mace", 6: "Polearm", 7: "Sword", 8: "Two-handed Sword",
    10: "Staff", 13: "Fist Weapon", 14: "Misc", 15: "Dagger", 16: "Thrown",
    18: "Crossbow", 19: "Wand", 20: "Fishing Pole",
}

STATS = {
    "str": "Strength", "agi": "Agility", "sta": "Stamina", "int": "Intellect",
    "spi": "Spirit", "splpwr": "Spell Power", "spldmg": "Spell Damage",
    "splheal": "Healing", "splpen": "Spell Penetration", "atkpwr": "Attack Power",
    "rgdatkpwr": "Ranged Attack Power", "manargn": "Mana per 5", "healthrgn": "Health per 5",
    "hitrtng": "Hit", "critstrkrtng": "Critical Strike", "hastertng": "Haste",
    "exprtng": "Expertise", "defrtng": "Defense", "def": "Defense Skill",
    "dodgertng": "Dodge", "parryrtng": "Parry", "blockrtng": "Block",
    "armorbonus": "Bonus Armor", "arcres": "Arcane Resistance", "firres": "Fire Resistance",
    "frores": "Frost Resistance", "holres": "Holy Resistance", "natres": "Nature Resistance",
    "shares": "Shadow Resistance",
}

SOURCE = {1: "Crafted", 2: "Drop", 4: "Quest", 5: "Vendor", 8: "PvP"}
SOURCE_DETAIL = {1: "drop", 2: "object", 3: "container", 5: "quest", 6: "crafted"}


def load_zones() -> dict[int, dict]:
    path = RAW / "zones.json"
    if not path.exists():
        return {}
    return {
        z["id"]: {"name": z["name"], "instance": z.get("instance", 0)}
        for z in json.loads(path.read_text())
    }


def item_type(row: dict) -> str | None:
    cls, sub = row.get("classs"), row.get("subclass")
    if cls == 4:
        return ARMOR.get(sub)
    if cls == 2:
        return WEAPON.get(sub)
    return None


def sources(row: dict, zones: dict) -> list[dict]:
    out = []
    codes = row.get("source") or []
    broad = next((SOURCE[c].lower() for c in codes if c in SOURCE), None)
    for more in row.get("sourcemore") or []:
        kind = SOURCE_DETAIL.get(more.get("t"), broad)
        zone = zones.get(more.get("z"))
        out.append(
            {
                "kind": kind,
                "name": more.get("n"),
                "id": more.get("ti"),
                "zone": zone["name"] if zone else None,
                "instance": bool(zone and zone["instance"]),
            }
        )
    if not out:
        # no detail, but the listing still tells us the broad category
        for code in row.get("source") or []:
            if code in SOURCE:
                out.append({"kind": SOURCE[code].lower(), "name": None, "id": None,
                            "zone": None, "instance": False})
    return out


def build() -> None:
    zones = load_zones()
    items: dict[int, dict] = {}

    for path in sorted(RAW.glob("slot-*.json")):
        raw = json.loads(path.read_text())
        gathered = raw["gathered"]
        for row in raw["rows"]:
            if row.get("quality", 0) < 2 or not row.get("slot"):
                continue
            equip = (gathered.get(str(row["id"])) or {}).get("jsonequip") or {}
            stats = {STATS[k]: v for k, v in equip.items() if k in STATS and v}
            items[row["id"]] = {
                "id": row["id"],
                "name": row["name"],
                "quality": row.get("quality"),
                "qualityName": QUALITY.get(row.get("quality"), "?"),
                "slot": row["slot"],
                "type": item_type(row),
                "ilvl": row.get("level"),
                "reqLevel": row.get("reqlevel") or equip.get("reqlevel") or 0,
                "armor": equip.get("armor"),
                "faction": row.get("side"),
                "stats": stats,
                "sourceCodes": row.get("source") or [],
                "sources": sources(row, zones),
            }

    OUT.mkdir(parents=True, exist_ok=True)
    payload = sorted(items.values(), key=lambda i: (i["slot"], -(i["ilvl"] or 0)))
    (OUT / "items.json").write_text(json.dumps(payload, separators=(",", ":")))
    print(f"{len(payload)} items -> {OUT / 'items.json'}")

    unnamed = sum(1 for i in payload if not i["type"])
    nostats = sum(1 for i in payload if not i["stats"])
    nosource = sum(1 for i in payload if not i["sources"])
    print(f"  no type: {unnamed}   no stats: {nostats}   no source: {nosource}")


if __name__ == "__main__":
    build()
