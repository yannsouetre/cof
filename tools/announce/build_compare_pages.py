#!/usr/bin/env python3
"""Builds compare/index.html and compare/index.<lang>.html from tools/announce/compare_i18n/<lang>.json.

    python3 tools/announce/build_compare_pages.py            # every language whose JSON exists
    python3 tools/announce/build_compare_pages.py --check    # same keys and same marks in every language

The English file is the reference: the other files carry the same keys with translated values; the
marks of the table (y / p / n / c / g) are never translated and are checked against the English file."""
import json, sys, html
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
I18N = ROOT / "tools/announce/compare_i18n"
OUT = ROOT / "compare"
BASE = "https://yannsouetre.github.io/cof/compare/"
LANGS = ["en", "fr", "de", "es", "zh", "ja"]
HTML_LANG = {"zh": "zh-Hans"}
SYM = {"y": "✓", "p": "~", "n": "✕", "c": "→", "g": "○"}
COLKEYS = ["cof", "v2", "v3", "md", "af", "mem", "vrm"]
FONT_URL = ("https://fonts.googleapis.com/css2?family=Michroma&family=Cormorant+Garamond:ital,wght@1,500"
            "&family=Bricolage+Grotesque:wght@700;800&family=IBM+Plex+Sans:ital,wght@0,400;0,500;0,600;1,400"
            "&family=IBM+Plex+Mono:wght@400;500&display=swap")
CJK = {"ja": '"Noto Sans JP","Hiragino Sans","Yu Gothic",', "zh": '"Noto Sans SC","PingFang SC","Microsoft YaHei",'}


def file_for(lang):
    return "index.html" if lang == "en" else f"index.{lang}.html"


def canonical(lang):
    return BASE + ("" if lang == "en" else file_for(lang))


def langs_nav(cur, aria):
    items = "".join(
        f'<a href="{"./" if l == "en" else file_for(l)}" hreflang="{HTML_LANG.get(l, l)}" lang="{l}"'
        f'{" class=\"on\" aria-current=\"page\"" if l == cur else ""}>{l.upper()}</a>' for l in LANGS)
    return f'<nav class="langs" aria-label="{aria}">{items}</nav>'


def hreflangs():
    out = [f'<link rel="alternate" hreflang="{HTML_LANG.get(l, l)}" href="{canonical(l)}">' for l in LANGS]
    out.append(f'<link rel="alternate" hreflang="x-default" href="{canonical("en")}">')
    return "\n".join(out)


