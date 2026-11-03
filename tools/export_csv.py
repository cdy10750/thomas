#!/usr/bin/env python3
"""Validate a week's lesson JSON and export the native-speaker review CSV.

Usage: python3 tools/export_csv.py 1
Writes review/weekNN_review.csv (UTF-8 with BOM so Excel/Google Sheets open it cleanly).
Columns: 週, ID, セブアノ語, 英訳, 話者, 場面, 備考
"""
import csv
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def norm(s):
    return re.sub(r"[^\w'\- ]", "", s.lower()).split()


PROPER = {"Thomas", "Jiana", "Nay", "Tay", "Inday", "Bisaya", "English", "Bohol", "Ginoo", "America"}


def pretty(tiles, original):
    """Turn a tile sequence into a readable sentence for the reviewer."""
    out = ""
    for i, t in enumerate(tiles):
        first_word = t.split()[0].strip("?!.,")
        if i == 0 or out.endswith(("?", "!", ".")):
            t = t[0].upper() + t[1:]
        elif first_word not in PROPER:
            t = t[0].lower() + t[1:]
        if i == 0:
            out = t
        elif out.endswith(("?", "!", ".")):
            out += " " + t
        else:
            out += ", " + t
    end = original.rstrip()[-1]
    if end in "?!." and not out.endswith(end):
        out = out.rstrip("?!.") + end
    return out


def main(week):
    src = ROOT / "data" / f"week{week:02d}.json"
    d = json.loads(src.read_text(encoding="utf-8"))
    errors = []

    voice_of = {sp: v for v, sps in d["voices"].items() for sp in sps}
    other = {}  # chunks and dialogue lines from other weeks (cross-week references)
    for p in sorted((ROOT / "data").glob("week[0-9][0-9].json")):
        if p == src:
            continue
        od = json.loads(p.read_text(encoding="utf-8"))
        for c in od["chunks"]:
            other[c["id"]] = c
        for dl in od["dialogues"]:
            for ln in dl["lines"]:
                if "id" in ln:
                    other[ln["id"]] = ln
    items = {}  # id -> dict(ceb, en, speaker, scene)
    for c in d["chunks"]:
        items[c["id"]] = c
    for dlg in d["dialogues"]:
        prev_voice = None
        for ln in dlg["lines"]:
            if "chunk" in ln:
                c = items.get(ln["chunk"])
                if not c:
                    errors.append(f"{dlg['id']}: unknown chunk {ln['chunk']}")
                    continue
                sp = c["speaker"]
            else:
                ln.setdefault("scene", dlg["scene"])
                items[ln["id"]] = ln
                sp = ln["speaker"]
            if sp not in voice_of:
                errors.append(f"{dlg['id']}: speaker {sp} has no voice")
            speakers = {items[l["chunk"]]["speaker"] if "chunk" in l else l["speaker"] for l in dlg["lines"]}
            if len(speakers) != 2 or len({voice_of.get(s) for s in speakers}) != 2:
                errors.append(f"{dlg['id']}: dialogue must have exactly 2 speakers with different voices")
                break

    for day in d["days"]:
        for cid in day["new"]:
            if cid not in items:
                errors.append(f"Day {day['day']}: unknown new chunk {cid}")
        for i, ex in enumerate(day["exercises"]):
            tag = f"Day {day['day']} ex{i+1} ({ex['type']})"
            refs = [ex.get("ref"), ex.get("prompt")]
            if ex["type"] == "respond":
                refs += [ex["answer"], *ex["distractors"]]
            for r in filter(None, refs):
                if r not in items and r not in other:
                    errors.append(f"{tag}: unknown id {r}")
            if ex["type"] in ("scene", "fill") and ex["answer"] not in ex["options"]:
                errors.append(f"{tag}: answer not in options")
            if ex["type"] == "fill":
                full = ex["text"].replace("___", ex["answer"])
                if norm(full) != norm(items[ex["ref"]]["ceb"]):
                    errors.append(f"{tag}: filled text '{full}' != chunk '{items[ex['ref']]['ceb']}'")
            if ex["type"] == "order":
                target = norm(items[ex["ref"]]["ceb"])
                for a in ex["answers"]:
                    if any(norm(t) not in [norm(x) for x in ex["tiles"]] for t in a):
                        errors.append(f"{tag}: answer uses a tile not in tiles")
                if norm(" ".join(ex["answers"][0])) != target:
                    errors.append(f"{tag}: first answer does not match chunk text")

    if errors:
        print("VALIDATION ERRORS:")
        print("\n".join(errors))
        sys.exit(1)

    rows = []

    def note(tip, check):
        parts = []
        if tip:
            parts.append(f"Learner tip: {tip}")
        if check:
            parts.append(f"QUESTION FOR REVIEWER: {check}")
        return " | ".join(parts)

    for c in d["chunks"]:
        tip = c.get("tip", "")
        if c.get("lit"):
            tip = f"(lit. '{c['lit']}') {tip}"
        rows.append([week, c["id"], c["ceb"], c["en"], c["speaker"], c["scene"], note(tip, c.get("check"))])
    for dlg in d["dialogues"]:
        for ln in dlg["lines"]:
            if "chunk" in ln:
                continue
            rows.append([week, ln["id"], ln["ceb"], ln["en"], ln["speaker"], ln["scene"],
                         note(f"Dialogue: {dlg['title']}", ln.get("check"))])
    for day in d["days"]:
        for i, ex in enumerate(day["exercises"]):
            if ex["type"] != "order" or len(ex["answers"]) < 2:
                continue
            for j, a in enumerate(ex["answers"][1:], start=2):
                ref = items[ex["ref"]]
                ceb = pretty(a, ref["ceb"])
                rows.append([week, f"{ex['ref']}-ALT{j}", ceb, ref["en"], ref["speaker"], ref.get("scene", ""),
                             note("", f"Alternative word order accepted as CORRECT in the Day {day['day']} word-order exercise. Is it natural? (punctuation is ignored)")])
    for x in d.get("reviewExtras", []):
        rows.append([week, x["id"], x["ceb"], x["en"], "(text only, no audio)", x["where"], note("", x.get("check"))])

    out = ROOT / "review" / f"week{week:02d}_review.csv"
    with out.open("w", encoding="utf-8-sig", newline="") as f:
        w = csv.writer(f)
        w.writerow(["週", "ID", "セブアノ語", "英訳", "話者", "場面", "備考"])
        w.writerows(rows)
    print(f"OK: {len(d['chunks'])} chunks, {len(rows)} review rows -> {out.relative_to(ROOT)}")


if __name__ == "__main__":
    main(int(sys.argv[1]) if len(sys.argv) > 1 else 1)
