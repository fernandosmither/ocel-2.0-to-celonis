#!/usr/bin/env python3
"""
jsonocel_tui.py
Interactive terminal UI for inspecting & pruning JSON-OCEL files.

USAGE
  python jsonocel_tui.py mylog.json
"""

from __future__ import annotations
import json, sys, pathlib, typing as t
import questionary as q
from questionary import Choice

PathLike = t.Union[str, pathlib.Path]

# ───────────────────────── helpers ──────────────────────────
def load(path: PathLike) -> dict:
    with open(path, encoding="utf-8") as fh:
        return json.load(fh)

def save(data: dict, original: pathlib.Path) -> None:
    fname = q.text(
        f"Save as (ENTER for '{original.stem}.pruned{original.suffix}'):",
        default=f"{original.stem}.pruned{original.suffix}"
    ).ask()
    out = pathlib.Path(fname or f"{original.stem}.pruned{original.suffix}").expanduser()
    with open(out, "w", encoding="utf-8") as fh:
        json.dump(data, fh, indent=2)
    print(f"✔  wrote {out}")

def tally(items: list[dict]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for item in items:
        counts[item["type"]] = counts.get(item["type"], 0) + 1
    return counts

def slice_indices(seq_len: int) -> list[int]:
    modo = q.select(
        "Delete which slice?",
        choices=[
            Choice("all", "all"), Choice("first N", "first"),
            Choice("last N", "last"), Choice("range start:end", "range"),
            Choice("cancel", None)
        ],
    ).ask()
    if not modo or modo == "all":
        return list(range(seq_len))

    if modo == "first":
        n = int(q.text("How many from start?", default="1").ask())
        return list(range(min(n, seq_len)))

    if modo == "last":
        n = int(q.text("How many from end?", default="1").ask())
        return list(range(seq_len - min(n, seq_len), seq_len))

    if modo == "range":
        start = q.text("Start index (0-based, blank = 0):").ask()
        end   = q.text("End index (exclusive, blank = end):").ask()
        s = int(start) if start else 0
        e = int(end)   if end   else seq_len
        return list(range(max(0, s), min(e, seq_len)))
    return []

def filter_by_attr(records: list[dict], attr_name: str, attr_value: str) -> list[int]:
    idxs = []
    for i, rec in enumerate(records):
        attrs = {a["name"]: a.get("value") for a in rec.get("attributes", [])}
        if attrs.get(attr_name) == attr_value:
            idxs.append(i)
    return idxs

# ───────────────────────── actions ──────────────────────────
def show_stats(data: dict) -> None:
    print("\nEvent counts")
    for k, v in tally(data.get("events", [])).items():
        print(f"  {k:30} {v}")
    print("\nObject counts")
    for k, v in tally(data.get("objects", [])).items():
        print(f"  {k:30} {v}")
    input("\nPress ENTER to continue")

def delete_records(kind: str, data: dict) -> None:
    """Interactive deletion of Events / Objects."""
    key   = "events" if kind == "Events" else "objects"
    recs  = data[key]
    if not recs:
        print("No records present.")
        return

    # 1️⃣ choose the type
    types = sorted({r["type"] for r in recs})
    chosen_type = q.autocomplete(
        f"Select {kind.lower()} type to delete:", choices=types
    ).ask()
    if not chosen_type:
        return

    # 2️⃣ start with all rows of that type
    candidates = [i for i, r in enumerate(recs) if r["type"] == chosen_type]

    # 3️⃣ optional attribute filter (applied on the same rows)
    if q.confirm("Filter by attribute value?", default=False).ask():
        name  = q.text("Attribute name:").ask()
        value = q.text("Attribute value:").ask()
        def matches(i: int) -> bool:
            attrs = {a["name"]: a.get("value") for a in recs[i].get("attributes", [])}
            return attrs.get(name) == value
        candidates = [i for i in candidates if matches(i)]

    if not candidates:
        print("Nothing matches those filters.")
        return

    # 4️⃣ slice (first N, last N, range…)
    slice_idxs = slice_indices(len(candidates))
    targets = [candidates[i] for i in slice_idxs]

    if not targets:
        print("No rows selected.")
        return

    # 5️⃣ confirm & delete
    if q.confirm(f"Delete {len(targets)} {kind.lower()} now?", default=False).ask():
        for idx in sorted(targets, reverse=True):
            recs.pop(idx)
        print(f"🗑  Deleted {len(targets)} {kind.lower()}.")


# ─────────────────────────── main ───────────────────────────
def main() -> None:
    if len(sys.argv) < 2:
        sys.exit("usage: jsonocel_tui.py log.json")

    path = pathlib.Path(sys.argv[1]).expanduser()
    data = load(path)

    while True:
        choice = q.select(
            "JSON-OCEL tool – pick an action",
            choices=[
                "Show stats",
                "Delete Events",
                "Delete Objects",
                "Save & quit",
                "Quit without saving",
            ],
        ).ask()

        if choice == "Show stats":
            show_stats(data)
        elif choice in ("Delete Events", "Delete Objects"):
            delete_records(choice.split()[1], data)
        elif choice == "Save & quit":
            save(data, path)
            break
        else:
            break

if __name__ == "__main__":
    main()
