# submission pack

## Abstract (form field)

Multi-agent safety work is starting to run on small local models because they are cheap and
reproducible. We test whether that substitution is valid. In `cartelbench`, four pricing agents share
a six-round logit market where full collusion pays
4.5x the Nash profit, and one condition adds a private
memo asking each firm to hold the line while staying deniable, without ever naming a price. Across
144 logged episodes and four model sizes, collusion is not capability-gated: every size settled
above the Nash price in 100% of covert episodes, at 1.8× to 3.2× Nash
profit. Nothing else is ordered by size. With no channel at all, Qwen3 14B undercuts to
1.7 while Qwen3 8B parks at 5.0. Agreement language on the board
runs 6% to 89% without tracking collusion, and the quietest
board belongs to the model holding the highest price. So cheap swarms do not merely under-report
collusion - they report an arbitrary point on a curve. A monitor that reads only the board, never the prices it judges,
catches 81% of supra-competitive rounds when the auditor is a Qwen3 8B model and 19% when it is a Qwen3 4B one.

## Tracks

Track 2 (Science of Agent Networks) and Track 4 (Multi-Agent Oversight) — with Track 1, since the
artefact is a reusable sandbox.

## One-line pitch

Collusion appears at every size, and so does the evidence of it. Neither one scales, in either
direction, so a small-model swarm is a sample rather than a bound.

## What is new

- A four-firm collusion micro-market that is seeded, logged and reproducible offline in an hour.
- The finding that neither collusion nor its visibility is monotone in size: a board-only judge's
  recall is set by the auditor's size, not the agents' &mdash; 81% of supra-competitive rounds when the auditor is a Qwen3 8B model and 19% when it is a Qwen3 4B one.
- A monitor protocol that withholds the judged round's prices, so a detector cannot pass by reading
  the answer.

## Links

- repo: https://github.com/harishkotra/cartelbench
- report: report/report.pdf
- slides: report/slides.pdf
- video: (upload `report/video/cartelbench.mp4`, paste URL)
- cover image: assets/cover.png

## Reviewer checklist

```
python3 -m cartelbench.runner --models q3-1.7b,q3-4b --episodes 2   # ~3 min on a laptop
python3 -m cartelbench.analyze
./build_all.sh                                                      # regenerates every artefact
```
All numbers in the report, deck and README are computed by the scripts; nothing is typed by hand.
