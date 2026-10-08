---
name: screen-walkthrough-video
description: End-to-end product screen-walkthrough pipeline — house-style narration, audio-aligned .srt, offline Piper (Alba en_GB) voiceover, same-timing translations. Use for a product videos repo, a walkthrough/tutorial/overview video, an .srt or subtitles/captions, a voiceover or TTS, aligning captions to a recording, or translating subtitles.
compatibility: macOS (Apple Silicon). Homebrew ffmpeg + a Python venv (mlx-whisper, piper-tts). First run fetches models; all local/offline after.
---

# Screen Walkthrough Video

Produce a narrated walkthrough for one screen: narration script, subtitles aligned to the spoken audio,
an optional Alba voiceover, and translated tracks sharing the same timings. Distilled from the Inventory
Management and Site Ops Overview videos in `$VIDEOS_DIR` (set in `.env`; see `.env.example`).

## Pick the timing mode first

Two modes; decide before anything else:

1. **Generated voice (Alba TTS).** You synthesize the audio. `scripts/tts_alba.py` writes the **mp3 only**
   and prints per-line reading speed (CPS) from the true clip lengths. **It writes no SRT** — the shipping
   SRT is still built later from the final cut (mode 2), because the Alba take is an *earlier take* whose
   timings the edit will change.
2. **Human recording / placed voiceover / final cut.** Timings unknown, and the audio may reword,
   reorder, or drop lines. Transcribe and align the known script lines. `scripts/align_srt.py`. **This is
   the only step that creates the SRT.**

**Canonical mode-2 rule (stated once):** build the SRT from the ACTUAL final audio that ships — never the
script alone, never an earlier take. `align_srt.py` keeps a line only if it truly appears and **DROPS the
rest, reporting them**. After running: read the DROPPED report, confirm each was genuinely cut, and check
the cue count and last cue. Never re-add or interpolate a phantom cue (classic bug: a cut outro left
dangling at the end).

Record-your-own → mode 2. Want a generated voice → mode 1. Projects often use mode 2 for a human take,
then switch to mode 1 on the voice swap.

## Inputs

- Screen guide/spec (HTML/PDF/Doc) — read it fully; the narration is a spoken tour of it. Verify or
  capture screens live via Playwright MCP + Brave — see `references/app-capture-brave.md`.
- Reference house-style SRT: `$VIDEOS_DIR/site-ops-overview/EN-operator-walkthrough.srt`.
- Runtime target (Site Ops ~5 min; Inventory 2–3 min).
- Optional: a recording (mode 2) or a request to generate the voice (mode 1).

## Workflow

### 1. Draft narration (house style)

Follow `references/house-style.md`: short present-tense declaratives, imperative verbs, one idea per cue,
cues back-to-back, logical screen order, lead with the screen's organizing rule. Deliver in the screen
folder:

- `EN-<screen>-script.md` — teleprompter with **Screen:** headings (where to be / what to click).
- `script.text` — narration only, one line per cue, no numbers/timestamps/headings (TTS input).
- `EN-<screen>.srt` — created **only** by step 2b, from the final cut. **Never** at the voiceover step.

Confirm intro wording, permissions emphasis, and UI-term decisions before recording.

### 2a. Generate voiceover — Alba (mode 1)

One-time setup (idempotent; prints WENV / VOICES / ESPHACK):

```bash
scripts/setup_env.sh
```

Render the mp3 (written directly — no .wav). **Audio only: it prints a per-line CPS report and writes NO
SRT.**

```bash
"$WENV/bin/python" scripts/tts_alba.py \
  --script /path/script.text --out-mp3 /path/EN-<screen>-voiceover.mp3 \
  --voice "$VOICES/alba.onnx" --espeak "$ESPHACK" \
  --length-scale 1.06 --gap 0.40 --lead 0.30
```

Synthesizes each line, stitches with `--gap` silence, and prints reading speed per line from the true
clip lengths (so the density pass is done here — no SRT needed). Pace with `--length-scale` (higher =
slower), breathing with `--gap`. Voice list + espeak detail: `references/alba-piper.md`.

> **Never create the SRT at this step.** `tts_alba.py` does not accept `--srt` on purpose. The Alba take
> is an *earlier take*; per the mode-2 rule the shipping SRT is built from the FINAL cut (2b). An SRT made
> from the voiceover is thrown away the moment the edit changes — pure waste.

### 2b. Or align to final audio (mode 2)

Point at the exact shipping audio (final cut / placed voiceover), not the script or an earlier take:

```bash
"$WENV/bin/python" scripts/align_srt.py \
  --audio /path/<screen>.mp4 --script /path/script.text --srt /path/EN-<screen>.srt
# --video-dur auto via ffprobe; --min-match (default 0.5) tunes drop sensitivity
```

Then apply the canonical mode-2 rule above (DROPPED report, cue count, last cue). If lines were
reworded/reordered rather than just cut, update `script.text` / the `.md` to the spoken reality, re-run,
and tell the user what diverged.

### 3. Density (reading speed) pass

The Alba step (2a) already prints per-line CPS from the true clip lengths, so mode-1 density is covered
there. For a mode-2 SRT, run it on that SRT:

```bash
"$WENV/bin/python" scripts/check_cps.py /path/EN-<screen>.srt
```

Target **< 20 CPS**, ideal ~17. For a DENSE cue, tighten the wording — **never change the timing** (it's
locked to the audio). Re-run until clean.

### 4. Translations (same timings)

See `references/translation.md`. Translate each cue, keep the timestamps **byte-identical**, and re-run
`check_cps.py` (pt-BR etc. run ~20–30% longer, so more cues go dense). Default UI-term policy: English
label + gloss on first appearance, English-only after; confirm whether the UI is English/localized/mixed.
Reduce density by dropping a gloss, not by rushing the reader. Name files `PT-BR-<screen>.srt`,
`ES-<screen>.srt`, matching the `EN-` prefix.

## Layout (per screen)

```
<screen-folder>/
├── EN-<screen>-script.md     # teleprompter
├── script.text              # TTS input
├── EN-<screen>.srt          # subtitles, aligned to the FINAL cut (mode 2 only)
├── EN-<screen>-voiceover.mp3 # Alba track (mode 1 — audio only, no SRT)
├── PT-BR-<screen>.srt       # translations, identical timings
└── <screen>.mp4 / *.cmproj  # video / editor project (user-supplied)
```

## Gotchas

- **Piper's espeak-ng-data path is broken** (hardcoded to the CI machine). `setup_env.sh` builds
  `esphack/`; don't skip it or synthesis fails with `phontab: No such file`. Full detail + more
  whisper/piper gotchas (whisper model id, no `sentence_silence`): `references/alba-piper.md`.
- **A recording rarely matches the script** — transcribe first, treat the audio as truth. The shipping
  cut is usually shorter (trimmed pauses, cut lines); let `align_srt.py` drop them, never force the full
  script in or interpolate a cut line back.
- **SRT cues** are back-to-back; the last cue ends at the last spoken word + a short tail, capped to the
  video duration.
- **Never build the SRT from the Alba take** (or any pre-final take). `tts_alba.py` writes audio only; the
  shipping SRT comes from the final cut via `align_srt.py`. An SRT made at the voiceover step is discarded
  on the next edit — creating one there is wasted work, not a shortcut.
