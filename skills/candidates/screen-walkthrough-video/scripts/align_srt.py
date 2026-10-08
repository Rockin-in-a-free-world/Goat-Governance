#!/usr/bin/env python3
"""Mode 2 — align known script lines to the ACTUAL audio and write an SRT.

THE FINAL AUDIO IS THE SOURCE OF TRUTH — always run this against the exact audio
that ships in the video (the final cut / the placed voiceover), never the raw script
alone. Editors routinely cut, trim, or reorder lines when placing audio, so the SRT
must contain ONLY what is actually spoken.

How it works: transcribes with word-level timestamps (mlx-whisper), then walks the
script lines in order and keeps a line ONLY if enough of its words actually appear,
in order, in the transcript (--min-match, default 0.5). Each kept cue starts at the
spoken time of its first matched word. **Lines that are not in the audio are DROPPED
(reported), not interpolated** — so a script line the editor cut (e.g. an outro like
"Happy mining!") will not appear as a phantom cue at the end.

Always read the DROPPED report: confirm each dropped line was genuinely cut (vs a
transcription miss) and that the kept cue count matches what you expect. If a line was
wrongly dropped, lower --min-match or fix the wording; if extra lines survive that were
actually cut, raise --min-match.

Run scripts/setup_env.sh first. Example:

  "$WENV/bin/python" align_srt.py --audio final.mp4 --script script.text --srt EN-screen.srt
"""
import argparse, os, re, subprocess, tempfile
import mlx_whisper


def ffprobe_duration(path):
    out = subprocess.run(["ffprobe","-v","error","-show_entries","format=duration",
        "-of","default=nk=1:nw=1", path], capture_output=True, text=True).stdout.strip()
    return float(out) if out else None


def to_wav16k(path):
    if path.lower().endswith(".wav"):
        return path, False
    tmp = tempfile.NamedTemporaryFile(suffix=".wav", delete=False).name
    subprocess.run(["ffmpeg","-y","-i",path,"-ac","1","-ar","16000","-vn",tmp],
                   check=True, capture_output=True)
    return tmp, True


def norm(x):
    return re.sub(r"[^a-z0-9]", "", x.lower())


def ts(t):
    if t < 0: t = 0
    h=int(t//3600); m=int((t%3600)//60); s=int(t%60); ms=int(round((t-int(t))*1000))
    if ms==1000: s+=1; ms=0
    return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--audio", required=True, help="the FINAL audio/video that ships (wav/mp3/mp4)")
    ap.add_argument("--script", required=True, help="narration, one cue per line")
    ap.add_argument("--srt", required=True)
    ap.add_argument("--model", default="mlx-community/whisper-small.en-mlx")
    ap.add_argument("--video-dur", type=float, default=None)
    ap.add_argument("--min-match", type=float, default=0.5,
                    help="fraction of a line's words that must appear in the audio to keep it")
    a = ap.parse_args()

    dur = a.video_dur or ffprobe_duration(a.audio) or 1e9
    wav, tmp = to_wav16k(a.audio)
    r = mlx_whisper.transcribe(wav, path_or_hf_repo=a.model, word_timestamps=True, language="en")
    if tmp: os.unlink(wav)
    print("\n===== TRANSCRIPT =====\n" + r["text"].strip() + "\n")

    atoks = [(norm(w["word"]), w["start"], w["end"])
             for seg in r["segments"] for w in seg.get("words", []) if norm(w["word"])]
    LINES = [l.strip() for l in open(a.script, encoding="utf-8") if l.strip()]

    # Monotonic presence match: keep a line only if it actually appears in the audio.
    p = 0
    kept = []       # (line_idx, start_time)
    dropped = []    # (line_idx, line, best_ratio)
    for li, line in enumerate(LINES):
        L = [norm(w) for w in line.split() if norm(w)]
        if not L:
            continue
        best = None  # (matched, start_idx, first_time, last_i, ratio)
        for start in range(p, max(p + 1, min(len(atoks), p + 12))):
            i = start; matched = 0; first_time = None; last_i = start
            for tok in L:
                for j in range(i, min(len(atoks), i + 6)):
                    if atoks[j][0] == tok:
                        matched += 1
                        if first_time is None: first_time = atoks[j][1]
                        i = j + 1; last_i = j; break
            ratio = matched / len(L)
            if best is None or matched > best[0]:
                best = (matched, start, first_time, last_i, ratio)
        if best and best[4] >= a.min_match and best[2] is not None:
            kept.append((li, best[2])); p = best[3] + 1
        else:
            dropped.append((li, line, round(best[4], 2) if best else 0.0))

    last_end = atoks[-1][2] if atoks else dur
    out = []
    for k, (li, st) in enumerate(kept):
        end = kept[k+1][1] if k < len(kept)-1 else min(last_end + 0.4, dur)
        if end <= st: end = st + 0.8
        out.append(f"{k+1}\n{ts(st)} --> {ts(end)}\n{LINES[li]}\n")
    open(a.srt, "w", encoding="utf-8").write("\n".join(out))

    print(f"media_dur={ts(dur)}  script_lines={len([l for l in LINES if l])}  kept={len(kept)}  dropped={len(dropped)}")
    if dropped:
        print("\n!! DROPPED (not found in the audio — confirm each was genuinely cut):")
        for li, line, ratio in dropped:
            print(f"   script#{li+1} (match {ratio}): {line}")
        print("   If a line was wrongly dropped, lower --min-match or fix its wording, then re-run.")
    print(f"\nwrote {a.srt} ({len(kept)} cues)")


if __name__ == "__main__":
    main()
