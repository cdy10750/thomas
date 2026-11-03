#!/usr/bin/env python3
"""Generate audio in batches (one TTS take per week and voice) and split it into one mp3 per line.

  python3 tools/batch_audio.py prompts 2 3 ... > batches.json
      Prints the batches: [{"batch": "W02-Danilo", "voice": "...", "ids": [...], "prompt": "line [long pause] line ..."}]
  python3 tools/batch_audio.py split batches.json DIR
      For each batch, reads DIR/<batch>.mp3, finds the pauses between lines with ffmpeg silencedetect,
      cuts at the longest gaps (one fewer than the number of lines) and writes audio/wNN/<ID>.mp3.

Requires ffmpeg. Lines are separated by the Eleven v4 audio tag [long pause].
"""
import json
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(Path(__file__).resolve().parent))
from generate_audio import lines_for_week  # noqa: E402

SEP = " [long pause] "
MAX_LINES = 25


def prompts(weeks):
    out = []
    for w in weeks:
        d = json.loads((ROOT / "data" / f"week{w:02d}.json").read_text(encoding="utf-8"))
        lines = lines_for_week(d)
        for voice in ("Danilo", "Marisol"):
            mine = [l for l in lines if l[2] == voice]
            for part in range(0, len(mine), MAX_LINES):
                chunk = mine[part:part + MAX_LINES]
                name = f"W{w:02d}-{voice}" + (f"-{part // MAX_LINES + 1}" if len(mine) > MAX_LINES else "")
                out.append({"batch": name, "voice": voice, "ids": [l[0] for l in chunk],
                            "texts": [l[1] for l in chunk], "prompt": SEP.join(l[1] for l in chunk)})
    return out


def silences(mp3):
    r = subprocess.run(["ffmpeg", "-hide_banner", "-i", str(mp3), "-af", "silencedetect=noise=-40dB:d=0.25",
                        "-f", "null", "-"], capture_output=True, text=True)
    starts = [float(x) for x in re.findall(r"silence_start: ([\d.]+)", r.stderr)]
    ends = [float(x) for x in re.findall(r"silence_end: ([\d.]+)", r.stderr)]
    dur = float(re.search(r"Duration: (\d+):(\d+):([\d.]+)", r.stderr).expand(r"\1 \2 \3").split()[2]) + \
        60 * float(re.search(r"Duration: (\d+):(\d+)", r.stderr).group(2))
    return list(zip(starts, ends)), dur


def split(batch_file, src_dir):
    batches = json.loads(Path(batch_file).read_text())
    ok = True
    for b in batches:
        mp3 = Path(src_dir) / f"{b['batch']}.mp3"
        n = len(b["ids"])
        gaps, dur = silences(mp3)
        # ignore leading / trailing silence
        inner = [(s, e) for s, e in gaps if s > 0.05 and e < dur - 0.05]
        inner.sort(key=lambda g: g[1] - g[0], reverse=True)
        cut = sorted(inner[:n - 1])
        if len(cut) != n - 1:
            print(f"{b['batch']}: FAILED - found {len(inner)} pauses for {n} lines")
            ok = False
            continue
        shortest_cut = min((e - s for s, e in cut), default=9)
        longest_rest = max((e - s for s, e in inner[n - 1:]), default=0)
        flag = "" if shortest_cut > 1.25 * longest_rest else "  <-- CHECK (pauses not clearly separated)"
        lead = next((e for s0, e in gaps if s0 <= 0.05), 0.0)
        tail = next((s0 for s0, e in gaps if e >= dur - 0.05), dur)
        starts = [max(0.0, lead - 0.08)] + [e - 0.08 for s0, e in cut]
        ends = [s0 + 0.18 for s0, e in cut] + [min(dur, tail + 0.18)]
        week = b["ids"][0][1:3]
        outdir = ROOT / "audio" / f"w{week}"
        outdir.mkdir(parents=True, exist_ok=True)
        lens = []
        for i, lid in enumerate(b["ids"]):
            a, z = starts[i], ends[i]
            subprocess.run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", "-i", str(mp3), "-ss", f"{a:.3f}",
                            "-to", f"{z:.3f}", "-codec:a", "libmp3lame", "-b:a", "128k", str(outdir / f"{lid}.mp3")],
                           check=True)
            lens.append(z - a)
        # sanity: seconds per character should be roughly similar for every line
        rates = [l / max(4, len(t)) for l, t in zip(lens, b["texts"])]
        avg = sum(rates) / len(rates)
        odd = [b["ids"][i] for i, r in enumerate(rates) if r > 2.2 * avg or r < avg / 2.2]
        print(f"{b['batch']}: {n} lines, {dur:.1f}s, min cut gap {shortest_cut:.2f}s vs next {longest_rest:.2f}s"
              f"{flag}{'  odd lengths: ' + ', '.join(odd) if odd else ''}")
    return ok


if __name__ == "__main__":
    if sys.argv[1] == "prompts":
        print(json.dumps(prompts([int(x) for x in sys.argv[2:]]), ensure_ascii=False, indent=1))
    elif sys.argv[1] == "split":
        sys.exit(0 if split(sys.argv[2], sys.argv[3]) else 1)