CSS = r"""
:root{--bg:#0d1312;--night:#070b12;--panel:#18201f;--line:#2a3533;--ink:#eef3f1;--muted:#93a39e;--teal:#4cc2a8;--deep:#0f6b5c;--mint:#bfeee2;--violet:#a98ae8;--coral:#f07a72;--warn:#e0a54a;--chip:#1f2927;--col:860px;
--sans:"IBM Plex Sans",%CJK%system-ui,-apple-system,"Segoe UI",sans-serif;--mono:"IBM Plex Mono",ui-monospace,Menlo,Consolas,monospace;--head:"Bricolage Grotesque",var(--sans)}
*{box-sizing:border-box}html{scroll-behavior:smooth}
body{margin:0;background:var(--bg);color:var(--ink);font:17px/1.6 var(--sans);-webkit-font-smoothing:antialiased}
a{color:var(--teal)}
.hero{position:relative;background:var(--night);background-image:radial-gradient(1200px 500px at 70% -10%,rgba(76,194,168,.18),transparent 60%),radial-gradient(800px 400px at 10% 110%,rgba(169,138,232,.14),transparent 60%);border-bottom:1px solid var(--line)}
.top{display:flex;align-items:center;gap:12px;padding:22px clamp(20px,5vw,64px);font:500 14px/1 var(--mono);color:var(--mint);letter-spacing:.06em}
.top svg{width:28px;height:28px;border-radius:7px;flex:0 0 auto}
.top a{color:inherit;text-decoration:none}.top>span{opacity:.7}
.top .langs{margin-left:auto;display:flex;gap:2px;letter-spacing:.04em}
.top .langs a{font:500 11px/1 var(--mono);color:var(--mint);opacity:.6;padding:6px 6px;border-radius:6px;border:1px solid transparent}
.top .langs a:hover{opacity:1}.top .langs a.on{opacity:1;color:var(--teal);border-color:rgba(255,255,255,.18)}
.share{margin-left:0;position:relative;letter-spacing:0}
.share summary{list-style:none;cursor:pointer;font:500 12px/1 var(--mono);letter-spacing:.06em;color:var(--mint);opacity:.75;padding:6px 8px;border:1px solid transparent;border-radius:8px}
.share summary::-webkit-details-marker{display:none}
.share summary:hover,.share[open] summary{opacity:1;border-color:rgba(255,255,255,.18)}
.share menu{position:absolute;right:0;top:calc(100% + 6px);margin:0;padding:6px;list-style:none;background:#0d1312;border:1px solid rgba(255,255,255,.14);border-radius:10px;min-width:11em;z-index:5;box-shadow:0 8px 24px rgba(0,0,0,.4)}
.share menu a,.share menu button{display:block;width:100%;text-align:left;font:500 12px/1 var(--mono);letter-spacing:.04em;color:#dfe7e4;background:none;border:0;padding:8px 10px;border-radius:6px;text-decoration:none;cursor:pointer}
.share menu a:hover,.share menu button:hover{background:rgba(255,255,255,.08);color:#fff}
@media (max-width:640px){.top{flex-wrap:wrap;row-gap:6px}.top .share{margin-left:auto}.top .langs{order:9;flex-basis:100%;margin-left:0;gap:4px;padding-left:40px}.top .langs a{padding:5px 6px;font-size:10px}}
@media (max-width:480px){.top>span{display:none}}
.hero .text{padding:clamp(36px,8vh,84px) clamp(20px,5vw,64px) clamp(44px,8vh,80px);max-width:1200px}
h1{font:400 clamp(20px,3.4vw,42px)/1.25 Michroma,%CJK%sans-serif;letter-spacing:.2em;text-transform:uppercase;margin:0 0 18px;color:#ece8e0}
html[lang=ja] h1,html[lang=zh-Hans] h1{letter-spacing:.12em;text-transform:none}
.rule{width:88px;height:1px;background:var(--mint);opacity:.8;margin:0 0 18px}
.sub{font:italic 500 clamp(21px,2.4vw,30px)/1.3 "Cormorant Garamond",%CJK%Georgia,serif;color:#e4dfd6;margin:0;max-width:760px}
html[lang=ja] .sub,html[lang=zh-Hans] .sub{font-style:normal;font-size:clamp(18px,2vw,24px)}
.kicker{position:absolute;right:clamp(20px,5vw,64px);bottom:18px;font:500 11px/1 var(--mono);letter-spacing:.18em;color:var(--mint);opacity:.6}
main{max-width:1240px;margin:0 auto;padding:40px clamp(16px,4vw,40px) 80px}
.prose{max-width:var(--col)}
.lede{font-size:21px;line-height:1.5;color:#dfe7e4}
h2{font:400 clamp(17px,2vw,21px)/1.4 Michroma,%CJK%sans-serif;letter-spacing:.14em;text-transform:uppercase;color:var(--mint);margin:72px 0 22px;padding-top:28px;border-top:1px solid var(--line)}
html[lang=ja] h2,html[lang=zh-Hans] h2{letter-spacing:.1em;text-transform:none}
h3{font:700 18px/1.3 var(--head);margin:28px 0 8px}
p{margin:10px 0}
code{font-family:var(--mono);font-size:.84em;background:var(--chip);padding:1px 5px;border-radius:4px}
.legend{display:flex;flex-wrap:wrap;gap:10px 18px;margin:18px 0 8px;font-size:14px;color:var(--muted)}
.legend span{display:inline-flex;align-items:center;gap:8px}
.mk{display:inline-grid;place-items:center;width:26px;height:26px;border-radius:8px;font:600 14px/1 var(--mono);flex:0 0 auto;font-style:normal}
.mk.y,.mk.c{background:rgba(76,194,168,.18);color:var(--teal);border:1px solid rgba(76,194,168,.45)}
.mk.c{font:600 19px/1 var(--sans)}
.mk.p{background:rgba(224,165,74,.16);color:var(--warn);border:1px solid rgba(224,165,74,.45)}
.mk.n{background:rgba(240,122,114,.14);color:var(--coral);border:1px solid rgba(240,122,114,.4)}
.mk.g{background:rgba(147,163,158,.12);color:var(--muted);border:1px dashed rgba(147,163,158,.5)}
.twrap{position:relative;overflow:auto;border:1px solid var(--line);border-radius:16px;background:var(--panel);margin:14px 0 10px}
table{border-collapse:separate;border-spacing:0;width:100%;min-width:1040px;font-size:14px}
thead th{position:sticky;top:0;z-index:3;background:#121a18;color:var(--ink);text-align:left;padding:14px 12px 10px;border-bottom:1px solid var(--line);vertical-align:bottom;font:700 14px/1.25 var(--head)}
thead th small{display:block;font:400 11.5px/1.35 var(--sans);color:var(--muted);margin-top:5px;letter-spacing:0}
thead th:first-child{z-index:4}
th.cof{color:var(--mint)}
thead th.cof{background:linear-gradient(180deg,rgba(15,107,92,.45),rgba(15,107,92,.2)),#121a18}
tbody th{position:sticky;left:0;z-index:2;background:var(--panel);text-align:left;font-weight:500;padding:10px 12px;border-bottom:1px solid var(--line);min-width:230px;max-width:300px;color:var(--ink)}
tbody th small{display:block;color:var(--muted);font-size:12px;line-height:1.35;margin-top:2px;font-weight:400}
td{padding:9px 10px;border-bottom:1px solid var(--line);vertical-align:top;min-width:112px}
td.cof{background:rgba(15,107,92,.10)}
td .note{display:block;font-size:11.5px;line-height:1.35;color:var(--muted);margin-top:4px;max-width:150px}
tr.grp th,tr.grp td{position:sticky;left:0;background:#0f1715;color:var(--teal);font:700 13px/1 var(--mono);letter-spacing:.12em;text-transform:uppercase;padding:16px 12px 8px;border-bottom:1px solid var(--line)}
tr.grp th{z-index:2}tr.grp.soon th{color:var(--muted)}
tr.rep th,tr.rep td{background:#0f1715;border-bottom:1px solid var(--line);padding:4px 10px 10px;font:700 12.5px/1.3 var(--head);color:var(--ink)}
tr.rep th{position:sticky;left:0;z-index:2;color:var(--muted);font-weight:500;font-family:var(--mono);font-size:11px;letter-spacing:.08em;text-transform:uppercase}
tr.rep td.cof{color:var(--mint);background:linear-gradient(180deg,rgba(15,107,92,.25),rgba(15,107,92,.12)),#0f1715}
tr:hover td{background:rgba(255,255,255,.025)}tr:hover td.cof{background:rgba(15,107,92,.16)}
tbody tr:last-child th,tbody tr:last-child td{border-bottom:0}
.tools{display:flex;gap:10px 22px;flex-wrap:wrap;align-items:center;margin:0 0 6px;font-size:13.5px;color:var(--muted)}
.tools label{display:inline-flex;align-items:center;gap:6px;cursor:pointer}.tools input{accent-color:var(--teal)}
.grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(250px,1fr));gap:14px;margin:14px 0}
.card{border:1px solid var(--line);border-radius:14px;padding:16px 18px;background:var(--panel)}
.card .t{font:700 18px/1.3 var(--head);margin:0 0 6px;color:var(--teal)}
.card.w .t{color:var(--warn)}
.card p{margin:6px 0;font-size:15px;color:#d6dedb}
.cta{display:flex;flex-wrap:wrap;gap:12px;margin:22px 0 0}
.cta a{display:inline-block;padding:11px 18px;border-radius:999px;text-decoration:none;font:600 15px var(--sans);border:1px solid var(--line);color:var(--ink);background:var(--chip)}
.cta a.pri{background:var(--deep);border-color:var(--deep);color:#fff}.cta a:hover{border-color:var(--teal)}
.src{font-size:14px;color:var(--muted)}.src li{margin:4px 0}
footer{border-top:1px solid var(--line);margin-top:40px;padding:28px clamp(20px,5vw,64px) 48px;color:var(--muted);font-size:14px;line-height:1.6}
footer .mark{font:400 13px/1 Michroma,sans-serif;letter-spacing:.3em;color:var(--mint);margin-bottom:10px}
@media (max-width:720px){body{font-size:16px}.lede{font-size:18px}td .note{max-width:none}tbody th{min-width:180px;max-width:200px}}
"""

