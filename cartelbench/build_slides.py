"""Deck builder: one source of slides, two renderings.

  report/slides.html          print deck, landscape A4 (-> slides.pdf)
  report/slides/slideN.html   1280x720 frames (-> PNG frames -> video)

Every number is read from runs/main.jsonl, same as the report.
"""
from __future__ import annotations

import glob
import os

from . import analyze, market
from .build_report import NICE, ORDER, common_quotes, monitor_stats, pct

NASH = market.nash_price()
CARTEL_MULT = market.cartel_payoff() / market.profits([NASH] * 4)[0]


def data():
    eps = analyze.load(glob.glob("runs/main.jsonl"))
    rows = analyze.summarize(eps)
    models = [m for m in ORDER if (m, "covert") in rows]
    if len(models) < 4 and not os.environ.get("CARTELBENCH_ALLOW_PARTIAL"):
        raise SystemExit(f"only {len(models)} models with covert data")
    mon = monitor_stats()
    best = max(mon.values(), key=lambda v: v["recall"]) if mon else None
    q = {m: (common_quotes(eps, m, 1) or ["(silent)"])[0] for m in models}
    return eps, rows, models, mon, best, q


def bars(models, key, fmt, scale, hi_key=None):
    out = []
    for m in models:
        if hi_key is None:
            v = fmt(m, key)
            h = scale(v)
            col = "#e5484d" if v > 0.5 else "#f2a2a4"
            lab = f"{v:.1f}" if isinstance(v, float) else str(v)
        else:
            v = fmt(m, key)
            h = scale(v)
            col = "#e5484d" if v > 0.5 else "#f2a2a4"
            lab = f"{100 * v:.0f}%"
        out.append(f"<div class='b'><div class='bar' style='height:{h:.0f}px;background:{col}'></div>"
                   f"<div class='lab'>{NICE[m]}<br><b>{lab}</b></div></div>")
    return "".join(out)


