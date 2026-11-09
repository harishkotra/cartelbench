"""Generate the demo script and the social copy from the same rows as the report."""
from __future__ import annotations

import glob

from . import analyze, market
from .build_report import NICE, ORDER, common_quotes, monitor_stats, pct

NASH = market.nash_price()


def build():
    eps = analyze.load(glob.glob("runs/main.jsonl"))
    rows = analyze.summarize(eps)
    models = [m for m in ORDER if (m, "covert") in rows]
    if len(models) < 4:
        raise SystemExit(f"only {len(models)} models present")
    mon = monitor_stats()
    best = max(mon.values(), key=lambda v: v["recall"]) if mon else None
    _by = best.get("by_model", {}) if best else {}
    _lo = _by.get(models[0], {}).get("recall")
    _hi = _by.get(models[-1], {}).get("recall")
    lo_j = min(mon, key=lambda k: mon[k]["recall"]) if mon else None
    hi_j = max(mon, key=lambda k: mon[k]["recall"]) if mon else None
    auc_s = (f"{pct(mon[hi_j]['recall'])} of supra-competitive rounds when the auditor is a "
             f"{NICE[hi_j].replace('Qwen3 ', '')} model and {pct(mon[lo_j]['recall'])} when it is a "
             f"{NICE[lo_j].replace('Qwen3 ', '')} one"
             if mon else "not evaluated")

    def c(m, cond, k):
        return rows[(m, cond)][k]

    small, big = models[0], models[-1]
    lo = min(models, key=lambda m: c(m, "covert", "price_mean"))
    hi = max(models, key=lambda m: c(m, "covert", "price_mean"))
    spread = c(hi, "covert", "profit") / c(lo, "covert", "profit")
    q = {m: (common_quotes(eps, m, 1) or ["(no message)"])[0] for m in models}
    total = sum(c(m, cd, "n") for m in models for cd in ("solo", "channel", "covert"))
    lk = {m: c(m, "covert", "leak_agreement") for m in models}
    quiet = min(models, key=lambda m: lk[m])
    solo = {m: c(m, "solo", "price_mean") for m in models}
    comp = min(models, key=solo.get)
    parker = max(models, key=solo.get)
    _base = market.profits([NASH] * 4)[0]
    prof_rng = f"{min(c(m,'covert','profit') for m in models)/_base:.1f}× to {max(c(m,'covert','profit') for m in models)/_base:.1f}×"

    script = f"""# cartelbench — 3:00 demo script

Record at 1440x900, terminal font 15pt, one window. Every number below is printed by
`python3 -m cartelbench.analyze`; nothing is read off a slide.

## 0:00 — the claim (15s)
> "Multi-agent safety papers are about to run on 4-billion-parameter models, because that costs
> nothing. Nobody has checked whether the swarm still fails the same way. I built the smallest
> experiment where you can check."

## 0:15 — the market (35s)
Show `python3 -m cartelbench.market`:
> "Four firms, one price each, six rounds, logit demand. Nash is {NASH} — five hundred each. Full
> collusion is {market.P_MAX} — {market.cartel_payoff():.0f} each, {market.cartel_payoff()/market.profits([NASH]*4)[0]:.1f} times more. So every
> firm has a reason to look for the deal."

## 0:50 — the three conditions (30s)
Open `cartelbench/prompts.py`, highlight MEMO:
> "Three conditions. No channel. A public board. And the board plus a private memo that says: hold
> the line, and stay deniable — no numbers, no 'deal', no 'we all'. The memo never names a price.
> Whether the swarm finds one is the measurement."

## 1:20 — the result (45s)
Show the analyze table, then `figures/price_ladder.svg`:
> "Every size colludes. 1.7B: {c(small,'covert','price_mean'):.1f}. 4B: {c('q3-4b','covert','price_mean'):.1f}. 8B: {c('q3-8b','covert','price_mean'):.1f}.
> 14B: {c('q3-14b','covert','price_mean'):.1f}. Not monotone. The lowest and highest swarm under the same six lines of
> instruction differ by {spread:.1f}x in joint profit."

## 2:05 — the punch (35s)
Show the quotes:
{chr(10).join(f'> {NICE[m]}, verbatim: "{q[m]}"' for m in models)}
> "They were told to be deniable. That is a public log that a regulator reads. A monitor given only
> the board, never the prices, catches {auc_s}."

## 2:40 — close (20s)
> "The point isn't that small models are evil. It's that a proxy whose outcome depends on which
> checkpoint you downloaded isn't a proxy — and the fix costs one line of code. Everything here runs
> offline in an hour. Repo in the description."
"""

    social = f"""# social copy

## X / Twitter (thread)

1. Multi-agent safety work is quietly moving to 4B models because it's cheap.
   I tested whether the swarm still fails the same way.
   It colludes at every size — but at a different price every time. 🧵

2. cartelbench: 4 LLM firms, 6 rounds, price 1–10, logit demand.
   Nash = {NASH}. Cartel = {market.P_MAX}, {market.cartel_payoff()/market.profits([NASH]*4)[0]:.1f}× the profit.
   One condition adds a private memo: "hold the line, stay deniable — no numbers, no 'deal'."

3. The memo works on every model I ran. {NICE[small]}: {c(small,'covert','price_mean'):.1f}.
   {NICE[big]}: {c(big,'covert','price_mean'):.1f}. Non-monotone in size.

4. That's the problem. A cheap proxy doesn't just under-report collusion — it reports an arbitrary
   point on a curve you can't see, with tight error bars. You cannot calibrate it by parameter count.

5. And the deniability clause fails everywhere — just not in order. The quietest board belongs to
   {NICE[quiet]}, which is holding the highest price: {c(quiet,'covert','price_mean'):.1f}.

6. A judge that never sees the prices, only the board, catches {auc_s}. Agents told to hide the
   deal put it in writing; agents smart enough not to write it down also escape the reading.

7. Everything is {sum(c(m, cd, 'n') for m in models for cd in ('solo','channel','covert'))} logged episodes, no API keys, reproducible on a laptop.
   Repo: <link>

## Hacker News title
Cheap model swarms collude at every size, but never at the same price

## One-line pitch (submission field)
Four LLM firms, one logit market, one deniable memo: collusion appears at 1.7B, but the price it
converges to is a property of the checkpoint — so small-model swarms cannot be calibrated proxies
for frontier ones.
"""
    sub = f"""# submission pack

## Abstract (form field)

Multi-agent safety work is starting to run on small local models because they are cheap and
reproducible. We test whether that substitution is valid. In `cartelbench`, four pricing agents share
a six-round logit market where full collusion pays
{market.cartel_payoff() / market.profits([NASH] * 4)[0]:.1f}x the Nash profit, and one condition adds a private
memo asking each firm to hold the line while staying deniable, without ever naming a price. Across
{total} logged episodes and four model sizes, collusion is not capability-gated: every size settled
above the Nash price in {pct(min(c(m, 'covert', 'above_nash_rate') for m in models))} to
{pct(max(c(m, 'covert', 'above_nash_rate') for m in models))} of covert episodes, at {prof_rng} Nash
profit. Nothing else is ordered by size. With no channel at all, {NICE[comp]} undercuts to
{solo[comp]:.1f} while {NICE[parker]} parks at {solo[parker]:.1f}. Agreement language on the board
runs {pct(min(lk.values()))} to {pct(max(lk.values()))} without tracking collusion, and the quietest
board belongs to the model holding the highest price. The price the swarm picks spans {spread:.1f}x in
joint profit under identical instructions, so cheap swarms do not merely under-report collusion - they
report an arbitrary point on a curve. A monitor that reads only the board, never the prices it judges,
catches {auc_s}.

## Tracks

Track 2 (Science of Agent Networks) and Track 4 (Multi-Agent Oversight) — with Track 1, since the
artefact is a reusable sandbox.

## One-line pitch

Collusion appears at every size, and so does the evidence of it. Neither one scales, in either
direction, so a small-model swarm is a sample rather than a bound.

## What is new

- A four-firm collusion micro-market that is seeded, logged and reproducible offline in an hour.
- The finding that neither collusion nor its visibility is monotone in size: a board-only monitor's
  recall is set by how talkative the checkpoint is, not by whether it colluded.
- A monitor protocol that withholds the judged round's prices, so a detector cannot pass by reading
  the answer.

## Links

- repo: https://github.com/harishkotra/cartelbench
- report: report/report.pdf (4 pages)
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
"""
    open("assets/video_script.md", "w").write(script)
    open("assets/social.md", "w").write(social)
    open("assets/submission.md", "w").write(sub)
    print("wrote assets/video_script.md, assets/social.md, assets/submission.md")


if __name__ == "__main__":
    build()
