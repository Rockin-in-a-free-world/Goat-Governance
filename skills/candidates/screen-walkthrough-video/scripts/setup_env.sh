#!/usr/bin/env bash
# One-time (idempotent) setup for the screen-walkthrough-video skill.
# Installs ffmpeg, a Python venv with mlx-whisper + piper-tts, downloads the Alba
# (en_GB) Piper voice, and builds the espeak-ng-data workaround dir Piper needs.
#
# Everything lives under $SKILL_HOME (default ~/.cache/screen-walkthrough) so it
# is reusable across screens and does not touch the video project.
#
# Prints WENV / VOICES / ESPHACK at the end — export them or pass to the scripts.
set -euo pipefail

: "${SKILL_HOME:=$HOME/.cache/screen-walkthrough}"
WENV="$SKILL_HOME/wenv"
VOICES="$SKILL_HOME/voices"
ESPHACK="$SKILL_HOME/esphack"
mkdir -p "$SKILL_HOME" "$VOICES"

# 1. ffmpeg (audio extraction + mp3 export)
if ! command -v ffmpeg >/dev/null 2>&1; then
  echo "Installing ffmpeg via Homebrew…"
  brew install ffmpeg
fi

# 2. Python venv + libraries
if [ ! -x "$WENV/bin/python" ]; then
  python3 -m venv "$WENV"
fi
"$WENV/bin/pip" install -q --upgrade pip
"$WENV/bin/pip" install -q mlx-whisper piper-tts numpy

# 3. Alba voice model (Piper, en_GB, medium)
BASE="https://huggingface.co/rhasspy/piper-voices/resolve/main/en/en_GB/alba/medium/en_GB-alba-medium.onnx"
[ -s "$VOICES/alba.onnx" ]      || curl -sL "$BASE"      -o "$VOICES/alba.onnx"
[ -s "$VOICES/alba.onnx.json" ] || curl -sL "$BASE.json" -o "$VOICES/alba.onnx.json"

# 4. esphack — work around Piper's broken hardcoded espeak-ng-data path.
# The bundled espeakbridge.so validates that <arg>/espeak-ng-data EXISTS, but then
# loads phontab from <arg> DIRECTLY. So we need one dir that contains BOTH the
# data files (phontab, phondata, …) AND a subdir literally named espeak-ng-data.
# We build it from symlinks so it stays in sync with the installed package.
ESPDATA="$("$WENV/bin/python" -c 'import piper,os;print(os.path.join(os.path.dirname(piper.__file__),"espeak-ng-data"))')"
if [ ! -f "$ESPDATA/phontab" ]; then
  echo "ERROR: could not find bundled espeak-ng-data at $ESPDATA" >&2; exit 1
fi
mkdir -p "$ESPHACK"
# Refresh only the symlinks we manage (never a recursive delete of a variable path).
find "$ESPHACK" -maxdepth 1 -type l -delete
for f in "$ESPDATA"/*; do ln -sfn "$f" "$ESPHACK/$(basename "$f")"; done
ln -sfn "$ESPDATA" "$ESPHACK/espeak-ng-data"   # satisfies the validator

echo
echo "Setup complete. Use these (export or pass as flags):"
echo "  export WENV=$WENV"
echo "  export VOICES=$VOICES"
echo "  export ESPHACK=$ESPHACK"
