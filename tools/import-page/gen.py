#!/usr/bin/env python3
"""Generate import/index.html (the Character.AI → COF page) from template.html.

The page shares its reading and writing code with the builder: every block marked
/* <shared:NAME> */ … /* </shared:NAME> */ in builder/index.html is copied as is in
place of /*@shared:NAME@*/ in the template. Edit those blocks in the builder only,
then run:  python tools/import-page/gen.py   (tests/builder/import_page_test.js checks
that the generated page is up to date).
"""
import pathlib, re, sys

ROOT = pathlib.Path(__file__).resolve().parents[2]
BLOCKS = ("zip", "png", "payloads", "selfdesc", "cai-core")


def shared_blocks(builder: str) -> dict:
    out = {}
    for name in BLOCKS:
        m = re.search(r"/\* <shared:%s>[^\n]*\*/\n(.*?)/\* </shared:%s> \*/" % (re.escape(name), re.escape(name)), builder, re.S)
        if not m:
            sys.exit(f"builder/index.html: shared block {name!r} not found")
        out[name] = m.group(1)
    return out


def render() -> str:
    builder = (ROOT / "builder/index.html").read_text("utf-8")
    tpl = (ROOT / "tools/import-page/template.html").read_text("utf-8")
    blocks = shared_blocks(builder)
    for name, body in blocks.items():
        mark = f"/*@shared:{name}@*/"
        if tpl.count(mark) != 1:
            sys.exit(f"template.html: marker {mark} must appear once")
        tpl = tpl.replace(mark, f"/* <shared:{name}> (from builder/index.html) */\n{body}/* </shared:{name}> */")
    left = re.findall(r"/\*@shared:[\w-]+@\*/", tpl)
    if left:
        sys.exit(f"template.html: unknown markers {left}")
    return tpl


def main():
    out = ROOT / "import/index.html"
    html = render()
    if "--check" in sys.argv:
        cur = out.read_text("utf-8") if out.exists() else ""
        if cur != html:
            sys.exit("import/index.html is out of date: run python tools/import-page/gen.py")
        print("import/index.html is up to date")
        return
    out.parent.mkdir(exist_ok=True)
    out.write_text(html, "utf-8", newline="\n")
    print(f"wrote {out.relative_to(ROOT)} ({len(html.encode()):,} bytes)")


if __name__ == "__main__":
    main()
