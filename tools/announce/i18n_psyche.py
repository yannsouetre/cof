"""Translations of the announcement pages: psyche/ (index.html, how-many.html, written by build_psyche_pages.py)
and memories/ (index.html, how-much.html, static). This module

  * extract  — cuts the English pages into translation units (block-level HTML fragments with their inline tags,
               a few attributes, the <head> metadata and the English string literals of the page scripts) and
               writes tools/announce/i18n/<page>.en.json;
  * apply    — reads tools/announce/i18n/<page>.<lang>.json (same keys, translated values) and writes
               psyche/<page>.<lang>.html: the English page with every unit replaced, lang="<lang>", the
               language switcher on the right language, the companion links pointing at the same language.

Usage:  python tools/announce/i18n_psyche.py prepare SITE          (memories only: switcher, hreflang, CSS in the EN pages)
        python tools/announce/i18n_psyche.py extract SITE
        python tools/announce/i18n_psyche.py apply SITE [lang ...]      (default: every language)
        python tools/announce/i18n_psyche.py check SITE [lang ...]      (same keys, same tags, same ${...} expressions)
SITE is psyche, memories or all. Dictionaries: tools/announce/i18n/SITE/PAGE.LANG.json.

A unit's key is a short hash of its English text, so a dictionary survives edits elsewhere on the page; an
edited English unit gets a new key and shows up as missing in `check`.
"""
import hashlib
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DICT = Path(__file__).resolve().parent / "i18n"
SITES = {"psyche": {"index": "index.html", "how-many": "how-many.html"},
         "memories": {"index": "index.html", "how-much": "how-much.html"}}
BASE = "https://yannsouetre.github.io/cof/"
LANGS = ["en", "fr", "de", "es", "zh", "ja"]
NAMES = {"en": "English", "fr": "Français", "de": "Deutsch", "es": "Español", "zh": "中文", "ja": "日本語"}
HTML_LANG = {"zh": "zh-Hans"}

INLINE = {"a", "b", "i", "em", "strong", "code", "span", "br", "sup", "sub", "small", "kbd", "abbr", "cite", "mark", "u",
          "s", "q", "time", "wbr", "img", "button", "label", "select", "option", "input", "output"}
SKIP_TAGS = {"script", "style", "svg", "template"}
ATTRS = ("alt", "title", "aria-label", "placeholder", "data-tip")
TOKEN = re.compile(r"<!--[\s\S]*?-->|<script\b[^>]*>[\s\S]*?</script>|<style\b[^>]*>[\s\S]*?</style>|<svg\b[^>]*>[\s\S]*?</svg>|<[^>]+>|[^<]+")
JS_STR = re.compile(r'"((?:[^"\\\n]|\\.)*)"|\'((?:[^\'\\\n]|\\.)*)\'|`((?:[^`\\]|\\.)*)`')


def key(text):
    return hashlib.sha1(text.encode("utf-8")).hexdigest()[:10]


def file_for(page, lang, site="psyche"):
    fn = SITES[site][page]
    return fn if lang == "en" else fn.replace(".html", f".{lang}.html")


def href_for(page, lang, site="psyche"):
    return "./" if (page == "index" and lang == "en") else file_for(page, lang, site)


def langs_nav(page, cur, site="psyche"):
    items = "".join(f'<a href="{href_for(page, l, site)}" hreflang="{l}" lang="{l}"{" class=\"on\" aria-current=\"page\"" if l == cur else ""}>{l.upper()}</a>'
                    for l in LANGS)
    return f'<nav class="langs" aria-label="Language">{items}</nav>'


def canonical(page, lang, site="psyche"):
    return BASE + site + "/" + ("" if (page == "index" and lang == "en") else file_for(page, lang, site))


def hreflang_links(page, site="psyche"):
    out = [f'<link rel="alternate" hreflang="{HTML_LANG.get(l, l)}" href="{canonical(page, l, site)}">' for l in LANGS]
    out.append(f'<link rel="alternate" hreflang="x-default" href="{canonical(page, "en", site)}">')
    return "\n".join(out)