LOGO = ('<svg viewBox="0 0 64 64" aria-hidden="true"><rect width="64" height="64" rx="16" fill="#0f6b5c"/>'
        '<path d="M20 24h24M20 32h18M20 40h24" stroke="#bfeee2" stroke-width="4" stroke-linecap="round"/><circle cx="46" cy="32" r="4" fill="#4cc2a8"/></svg>')
FAVICON = ("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 64 64'%3E%3Crect x='4' y='4' width='56' height='56' rx='14' "
           "fill='%230f6b5c'/%3E%3Cpath d='M20 24h24M20 32h18M20 40h24' stroke='%23bfeee2' stroke-width='4' stroke-linecap='round'/%3E%3Ccircle cx='46' cy='32' r='4' fill='%234cc2a8'/%3E%3C/svg%3E")


def mark(m, note, labels):
    lab = labels[m] + (": " + note if note else "")
    return f'<span class="mk {m}" title="{html.escape(lab, quote=True)}" aria-label="{html.escape(labels[m])}">{SYM[m]}</span>'


def table(T):
    labels = T["labels"]
    h = [f'<thead><tr><th>{T["feature"]}</th>']
    for k, c in zip(COLKEYS, T["cols"]):
        h.append(f'<th class="{k}">{c["n"]}<small>{c["s"]}</small></th>')
    h.append("</tr></thead><tbody>")
    for gi, g in enumerate(T["groups"]):
        h.append(f'<tr class="grp{" soon" if g.get("soon") else ""}"><th>{g["name"]}</th><td colspan="{len(COLKEYS)}"></td></tr>')
        if gi:   # repeat the column names, bold, without the details
            h.append('<tr class="rep"><th></th>' + "".join(f'<td class="{k}">{c["n"]}</td>' for k, c in zip(COLKEYS, T["cols"])) + "</tr>")
        for r in g["rows"]:
            cells = r["cells"]
            same = all(c[0] == cells[0][0] for c in cells)
            h.append(f'<tr data-same="{str(same).lower()}"><th>{r["name"]}{("<small>" + r["sub"] + "</small>") if r["sub"] else ""}</th>')
            for k, c in zip(COLKEYS, cells):
                h.append(f'<td class="{k}">{mark(c[0], c[1], labels)}{("<span class=\"note\">" + c[1] + "</span>") if c[1] else ""}</td>')
            h.append("</tr>")
    h.append("</tbody>")
    return "".join(h)