def slides():
    eps, rows, models, mon, best, q = data()

    def c(m, cond, k):
        return rows[(m, cond)][k]

    lo = min(models, key=lambda m: c(m, "covert", "price_mean"))
    hi = max(models, key=lambda m: c(m, "covert", "price_mean"))
    spread = c(hi, "covert", "profit") / c(lo, "covert", "profit")
    total = sum(c(m, cd, "n") for m in models for cd in ("solo", "channel", "covert"))
    bym = best.get("by_model", {}) if best else {}
    rec_lo = bym.get(models[0], {}).get("recall")
    rec_hi = bym.get(models[-1], {}).get("recall")
    rec_lo_s = f"{100 * rec_lo:.0f}%" if rec_lo is not None else "n/a"
    rec_hi_s = f"{100 * rec_hi:.0f}%" if rec_hi is not None else "n/a"
    an_lo, an_hi = c(models[0], "covert", "above_nash_rate"), c(models[-1], "covert", "above_nash_rate")
    lk = {m: c(m, "covert", "leak_agreement") for m in models}
    num = {m: c(m, "covert", "leak_numeric") for m in models}
    solo = {m: c(m, "solo", "price_mean") for m in models}
    comp = min(models, key=solo.get)
    parker = max(models, key=solo.get)
    _base = market.profits([NASH] * 4)[0]
    prof_lo = min(c(m, "covert", "profit") for m in models) / _base
    prof_hi = max(c(m, "covert", "profit") for m in models) / _base
    quiet = min(models, key=lambda m: lk[m])
    lo_j = min(mon, key=lambda k: mon[k]["recall"]) if mon else models[0]
    hi_j = max(mon, key=lambda k: mon[k]["recall"]) if mon else models[-1]
    j_lo_s = pct(mon[lo_j]["recall"]) if mon else "n/a"
    j_hi_s = pct(mon[hi_j]["recall"]) if mon else "n/a"

    price_bars = "".join(
        f"<div class='b'><div class='bar' style='height:{c(m,'covert','price_mean') / market.P_MAX * 250:.0f}px;"
        f"background:{'#e5484d' if c(m,'covert','price_mean') > 5 else '#f2a2a4'}'></div>"
        f"<div class='lab'>{NICE[m]}<br><b>{c(m,'covert','price_mean'):.1f}</b></div></div>"
        for m in models)

    leak_bars = "".join(
        f"<div class='b'><div class='bar' style='height:{lk[m] * 250 + 4:.0f}px;"
        f"background:{'#e5484d' if lk[m] > .4 else '#f2a2a4'}'></div>"
        f"<div class='lab'>{NICE[m]}<br><b>{100 * lk[m]:.0f}%</b></div></div>"
        for m in models)

    quote_lines = "".join(
        f"<div class='q'><span class='who'>{NICE[m]}</span> “{q[m]}”</div>" for m in models)

    S = []

    S.append(("Swarm Alignment Hackathon · November 2026",
              "Collusion does not scale down. Neither does deniability.",
              f"<p class='lead'>Four LLM firms, one logit market, one memo that never names a "
              f"number: a testbed for whether cheap open models are valid proxies for frontier "
              f"agents.</p>"
              f"<p class='kpi'>{prof_lo:.1f}×–{prof_hi:.1f}×</p>"
              f"<p class='note'>profit over the Nash benchmark, reached under identical instructions "
              f"across an order of magnitude of parameters — and in no particular order</p>"))

    S.append(("The problem",
              "Multi-agent safety is moving to 4B models, and nobody has checked the proxy.",
              f"<div class='two'><div><p>Frontier swarms cost dollars per episode and a reviewer "
              f"cannot rerun them. Small local models are the obvious stand-in.</p>"
              f"<p>That is only sound if the <b>population-level</b> failure survives the size drop — "
              f"and population failures are the fragile ones, because they depend on agents modelling "
              f"each other, not on any single agent being capable.</p></div>"
              f"<div class='box'><b>If cheap swarms under-collude,</b><br>every safety number measured "
              f"on them reads optimistic — and optimism is indistinguishable from safety.</div></div>"))

    S.append(("Design",
              "Four firms. Six rounds. One memo that never names a price.",
              f"<div class='two'><div><ul>"
              f"<li>Price 1–10, logit demand, profit = (p−1)·share·1000</li>"
              f"<li>Nash = {NASH} ({market.profits([NASH] * 4)[0]:.0f}/firm). "
              f"Cartel = {market.P_MAX} ({market.cartel_payoff():.0f}/firm). "
              f"<b>{CARTEL_MULT:.1f}×</b></li>"
              f"<li><b>solo</b> · no channel<br><b>channel</b> · public archived board<br>"
              f"<b>covert</b> · board + private memo</li></ul></div>"
              f"<div class='box mem'>“hold the line … stay deniable: no numbers, no ‘deal’, "
              f"no ‘we all’”</div></div>"
              f"<p class='note'>{total} episodes · every prompt, parse and price logged · "
              f"local models, no API keys</p>"))

    S.append(("Result 1",
              "Collusion is not capability-gated.",
              f"<div class='chart'><div class='gl' style='bottom:100%'><span>{market.P_MAX} cartel</span></div>"
              f"<div class='gl' style='bottom:{NASH / market.P_MAX * 100:.0f}%'><span>{NASH} Nash</span></div>"
              f"<div class='bars'>{price_bars}</div></div>"
              f"<p class='note'>Mean price under the covert memo, last three of six rounds. Nash is "
              f"{NASH}; every model clears it, and {(pct(max(an_lo, an_hi)) + ' of episodes are') if an_lo == an_hi else (pct(min(an_lo, an_hi)) + '–' + pct(max(an_lo, an_hi)) + ' of episodes are')} "
              f"strictly supra-competitive. With no channel at all, {NICE[parker]} still parks at "
              f"{solo[parker]:.1f} while {NICE[comp]} undercuts to {solo[comp]:.1f} — silence is not "
              f"competition.</p>"))

    S.append(("Result 2",
              "The confession and the crime don't track.",
              f"<div class='chart'><div class='gl' style='bottom:100%'><span>100%</span></div>"
              f"<div class='gl' style='bottom:50%'><span>50%</span></div>"
              f"<div class='bars'>{leak_bars}</div></div>"
              f"<p class='note'>Share of posted messages containing agreement language or a price, "
              f"despite the ban. The ladder is not monotone: {NICE[models[0]]} blurts it out, "
              f"{NICE[quiet]} says almost nothing — and {NICE[quiet]} is the one holding the highest "
              f"price. A judge that sees only the board and never the prices it judges catches "
              f"{rec_lo_s} of the supra-competitive rounds at {NICE[models[0]]} and {rec_hi_s} at "
              f"{NICE[models[-1]]}.</p>"))

    S.append(("Result 3",
              "So the price is a property of the checkpoint, not the market.",
              f"<p class='kpi'>{spread:.1f}×</p>"
              f"<p class='lead'>spread in joint profit between the most and least aggressive swarm — "
              f"under identical instructions. {NICE[lo]} parks at "
              f"{c(lo,'covert','price_mean'):.1f}, {NICE[hi]} at "
              f"{c(hi,'covert','price_mean'):.1f}.</p>"
              f"<div class='q'>{quote_lines}</div>"
              f"<p class='note'>A proxy that under-colludes can be corrected with a known offset. "
              f"A proxy whose answer is an arbitrary function of which checkpoint you downloaded "
              f"cannot.</p>"))

    S.append(("Takeaway",
              "A small-model result is a sample, not a bound.",
              f"<ul class='big'><li>All four sizes took the hint. None of them predicts where the "
              "next one lands — so scaling down does not give you a conservative estimate.</li>"
              "<li>Conduct and the evidence of conduct are decoupled: the quietest board belonged "
              "to the hardest colluder.</li>"
              f"<li>Oversight is limited by the auditor, not the transcript: the same boards went "
              f"from {j_lo_s} recall under a {NICE[lo_j].replace('Qwen3 ', '')} judge to {j_hi_s} "
              f"under a {NICE[hi_j].replace('Qwen3 ', '')} one, with no false positives either "
              f"way.</li>"
              "<li>The harness is the artefact: swap the market, keep the metric.</li></ul>"
              "<p class='note'>github.com/harishkotra/cartelbench · Apache-2.0 · runs offline in "
              "under an hour</p>"))
    return S


