#!/usr/bin/env python3
"""Generate the mp3 files for one week with ElevenLabs (Eleven v4).

Usage:
    export ELEVENLABS_API_KEY=...       # never commit the key
    python3 tools/generate_audio.py 1          # week 1, skips files that already exist
    python3 tools/generate_audio.py 1 --force  # regenerate everything for week 1
    python3 tools/generate_audio.py 1 --only W01-05 W01-D2-03   # regenerate specific lines
    python3 tools/generate_audio.py 1 --dry-run # list what would be generated (no API calls)

Voices are looked up by name through the API (GET /v2/voices?search=...) and the
IDs are cached in tools/voices.json. Each line is generated once, at natural speed;
the app offers a 0.75x "Slow" button instead of a second recording.
Only the Python standard library is used.
"""
import argparse
import json
import os
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
API = "https://api.elevenlabs.io"
MODEL_ID = "eleven_v4"
OUTPUT_FORMAT = "mp3_44100_128"
VOICE_NAMES = {"Danilo": "Danilo - Firm Cebu Ad", "Marisol": "Marisol - Bubbly Cebu Creator"}
VOICE_CACHE = ROOT / "tools" / "voices.json"


def request(method, path, key, body=None, accept="application/json"):
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(API + path, data=data, method=method, headers={
        "xi-api-key": key, "Content-Type": "application/json", "Accept": accept})
    with urllib.request.urlopen(req, timeout=120) as r:
        return r.read()


def find_voice(key, short_name, full_name):
    q = urllib.parse.urlencode({"search": short_name, "page_size": 50})
    res = json.loads(request("GET", f"/v2/voices?{q}", key))
    voices = res.get("voices", [])
    exact = [v for v in voices if v["name"] == full_name]
    cebuano = [v for v in voices if v.get("labels", {}).get("language") == "ceb"]
    pick = (exact or cebuano or [None])[0]
    if not pick:
        names = ", ".join(v["name"] for v in voices) or "(none)"
        sys.exit(f"Voice '{full_name}' not found in your ElevenLabs workspace. Search returned: {names}\n"
                 f"Add the voice to 'My Voices' in ElevenLabs, or put its ID in {VOICE_CACHE.name}.")
    return pick["voice_id"], pick["name"]


def voice_ids(key):
    cache = json.loads(VOICE_CACHE.read_text()) if VOICE_CACHE.exists() else {}
    changed = False
    for short, full in VOICE_NAMES.items():
        if short not in cache:
            vid, name = find_voice(key, short, full)
            cache[short] = {"voice_id": vid, "name": name}
            changed = True
            print(f"Voice {short}: {name} -> {vid}")
    if changed:
        VOICE_CACHE.write_text(json.dumps(cache, indent=2) + "\n")
    return {k: v["voice_id"] for k, v in cache.items()}


def lines_for_week(d):
    """Every line that needs its own mp3: all chunks + dialogue lines that are not chunks."""
    voice_of = {sp: v for v, sps in d["voices"].items() for sp in sps}
    out = [(c["id"], c["ceb"], voice_of[c["speaker"]]) for c in d["chunks"]]
    for dlg in d["dialogues"]:
        for ln in dlg["lines"]:
            if "id" in ln:
                out.append((ln["id"], ln.get("tts", ln["ceb"]), voice_of[ln["speaker"]]))
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("week", type=int)
    ap.add_argument("--force", action="store_true")
    ap.add_argument("--only", nargs="*")
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    d = json.loads((ROOT / "data" / f"week{args.week:02d}.json").read_text(encoding="utf-8"))
    outdir = ROOT / "audio" / f"w{args.week:02d}"
    outdir.mkdir(parents=True, exist_ok=True)
    todo = [l for l in lines_for_week(d)
            if (not args.only or l[0] in args.only)
            and (args.force or args.only or not (outdir / f"{l[0]}.mp3").exists())]
    chars = sum(len(t) for _, t, _ in todo)
    print(f"Week {args.week}: {len(todo)} lines to generate (~{chars} characters).")
    if args.dry_run:
        for i, t, v in todo:
            print(f"  {i:<12} {v:<8} {t}")
        return

    key = os.environ.get("ELEVENLABS_API_KEY")
    if not key:
        sys.exit("Set ELEVENLABS_API_KEY first.")
    vids = voice_ids(key)
    for n, (lid, text, voice) in enumerate(todo, 1):
        body = {"text": text, "model_id": MODEL_ID}
        for attempt in range(4):
            try:
                audio = request("POST", f"/v1/text-to-speech/{vids[voice]}?output_format={OUTPUT_FORMAT}",
                                key, body, accept="audio/mpeg")
                break
            except urllib.error.HTTPError as e:
                msg = e.read().decode(errors="replace")[:300]
                if e.code in (429, 500, 502, 503) and attempt < 3:
                    time.sleep(2 ** (attempt + 1))
                    continue
                sys.exit(f"{lid}: HTTP {e.code} {msg}")
        (outdir / f"{lid}.mp3").write_bytes(audio)
        print(f"[{n}/{len(todo)}] {lid} ({voice}) {text}")
    print("Done.")


if __name__ == "__main__":
    main()
