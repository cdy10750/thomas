# Bisaya for Thomas

A phone-first, static self-study web app for learning conversational Cebuano (Bisaya) in 13 weeks,
built around the things Jiana's family in Bohol actually says. No server, no build step.

## Folder layout

```
index.html            app shell
css/style.css         styles (light and dark mode)
js/app.js             app logic: lessons, exercises, review (Leitner), progress in localStorage
data/weeks.json       13-week plan (which weeks are available)
data/weekNN.json      lesson data for one week (chunks, dialogues, 7 days of exercises, mission)
audio/wNN/<ID>.mp3    one mp3 per phrase / dialogue line (generated with ElevenLabs)
review/weekNN_review.csv  native-speaker review sheet
tools/export_csv.py   validate a week's JSON and export the review CSV
tools/generate_audio.py   generate a week's mp3 files with ElevenLabs (Eleven v4)
tools/voices.json     ElevenLabs voice IDs (Danilo = male, Marisol = female)
```

## Run it locally

Browsers block `fetch()` from `file://`, so serve the folder:

```bash
python3 -m http.server 8000
```

Then open http://localhost:8000 (on a phone on the same Wi-Fi: http://<computer-ip>:8000).

## Generate the audio

```bash
export ELEVENLABS_API_KEY=your-key-here
```

```bash
python3 tools/generate_audio.py 1
```

- Existing files are skipped; `--force` regenerates the whole week, `--only W01-05 W01-D2-03` regenerates specific lines.
- `--dry-run` lists every line and its voice without calling the API.
- Voices: Danilo (Thomas, Tatay, Kuya, Dodong) and Marisol (Jiana, Nanay, Inday). IDs are in `tools/voices.json`;
  delete that file to look them up again by name.
- Each line is generated once at natural speed. The app's Slow button plays it at 0.75x.

## Edit lessons

1. Edit `data/weekNN.json`.
2. Run `python3 tools/export_csv.py NN` - it checks every reference, fill-in answer and word-order answer, then rewrites the review CSV.
3. Regenerate audio for changed lines with `--only`.

## Review schedule

Each exercise has a Leitner box (1-5). New or missed items come back the next day; each correct review moves the item up a box
(next review after 1, 3, 7, 14, 30 days). Progress is stored in this browser only (localStorage).