def prepare(site):
    """Static EN pages (memories): add the switcher before the share menu, canonical + hreflang in <head>, the CSS. Idempotent."""
    for page, fn in SITES[site].items():
        f = ROOT / site / fn
        s = f.read_text("utf-8")
        s = re.sub(r'<nav class="langs".*?</nav>', "", s, count=1)
        s = s.replace('<details class="share"', langs_nav(page, "en", site) + '<details class="share"', 1)
        s = re.sub(r'<link rel="canonical"[^>]*>\n?', "", s)
        s = re.sub(r'<link rel="alternate" hreflang=[^>]*>\n?', "", s)
        links = f'<link rel="canonical" href="{canonical(page, "en", site)}">\n' + hreflang_links(page, site) + "\n"
        s = s.replace("</head>", links + "</head>", 1)
        if LANGS_CSS not in s:
            s = s.replace("</style>", LANGS_CSS + "</style>", 1)
        f.write_text(s, "utf-8")
        print("prepared", site, fn)


# node kinds and stability levels as the builder and the explorer name them (rendered from code in the hover card)
_K = ["wound", "value", "belief", "want", "need", "fear", "stance", "taste", "habit", "contradiction", "rule", "core", "settled", "shifting", "fragile"]
_W = {"fr": ["blessure", "valeur", "croyance", "désir", "besoin", "peur", "position", "goût", "habitude", "contradiction", "règle", "noyau", "établi", "mouvant", "fragile"],
      "de": ["Wunde", "Wert", "Überzeugung", "Wunsch", "Bedürfnis", "Angst", "Haltung", "Geschmack", "Gewohnheit", "Widerspruch", "Regel", "Kern", "gefestigt", "im Wandel", "fragil"],
      "es": ["herida", "valor", "creencia", "deseo", "necesidad", "miedo", "postura", "gusto", "hábito", "contradicción", "regla", "núcleo", "asentado", "cambiante", "frágil"],
      "zh": ["创伤", "价值观", "信念", "欲望", "需求", "恐惧", "立场", "喜好", "习惯", "矛盾", "规则", "核心", "稳定", "变动", "脆弱"],
      "ja": ["傷", "価値観", "信念", "欲求", "必要", "恐れ", "態度", "好み", "習慣", "矛盾", "ルール", "核", "安定", "変動", "脆弱"]}
WORDS = {l: dict(zip(_K, w)) for l, w in _W.items()}

LANGS_CSS = (".top .langs{margin-left:auto;display:flex;gap:2px;letter-spacing:.04em}"
             ".top .langs a{font:500 11px/1 PlexMono,monospace;color:var(--mint);opacity:.6;padding:6px 6px;border-radius:6px;border:1px solid transparent}"
             ".top .langs a:hover{opacity:1}.top .langs a.on{opacity:1;color:var(--teal);border-color:rgba(255,255,255,.18)}"
             ".top .share{margin-left:0}"
             "@media (max-width:640px){.top{flex-wrap:wrap;row-gap:6px}.top .share{margin-left:auto}.top .langs{order:9;flex-basis:100%;margin-left:0;gap:4px;padding-left:40px}.top .langs a{padding:5px 6px;font-size:10px}}"
             "@media (max-width:480px){.top>span:not(.crumb){display:none}}")


# ------------------------------------------------------------------------------------------------------- extraction
def _tag_name(tok):
    m = re.match(r"<\s*/?\s*([a-zA-Z][\w-]*)", tok)
    return m.group(1).lower() if m else ""


def _has_words(s):
    return re.search(r"[A-Za-zÀ-ɏ]{2,}", s) is not None


