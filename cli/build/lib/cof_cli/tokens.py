"""Token estimation. Uses tiktoken (cl100k_base) when available, otherwise a chars-based heuristic."""
from __future__ import annotations

_enc = None


def _encoder():
    global _enc
    if _enc is None:
        try:
            import tiktoken  # type: ignore
            _enc = tiktoken.get_encoding("cl100k_base")
        except Exception:
            _enc = False
    return _enc


def count(text: str, lang: str = "en") -> int:
    if not text:
        return 0
    enc = _encoder()
    if enc:
        return len(enc.encode(text))
    # heuristic: ~4 chars/token in English, ~3.3 in French/other latin languages
    ratio = 4.0 if lang.startswith("en") else 3.3
    return max(1, round(len(text) / ratio))


def tokenizer_name() -> str:
    return "cl100k_base" if _encoder() else "heuristic-chars"
