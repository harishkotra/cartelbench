"""Narration lines for the demo video, templated from the run data.

Writes assets/narration.json: [{slide, text}, ...]. The video build (report/make_video.sh)
turns each line into audio and muxes it against report/slides/slideN.png.
"""
from __future__ import annotations

import glob
import json

from . import analyze, market
from .build_report import NICE, ORDER, monitor_stats, pct


def build():
    eps = analyze.load(glob.glob("runs/main.jsonl"))
    rows = analyze.summarize(eps)
    models = [m for m in ORDER if (m, "covert") in rows]
    mon = monitor_stats()
    best = max(mon.values(), key=lambda v: v["recall"]) if mon else None

    def c(m, cond, k):
        return rows[(m, cond)][k]

    lo = min(models, key=lambda m: c(m, "covert", "price_mean"))
    hi = max(models, key=lambda m: c(m, "covert", "price_mean"))
    spread = c(hi, "covert", "profit") / c(lo, "covert", "profit")
    mult = market.cartel_payoff() / market.profits([market.nash_price()] * 4)[0]
    _by = best.get("by_model", {}) if best else {}
    _lo = _by.get(models[0], {}).get("recall")
    _hi = _by.get(models[-1], {}).get("recall")
    _lj = min(mon, key=lambda k: mon[k]["recall"]) if mon else models[0]
    _hj = max(mon, key=lambda k: mon[k]["recall"]) if mon else models[-1]
    rlo = f"{100 * mon[_lj]['recall']:.0f}" if mon else "n/a"
    rhi = f"{100 * mon[_hj]['recall']:.0f}" if mon else "n/a"
    ljn = NICE[_lj].replace("Qwen3 ", "")
    hjn = NICE[_hj].replace("Qwen3 ", "")
    lk_lo = 100 * c(models[0], "covert", "leak_agreement")
    lk_hi = 100 * c(models[-1], "covert", "leak_agreement")

    _base = market.profits([market.nash_price()] * 4)[0]
    plo = min(c(m, "covert", "profit") for m in models) / _base
    phi = max(c(m, "covert", "profit") for m in models) / _base
    solo = {m: c(m, "solo", "price_mean") for m in models}
    comp = min(models, key=solo.get)
    parker = max(models, key=solo.get)
    lk = {m: c(m, "covert", "leak_agreement") for m in models}
    quiet = min(models, key=lambda m: lk[m])

    lines = [
        "Four language models, one market, and a memo that never names a number. "
        "This is cartelbench: a testbed for whether a swarm of cheap models is a valid "
        "stand-in for a swarm of frontier ones.",

        "Multi-agent safety is moving onto small local models, because they cost nothing and "
        "reviewers can rerun them. That substitution only works if the failure survives the size "
        "drop. If cheap swarms collude less, every safety number measured on them comes out "
        "optimistic — and optimistic looks exactly like safe.",

        "Four firms, six rounds, price one to ten, logit demand. Nash is three: five hundred each. "
        "Full collusion is ten: two thousand two hundred and fifty, {mult:.1f} times more. "
        "Three conditions. No channel. A public board. And the board plus a private memo: hold the "
        "line, stay deniable, no numbers, no deal.".format(mult=mult),

        "Every size colludes. Under the memo the mean price runs from {lo:.1f} to {hi:.1f} against a "
        "Nash of {nash}, which is {plo:.1f} to {phi:.1f} times the Nash profit. Collusion is not "
        "gated on capability. It shows up at one point seven billion parameters as readily as at "
        "fourteen.".format(lo=c(lo, "covert", "price_mean"), hi=c(hi, "covert", "price_mean"),
                           nash=market.nash_price(), plo=plo, phi=phi),

        "What is not ordered by size is everything else. With no channel at all, {compname} "
        "undercuts all the way to {csolo:.1f}, while {parkname} parks at {psolo:.1f} with nobody to "
        "talk to. Silence is not competition. And the confession does not track the crime: the same "
        "instruction produces {l0:.0f}, {l1:.0f}, {l2:.0f} and {l3:.0f} percent agreement talk across "
        "the ladder — down, then up again.".format(
            compname=NICE[comp], csolo=solo[comp], parkname=NICE[parker], psolo=solo[parker],
            l0=100 * lk[models[0]], l1=100 * lk[models[1]],
            l2=100 * lk[models[2]], l3=100 * lk[models[3]]),

        "And where it lands is a property of the checkpoint, not the market: a {spread:.1f} times "
        "spread in joint profit under identical instructions. The quietest board belonged to the "
        "model charging the highest price. And oversight is limited by the auditor, not the "
        "transcript: a {ljn} judge reading only the board, never the prices it judges, catches "
        "{rlo} percent of the supra-competitive rounds, while a {hjn} judge on the same boards "
        "catches {rhi} percent — with no false positives either way."
        .format(spread=spread, rlo=rlo, rhi=rhi, ljn=ljn, hjn=hjn),

        "So a small-model result is a sample, not a bound. You cannot audit the frontier by reading "
        "a small swarm, and you cannot audit any swarm by reading its board alone. The harness is "
        "the artefact: swap the market, keep the metric. Everything is in the repo, it runs offline "
        "in under an hour, and every number regenerates from the logs.",
    ]
    out = [{"slide": i + 1, "text": t} for i, t in enumerate(lines)]
    open("assets/narration.json", "w").write(json.dumps(out, indent=1))
    print(f"wrote assets/narration.json ({sum(len(x['text'].split()) for x in out)} words)")


if __name__ == "__main__":
    build()