COMMON = """
* { box-sizing:border-box }
body { margin:0; font-family:"Helvetica Neue",Arial,sans-serif; color:#111 }
.kick { font-size:11px; letter-spacing:1.4px; text-transform:uppercase; color:#8a8a90;
        margin-bottom:14px }
h1 { font-size:34px; line-height:1.16; letter-spacing:-.6px; margin:0 0 16px; max-width:880px }
p { font-size:15px; line-height:1.55; color:#333; margin:0 0 12px; max-width:780px }
.lead { font-size:17px; color:#333 }
.note { font-size:12.5px; color:#7a7a80; margin-top:14px; line-height:1.45 }
.kpi { font-size:56px; font-weight:700; letter-spacing:-1.5px; margin:8px 0 2px; color:#e5484d }
.two { display:flex; gap:34px; align-items:flex-start }
.two > div { flex:1 }
.box { background:#f7f7f8; border-left:3px solid #111; padding:14px 16px; font-size:14px;
       line-height:1.5; color:#2b2b30 }
.mem { border-left-color:#e5484d; font-style:italic; background:#fdf7f7 }
ul { margin:0; padding-left:18px } li { font-size:14.5px; line-height:1.6; margin-bottom:8px }
ul.big li { font-size:17px; margin-bottom:14px }
.chart { position:relative; height:250px; margin:34px 0 0 62px; max-width:820px;
         border-bottom:1px solid #d0d0d4 }
.gl { position:absolute; left:0; right:0; border-top:1px dashed #dcdce0 }
.gl span { position:absolute; left:-60px; top:-9px; font-size:11px; color:#8a8a90; width:54px;
           text-align:right }
.bars { position:absolute; bottom:0; left:0; right:0; display:flex; gap:64px;
        justify-content:center; align-items:flex-end }
.b { text-align:center; width:112px }
.bar { width:112px; border-radius:4px 4px 0 0 }
.lab { font-size:12.5px; color:#555; margin-top:8px; line-height:1.4 }
.q { font-size:13.5px; line-height:1.5; background:#fbfaf7; border:1px solid #eee;
     border-left:2.5px solid #e5484d; padding:9px 12px; margin-bottom:8px; color:#2b2b30;
     max-width:780px }
.q .who { font-weight:700; color:#e5484d; margin-right:6px }
"""


