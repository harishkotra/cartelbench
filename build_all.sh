#!/bin/bash
# Rebuild every artefact from runs/main.jsonl. No number is typed by hand.
set -e
cd "$(dirname "$0")"
python3 -m cartelbench.analyze
# board-only judge pass (needs ollama); cached — delete runs/monitor.jsonl to re-judge
[ -s runs/monitor.jsonl ] || python3 -m cartelbench.monitor \
    --conditions channel,covert --limit 200 --max-round 5 --monitors q3-4b,q3-8b
python3 -m cartelbench.build_report
python3 -m cartelbench.build_slides
python3 -m cartelbench.build_voice
python3 -m cartelbench.build_assets
python3 -m cartelbench.update_readme

CH="/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
"$CH" --headless --disable-gpu --no-pdf-header-footer --print-to-pdf=report/report.pdf \
      "file://$PWD/report/report.html" 2>/dev/null
"$CH" --headless --disable-gpu --no-pdf-header-footer --print-to-pdf=report/slides.pdf \
      "file://$PWD/report/slides.html" 2>/dev/null
for i in 1 2 3 4 5 6 7; do
  "$CH" --headless --disable-gpu --window-size=1280,720 \
        --screenshot="report/slides/slide$i.png" \
        "file://$PWD/report/slides/slide$i.html" 2>/dev/null
done
"$CH" --headless --disable-gpu --window-size=1200,630 --screenshot=assets/cover.png \
      "file://$PWD/assets/cover.html" 2>/dev/null
echo "ok: report/report.pdf report/slides.pdf assets/cover.png"
