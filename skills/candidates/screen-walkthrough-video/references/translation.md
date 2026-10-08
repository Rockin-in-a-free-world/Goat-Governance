# Translated subtitle tracks

Goal: a subtitle track in another language that **shares the source SRT's timings exactly**, reads
comfortably, and handles product UI terms consistently.

## Hard rules

- **Timestamps stay byte-identical** to the source SRT. Only the text of each cue changes. Same number
  of cues, same order. Verify:

  ```python
  import re
  st = lambda p: re.findall(r"\d\d:\d\d:\d\d,\d\d\d --> \d\d:\d\d:\d\d,\d\d\d", open(p,encoding="utf-8").read())
  assert st("EN-<screen>.srt") == st("PT-BR-<screen>.srt")
  ```

- **Run `scripts/check_cps.py` on the translation.** Most languages run ~20–30% longer than English, so
  more cues will exceed 20 CPS even though the English was fine. Tighten those cues (the timing is
  locked). To buy space, drop a first-appearance gloss or move it to a later, roomier cue rather than
  rushing the reader.

- File naming mirrors the `EN-` prefix: `PT-BR-<screen>.srt`, `ES-<screen>.srt`, `FR-<screen>.srt`.

## UI-term policy

**Standing decision (confirmed 2026-09-23): use policy 3 — English label + gloss on first
appearance.** The product UI ships in English, so subtitles keep the on-screen labels in English and add a
short native gloss the first time each appears. Apply this by default for product translations without
re-asking; only re-confirm if a specific deployment ships a localized (non-English) UI, in which case pick
policy 1 or 2 below to match what's on screen.

The tool's interface may be English, localized, or mixed — this decides how labels are rendered. The three
policies, applied consistently:

1. **Keep labels in English** — for an English-only UI. Translate narration; leave on-screen
   button/page names in English so subtitles match what the viewer sees.
2. **Translate everything** — for a fully localized UI (e.g. Work Order → Ordem de Serviço,
   Dashboard → Painel, Spare Parts → Peças).
3. **English label + gloss on first appearance** (the pt-BR default used for Inventory Management):
   keep the English label, add a short native gloss the *first* time each appears, English-only after.
   e.g. `Work Order (Ordem de Serviço)`, `Dashboard (Painel)`, `Repair History (Histórico de Reparos)`.

Under policy 3, gloss genuine on-screen labels only; leave product/brand names (Mining OS, MicroBT, PSU,
Hashboard, CSV, MAC, rack) untranslated. Glosses are the first thing to cut when a cue is too dense —
if the same term recurs in a roomier later cue, gloss it there instead.

## Worked example (Inventory Management → pt-BR)

- The intro's `Inventory Management` gloss was dropped because the phrase "gestão de inventário" already
  appears naturally later — no need to gloss a term the narration translates on its own elsewhere.
- The busiest cue named two labels in ~3s (Register New Miner + Register Devices). Both glosses there
  were impossible to read; the fix was English-only in that cue and glossing `Register Devices` in a
  later 5-second cue.
- Result: 41 cues, timings identical to EN, every cue under 20 CPS.
