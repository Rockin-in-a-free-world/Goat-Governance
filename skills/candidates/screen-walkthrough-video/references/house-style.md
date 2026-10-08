# Narration house style

The style is set by the Site Ops Overview:
`$VIDEOS_DIR/site-ops-overview/EN-operator-walkthrough.srt`.
Read it before drafting a new screen so the two videos feel like one series.

## Voice and sentence shape

- **Short, declarative, present tense.** One idea per cue. "The Miners page lists every device."
- **Imperative verbs for actions the viewer can take.** "Review…", "Monitor…", "Open…", "Filter…".
- **No filler.** No "In this video we will…", no "As you can see", no marketing language.
- **Neutral, instructional.** The screen follows the narration; describe what is on screen and what it
  is for, not how to feel about it.
- **Name on-screen labels exactly** and keep their casing (Work Order, Move Part, Spare Parts, MicroBT).

## Structure

- Open with a one-line welcome that parallels the reference ("Welcome to the Mining OS … walkthrough.").
- If the screen has an organizing rule, state it up front and let the rest pay it off. (Inventory
  Management's rule: *you view everywhere, but change only through Work Orders* — every read-only page
  then lands as "here's what you can see", and Work Orders arrives as the payoff.)
- Walk the screen in the order a user would move through it. Group cues by screen/section.
- Close with a short wrap ("This completes the … walkthrough." or a signoff the user approves).

## Cue / timing conventions

- Cues are spoken **back-to-back**: each cue's end time is the next cue's start time. No gaps in the SRT.
- The last cue ends at the last spoken word plus a short tail, capped to the video duration.
- Typical cue is ~2–6 seconds. Don't cram two ideas into one cue; split them.
- **Reading speed:** keep every cue under **20 characters/second**, ideal ~17. Verify with
  `scripts/check_cps.py`. Tighten wording, never stretch timing (timing is locked to the audio).

## Runtime targets

- Match the scope the user asks for. Site Ops Overview ≈ 5:00; Inventory Management was scoped to
  **2–3 min** (landed ~2:40). At ~150 wpm, 2–3 min ≈ 300–450 words ≈ ~40 cues.
- Prefer trimming to hitting a number — a tight 2:30 beats a padded 3:00.

## Deliverables per screen

1. `EN-<screen>-script.md` — the **teleprompter**. Group cues into screen blocks, each with a bold
   **Screen:** line saying where to be and what to click (e.g. "open a row's kebab menu on cue 13").
   Include the cue numbers so it cross-references the SRT one-to-one.
2. `script.text` — narration only, one cue per line, **no numbers/timestamps/headings**. This is the
   TTS input; the user may specifically want a `.text` extension.
3. `EN-<screen>.srt` — subtitles, produced **only** by `align_srt.py` from the final cut. Not written at
   the Alba voiceover step (`tts_alba.py` outputs audio only).

## Decisions to confirm with the user before recording/generating

- Intro wording (match the reference vs. a "continuing the series" framing).
- How much to emphasize read-only users / permissions (a single closing line usually).
- Any UI-term handling that will also matter for translations (see `translation.md`).
