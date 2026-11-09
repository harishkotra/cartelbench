#!/usr/bin/env bash
# Render assets/narration.json to report/video/sN.mp3 with the macOS `say` voice.
set -e
cd "$(dirname "$0")/.."
VOICE="${VOICE:-Samantha}"
mkdir -p report/video
python3 - "$VOICE" <<'PY'
import json, os, subprocess, sys
voice = sys.argv[1]
for item in json.load(open("assets/narration.json")):
    n = item["slide"]
    aiff = f"report/video/_s{n}.aiff"
    mp3 = f"report/video/s{n}.mp3"
    subprocess.run(["say", "-v", voice, "-r", "168", "-o", aiff, item["text"]], check=True)
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", aiff,
                    "-af", "highpass=f=80,acompressor=threshold=-18dB:ratio=3:makeup=2",
                    "-ar", "44100", "-b:a", "160k", mp3], check=True)
    os.remove(aiff)
    print(f"s{n}.mp3  {len(item['text'].split())} words")
PY
