#!/usr/bin/env python3
"""Embeds the horoscope table of cof-cli (cli/cof_cli/zodiac.py) in the builder, so that « Depuis un signe astrologique » proposes
exactly what `cof psyche propose --zodiac` proposes, offline. Rewrites the text between /*zodiac:begin*/ and /*zodiac:end*/ in
builder/index.html. `--check` rewrites nothing and exits 1 when the builder is out of date (cli/tests compare the same way)."""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "cli"))
from cof_cli import zodiac  # noqa: E402

BUILDER = ROOT / "builder" / "index.html"
SPAN = re.compile(r"/\*zodiac:begin\*/(.*?)/\*zodiac:end\*/", re.S)


def table() -> dict:
    """{signs, names, table}: the table as the builder reads it, each candidate as [kind, {en, fr}]."""
    return {"signs": list(zodiac.SIGNS), "names": zodiac.NAMES, "table": {s: [[k, g] for k, g in zodiac.TABLE[s]] for s in zodiac.SIGNS}}


def embedded(html: str) -> str:
    return "/*zodiac:begin*/" + json.dumps(table(), ensure_ascii=False, separators=(",", ":")) + "/*zodiac:end*/"


def main(argv: list[str]) -> int:
    html = BUILDER.read_text("utf-8")
    if not SPAN.search(html):
        print("markers /*zodiac:begin*/ … /*zodiac:end*/ not found in builder/index.html")
        return 2
    new = SPAN.sub(lambda _m: embedded(html), html, count=1)
    if "--check" in argv:
        print("builder table up to date" if new == html else "builder table OUT OF DATE — run tools/psyche/zodiac_to_builder.py")
        return 0 if new == html else 1
    BUILDER.write_text(new, "utf-8")
    print(f"zodiac table embedded in {BUILDER.relative_to(ROOT)} ({len(zodiac.SIGNS)} signs)")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
