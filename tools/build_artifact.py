#!/usr/bin/env python3
"""Build a single-page version for publishing as a claude.ai Artifact.

Usage: python3 tools/build_artifact.py OUT_DIR
Writes OUT_DIR/bisaya.html (CSS and JS inlined, no <html>/<head>/<body> wrapper)
plus OUT_DIR/data/*.json and OUT_DIR/audio/wNN/*.mp3 copied from the repo.
"""
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def main(out):
    out = Path(out)
    out.mkdir(parents=True, exist_ok=True)
    css = (ROOT / "css" / "style.css").read_text(encoding="utf-8")
    js = (ROOT / "js" / "app.js").read_text(encoding="utf-8")
    page = f"""<title>Bisaya for Thomas</title>
<meta name="claude:viewport-fit-sides" content="cover">
<style>
{css}
</style>
<header class="topbar">
  <button class="topbar-back" id="backBtn" type="button" aria-label="Back to home" hidden>&larr; Home</button>
  <div class="topbar-title" id="topTitle">Bisaya for Thomas</div>
  <div class="topbar-progress" id="topProgress" hidden><div class="topbar-progress-fill" id="topProgressFill"></div></div>
</header>
<main id="app" class="app" aria-live="polite"><p class="muted">Loading lessons...</p></main>
<div class="toast" id="toast" role="status" hidden></div>
<audio id="player" preload="auto"></audio>
<script>
{js}
</script>
"""
    (out / "bisaya.html").write_text(page, encoding="utf-8")
    shutil.copytree(ROOT / "data", out / "data", dirs_exist_ok=True)
    if (ROOT / "audio").exists():
        shutil.copytree(ROOT / "audio", out / "audio", dirs_exist_ok=True)
    print("built", out / "bisaya.html")


if __name__ == "__main__":
    main(sys.argv[1])