def page(lang, T):
    css = CSS.replace("%CJK%", CJK.get(lang, ""))
    carried = '<i class="mk c" style="width:22px;height:22px;font-size:15px">→</i>'
    cards = lambda arr, cls: "".join(f'<div class="card {cls}"><p class="t">{c["t"]}</p><p>{c["p"]}</p></div>' for c in arr)
    legend = "".join(f'<span><i class="mk {k}">{SYM[k]}</i> {T["legend"][k]}</span>' for k in "ypncg")
    return f"""<!doctype html>
<html lang="{HTML_LANG.get(lang, lang)}">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{html.escape(T["meta"]["title"])}</title>
<meta name="description" content="{html.escape(T["meta"]["description"], quote=True)}">
<meta property="og:title" content="{html.escape(T["meta"]["og_title"], quote=True)}">
<meta property="og:description" content="{html.escape(T["meta"]["og_description"], quote=True)}">
<meta property="og:image" content="https://yannsouetre.github.io/cof/compare/og-compare.jpg">
<meta property="og:image:width" content="1200"><meta property="og:image:height" content="630">
<meta name="twitter:card" content="summary_large_image">
<meta name="twitter:image" content="https://yannsouetre.github.io/cof/compare/og-compare.jpg">
<link rel="canonical" href="{canonical(lang)}">
{hreflangs()}
<link rel="icon" type="image/svg+xml" href="{FAVICON}">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link href="{FONT_URL}" rel="stylesheet">
<style>{css}</style>
</head>
<body>
<header class="hero">
  <div class="top">{LOGO}<a href="../">COF</a><span>{T["top"]["crumb"]}</span>{langs_nav(lang, T["top"]["lang_aria"])}<details class="share" data-share><summary aria-label="{html.escape(T["top"]["share_aria"], quote=True)}">{T["top"]["share"]}</summary><menu><li><button type="button" data-copy>{T["top"]["copy"]}</button></li><li><a data-net="x" target="_blank" rel="noopener">X / Twitter</a></li><li><a data-net="linkedin" target="_blank" rel="noopener">LinkedIn</a></li><li><a data-net="bluesky" target="_blank" rel="noopener">Bluesky</a></li><li><a data-net="reddit" target="_blank" rel="noopener">Reddit</a></li><li><a data-net="mail">{T["top"]["email"]}</a></li></menu></details></div>
  <div class="text">
    <h1>{T["hero"]["h1"]}</h1>
    <div class="rule"></div>
    <p class="sub">{T["hero"]["sub"]}</p>
  </div>
  <div class="kicker">{T["hero"]["kicker"]}</div>
</header>

<main>
<div class="prose">
<p class="lede">{T["lede"]}</p>
<p>{T["intro"]}</p>
</div>

<h2 id="table">{T["h_table"]}</h2>
<div class="legend">{legend}</div>
<div class="tools">
  <label><input type="checkbox" id="onlydiff"> {T["tools"]["onlydiff"]}</label>
  <label><input type="checkbox" id="shownotes" checked> {T["tools"]["shownotes"]}</label>
</div>
<div class="twrap"><table id="cmp" aria-describedby="table">{table(T)}</table></div>
<p class="src" style="margin-top:6px">{T["hint"]}</p>

<h2>{T["h_not"]}</h2>
<div class="grid">{cards(T["cards_not"], "w")}</div>

<h2>{T["h_only"]}</h2>
<div class="grid">{cards(T["cards_only"], "t")}</div>

<h2>{T["h_embrace"]}</h2>
<div class="prose">
<p>{T["embrace1"].replace("${CARRIED}", carried)}</p>
<p>{T["embrace2"]}</p>
<div class="cta">
  <a class="pri" href="../builder/">{T["cta"]["build"]}</a>
  <a href="../viewer/#clara/psyche:graph">{T["cta"]["explore"]}</a>
  <a href="https://github.com/yannsouetre/cof/blob/main/spec/SPEC.md">{T["cta"]["spec"]}</a>
  <a href="https://github.com/yannsouetre/cof/blob/main/docs/IMPLEMENTING.md">{T["cta"]["impl"]}</a>
</div>
</div>

<h2>{T["h_sources"]}</h2>
<ul class="src prose">{"".join(f"<li>{s}</li>" for s in T["sources"])}</ul>
</main>

<footer>
  <div class="mark">COF</div>
  {T["footer"]}
</footer>

<script>
(function(){{var t=document.getElementById("cmp"),od=document.getElementById("onlydiff"),sn=document.getElementById("shownotes");
od.onchange=function(){{t.querySelectorAll('tr[data-same="true"]').forEach(function(tr){{tr.style.display=od.checked?"none":""}})}};
sn.onchange=function(){{t.querySelectorAll(".note").forEach(function(n){{n.style.display=sn.checked?"":"none"}})}};}})();
(function(){{const d=document.querySelector("[data-share]");if(!d)return;const url=(document.querySelector('link[rel=canonical]')||{{}}).href||location.href.split("#")[0],title=document.title,u=encodeURIComponent(url),t=encodeURIComponent(title);
const H={{x:"https://twitter.com/intent/tweet?url="+u+"&text="+t,linkedin:"https://www.linkedin.com/sharing/share-offsite/?url="+u,bluesky:"https://bsky.app/intent/compose?text="+t+"%20"+u,reddit:"https://www.reddit.com/submit?url="+u+"&title="+t,mail:"mailto:?subject="+t+"&body="+u}};
d.querySelectorAll("[data-net]").forEach(a=>a.href=H[a.dataset.net]);const c=d.querySelector("[data-copy]"),c0=c.textContent;c.onclick=async()=>{{try{{await navigator.clipboard.writeText(url);c.textContent={json.dumps(T["top"]["copied"])}}}catch(e){{prompt("Copy this link:",url)}}setTimeout(()=>{{c.textContent=c0;d.open=false}},1200)}};
document.addEventListener("click",e=>{{if(!d.contains(e.target))d.open=false}});document.addEventListener("keydown",e=>{{if(e.key==="Escape")d.open=false}})}})();
</script>
<!-- Visit counter: GoatCounter (no cookies, no personal data). Loaded only on the public site, never from a local copy or another host; it counts page views and referrers, never the files you open. -->
<script>(function(){{if(location.hostname!=="yannsouetre.github.io")return;var s=document.createElement("script");s.async=true;s.src="https://gc.zgo.at/count.js";s.setAttribute("data-goatcounter","https://syanngpt.goatcounter.com/count");document.body.appendChild(s)}})();</script>
</body>
</html>
"""


