# Alba / Piper voiceover

Piper is a free, offline, neural TTS. **Alba** (`en_GB-alba-medium`) is the chosen house voice for this
series — a calm, clear British female that suits the neutral instructional tone. It sounds close to
commercial TTS and costs nothing (the user rejected paid tools like Audiate).

## Setup

Run `scripts/setup_env.sh` once. It installs ffmpeg + a venv (mlx-whisper, piper-tts, numpy), downloads
Alba into `$VOICES`, and builds the espeak workaround dir `$ESPHACK`. It prints the three paths; export
them for the session:

```bash
source <(scripts/setup_env.sh | sed -n 's/^  //p')   # or copy the export lines it prints
```

## Generate a track

Use `scripts/tts_alba.py` (see its header). It renders per-line clips, stitches them with a silence
`--gap`, writes the **mp3 only**, and prints per-line reading speed (CPS) from the clip lengths. **It
writes no SRT** — the shipping SRT is built from the final cut with `align_srt.py`; an SRT from the Alba
take is discarded on the next edit (see SKILL.md, mode 1).

- **Pace:** `--length-scale` — higher is slower. `1.06` ≈ slightly slower than default (used for
  Inventory Management, landed ~2:42 of pure narration); `1.15` is noticeably slower. Alba tends to run
  a bit faster than a human read of the same script.
- **Breathing room:** `--gap` (silence between lines, default 0.40s), `--lead` (0.30s at the very start,
  so cue 1 doesn't clip), and `--tail` (0.50s after the last line, so the mp3 encoder's end padding never
  clips the final words).
- Output: `tts_alba.py --out-mp3` writes the mp3 directly (PCM piped to ffmpeg at 192k) — no .wav kept.
  Piper outputs 22.05 kHz mono; fine for video. Resample to 48 kHz stereo only if the editor needs it.

## Other voices (same pipeline)

Download from `rhasspy/piper-voices` on HuggingFace and pass with `--voice`:

| Voice | Repo file | Character |
|---|---|---|
| **Alba (default)** | `en/en_GB/alba/medium/en_GB-alba-medium.onnx` | UK female, calm, clear |
| Alan | `en/en_GB/alan/medium/en_GB-alan-medium.onnx` | UK male, documentary |
| Amy | `en/en_US/amy/medium/en_US-amy-medium.onnx` | US female, warm |
| Ryan (high) | `en/en_US/ryan/high/en_US-ryan-high.onnx` | US male, professional |
| pt-BR Faber | `pt/pt_BR/faber/medium/pt_BR-faber-medium.onnx` | Brazilian male — for a pt-BR voiceover |

Fetch both the `.onnx` and its `.onnx.json` (append `.json` to the URL).

## The espeak-ng-data workaround (why $ESPHACK exists)

The piper-tts wheel ships `espeakbridge.so` with a data path **hardcoded to the CI build machine**
(`/Users/runner/work/piper1-gpl/.../espeak-ng-data`). Synthesis otherwise fails with:

```
Error processing file '.../espeak-ng-data/phontab': No such file or directory.
```

Observed behaviour of the bridge:
- It **validates** that `<arg>/espeak-ng-data` exists.
- But it then **loads** `phontab` (and friends) from `<arg>` **directly**.
- Passing the real data dir fails validation (`data/espeak-ng-data` doesn't exist); passing its parent
  fails the load (`parent/phontab` doesn't exist). Neither the `espeak_data_dir=` argument nor
  `ESPEAK_DATA_PATH` reliably override the compiled default.

Fix: build one directory that satisfies **both** checks — it contains the data files **and** a subdir
named `espeak-ng-data`. `setup_env.sh` does this with symlinks:

```bash
for f in "$ESPDATA"/*; do ln -sfn "$f" "$ESPHACK/$(basename "$f")"; done  # phontab, phondata, …
ln -sfn "$ESPDATA" "$ESPHACK/espeak-ng-data"                              # satisfies validator
```

Then pass `--espeak "$ESPHACK"` (i.e. `PiperVoice.load(model, espeak_data_dir=ESPHACK)`). Verify with:

```python
from piper import espeakbridge as eb
eb.initialize(ESPHACK); eb.set_voice("en-gb-x-rp")
print(eb.get_phonemes("Hello there."))   # -> [('həlˈəʊ ðˈeə', '.', True)]
```

## Other gotchas

- `SynthesisConfig` fields are `speaker_id, length_scale, noise_scale, noise_w_scale, normalize_audio,
  volume` — **no `sentence_silence`**. Control pauses with `--gap` / `--lead`, not a config kwarg.
- Model id for whisper is `mlx-community/whisper-small.en-mlx`. `mlx-community/whisper-base.en` 404s.
