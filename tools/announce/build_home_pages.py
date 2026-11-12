#!/usr/bin/env python3
"""Builds the site's home page, index.html and index.<lang>.html at the repository root, from
tools/announce/home_i18n/<lang>.json — the same look as compare/, psyche/ and memories/ (night hero,
language switcher and share menu at the top right, Michroma titles, cards with coloured titles).

    python3 tools/announce/build_home_pages.py            # every language whose JSON exists
    python3 tools/announce/build_home_pages.py --check    # same keys in every language

The English file is the reference; links (href, src, img) are never translated and are checked."""
import json, sys, html
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from build_compare_pages import CSS as BASE_CSS, LOGO, FONT_URL, CJK, HTML_LANG, LANGS, flat  # noqa: E402

ROOT = Path(__file__).resolve().parents[2]
I18N = ROOT / "tools/announce/home_i18n"
BASE = "https://yannsouetre.github.io/cof/"
LINK_KEYS = ("href", "src", "img", "poster", "id")


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


EXTRA_CSS = r"""
.grid{grid-template-columns:repeat(auto-fit,minmax(320px,1fr))}
.status{font-size:15px;color:var(--muted);border-left:2px solid var(--deep);padding:2px 0 2px 14px;margin:18px 0 0}
.status b{color:var(--ink);font-weight:600}
.cta{margin:26px 0 8px}
figure{margin:18px 0 8px}
figure video,figure img,.film video{width:100%;display:block;border-radius:18px;border:1px solid var(--line);background:#000}
figcaption{color:var(--muted);font-size:14.5px;margin-top:10px}
a.card{display:block;color:inherit;text-decoration:none}a.card:hover{border-color:var(--teal)}
.films{display:grid;grid-template-columns:repeat(auto-fit,minmax(320px,1fr));gap:18px;margin:14px 0}
.film .t{font:700 18px/1.3 var(--head);color:var(--teal);margin:12px 0 4px}
.film p{margin:0;font-size:15px;color:#d6dedb}
.sec{display:grid;grid-template-columns:minmax(0,1.35fr) minmax(0,1fr);gap:26px;align-items:center}
.sec.flip{grid-template-columns:minmax(0,1fr) minmax(0,1.35fr)}
.sec.flip figure{order:2}
.sec p{font-size:16.5px;color:#d6dedb;margin:0}
.sec.wide{grid-template-columns:1fr}
.shots{display:grid;grid-template-columns:repeat(auto-fit,minmax(300px,1fr));gap:18px;margin:18px 0}
.shots a.card img{width:100%;display:block;border-radius:10px;margin:0 0 10px;border:1px solid var(--line)}
.box{border:1px solid var(--line);border-radius:14px;padding:18px 20px;background:var(--panel)}
.box p{margin:0;color:#d6dedb}
@media (max-width:820px){.sec,.sec.flip{grid-template-columns:1fr}.sec.flip figure{order:0}}
"""


LOCAL = {"compare/": "compare/index.{l}.html", "psyche/": "psyche/index.{l}.html", "psyche/how-many.html": "psyche/how-many.{l}.html",
         "memories/": "memories/index.{l}.html", "memories/how-much.html": "memories/how-much.{l}.html"}


def localize(out, lang):
    """Internal links to pages that exist in every language point at the same language."""
    if lang == "en":
        return out
    for a, b in LOCAL.items():
        out = out.replace(f'href="{a}"', f'href="{b.format(l=lang)}"')
    return out