def flat(o, pre=""):
    """(key path, value) for every string; marks included so --check can compare them."""
    if isinstance(o, dict):
        for k, v in o.items():
            yield from flat(v, f"{pre}.{k}")
    elif isinstance(o, list):
        for i, v in enumerate(o):
            yield from flat(v, f"{pre}[{i}]")
    else:
        yield pre, o


def check(en, lang, T):
    a, b = dict(flat(en)), dict(flat(T))
    bad = [k for k in a if k not in b] + [k for k in b if k not in a]
    marks = [k for k in a if k.endswith("[0]") and ".cells[" in k and a[k] != b.get(k)]
    empty = [k for k in a if a[k] and not b.get(k) and k in b]
    return bad, marks, empty


def main():
    en = json.load(open(I18N / "en.json", encoding="utf-8"))
    checking = "--check" in sys.argv
    ok = True
    for lang in LANGS:
        f = I18N / f"{lang}.json"
        if not f.exists():
            print(f"{lang}: no translation yet"); continue
        T = json.load(open(f, encoding="utf-8"))
        bad, marks, empty = check(en, lang, T)
        if bad or marks:
            ok = False; print(f"{lang}: keys {bad[:5]} marks {marks[:5]}")
        if empty:
            print(f"{lang}: {len(empty)} empty values, e.g. {empty[:3]}")
        if not checking:
            (OUT / file_for(lang)).write_text(page(lang, T), encoding="utf-8")
            print(f"{lang}: {file_for(lang)} written")
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