def html_units(s):
    """Block-level fragments: maximal runs of text + inline tags, between block tags. Returns [(start, end, text)]."""
    units, run_start, run_text, pos = [], None, [], 0
    for m in TOKEN.finditer(s):
        tok = m.group(0)
        is_tag = tok.startswith("<")
        name = _tag_name(tok) if is_tag else ""
        inline = (not is_tag) or (name in INLINE and not tok.startswith("<!--") and name not in SKIP_TAGS)
        if inline:
            if run_start is None:
                run_start = m.start()
            run_text.append(tok)
        else:
            if run_start is not None:
                frag = "".join(run_text)
                units.append((run_start, run_start + len(frag), frag))
            run_start, run_text = None, []
    if run_start is not None:
        frag = "".join(run_text)
        units.append((run_start, run_start + len(frag), frag))
    out = []
    for a, b, frag in units:
        # trim surrounding whitespace, keep it outside the unit
        lead = len(frag) - len(frag.lstrip())
        trail = len(frag) - len(frag.rstrip())
        core = frag.strip()
        if not core or not _has_words(re.sub(r"<[^>]+>", "", core)):
            continue
        if re.fullmatch(r"(?:<a [^>]*>[A-Z]{2}</a>)+", core):      # the language switcher
            continue
        out.append((a + lead, b - trail, core))
    return out


def attr_units(s):
    out = []
    for m in re.finditer(r"<(?!script|style)[a-zA-Z][^>]*>", s):
        tag = m.group(0)
        for a in ATTRS:
            for am in re.finditer(rf'\s{a}="([^"]*)"', tag):
                v = am.group(1)
                if v and _has_words(v):
                    out.append((m.start() + am.start(1), m.start() + am.end(1), v))
    for m in re.finditer(r'<meta (?:name|property)="(?:description|og:title|og:description|twitter:title|twitter:description)" content="([^"]*)"', s):
        out.append((m.start(1), m.end(1), m.group(1)))
    return out


def _js_literals(js):
    """(start, end, value) of every top-level string literal of a script, template literals included whole
    (nested ${...} expressions kept inside the value). Comments and regex literals are skipped roughly."""
    out, i, n = [], 0, len(js)
    def scan_template(i):
        # js[i] == "`"; returns index after the closing backtick
        i += 1
        while i < n:
            c = js[i]
            if c == "\\":
                i += 2; continue
            if c == "`":
                return i + 1
            if c == "$" and js.startswith("${", i):
                i = scan_expr(i + 2); continue
            i += 1
        return n
    def scan_expr(i):
        # inside ${ ... }: returns index after the matching }
        depth = 1
        while i < n and depth:
            c = js[i]
            if c in "\"'":
                i = scan_str(i); continue
            if c == "`":
                i = scan_template(i); continue
            if c == "{": depth += 1
            elif c == "}": depth -= 1
            i += 1
        return i
    def scan_str(i):
        q = js[i]; i += 1
        while i < n:
            c = js[i]
            if c == "\\":
                i += 2; continue
            if c == q or c == "\n":
                return i + 1
            i += 1
        return n
    while i < n:
        c = js[i]
        if c == "/" and js.startswith("//", i):
            j = js.find("\n", i); i = n if j < 0 else j + 1; continue
        if c == "/" and js.startswith("/*", i):
            j = js.find("*/", i + 2); i = n if j < 0 else j + 2; continue
        if c in "\"'":
            j = scan_str(i); out.append((i + 1, j - 1, js[i + 1:j - 1])); i = j; continue
        if c == "`":
            j = scan_template(i); out.append((i + 1, j - 1, js[i + 1:j - 1])); i = j; continue
        i += 1
    return out


def js_units(s):
    """English string literals of the page scripts (quotes excluded); selectors, keys and code-ish literals skipped."""
    out = []
    for sm in re.finditer(r"<script\b[^>]*>([\s\S]*?)</script>", s):
        js, base = sm.group(1), sm.start(1)
        for a, b, v in _js_literals(js):
            if not v.strip():
                continue
            if re.search(r'"[lg]":\s*$', js[max(0, a - 8):a - 1]) and re.search(r"[A-Za-z\u00C0-\u024F]{2,}", v):
                out.append((base + a, base + b, v)); continue
            if not re.search(r"[A-Za-z]{3,}", v):
                continue
            if re.match(r"^[.#:\[(]|^https?:|^mailto:|^url\(|^rgba?\(", v) or re.fullmatch(r"[\w\-./:#%]+", v) or v.startswith("xMid"):
                continue
            if "[rel=" in v or v in ("ln off", "n off", "n piv", "n on", "ln on", "on") or re.fullmatch(r"\w+ (?:in|on|off|draw)", v):
                continue      # class-name strings of the graph scripts
            plain = re.sub(r"\$\{[^}]*\}", " ", v)
            plain = re.sub(r"<[^>]+>", " ", plain)
            if not (re.search(r"[A-Za-z]{2,}\W+[A-Za-z]{2,}", plain) or re.search(r"[.!?:…]$", plain.strip())
                    or ("${" in v and re.search(r"[A-Za-z]{3,}", plain))):
                continue
            out.append((base + a, base + b, v))
    return out


