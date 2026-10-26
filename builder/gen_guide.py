#!/usr/bin/env python3
"""Regenerates the advanced-version guide from guide_src.py:
- the `const GUIDE=…,GUIDE_UI=…;` line of builder/index.html (the 📖 Guide window, six languages);
- docs/builder-guide.md (EN) and docs/builder-guide.fr.md (FR).
Run from anywhere: python3 builder/gen_guide.py
"""
import json
import re
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
ns = {}
exec((HERE / "guide_src.py").read_text("utf-8"), ns)
G, UI, LANGS = ns["G"], ns["UI"], ns["LANGS"]


def html_of(blocks):
    out = []
    for kind, body in blocks:
        if kind == "p":
            out.append(f"<p>{body}</p>")
        else:
            out.append("<ul>" + "".join(f"<li>{x}</li>" for x in body) + "</ul>")
    return "".join(out)


def md_of(text):
    text = re.sub(r"<b>(.*?)</b>", r"**\1**", text)
    text = re.sub(r"<code>(.*?)</code>", r"`\1`", text)
    return text


guide = {lang: [{"t": title, "h": html_of(blocks)} for title, blocks in G[lang]] for lang in LANGS}
ui = {lang: {k: v[i] for k, v in UI.items()} for i, lang in enumerate(LANGS)}
line = "const GUIDE=" + json.dumps(guide, ensure_ascii=False, separators=(",", ":")) + ",GUIDE_UI=" + json.dumps(ui, ensure_ascii=False, separators=(",", ":")) + ";"

idx = ROOT / "builder/index.html"
s = idx.read_text("utf-8")
new, n = re.subn(r"^const GUIDE=\{.*?\},GUIDE_UI=\{.*?\};$", lambda m: line, s, count=1, flags=re.M)
assert n == 1, "const GUIDE line not found"
idx.write_text(new, "utf-8")

HEAD = {
    "en": "# Builder guide — advanced version\n\n*The same guide opens from the **📖 Guide** button of the builder in advanced version. Source: `builder/guide_src.py` (it also feeds the builder window, in six languages).*\n\nFrançais : [builder-guide.fr.md](builder-guide.fr.md)\n",
    "fr": "# Guide du builder — version avancée\n\n*Le même guide s'ouvre avec le bouton **📖 Guide** du builder en version avancée. Source : `builder/guide_src.py` (elle alimente aussi la fenêtre du builder, en six langues).*\n\nEnglish: [builder-guide.md](builder-guide.md)\n",
}
for lang, name in (("en", "builder-guide.md"), ("fr", "builder-guide.fr.md")):
    parts = [HEAD[lang]]
    for i, (title, blocks) in enumerate(G[lang], 1):
        parts.append(f"\n## {i}. {title}\n")
        for kind, body in blocks:
            if kind == "p":
                parts.append("\n" + md_of(body) + "\n")
            else:
                parts.append("\n" + "".join(f"- {md_of(x)}\n" for x in body))
    (ROOT / "docs" / name).write_text("".join(parts), "utf-8")
print("guide:", {lang: len(G[lang]) for lang in LANGS}, "pages — index.html and docs updated")
