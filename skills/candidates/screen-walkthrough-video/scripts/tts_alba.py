#!/usr/bin/env python3
"""Mode 1 — generate a full Piper (Alba) voiceover from a plain narration file.

Each line of --script is synthesized separately and the clips are concatenated
with --gap seconds of silence between them, plus a --tail of trailing silence after
the last line so the mp3 encoder's end padding never clips the final words. Writes
the mp3 directly (PCM piped to ffmpeg) — no intermediate .wav. Prints a per-line
reading-speed (CPS) report from the true spoken clip lengths, so density is checked
here without any SRT.

DELIBERATELY WRITES NO SRT — and does not accept --srt.
  The Alba take is an *earlier take*. Per the skill's canonical mode-2 rule the
  shipping SRT must be built from the FINAL cut audio (scripts/align_srt.py). An
  SRT generated at the voiceover step is discarded the moment the edit changes
  (trimmed pauses, reordered b-roll), so it is pure waste. Don't create one here.

Run scripts/setup_env.sh first. Example:

  "$WENV/bin/python" tts_alba.py \
      --script script.text --out-mp3 EN-screen-voiceover.mp3 \
      --voice "$VOICES/alba.onnx" --espeak "$ESPHACK" \
      --length-scale 1.06 --gap 0.40 --lead 0.30
"""
import argparse, io, os, subprocess, wave
from piper import PiperVoice, SynthesisConfig


def mmss(t):
    m = int(t // 60); s = t % 60
    return f"{m:d}:{s:04.1f}"


def main():
    home = os.environ.get("SKILL_HOME", os.path.expanduser("~/.cache/screen-walkthrough"))
    ap = argparse.ArgumentParser()
    ap.add_argument("--script", required=True, help="narration, one cue per line, no meta")
    ap.add_argument("--out-mp3", required=True)
    ap.add_argument("--voice", default=os.path.join(home, "voices", "alba.onnx"))
    ap.add_argument("--espeak", default=os.path.join(home, "esphack"))
    ap.add_argument("--length-scale", type=float, default=1.06, help="higher = slower")
    ap.add_argument("--gap", type=float, default=0.40, help="silence between lines (s)")
    ap.add_argument("--lead", type=float, default=0.30, help="lead-in silence (s)")
    ap.add_argument("--tail", type=float, default=0.50,
                    help="trailing silence after the LAST line (s); guards the final words from being "
                         "clipped by the mp3 encoder's end padding")
    ap.add_argument("--cps-limit", type=float, default=20.0, help="flag lines at/above this reading speed")
    a = ap.parse_args()

    voice = PiperVoice.load(a.voice, espeak_data_dir=a.espeak)
    syn = SynthesisConfig(volume=1.0, length_scale=a.length_scale)

    lines = [l.strip() for l in open(a.script, encoding="utf-8") if l.strip()]

    def synth(text):
        buf = io.BytesIO()
        with wave.open(buf, "wb") as wf:
            voice.synthesize_wav(text, wf, syn_config=syn)
        buf.seek(0)
        with wave.open(buf, "rb") as wf:
            return wf.getparams(), wf.readframes(wf.getnframes())

    p0, _ = synth(lines[0])
    sr, sw, ch = p0.framerate, p0.sampwidth, p0.nchannels
    bytes_per_sec = sr * sw * ch
    sil = (b"\x00" * (sw * ch))

    audio = bytearray(sil * int(round(a.lead * sr)))
    rows = []  # (spoken_seconds, text)
    for i, line in enumerate(lines):
        _, frames = synth(line)
        rows.append((len(frames) / bytes_per_sec, line))
        audio += frames
        if i < len(lines) - 1:
            audio += sil * int(round(a.gap * sr))

    # Trailing silence after the last line so the mp3 encoder's end padding never clips the final words.
    audio += sil * int(round(a.tail * sr))

    total = len(audio) / bytes_per_sec

    fmt = {1: "u8", 2: "s16le", 3: "s24le", 4: "s32le"}[sw]
    subprocess.run(["ffmpeg", "-y", "-f", fmt, "-ar", str(sr), "-ac", str(ch),
                    "-i", "-", "-b:a", "192k", a.out_mp3],
                   input=bytes(audio), check=True, capture_output=True)

    # Inline reading-speed report. CPS is over the caption's on-screen window (spoken clip + the
    # trailing --gap), matching how check_cps.py measures a back-to-back SRT — so no SRT is needed here.
    dense = 0
    print(f"  #  window  chars   cps  text")
    for i, (d, tx) in enumerate(rows, 1):
        window = d + a.gap
        cps = len(tx) / window if window else 0.0
        flag = " (DENSE)" if cps >= a.cps_limit else ""
        print(f"{i:3d} {window:6.2f} {len(tx):5d} {cps:5.1f}{flag}  {tx[:48]}")
        if cps >= a.cps_limit:
            dense += 1

    print(f"\nlines={len(lines)} total={mmss(total)} ({total:.1f}s) dense(>= {a.cps_limit} cps)={dense}")
    print(f"wrote {a.out_mp3}")
    print("NOTE: no SRT written by design — build it from the FINAL cut with align_srt.py (mode 2).")


if __name__ == "__main__":
    main()
