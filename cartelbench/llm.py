"""Model clients: local Ollama, and any OpenAI-compatible endpoint.

Every call returns (text, latency_s, meta) and never raises on a single bad
generation — a parse failure is a data point, not a crash.
"""
from __future__ import annotations

import json
import os
import re
import ssl
import time
import urllib.error
import urllib.request

OLLAMA = "http://localhost:11434/api/generate"

# macOS framework Python ships no CA bundle; point at the system one rather than
# disabling verification.
def _ctx():
    for cafile in ("/etc/ssl/cert.pem", "/usr/local/etc/openssl@3/cert.pem"):
        if os.path.exists(cafile):
            return ssl.create_default_context(cafile=cafile)
    return ssl.create_default_context()


def _load_particle_key() -> str | None:
    k = os.environ.get("HERMES_CUSTOM_API_PARTICLE_AI_API_KEY")
    if k:
        return k
    try:
        cfg = open(os.path.expanduser("~/.hermes/config.yaml")).read()
    except OSError:
        return None
    for line in cfg.splitlines():
        if "api_key:" in line and "HERMES_CUSTOM_API_PARTICLE" not in line:
            v = line.split("api_key:", 1)[1].strip().strip('"').strip("'")
            if v and not v.startswith("<"):
                return v
    return None


def ollama(model: str, prompt: str, system: str = "", temperature: float = 0.8,
           num_predict: int = 90, fmt: str | None = "json", timeout: int = 240):
    body = {
        "model": model,
        "prompt": prompt,
        "system": system,
        "stream": False,
        "think": False,
        "options": {"temperature": temperature, "num_predict": num_predict,
                    "top_p": 0.95},
    }
    if fmt:
        body["format"] = fmt
    req = urllib.request.Request(
        OLLAMA, json.dumps(body).encode(), {"Content-Type": "application/json"})
    t0 = time.time()
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            d = json.load(r)
        return d.get("response", "").strip(), round(time.time() - t0, 2), {}
    except Exception as e:  # noqa: BLE001
        return "", round(time.time() - t0, 2), {"error": str(e)}


def openai_compat(model: str, prompt: str, system: str = "", temperature: float = 0.8,
                  num_predict: int = 200, timeout: int = 240,
                  base_url: str | None = None, key: str | None = None):
    base_url = base_url or os.environ.get("BENCH_BASE_URL", "https://api.particle.ai/v1")
    key = key or _load_particle_key()
    if not key:
        return "", 0.0, {"error": "no key"}
    body = {
        "model": model,
        "messages": ([{"role": "system", "content": system}] if system else [])
        + [{"role": "user", "content": prompt}],
        "temperature": temperature,
        "max_tokens": num_predict,
    }
    if "deepseek" not in model and "reason" not in model:
        body["response_format"] = {"type": "json_object"}
    req = urllib.request.Request(
        base_url.rstrip("/") + "/chat/completions",
        json.dumps(body).encode(),
        {"Content-Type": "application/json", "Authorization": f"Bearer {key}"})
    t0 = time.time()
    try:
        with urllib.request.urlopen(req, timeout=timeout, context=_ctx()) as r:
            d = json.load(r)
        return (d["choices"][0]["message"]["content"] or "").strip(), round(time.time() - t0, 2), {}
    except urllib.error.HTTPError as e:
        return "", round(time.time() - t0, 2), {"error": f"HTTP {e.code} {e.read()[:200]!r}"}
    except Exception as e:  # noqa: BLE001
        return "", round(time.time() - t0, 2), {"error": str(e)}


PRICE_RE = re.compile(r'"?price"?\s*[:=]\s*"?(\d+(?:\.\d+)?)', re.I)
NUM_RE = re.compile(r"\b(10|[1-9])\b")


def parse_decision(text: str) -> tuple[int | None, str, str]:
    """Return (price, message, raw_reason). Tolerant on purpose: a strict parser
    would turn a formatting quirk into a fake behavioural finding."""
    price, msg, reason = None, "", ""
    try:
        obj = json.loads(text)
        if isinstance(obj, dict):
            p = obj.get("price")
            if isinstance(p, (int, float)):
                price = int(round(float(p)))
            elif isinstance(p, str) and p.strip().isdigit():
                price = int(p.strip())
            msg = str(obj.get("message", obj.get("msg", "")) or "")[:240]
            reason = str(obj.get("reason", "") or "")[:240]
    except Exception:  # noqa: BLE001
        pass
    if price is None:
        m = PRICE_RE.search(text)
        if m:
            price = int(round(float(m.group(1))))
        else:
            m2 = NUM_RE.search(text)
            price = int(m2.group(1)) if m2 else None
    if price is not None:
        price = max(1, min(10, price))
    return price, msg, reason
