#!/bin/bash
# Assemble the demo video: slide PNG + narration MP3 per slide, then concat.
# Requires: report/slides/slideN.png (Chrome screenshots) and report/video/sN.mp3 (TTS).
set -e
cd "$(dirname "$0")/.."
mkdir -p report/video
: > report/video/list.txt
N=$(ls report/slides/slide*.png 2>/dev/null | wc -l | tr -d ' ')
[ "$N" -ge 4 ] || { echo "no slide frames"; exit 1; }
for i in $(seq 1 "$N"); do
  img="report/slides/slide$i.png"; aud="report/video/s$i.mp3"
  [ -f "$img" ] && [ -f "$aud" ] || { echo "missing $img or $aud"; exit 1; }
  d=$(ffprobe -v error -show_entries format=duration -of csv=p=0 "$aud")
  t=$(python3 -c "print(round(float('$d') + 0.55, 2))")
  ffmpeg -y -loglevel error -loop 1 -i "$img" -i "$aud" \
    -filter_complex "[0:v]scale=1280:720,format=yuv420p[v];[1:a]apad=pad_dur=0.5[a]" \
    -map "[v]" -map "[a]" -t "$t" -r 30 -c:v libx264 -preset medium -crf 20 \
    -c:a aac -b:a 160k report/video/seg$i.mp4
  echo "file 'seg$i.mp4'" >> report/video/list.txt
  echo "  slide $i  ${t}s"
done
ffmpeg -y -loglevel error -f concat -safe 0 -i report/video/list.txt -c copy \
  report/video/cartelbench.mp4
ffprobe -v error -show_entries format=duration,size -of default=nw=1 report/video/cartelbench.mp4
