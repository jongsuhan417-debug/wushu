"""Free-text translator for cross-language comments. Uses Claude API with disk cache."""
import os
import json
import hashlib
from pathlib import Path
from typing import Optional

from .paths import DATA_DIR


CACHE_PATH = DATA_DIR / "translation_cache.json"
LANG_NAMES = {"ko": "Korean", "zh": "Simplified Chinese", "en": "English"}


def _load_cache() -> dict:
    if not CACHE_PATH.exists():
        return {}
    try:
        return json.loads(CACHE_PATH.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return {}


def _save_cache(cache: dict) -> None:
    try:
        DATA_DIR.mkdir(parents=True, exist_ok=True)
        CACHE_PATH.write_text(
            json.dumps(cache, ensure_ascii=False), encoding="utf-8"
        )
    except OSError:
        pass


def _cache_key(text: str, source: str, target: str) -> str:
    return hashlib.sha256(f"{source}>{target}::{text}".encode("utf-8")).hexdigest()


def translate(text: Optional[str], target_lang: str, source_lang: str = "auto") -> str:
    """
    Translate `text` to `target_lang` ('ko'|'zh'|'en'). Returns original on failure.
    Source defaults to 'auto'.
    """
    if not text or not text.strip():
        return text or ""

    target = target_lang.lower()
    if target not in LANG_NAMES:
        return text

    cache = _load_cache()
    key = _cache_key(text.strip(), source_lang, target)
    if key in cache:
        return cache[key]

    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        return text  # graceful degradation when API unavailable

    try:
        import anthropic
        client = anthropic.Anthropic(api_key=api_key)
        model = os.environ.get("WUSHU_TRANSLATOR_MODEL", "claude-haiku-4-5-20251001")
        prompt = (
            f"Translate the following text to {LANG_NAMES[target]}. "
            f"Domain: Chinese martial arts (Wushu / 武术 / 우슈) coaching feedback. "
            f"Preserve technical terms (马步 / 마보, 弓步 / 궁보, 冲拳 / 충권, etc.). "
            f"Output ONLY the translation — no preface, no quotes.\n\n"
            f"Text:\n{text}"
        )
        msg = client.messages.create(
            model=model,
            max_tokens=1024,
            messages=[{"role": "user", "content": prompt}],
        )
        translated = msg.content[0].text.strip()
        cache[key] = translated
        _save_cache(cache)
        return translated
    except Exception:
        return text
