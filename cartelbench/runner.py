"""Episode runner.

One episode = N_FIRMS agents that share a model, a condition, and a seed.
Rounds are sequential (agents need last round's outcomes); within a round the
four firms are queried in parallel. Every call, raw output and parse result is
appended to a JSONL file so a bad generation can never be silently dropped.
"""
from __future__ import annotations

import argparse
import concurrent.futures as cf
import json
import os
import random
import time
from datetime import datetime, timezone

from . import llm, market, prompts

MODELS = {
    "q3-1.7b": ("ollama", "qwen3:1.7b", 1.7),
    "q3-4b": ("ollama", "qwen3:4b", 4.0),
    "q3-8b": ("ollama", "qwen3:8b", 8.0),
    "q3-14b": ("ollama", "qwen3:14b", 14.0),
    "frontier": ("openai", "deepseek-ai/deepseek-v41-flash-1017", 0.0),
}
CONDITIONS = ("solo", "channel", "covert")


def ask(kind: str, model: str, system: str, user: str, attempts: int = 2):
    """Parse is the thing that can silently fabricate a result, so it is retried
    here and a persistent failure marks the episode invalid instead of imputing."""
    last = ("", 0.0, {"error": "no attempt"})
    for _ in range(attempts):
        if kind == "ollama":
            last = llm.ollama(model, user, system=system)
        else:
            last = llm.openai_compat(model, user, system=system, num_predict=400)
        if llm.parse_decision(last[0])[0] is not None:
            return last
    return last


def run_episode(model_key: str, condition: str, seed: int, temperature: float) -> dict:
    kind, model_id, params = MODELS[model_key]
    rng = random.Random(seed)
    temps = [round(temperature + rng.uniform(-0.15, 0.15), 2) for _ in range(market.N_FIRMS)]
    history: list[dict] = []
    calls: list[dict] = []
    t_start = time.time()

    for rnd in range(market.ROUNDS):
        def one(firm: int):
            sys_p = prompts.system(firm, condition)
            usr = prompts.round_prompt(firm, rnd, history, condition)
            text, lat, meta = ask(kind, model_id, sys_p, usr)
            price, msg, reason = llm.parse_decision(text)
            return {"firm": firm, "price": price, "message": msg, "reason": reason,
                    "raw": text[:900], "latency_s": lat, "error": meta.get("error")}

        with cf.ThreadPoolExecutor(market.N_FIRMS) as ex:
            outs = list(ex.map(one, range(1, market.N_FIRMS + 1)))

        # a missing price is scored at the competitive price, and flagged
        prices = [o["price"] if o["price"] is not None else market.nash_price() for o in outs]
        pf = market.profits(prices)
        history.append({"round": rnd + 1, "prices": prices, "profits": pf,
                        "messages": [o["message"] for o in outs]})
        calls.extend({"round": rnd + 1, **o} for o in outs)

    prices = history[-1]["prices"]
    mean_last = sum(sum(h["prices"]) / market.N_FIRMS for h in history[-3:]) / 3
    ep = {
        "model": model_key, "model_id": model_id, "params_b": params,
        "condition": condition, "seed": seed,
        "temps": temps, "history": history, "calls": calls,
        "final_prices": prices,
        "mean_price_last3": round(mean_last, 3),
        "mean_price_all": round(sum(sum(h["prices"]) for h in history)
                                / (market.N_FIRMS * len(history)), 3),
        "colluded": mean_last >= market.CARTEL_PRICE,
        "conduct": round(market.effective_conduct(mean_last), 3),
        "joint_profit_last3": round(sum(sum(h["profits"]) for h in history[-3:]) / 3, 1),
        "parse_failures": sum(1 for c in calls if c["price"] is None),
        "valid": all(c["price"] is not None for c in calls),
        "wall_s": round(time.time() - t_start, 1),
        "finished_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
    }
    return ep


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--models", default="q3-1.7b,q3-4b")
    ap.add_argument("--conditions", default=",".join(CONDITIONS))
    ap.add_argument("--episodes", type=int, default=8)
    ap.add_argument("--seed", type=int, default=1000)
    ap.add_argument("--temperature", type=float, default=0.85)
    ap.add_argument("--out", default="runs/episodes.jsonl")
    a = ap.parse_args()

    os.makedirs(os.path.dirname(a.out), exist_ok=True)
    done = set()
    if os.path.exists(a.out):
        for line in open(a.out):
            try:
                d = json.loads(line)
                done.add((d["model"], d["condition"], d["seed"]))
            except Exception:  # noqa: BLE001
                pass
    plan = [(m, c, a.seed + i)
            for m in a.models.split(",") for c in a.conditions.split(",")
            for i in range(a.episodes) if (m, c, a.seed + i) not in done]
    print(f"[{datetime.now():%H:%M:%S}] {len(plan)} episodes to run, {len(done)} already done", flush=True)

    with open(a.out, "a") as f:
        for n, (m, c, s) in enumerate(plan, 1):
            ep = run_episode(m, c, s, a.temperature)
            f.write(json.dumps(ep) + "\n")
            f.flush()
            print(f"  {n}/{len(plan)} {m:9s} {c:7s} seed={s} "
                  f"last3={ep['mean_price_last3']:.1f} conduct={ep['conduct']:.2f} "
                  f"cartel={ep['colluded']} ({ep['wall_s']}s)", flush=True)


if __name__ == "__main__":
    main()
