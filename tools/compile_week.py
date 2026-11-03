#!/usr/bin/env python3
"""Compile a compact lesson source (content/weekNN.txt) into data/weekNN.json.

Usage: python3 tools/compile_week.py 2        (or several: 2 3 4)

Source format - one directive per line, fields separated by " | ".
Short ids ("05", "D1-03") are expanded to "W02-05", "W02-D1-03"; full ids ("W01-18") pass through.

  TITLE / SUBTITLE / GOAL <text>
  C <id> | <speaker> | <scene> | <ceb> | <en> | <tip> [| check: ...] [| lit: ...]
  D <n> | <title> | <scene>                 dialogue header; then its lines:
  L <id>                                    line that reuses a chunk
  L <speaker> | <ceb> | <en> [| check: ...] new line (id = W02-D<n>-<position>)
  DAY <n> | <title> | <intro>
  CULTURE <title> | <text>
  NEW <id> <id> ...
  DIALOGUES <n> <n> ...
  SCENE <id> | <answer> | <option> | <option>
  RESP <prompt id> > <answer id> | <distractor id> <distractor id>
  RESPC <situation text> > <answer id> | <distractor id> <distractor id>
  FILL <id> | <word> | <distractor>; <distractor>
  ORDER <id> | t1 / t2 / t3 [| alt: t2 / t1 / t3] [| extra: tile]
  MISSION <title>
  STEP <text>
  X | <ceb> | <en> | <where> [| check: ...]   text-only Cebuano for the review sheet
"""
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
VOICES = {"Danilo": ["Thomas", "Tatay", "Kuya", "Dodong"], "Marisol": ["Jiana", "Nanay", "Inday", "Tindera"]}


def compile_week(w):
    src = (ROOT / "content" / f"week{w:02d}.txt").read_text(encoding="utf-8")
    pre = f"W{w:02d}-"

    def rid(s):
        s = s.strip()
        return s if s.startswith("W") else pre + s

    out = {"week": w, "title": "", "subtitle": "", "goal": "", "voices": VOICES,
           "chunks": [], "dialogues": [], "days": [], "mission": {"title": "", "steps": []}, "reviewExtras": []}
    dlg = day = None
    xn = 0
    for n, raw in enumerate(src.splitlines(), 1):
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        key, _, rest = line.partition(" ")
        f = [x.strip() for x in rest.split(" | ")]
        try:
            if key in ("TITLE", "SUBTITLE", "GOAL"):
                out[key.lower()] = rest.strip()
            elif key == "C":
                c = {"id": rid(f[0]), "ceb": f[3], "en": f[4], "speaker": f[1], "scene": f[2], "tip": f[5] if len(f) > 5 else "", "check": ""}
                for extra in f[6:]:
                    if extra.startswith("check:"):
                        c["check"] = extra[6:].strip()
                    elif extra.startswith("lit:"):
                        c["lit"] = extra[4:].strip()
                out["chunks"].append(c)
            elif key == "D":
                dlg = {"id": f"{pre}D{f[0]}", "title": f[1], "scene": f[2], "lines": []}
                out["dialogues"].append(dlg)
            elif key == "L":
                pos = len(dlg["lines"]) + 1
                if len(f) == 1:
                    dlg["lines"].append({"chunk": rid(f[0])})
                else:
                    ln = {"id": f"{dlg['id']}-{pos:02d}", "speaker": f[0], "ceb": f[1], "en": f[2], "check": ""}
                    for extra in f[3:]:
                        if extra.startswith("check:"):
                            ln["check"] = extra[6:].strip()
                    dlg["lines"].append(ln)
            elif key == "DAY":
                day = {"day": int(f[0]), "title": f[1], "intro": f[2], "new": [], "exercises": []}
                out["days"].append(day)
            elif key == "CULTURE":
                day["culture"] = {"title": f[0], "text": f[1]}
            elif key == "NEW":
                day["new"] = [rid(x) for x in rest.split()]
            elif key == "DIALOGUES":
                day["dialogues"] = [f"{pre}D{x}" for x in rest.split()]
            elif key == "SCENE":
                day["exercises"].append({"type": "scene", "ref": rid(f[0]), "answer": f[1], "options": f[1:]})
            elif key in ("RESP", "RESPC"):
                head, _, ans = f[0].rpartition(" > ")
                ex = {"type": "respond", "answer": rid(ans), "distractors": [rid(x) for x in f[1].split()]}
                if key == "RESP":
                    ex["prompt"] = rid(head)
                else:
                    ex["context"] = head
                day["exercises"].append(ex)
            elif key == "FILL":
                ref = rid(f[0])
                chunk = next((c for c in out["chunks"] if c["id"] == ref), None)
                text = None
                if chunk:
                    pat = re.compile(r"(?<![\w'-])" + re.escape(f[1]) + r"(?![\w'-])")
                    if pat.search(chunk["ceb"]):
                        text = pat.sub("___", chunk["ceb"], count=1)
                if text is None:
                    raise ValueError(f"FILL word '{f[1]}' not found in {ref}")
                opts = [f[1]] + [x.strip() for x in f[2].split(";")]
                day["exercises"].append({"type": "fill", "ref": ref, "text": text, "answer": f[1], "options": opts})
            elif key == "ORDER":
                main = [t.strip() for t in f[1].split(" / ")]
                answers, extras = [main], []
                for extra in f[2:]:
                    if extra.startswith("alt:"):
                        answers.append([t.strip() for t in extra[4:].split(" / ")])
                    elif extra.startswith("extra:"):
                        extras.append(extra[6:].strip())
                day["exercises"].append({"type": "order", "ref": rid(f[0]), "tiles": main + extras, "answers": answers})
            elif key == "MISSION":
                out["mission"]["title"] = rest.strip()
            elif key == "STEP":
                out["mission"]["steps"].append(rest.strip())
            elif key == "X":
                xn += 1
                x = {"id": f"{pre}X{xn}", "ceb": f[0], "en": f[1], "where": f[2], "check": ""}
                if len(f) > 3 and f[3].startswith("check:"):
                    x["check"] = f[3][6:].strip()
                out["reviewExtras"].append(x)
            else:
                raise ValueError(f"unknown directive {key}")
        except (IndexError, ValueError, AttributeError, TypeError) as e:
            sys.exit(f"week{w:02d}.txt line {n}: {e}\n  {raw}")
    path = ROOT / "data" / f"week{w:02d}.json"
    path.write_text(json.dumps(out, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"compiled {path.relative_to(ROOT)}: {len(out['chunks'])} chunks, "
          f"{sum(len(d['lines']) for d in out['dialogues'])} dialogue lines, "
          f"{sum(len(d['exercises']) for d in out['days'])} exercises")


if __name__ == "__main__":
    for a in sys.argv[1:]:
        compile_week(int(a))
