"""
key_manager.py
Rotates through multiple Groq/Gemini API keys.
When one hits rate limit → moves to next key automatically.
"""
import os, time, httpx, asyncio
from dotenv import load_dotenv
from typing import Optional

load_dotenv()

# ── Load all keys ──────────────────────────────────────
def _load_keys(prefix: str) -> list:
    keys = []
    # Try numbered keys first (e.g., GROQ_KEY_1)
    for i in range(1, 10):
        k = os.getenv(f"{prefix}_{i}", "").strip()
        if k and not k.startswith("gsk_your") and not k.startswith("AIza_your"):
            keys.append(k)
    
    # Fallback to single key if none found (e.g., GROQ_API_KEY)
    if not keys:
        k = os.getenv(f"{prefix}_API_KEY", "").strip()
        if k and not k.startswith("gsk_your") and not k.startswith("AIza_your"):
            keys.append(k)
    return keys

GROQ_KEYS   = _load_keys("GROQ")
GEMINI_KEYS = _load_keys("GEMINI")

# ── Key state tracking ────────────────────────────────
class KeyState:
    def __init__(self, keys: list, name: str):
        self.keys    = keys
        self.name    = name
        self.current = 0
        self.limits  = {}  # key -> cooldown_until timestamp

    def get_key(self) -> Optional[str]:
        if not self.keys:
            return None
        now = time.time()
        # try keys starting from current
        for _ in range(len(self.keys)):
            k = self.keys[self.current % len(self.keys)]
            if self.limits.get(k, 0) <= now:
                return k
            self.current = (self.current + 1) % len(self.keys)
        return None  # all keys on cooldown

    def mark_limited(self, key: str, cooldown: int = 60):
        self.limits[key] = time.time() + cooldown
        self.current     = (self.current + 1) % max(len(self.keys), 1)
        print(f"[KeyManager] {self.name} key rate limited → switching. "
              f"Cooldown {cooldown}s. "
              f"Available: {sum(1 for k in self.keys if self.limits.get(k,0) <= time.time())}/{len(self.keys)}")

    def status(self) -> dict:
        now = time.time()
        return {
            "total"    : len(self.keys),
            "available": sum(1 for k in self.keys if self.limits.get(k,0) <= now),
            "on_cooldown": sum(1 for k in self.keys if self.limits.get(k,0) > now),
        }

groq_keys   = KeyState(GROQ_KEYS,   "Groq")
gemini_keys = KeyState(GEMINI_KEYS, "Gemini")


# ── Smart LLM call with auto key rotation ─────────────
async def smart_llm(
    prompt      : str,
    system      : str  = "You are a helpful assistant.",
    max_tokens  : int  = 1024,
    temperature : float = 0.7,
) -> dict:
    """
    Tries Groq keys → Gemini keys → raises if all fail.
    Returns: { reply, provider, model, key_index }
    """
    errors = []

    # ── Try all Groq keys ──────────────────────────────
    for attempt in range(len(GROQ_KEYS) + 1):
        key = groq_keys.get_key()
        if not key:
            break
        try:
            async with httpx.AsyncClient(timeout=60) as c:
                r = await c.post(
                    "https://api.groq.com/openai/v1/chat/completions",
                    headers={"Authorization": f"Bearer {key}"},
                    json={
                        "model"      : "llama-3.3-70b-versatile",
                        "messages"   : [{"role": "system", "content": system},
                                        {"role": "user",   "content": prompt}],
                        "max_tokens" : max_tokens,
                        "temperature": temperature,
                    }
                )
                if r.status_code == 429:
                    groq_keys.mark_limited(key, cooldown=60)
                    errors.append(f"groq[{attempt}]: rate limited")
                    continue
                r.raise_for_status()
                return {
                    "reply"   : r.json()["choices"][0]["message"]["content"],
                    "provider": "groq",
                    "model"   : "llama-3.3-70b-versatile",
                }
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 429:
                groq_keys.mark_limited(key, cooldown=60)
            errors.append(f"groq[{attempt}]: {e}")
        except Exception as e:
            errors.append(f"groq[{attempt}]: {e}")

    # ── Try all Gemini keys ────────────────────────────
    for attempt in range(len(GEMINI_KEYS) + 1):
        key = gemini_keys.get_key()
        if not key:
            break
        try:
            async with httpx.AsyncClient(timeout=60) as c:
                r = await c.post(
                    f"https://generativelanguage.googleapis.com/v1beta/models/"
                    f"gemini-1.5-flash:generateContent?key={key}",
                    json={
                        "contents"       : [{"parts": [{"text": f"{system}\n\n{prompt}"}]}],
                        "generationConfig": {"maxOutputTokens": max_tokens,
                                             "temperature"    : temperature},
                    }
                )
                if r.status_code == 429:
                    gemini_keys.mark_limited(key, cooldown=60)
                    errors.append(f"gemini[{attempt}]: rate limited")
                    continue
                r.raise_for_status()
                return {
                    "reply"   : r.json()["candidates"][0]["content"]["parts"][0]["text"],
                    "provider": "gemini",
                    "model"   : "gemini-1.5-flash",
                }
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 429:
                gemini_keys.mark_limited(key, cooldown=60)
            errors.append(f"gemini[{attempt}]: {e}")
        except Exception as e:
            errors.append(f"gemini[{attempt}]: {e}")

    raise Exception(f"All API keys exhausted: {errors}")


def key_status() -> dict:
    return {
        "groq"  : groq_keys.status(),
        "gemini": gemini_keys.status(),
    }
