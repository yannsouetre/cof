#!/usr/bin/env python3
"""Embeds the personality-profile tables of cof-cli (cli/cof_cli/profiles.py: Myers-Briggs four-letter types, Enneagram types, Big Five)
in the builder, so that the three blocks of « Proposer une psyché » propose exactly what `cof psyche propose --mbti / --enneagram /
--big-five` propose, offline. Rewrites the text between /*profiles:begin*/ and /*profiles:end*/ in builder/index.html (the horoscope
has its own: tools/psyche/zodiac_to_builder.py). `--check` rewrites nothing and exits 1 when the builder is out of date (cli/tests compare the same way)."""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "cli"))
from cof_cli import profiles  # noqa: E402

BUILDER = ROOT / "builder" / "index.html"
SPAN = re.compile(r"/\*profiles:begin\*/(.*?)/\*profiles:end\*/", re.S)


def table() -> dict:
    """The tables as the builder reads them, each candidate as [kind, {en, fr}]."""
    pairs = lambda rows: [[k, g] for k, g in rows]
    return {"mbti": {"types": list(profiles.MBTI_TYPES), "table": {t: pairs(profiles.MBTI_TABLE[t]) for t in profiles.MBTI_TYPES}},
            "enneagram": {"types": list(profiles.ENNEAGRAM_TYPES), "names": profiles.ENNEAGRAM_NAMES, "table": {t: pairs(profiles.ENNEAGRAM_TABLE[t]) for t in profiles.ENNEAGRAM_TYPES}},
            "bigfive": {"traits": list(profiles.TRAITS), "names": profiles.BIGFIVE_NAMES, "high": profiles.HIGH, "low": profiles.LOW,
                        "table": {t: {p: pairs(profiles.BIGFIVE_TABLE[t][p]) for p in ("high", "low")} for t in profiles.TRAITS}}}


def embedded() -> str:
    return "/*profiles:begin*/" + json.dumps(table(), ensure_ascii=False, separators=(",", ":")) + "/*profiles:end*/"


def main(argv: list[str]) -> int:
    html = BUILDER.read_text("utf-8")
    if not SPAN.search(html):
        print("markers /*profiles:begin*/ … /*profiles:end*/ not found in builder/index.html")
        return 2
    new = SPAN.sub(lambda _m: embedded(), html, count=1)
    if "--check" in argv:
        print("builder profile tables up to date" if new == html else "builder profile tables OUT OF DATE — run tools/psyche/profiles_to_builder.py")
        return 0 if new == html else 1
    BUILDER.write_text(new, "utf-8")
    print(f"profile tables embedded in {BUILDER.relative_to(ROOT)} (16 Myers-Briggs types, 9 Enneagram types, Big Five)")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