def page(lang, T):
    css = BASE_CSS.replace("%CJK%", CJK.get(lang, "")) + EXTRA_CSS
    card = lambda c, cls="t": f'<a class="card {cls}" href="{c["href"]}"><p class="t">{c["t"]}</p><p>{c["p"]}</p></a>'
    secs = []
    for i, s in enumerate(T["sections"]):
        wide = s["id"] in ("contents", "tools")
        cls = "sec wide" if wide else ("sec flip" if i % 2 else "sec")
        fig = f'<figure><img src="{s["img"]}" alt="{html.escape(s["alt"], quote=True)}" loading="lazy"></figure>'
        secs.append(f'<h2 id="{s["id"]}">{s["h"]}</h2>\n<div class="{cls}">{fig}<p>{s["p"]}</p></div>')
        if s["id"] == "tools":
            secs.append('<div class="shots">' + "".join(
                f'<a class="card" href="{c["href"]}"><img src="{c["img"]}" alt="{html.escape(c["alt"], quote=True)}" loading="lazy">'
                f'<p class="t">{c["t"]}</p><p>{c["p"]}</p></a>' for c in T["tools_cards"]) + "</div>")
    films = "".join(
        f'<div class="film"><video src="{f["src"]}" poster="{f["poster"]}" controls preload="none" playsinline></video>'
        f'<p class="t">{f["t"]}</p><p>{f["p"]}</p></div>' for f in T["films"])
    return f"""<!doctype html>
<html lang="{HTML_LANG.get(lang, lang)}">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{html.escape(T["meta"]["title"])}</title>
<meta name="description" content="{html.escape(T["meta"]["description"], quote=True)}">
<meta property="og:title" content="{html.escape(T["meta"]["og_title"], quote=True)}">
<meta property="og:description" content="{html.escape(T["meta"]["og_description"], quote=True)}">
<meta property="og:image" content="https://yannsouetre.github.io/cof/docs/img/cof-social.jpg">
<meta property="og:image:width" content="1280"><meta property="og:image:height" content="640">
<meta name="twitter:card" content="summary_large_image">
<meta name="twitter:image" content="https://yannsouetre.github.io/cof/docs/img/cof-social.jpg">
<link rel="canonical" href="{canonical(lang)}">
{hreflangs()}
<link rel="icon" type="image/svg+xml" href="builder/icon/cof-icon-dark.svg">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link href="{FONT_URL}" rel="stylesheet">
<style>{css}</style>
</head>
<body>
<header class="hero">
  <div class="top">{LOGO}<a href="./">COF</a><span>{T["top"]["crumb"]}</span>{langs_nav(lang, T["top"]["lang_aria"])}<details class="share" data-share><summary aria-label="{html.escape(T["top"]["share_aria"], quote=True)}">{T["top"]["share"]}</summary><menu><li><button type="button" data-copy>{T["top"]["copy"]}</button></li><li><a data-net="x" target="_blank" rel="noopener">X / Twitter</a></li><li><a data-net="linkedin" target="_blank" rel="noopener">LinkedIn</a></li><li><a data-net="bluesky" target="_blank" rel="noopener">Bluesky</a></li><li><a data-net="reddit" target="_blank" rel="noopener">Reddit</a></li><li><a data-net="mail">{T["top"]["email"]}</a></li></menu></details></div>
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
<p class="status">{T["status"]}</p>
<div class="cta">
  <a class="pri" href="viewer/">{T["cta"]["explore"]}</a>
  <a href="builder/">{T["cta"]["build"]}</a>
  <a href="https://github.com/yannsouetre/ComfyUI-COF">{T["cta"]["comfy"]}</a>
  <a href="https://github.com/yannsouetre/cof">{T["cta"]["github"]}</a>
</div>
</div>

<figure id="clip"><video src="docs/media/cof-clip.mp4" poster="docs/img/cof-poster.jpg" controls preload="metadata" playsinline></video>
<figcaption>{T["clip_caption"]}</figcaption></figure>

<h2 id="new">{T["h_new"]}</h2>
<div class="grid">{"".join(card(c) for c in T["cards_new"])}</div>

<h2 id="work">{T["h_work"]}</h2>
<p class="prose">{T["work_intro"]}</p>
<div class="films">{films}</div>

{chr(10).join(secs)}

<h2 id="character-ai">{T["h_cai"]}</h2>
<div class="box prose"><p>{T["cai"]}</p></div>

<h2 id="embrace">{T["h_embrace"]}</h2>
<p class="prose">{T["embrace"]}</p>

<h2 id="more">{T["h_more"]}</h2>
<div class="grid">{"".join(card(c) for c in T["cards_more"])}</div>
</main>

<footer>
  <div class="mark">COF</div>
  {T["footer"]}
</footer>

<script>
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


def check(en, T):
    a, b = dict(flat(en)), dict(flat(T))
    bad = [k for k in a if k not in b] + [k for k in b if k not in a]
    links = [k for k in a if k.rsplit(".", 1)[-1] in LINK_KEYS and a[k] != b.get(k)]
    empty = [k for k in a if a[k] and k in b and not b[k]]
    return bad, links, empty


def main():
    en = json.load(open(I18N / "en.json", encoding="utf-8"))
    checking = "--check" in sys.argv
    ok = True
    for lang in LANGS:
        f = I18N / f"{lang}.json"
        if not f.exists():
            print(f"{lang}: no translation yet"); continue
        T = json.load(open(f, encoding="utf-8"))
        bad, links, empty = check(en, T)
        if bad or links or empty:
            ok = False; print(f"{lang}: keys {bad[:5]} links {links[:5]} empty {empty[:5]}")
        if not checking:
            (ROOT / file_for(lang)).write_text(localize(page(lang, T), lang), encoding="utf-8")
            print(f"{lang}: {file_for(lang)} written")
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