def units(s):
    found = sorted(set(html_units(s) + attr_units(s) + js_units(s)))
    # drop units nested in another (an attribute inside a fragment is impossible here, but js/html cannot overlap)
    out, last_end = [], -1
    for a, b, t in found:
        if a < last_end:
            continue
        out.append((a, b, t))
        last_end = b
    return out


def extract(site):
    (DICT / site).mkdir(parents=True, exist_ok=True)
    for page, fn in SITES[site].items():
        s = (ROOT / site / fn).read_text("utf-8")
        d = {}
        for a, b, t in units(s):
            d.setdefault(key(t), t)
        (DICT / site / f"{page}.en.json").write_text(json.dumps(d, ensure_ascii=False, indent=1), "utf-8")
        print(site, page, len(d), "units", sum(len(v) for v in d.values()), "chars")


def _tpl_spans(v):
    """[(start, end)] of the top-level ${...} expressions of a template value (end after the closing brace)."""
    spans, i, n = [], 0, len(v)
    while i < n:
        if v.startswith("${", i):
            j, depth = i + 2, 1
            while j < n and depth:
                c = v[j]
                if c in "\"'":
                    q = c; j += 1
                    while j < n and v[j] != q:
                        j += 2 if v[j] == "\\" else 1
                elif c == "`":
                    j += 1
                    while j < n and v[j] != "`":
                        if v.startswith("${", j):
                            k = _tpl_spans(v[j:])[0][1] if _tpl_spans(v[j:]) else 2
                            j += k; continue
                        j += 2 if v[j] == "\\" else 1
                elif c == "{": depth += 1
                elif c == "}": depth -= 1
                j += 1
            spans.append((i, j)); i = j
        else:
            i += 1
    return spans


def _exprs(v):
    """Normalized top-level expressions: the literal text of nested template literals is blanked, so a
    translation may reword `${c?`age ${a}`:`age ${b}`}` and still match."""
    out = []
    for a, b in _tpl_spans(v):
        e = v[a:b]
        def blank(m):
            inner = m.group(1)
            keep = "".join(inner[x:y] for x, y in _tpl_spans(inner))
            return "`" + keep + "`"
        e = re.sub(r"`((?:[^`\\]|\\.)*)`", blank, e)
        out.append(e)
    return out


# -------------------------------------------------------------------------------------------------------- application
def _escape_for(s, a, b, t):
    """The replacement must be escaped like its context: a JS literal gets its quote escaped, an attribute its quotes."""
    q = s[a - 1] if a > 0 else ""
    before = s[max(0, a - 40):a]
    if re.search(r'(?:\s(?:alt|title|aria-label|placeholder|data-tip)|content)="$', before):
        return t.replace('"', "&quot;")
    if q in ('"', "'", "`") and re.search(r"<script\b", s[:a]) and s.rfind("<script", 0, a) > s.rfind("</script>", 0, a):
        if q == "`":
            out, i = [], 0
            for x, y in _tpl_spans(t):
                out.append(t[i:x].replace("\\", "\\\\").replace("`", "\\`")); out.append(t[x:y]); i = y
            out.append(t[i:].replace("\\", "\\\\").replace("`", "\\`"))
            return "".join(out)
        return t.replace("\\", "\\\\").replace(q, "\\" + q).replace("\n", "\\n")
    return t