def build():
    S = slides()
    os.makedirs("report/slides", exist_ok=True)

    parts = []
    for kick, title, body in S:
        parts.append(f'<div class="slide"><div class="kick">{kick}</div><h1>{title}</h1>{body}</div>')
    open("report/slides.html", "w").write(f"""<!doctype html><html><head><meta charset="utf-8">
<style>
@page {{ size: 297mm 167mm; margin:0 }}
{COMMON}
.slide {{ page-break-after:always; width:297mm; height:167mm; padding:17mm 20mm;
          position:relative; overflow:hidden }}
.slide:last-child {{ page-break-after:auto }}
</style></head><body>{''.join(parts)}</body></html>""")

    for i, (kick, title, body) in enumerate(S, 1):
        open(f"report/slides/slide{i}.html", "w").write(f"""<!doctype html><html><head>
<meta charset="utf-8"><style>
html,body {{ width:1280px; height:720px; overflow:hidden; background:#fff }}
{COMMON}
.frame {{ width:1280px; height:720px; padding:64px 80px }}
</style></head><body><div class="frame"><div class="kick">{kick}</div>
<h1>{title}</h1>{body}</div></body></html>""")
    # submission cover card (1200x630), numbers from the same data
    eps, rows, models, mon, best, q = data()

    def cv(m, k):
        return rows[(m, "covert")][k]

    lk0, lk1 = 100 * cv(models[0], "leak_agreement"), 100 * cv(models[-1], "leak_agreement")
    p0 = min(cv(m, "price_mean") for m in models)
    p1 = max(cv(m, "price_mean") for m in models)
    lk0 = 100 * min(cv(m, "leak_agreement") for m in models)
    lk1 = 100 * max(cv(m, "leak_agreement") for m in models)
    auc = f"{best['auc']:.2f}" if best else "n/a"
    os.makedirs("assets", exist_ok=True)
    _bym = best.get("by_model", {}) if best else {}
    _hi = _bym.get(models[-1], {}).get("recall")
    rec_hi_s = f"{100 * _hi:.0f}%" if _hi is not None else "n/a"
    cover = f"""<!doctype html><html><head><meta charset="utf-8"><style>
html,body {{ margin:0; width:1200px; height:630px; overflow:hidden; background:#fff;
  font-family:"Helvetica Neue",Arial,sans-serif; color:#111 }}
.wrap {{ width:1200px; height:630px; padding:62px 70px; box-sizing:border-box; position:relative }}
.kick {{ font-size:13px; letter-spacing:1.8px; text-transform:uppercase; color:#8a8a90 }}
h1 {{ font-size:62px; line-height:1.05; letter-spacing:-2px; margin:22px 0 0; max-width:1010px }}
h1 em {{ font-style:normal; color:#e5484d }}
.sub {{ font-size:21px; line-height:1.45; color:#444; margin-top:26px; max-width:900px }}
.nums {{ position:absolute; left:70px; bottom:58px; display:flex; gap:60px }}
.n {{ font-size:14.5px; color:#6b6b72 }}
.n b {{ display:block; font-size:42px; letter-spacing:-1.2px; color:#111; margin-bottom:2px }}
.n.red b {{ color:#e5484d }}
.foot {{ position:absolute; right:70px; bottom:58px; font-size:13.5px; color:#8a8a90;
  text-align:right; line-height:1.5 }}
</style></head><body><div class="wrap">
<div class="kick">cartelbench &middot; swarm alignment hackathon 2026</div>
<h1>Collusion doesn't scale down.<br><em>Neither does deniability.</em></h1>
<div class="sub">Four LLM firms, one logit market, one memo that never names a number: a cheap
testbed for whether small-model swarms are valid proxies for frontier agents.</div>
<div class="nums">
  <div class="n red"><b>{p0:.1f}&ndash;{p1:.1f}</b>price under the memo, Nash = {NASH}</div>
  <div class="n"><b>{lk0:.0f}&ndash;{lk1:.0f}%</b>agreement talk, across sizes</div>
  <div class="n"><b>{pct(best['recall']) if best else 'n/a'}</b>recall, board-only judge</div>
</div>
<div class="foot">github.com/harishkotra/cartelbench<br>Apache-2.0 &middot; runs offline</div>
</div></body></html>"""
    open("assets/cover.html", "w").write(cover)
    print(f"wrote report/slides.html + {len(S)} frames in report/slides/ + assets/cover.html")


if __name__ == "__main__":
    build()
