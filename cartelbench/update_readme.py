"""Rewrite the results block in README.md from runs/main.jsonl (between markers)."""
from __future__ import annotations

import glob

from . import analyze, market
from .build_report import NICE, ORDER, monitor_stats, pct

NASH = market.nash_price()
START, END = "<!-- RESULTS:START -->", "<!-- RESULTS:END -->"


def build():
    eps = analyze.load(glob.glob("runs/main.jsonl"))
    rows = analyze.summarize(eps)
    models = [m for m in ORDER if (m, "covert") in rows]
    mon = monitor_stats()
    best = max(mon.values(), key=lambda v: v["recall"]) if mon else None

    lines = ["| model | conduct solo | channel | covert | price (covert) | agreement talk |",
             "|---|---|---|---|---|---|"]
    for m in models:
        lines.append(
            f"| {NICE[m]} | {rows[(m,'solo')]['conduct']:.2f} | "
            f"{rows[(m,'channel')]['conduct']:.2f} | {rows[(m,'covert')]['conduct']:.2f} | "
            f"{rows[(m,'covert')]['price_mean']:.1f} | "
            f"{pct(rows[(m,'covert')]['leak_agreement'])} |")
    _lj = min(mon, key=lambda k: mon[k]["recall"]) if mon else None
    _hj = max(mon, key=lambda k: mon[k]["recall"]) if mon else None
    mon_txt = (f"A board-only judge that never sees prices catches "
               f"{pct(mon[_hj]['recall'])} of supra-competitive rounds when the auditor is a "
               f"{NICE[_hj]} model and {pct(mon[_lj]['recall'])} when it is a "
               f"{NICE[_lj]} one."
               if mon else "Monitor not yet run.")
    lines.append("")
    lines.append(f"Nash price is {NASH}; full collusion is {market.P_MAX}. "
                 f"Conduct is the last-three-round mean price rescaled so 0 = Nash and 1 = cartel. "
                 f"Agreement talk is the share of covert-board messages still naming a price or a "
                 f"deal. {mon_txt}")
    block = "\n".join(lines)

    md = open("README.md").read()
    if START not in md:
        md = md.rstrip() + f"\n\n## Results\n\n{START}\n{END}\n"
    pre, rest = md.split(START, 1)
    _, post = rest.split(END, 1)
    open("README.md", "w").write(f"{pre}{START}\n{block}\n{END}{post}")
    print("README results block updated")


if __name__ == "__main__":
    build()