def apply(site, langs):
    pages = SITES[site]
    for page, fn in pages.items():
        en = (ROOT / site / fn).read_text("utf-8")
        for lang in langs:
            df = DICT / site / f"{page}.{lang}.json"
            if not df.exists():
                print("no dictionary", df.name)
                continue
            tr = json.loads(df.read_text("utf-8"))
            s, missing = en, []
            for a, b, t in sorted(units(en), reverse=True):
                k = key(t)
                if k not in tr or not tr[k].strip():
                    missing.append(t[:60])
                    continue
                s = s[:a] + _escape_for(en, a, b, tr[k]) + s[b:]
            s = s.replace('<html lang="en">', f'<html lang="{HTML_LANG.get(lang, lang)}">', 1)
            if site == "psyche" and page == "index" and lang in WORDS:
                s = s.replace("${n.k}", "${(window.__KW||{})[n.k]||n.k}").replace("${n.st}", "${(window.__KW||{})[n.st]||n.st}")
                s = s.replace("<script>", "<script>window.__KW=" + json.dumps(WORDS[lang], ensure_ascii=False) + ";</script>\n<script>", 1)
            s = re.sub(r'<nav class="langs".*?</nav>', langs_nav(page, lang, site), s, count=1)
            other = [q for q in pages if q != page][0]
            s = s.replace(f'href="{pages[other]}"', f'href="{file_for(other, lang, site)}"')
            if other == "index":
                s = s.replace('href="./"', f'href="{file_for(other, lang, site)}"')
            s = s.replace(f'<link rel="canonical" href="{canonical(page, "en", site)}">',
                          f'<link rel="canonical" href="{canonical(page, lang, site)}">')
            (ROOT / site / file_for(page, lang, site)).write_text(s, "utf-8")
            print(site, page, lang, len(s), "missing", len(missing), missing[:5])


def check(site, langs):
    bad = 0
    for page in SITES[site]:
        en = json.loads((DICT / site / f"{page}.en.json").read_text("utf-8"))
        for lang in langs:
            df = DICT / site / f"{page}.{lang}.json"
            if not df.exists():
                print("MISSING FILE", df.name); bad += 1
                continue
            tr = json.loads(df.read_text("utf-8"))
            for k, v in en.items():
                if k not in tr:
                    print(page, lang, "missing", k, v[:60]); bad += 1
                    continue
                w = tr[k]
                tags_en = re.findall(r"<(/?\w+)", v); tags_tr = re.findall(r"<(/?\w+)", w)
                if sorted(tags_en) != sorted(tags_tr):
                    print(page, lang, "tags", k, v[:50], "->", w[:50]); bad += 1
                plural = re.compile(r'\$\{[^}]*\?(?:"":"s"|"s":"")\}')      # an English plural suffix may be dropped by a translation
                ex_en = _exprs(v); ex_tr = _exprs(w)
                if sorted(ex_en) != sorted(ex_tr) and sorted(e for e in ex_en if not plural.fullmatch(e)) != sorted(e for e in ex_tr if not plural.fullmatch(e)):
                    print(page, lang, "${}", k, v[:50], "->", w[:50]); bad += 1
                if re.findall(r'href="[^"]*"', v) != re.findall(r'href="[^"]*"', w):
                    print(page, lang, "href", k, v[:50]); bad += 1
            extra = set(tr) - set(en)
            if extra:
                print(page, lang, "extra keys", len(extra))
    print("check:", "OK" if not bad else f"{bad} problem(s)")
    return bad


if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else "extract"
    site = sys.argv[2] if len(sys.argv) > 2 else "psyche"
    sites = list(SITES) if site == "all" else [site]
    langs = sys.argv[3:] or [l for l in LANGS if l != "en"]
    bad = 0
    for st in sites:
        if cmd == "prepare":
            prepare(st)
        elif cmd == "extract":
            extract(st)
        elif cmd == "apply":
            apply(st, langs)
        elif cmd == "check":
            bad += check(st, langs)
        else:
            sys.exit(__doc__)
    sys.exit(1 if bad else 0)
