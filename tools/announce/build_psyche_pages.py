"""The two announcement pages of COF 1.2 (the psyche): psyche/index.html and psyche/how-many.html.

    python3 tools/announce/build_psyche_pages.py

They reuse the style of the memories page (memories/index.html, same hero, column, fonts, share menu, footer) so the
site reads as one; the data of the graph, of the « why » chain and of the simulator is Clara's
(spec/examples/10-clara-mercier), read here, not copied by hand. Text in English, like the rest of the site. Decided
with Yann on 3 Nov. 2026: title « AI characters now have an inner life », subtitle « A psyche you can read, edit and
take with you — every conviction tied to the memory that made it. »; on 4 Nov. 2026 the companion page became « How
many convictions make a person? » (psyche/how-many.html, the companion of memories/how-much.html), with « Why did she
say no? » as its opening section. The earlier name psyche/why.html was never published and is no longer written."""
import json, re, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]

# Hero images, one line each: the companion's own image will come from Gemini later (e.g. "img/how-many.jpg", relative to
# psyche/); until then both pages use the studio memory of example 10.
HERO_INDEX = "img/hero-inner.jpg"
HERO_HOW_MANY = "img/hero-how-many.jpg"
COMPANION = "how-many.html"
EX = ROOT / "spec/examples/10-clara-mercier"
MAN = json.loads((EX / "manifest.json").read_text("utf-8"))
PV = MAN["elements"]["psyche"]["variants"]
MV = MAN["elements"]["memories"]["variants"]
en = lambda lab: lab.split(" / ")[-1] if isinstance(lab, str) else (lab or {}).get("en", "")


def nodes():
    out = []
    for vid, v in PV.items():
        n = json.loads((EX / "elements/psyche" / vid / "psyche-node.json").read_text("utf-8"))
        age = lambda p: ((p or {}).get("age") or {}).get("value")
        out.append({"id": vid, "k": v.get("kind"), "l": en(v.get("label")), "g": (n.get("gist") or {}).get("en", ""),
                    "s": n.get("strength"), "st": n.get("stability", "settled"), "since": age(n.get("since")), "until": age(n.get("until")),
                    "aw": n.get("aware"), "va": n.get("valence"), "fb": bool(n.get("false_but_held")),
                    "links": [[l["type"], l["to"]] for l in n.get("links", [])]})
    return out


def memories():
    out = {}
    for vid, v in MV.items():
        n = json.loads((EX / "elements/memories" / vid / "memory.json").read_text("utf-8"))
        w = n.get("when") or {}
        a = (w.get("age") or {}).get("value") or ((w.get("from") or {}).get("age") or {}).get("value")
        b = ((w.get("to") or {}).get("age") or {}).get("value")
        out[vid] = {"l": en(v.get("label")), "g": (n.get("gist") or {}).get("en", ""), "a": a, "b": b, "per": v.get("kind") == "period"}
    return out


sys.path.insert(0, str(Path(__file__).resolve().parent))
from i18n_psyche import langs_nav, hreflang_links, LANGS_CSS  # noqa: E402

SRC = (ROOT / "memories/index.html").read_text("utf-8")
CSS = SRC[SRC.index("<style>"):SRC.index("</style>")]
SHARE_JS = re.findall(r"<script>([\s\S]*?)</script>", SRC)[1]
COUNTER = re.findall(r"(<!-- Visit counter[\s\S]*?</script>)", SRC)[0]
TOP = re.search(r'<div class="top">[\s\S]*?</div>', SRC).group(0)
TOP = re.sub(r'<nav class="langs".*?</nav>', "", TOP)   # the memories page carries its own switcher since 7 Nov.
FOOT = re.search(r"<footer>[\s\S]*?</footer>", SRC).group(0)

KINDS = {"wound": "#e8876b", "value": "#4cc2a8", "belief": "#a98ae8", "want": "#e3b04f", "need": "#7fb3e8", "fear": "#d9708f",
         "stance": "#cdb67f", "taste": "#9fd27c", "habit": "#9aaca7", "contradiction": "#eef3f1", "rule": "#bfeee2"}

EXTRA_CSS = """
/* 1.2: the psyche pages (same system as the memories pages) */
.hero::before{background:linear-gradient(180deg,rgba(7,11,18,.45) 0%,rgba(7,11,18,0) 22%,rgba(7,11,18,0) 76%,rgba(13,19,18,1) 100%),linear-gradient(90deg,rgba(7,11,18,.9) 0%,rgba(7,11,18,.8) 36%,rgba(7,11,18,.3) 54%,rgba(7,11,18,0) 66%,rgba(7,11,18,0) 100%)}   /* 7 Nov.: no darkening over the head any more — the left stays dark for the text, the skull and its galaxy keep the picture's own light */   /* the fade into the page first: the first layer is drawn on top (the bottom edge was the darkening layer's night, not the page colour) */
.hero .sub{font:500 clamp(18px,2vw,23px)/1.45 Plex,system-ui,sans-serif;color:#dfe8e5;max-width:680px;margin:0 0 26px}
figure.node{margin:30px 0 8px;padding:22px 24px;border:1px solid var(--line);border-radius:18px;background:var(--panel)}
figure.node .nk{display:flex;flex-wrap:wrap;gap:8px;align-items:center;margin:0 0 10px}
figure.node .nk b{font:700 22px/1.2 Bricolage,Plex,sans-serif}
.pill{font:500 12px/1 PlexMono,monospace;letter-spacing:.04em;text-transform:uppercase;padding:5px 8px;border-radius:999px;border:1px solid var(--line);color:var(--muted)}
.pill.k{color:#0d1312;border:0}
figure.node .gist{font:500 21px/1.45 Cormorant,Georgia,serif;color:#e4dfd6;margin:0 0 14px}
figure.node .facts{display:grid;grid-template-columns:110px 1fr;gap:4px 14px;margin:0;font-size:15px}
figure.node .facts dt{color:var(--muted)}figure.node .facts dd{margin:0}
.legend{display:flex;flex-wrap:wrap;gap:6px 14px;font-size:13px;color:var(--muted);margin:10px auto 0;max-width:calc(var(--col) - 40px)}
.legend i{display:inline-block;width:10px;height:10px;border-radius:50%;margin-right:5px;vertical-align:-1px}
.pgraph .replay{position:absolute;right:14px;top:12px;font:500 13px PlexMono,monospace;background:var(--panel);color:var(--ink);border:1px solid var(--line);border-radius:999px;padding:6px 12px;cursor:pointer;z-index:1}
.pgraph{position:relative}.pgraph .agec{position:absolute;left:18px;top:14px;font:500 11px PlexMono,monospace;color:#5f6f6b;letter-spacing:.06em;text-transform:uppercase;z-index:1}
/* the psyche graph, in the visual language of the memories graph (memories/index.html): rings, halo and scale on focus, arrival by fade and drawing */
.pgraph svg .lane{font:500 11px PlexMono,monospace;fill:#5f6f6b;letter-spacing:.06em}
.pgraph svg .n{cursor:pointer;transition:opacity .6s ease}
.pgraph svg .n .node{transform-box:fill-box;transform-origin:center;transition:transform .45s cubic-bezier(.2,.8,.2,1),filter .3s}
.pgraph svg .n.off{opacity:0!important}.pgraph svg .n.off .node{transform:scale(.55)}
.pgraph svg .piv .ring{fill:#0b100f;stroke:var(--teal);stroke-width:2;transition:stroke-width .3s}
.pgraph svg .piv image{transition:filter .4s}
.pgraph svg .piv .pill{fill:rgba(169,138,232,.10);stroke:rgba(169,138,232,.55);stroke-width:1}
.pgraph svg .piv .pt{font:500 13px Plex,sans-serif;fill:#cbbcf0;text-anchor:middle}.pgraph svg .piv .ps{font:500 11px PlexMono,monospace;fill:#9f8cd0;text-anchor:middle}
.pgraph svg .lab{font:500 14px Plex,sans-serif;fill:var(--ink);text-anchor:middle}
.pgraph svg .sub{font:400 11.5px Plex,sans-serif;fill:var(--muted);text-anchor:middle}
.pgraph svg .nl{font:500 11.5px Plex,sans-serif;fill:#dfe8e5;text-anchor:middle}
.pgraph svg .ln{transition:opacity .6s ease,stroke-dashoffset 1.4s ease}.pgraph svg .ln.off{opacity:0}
.pgraph svg.hl .ln{opacity:.12}.pgraph svg.hl .ln.on{opacity:1}
.pgraph svg.hl .n:not(.on){opacity:.35}.pgraph svg.hl .piv:not(.on) image{filter:saturate(.5) brightness(.75)}
.pgraph svg .n.on .node{transform:scale(1.2);filter:drop-shadow(0 0 10px var(--hc,rgba(76,194,168,.55)))}
.pgraph svg .piv.on .ring{stroke-width:3}
.pfocus{display:grid;grid-template-columns:120px 1fr;gap:16px;align-items:center;max-width:calc(var(--col) - 40px);margin:18px auto 0;min-height:120px;transition:opacity .35s}
.pfocus.fade{opacity:0}
.pfocus .vis{width:120px;height:120px;border-radius:14px;border:1px solid var(--line);background:#0e1514;display:grid;place-items:center;overflow:hidden}
.pfocus .vis:empty{visibility:hidden}.pfocus .vis img{width:100%;height:100%;object-fit:cover}.pfocus .vis i{display:block;border-radius:50%}
.pfocus .vis b{font:500 12px PlexMono,monospace;color:#cbbcf0;letter-spacing:.04em}
.pfocus .gist{font:500 20px/1.4 Cormorant,Georgia,serif;color:#e8e3da;margin:0 0 8px}
.pfocus .meta{font:500 12px/1.7 PlexMono,monospace;color:var(--muted);margin:0;letter-spacing:.03em}.pfocus .meta b{color:var(--teal);font-weight:500}
@media (max-width:640px){.pfocus{grid-template-columns:84px 1fr}.pfocus .vis{width:84px;height:84px}.pfocus .gist{font-size:17px}}
@media (prefers-reduced-motion:reduce){.pgraph svg .n,.pgraph svg .n .node,.pgraph svg .ln,.pfocus{transition:none}}
table.cmp{width:100%;border-collapse:collapse;margin:22px 0 8px;font-size:15px}
table.cmp th,table.cmp td{text-align:left;vertical-align:top;padding:9px 10px;border-bottom:1px solid var(--line)}
table.cmp thead th{font:700 15px Bricolage,Plex,sans-serif;color:var(--ink)}table.cmp tbody th{color:var(--muted);font-weight:500;width:28%}
table.cmp td.y{color:var(--mint)}table.cmp td.n{color:#d9a0a0}table.cmp thead .hint{display:block;font:400 13px Plex,sans-serif;color:var(--muted);margin-top:2px}
.chain{margin:26px 0 10px}
.chat{border:1px solid var(--line);border-radius:18px;padding:18px 20px;background:var(--panel)}
.chat p{margin:0 0 12px}.chat .who{font:500 12px PlexMono,monospace;letter-spacing:.05em;text-transform:uppercase;color:var(--muted);display:block;margin-bottom:2px}
.chat .her{font:500 22px/1.4 Cormorant,Georgia,serif;color:#e4dfd6}
.step{display:grid;grid-template-columns:30px 1fr;gap:14px;margin:18px 0 0;opacity:0;transform:translateY(8px);transition:opacity .5s,transform .5s}
.step.on{opacity:1;transform:none}.step[hidden]{display:none}
.step .dot{width:30px;height:30px;border-radius:50%;display:grid;place-items:center;font:700 13px PlexMono,monospace;color:#0d1312}
.step .card{border:1px solid var(--line);border-radius:14px;padding:14px 16px;background:var(--panel)}
.step .card .t{font:700 18px/1.3 Bricolage,Plex,sans-serif;margin:0 0 3px}.step .card .m{font:500 12px PlexMono,monospace;color:var(--muted);margin:0 0 8px}
.step .card .g{font:500 19px/1.45 Cormorant,Georgia,serif;color:#e4dfd6;margin:0}.step .card img{border-radius:10px;margin:12px 0 4px;width:100%;max-height:280px;object-fit:cover}
.step .why{font-size:15px;color:var(--muted);margin:10px 0 0}
.step.hidden-layer .card{border-style:dashed;border-color:var(--violet)}
.whyb{margin:22px 0 0;display:flex;gap:10px;flex-wrap:wrap}
.whyb button{font:700 17px Bricolage,Plex,sans-serif;padding:12px 22px;border-radius:999px;border:0;background:var(--teal);color:#0d1312;cursor:pointer}
.whyb button.ghost{background:transparent;color:var(--ink);border:1px solid var(--line)}
.whyb button:disabled{opacity:.4;cursor:default}
.orders{list-style:none;padding:0;margin:22px 0 8px;border-top:1px solid var(--line)}
.orders li{display:grid;grid-template-columns:150px 1fr;gap:16px;padding:12px 0;border-bottom:1px solid var(--line)}
.orders b{font:700 24px Bricolage,Plex,sans-serif;color:var(--mint)}
@media (max-width:640px){figure.node .facts{grid-template-columns:90px 1fr}.orders li{grid-template-columns:1fr;gap:2px}table.cmp{font-size:13px}table.cmp th,table.cmp td{padding:7px 5px}}
"""


def head(title, desc, ogt, ogd, img, url):
    css = CSS.replace("url(img/electric-sheep.jpg) center 70%/cover", f"url({img}) " + ("76%" if "inner" in img else "72%") + " center/cover")   # both images are wide (hero-inner outpainted to 21:9 by Gemini, 4 Nov.): cover, held so that the head / the person stays in view on a phone
    return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{title}</title>
<meta name="description" content="{desc}">
<meta property="og:title" content="{ogt}">
<meta property="og:description" content="{ogd}">
<meta property="og:image" content="https://yannsouetre.github.io/cof/psyche/img/{'og-how-many.jpg' if url.startswith('how-many') else 'og-psyche.jpg'}">
<meta property="og:image:width" content="1200"><meta property="og:image:height" content="630">
<meta name="twitter:card" content="summary_large_image">
<meta name="twitter:image" content="https://yannsouetre.github.io/cof/psyche/img/{'og-how-many.jpg' if url.startswith('how-many') else 'og-psyche.jpg'}">
<link rel="canonical" href="https://yannsouetre.github.io/cof/psyche/{url}">
{hreflang_links("index" if url == "" else "how-many")}
<link rel="icon" type="image/svg+xml" href="../builder/icon/cof-icon-dark.svg">
{css}{EXTRA_CSS}{"" if LANGS_CSS in css else LANGS_CSS}</style>
</head>
<body>
"""


def tail(scripts, note=""):
    return f"""{FOOT.replace("Clara Mercier and the Martian are fictional example characters; their images are AI-generated.", "Clara Mercier is a fictional example character; her images are AI-generated, her psyche is written by hand." + note)}
<script>{SHARE_JS}</script>
{scripts}
{COUNTER}
</body>
</html>
"""


TOP12 = TOP.replace("· 1.1</span>", "· 1.2</span>")
TOPI = TOP12.replace('<details class="share"', langs_nav("index", "en") + '<details class="share"')
TOPH = TOP12.replace('<details class="share"', langs_nav("how-many", "en") + '<details class="share"')
N, MEM = nodes(), memories()
ND = {n["id"]: n for n in N}

# ---------------------------------------------------------------------------------------------------- index.html
def meta(n):
    bits = [n["k"], f"strength {n['s']}", n["st"]]
    if n["since"] is not None: bits.append(f"since age {n['since']}")
    if n["until"] is not None: bits.append(f"until about {n['until']}")
    return " · ".join(bits)

GRAPH_JS = """
(function(){
const N=__N__,MEM=__M__,K=__K__;
const svg=document.getElementById("psvg"),fc=document.getElementById("pfocus"),ac=document.getElementById("pagec"),NS="http://www.w3.org/2000/svg";
const vis=fc.querySelector(".vis"),gist=fc.querySelector(".gist"),meta=fc.querySelector(".meta");
/* layout: the memories Clara's nodes hang on, left to right by age, each with its nodes below; the nodes tied to no memory in a band at the bottom */
const PIV=["ev1","ep1","ev2","ev3","ev4"],PX={ev1:120,ep1:355,ev2:590,ev3:825,ev4:1060},PY=128,R=30;
const hang={};N.forEach(n=>{const m=n.links.find(l=>l[1].startsWith("memories/")&&PIV.includes(l[1].slice(9)));n.p=m?m[1].slice(9):null;if(n.p)(hang[n.p]=hang[n.p]||[]).push(n)});
const pos={};PIV.forEach(p=>{pos["m:"+p]={x:PX[p],y:PY};(hang[p]||[]).forEach((n,i)=>{pos[n.id]={x:PX[p]+(i%2?44:-44)*(hang[p].length>1?1:0),y:PY+92+i*62}})});
const free=N.filter(n=>!n.p),per=Math.ceil(free.length/2);free.forEach((n,i)=>{const r=Math.floor(i/per),c=i%per;pos[n.id]={x:95+c*155+(r?78:0),y:505+r*82}});
const el=(t,a,p)=>{const e=document.createElementNS(NS,t);for(const k in a)e.setAttribute(k,a[k]);(p||svg).appendChild(e);return e};
const rgba=(h,a)=>{const v=parseInt(h.slice(1),16);return `rgba(${v>>16&255},${v>>8&255},${v&255},${a})`};
const defs=el("defs",{}),gl=el("g",{}),gn=el("g",{});
el("text",{class:"lane",x:20,y:468},svg).textContent="NOT TIED TO ONE MEMORY — HELD FOR AS LONG AS SHE CAN REMEMBER, OR LEARNED ALONG THE WAY";
const lines=[];
N.forEach(n=>{n.links.forEach(([t,to])=>{const [c,id]=to.split("/");const b=c==="memories"?pos["m:"+id]:pos[id];if(!b)return;const a=pos[n.id],mx=(a.x+b.x)/2,my=(a.y+b.y)/2-30;
  const dash=t==="about"?"4 4":t==="conflicts"?"2 4":"";
  const l=el("path",{d:`M${a.x},${a.y} Q${mx},${my} ${b.x},${b.y}`,fill:"none",stroke:t==="conflicts"?"#d9708f":t==="because"?"#4cc2a8":"#93a39e","stroke-width":t==="because"?1.6:1.1,"stroke-dasharray":dash,"stroke-linecap":"round","class":"ln off"},gl);
  l.dataset.a=n.id;l.dataset.b=c==="memories"?"m:"+id:id;l.dataset.t=t;
  if(!dash){const L=Math.ceil(l.getTotalLength());l.style.strokeDasharray=L;l.style.strokeDashoffset=L;l.dataset.len=L}   /* solid lines draw themselves, dashed ones fade in */
  lines.push(l)})});
const pg={};PIV.forEach(p=>{const m=MEM[p],P=pos["m:"+p],g=el("g",{class:"n piv",tabindex:0},gn);g.dataset.id="m:"+p;g.style.setProperty("--hc",m.per?"rgba(169,138,232,.55)":"rgba(76,194,168,.55)");const nd=el("g",{class:"node"},g);
  if(m.per){el("rect",{class:"pill",x:P.x-80,y:P.y-25,width:160,height:50,rx:25},nd);el("text",{class:"pt",x:P.x,y:P.y-3},nd).textContent=m.l;el("text",{class:"ps",x:P.x,y:P.y+14},nd).textContent=`a period · ${m.a}–${m.b}`}
  else{const c=el("clipPath",{id:"pc-"+p},defs);el("circle",{cx:P.x,cy:P.y,r:R-3},c);el("circle",{class:"ring",cx:P.x,cy:P.y,r:R},nd);
    el("image",{href:"../memories/img/"+p+"-t.jpg",x:P.x-R+3,y:P.y-R+3,width:2*R-6,height:2*R-6,preserveAspectRatio:"xMidYMid slice","clip-path":`url(#pc-${p})`},nd);
    el("text",{class:"lab",x:P.x,y:P.y-R-12},g).textContent=m.l;el("text",{class:"sub",x:P.x,y:P.y+R+18},g).textContent=`age ${m.a}`}
  pg["m:"+p]=g});
const ng={};N.forEach(n=>{const P=pos[n.id],r=7+n.s/10,c=K[n.k]||"#ccc",g=el("g",{class:"n off",tabindex:0},gn);g.dataset.id=n.id;g.style.setProperty("--hc",rgba(c,.6));const nd=el("g",{class:"node"},g);
  el("circle",{cx:P.x,cy:P.y,r:r,fill:c,"fill-opacity":n.k==="contradiction"?0:.9,stroke:n.k==="contradiction"?"#eef3f1":n.aw==="no"?"#eef3f1":"none","stroke-width":n.aw==="no"?2:1.5,"stroke-dasharray":n.aw==="no"||n.k==="contradiction"?"3 3":""},nd);
  if(n.st==="core")el("circle",{cx:P.x,cy:P.y,r:r+4,fill:"none",stroke:c,"stroke-opacity":.6,"stroke-width":1.2},nd);
  el("text",{class:"nl",x:P.x,y:P.y+r+14},g).textContent=n.l.length>24?n.l.slice(0,23)+"…":n.l;ng[n.id]=g});
function card(v,g,m){fc.classList.add("fade");setTimeout(()=>{vis.innerHTML=v;gist.textContent=g;meta.innerHTML=m;fc.classList.remove("fade")},180)}
function show(id){const on=new Set([id]);lines.forEach(l=>{const h=l.dataset.a===id||l.dataset.b===id;l.classList.toggle("on",h);if(h){on.add(l.dataset.a);on.add(l.dataset.b)}});
  Object.entries({...ng,...pg}).forEach(([k,g])=>g.classList.toggle("on",on.has(k)));svg.classList.add("hl");
  if(id.startsWith("m:")){const p=id.slice(2),m=MEM[p];card(m.per?`<b>a period</b>`:`<img alt="" src="../memories/img/${p}-t.jpg">`,m.g,`<b>${m.l}</b> · memory · ${m.b?`age ${m.a}–${m.b}`:`age ${m.a}`}`);return}
  const n=N.find(x=>x.id===id),x=[];if(n.aw==="no")x.push("she acts on it without knowing it — never says it");if(n.aw==="partly")x.push("she is only half aware of it");if(n.fb)x.push("false, but held");if(n.va!=null)x.push(`valence ${n.va>0?"+":""}${n.va}`);
  const c=K[n.k]||"#ccc",d=Math.round(26+n.s*.5);
  card(`<i style="width:${d}px;height:${d}px;background:${n.k==="contradiction"?"transparent":c};${n.k==="contradiction"||n.aw==="no"?"border:2px dashed #eef3f1;":""}box-shadow:0 0 22px ${rgba(c,.55)}"></i>`,n.g,
    `<b>${n.l}</b> · ${n.k} · strength ${n.s} · ${n.st}${n.since!=null?` · since age ${n.since}`:""}${n.until!=null?` · until about ${n.until}`:""}${x.length?" · "+x.join(" · "):""}`)}
function clear(){svg.classList.remove("hl");lines.forEach(l=>l.classList.remove("on"));Object.values({...ng,...pg}).forEach(g=>g.classList.remove("on"))}
let hold=0,timer=null,cyc=0;const CYCLE=["m:ev1","val1","m:ep1","wound1","m:ev2","contra1","m:ev3","m:ev4"].filter(k=>ng[k]||pg[k]);
const user=k=>{hold=Date.now()+9000;show(k)};
Object.entries({...ng,...pg}).forEach(([k,g])=>{g.addEventListener("mouseenter",()=>user(k));g.addEventListener("focus",()=>user(k));g.addEventListener("click",()=>user(k))});
svg.addEventListener("mouseleave",()=>{hold=Date.now()+2500;clear()});
const reveal=l=>{l.classList.remove("off");if(l.dataset.len)l.style.strokeDashoffset=0};
const hide=l=>{l.classList.add("off");if(l.dataset.len)l.style.strokeDashoffset=l.dataset.len};
const reduce=matchMedia("(prefers-reduced-motion: reduce)").matches;
/* arrival: the nodes come in the order of her life — those without a date first, then age by age up to 45 (the 65-year-old Clara); then one at a time in focus, as on the memories page */
let tm=[];function play(){tm.forEach(clearTimeout);tm=[];clearInterval(timer);clear();Object.values(ng).forEach(g=>g.classList.add("off"));lines.forEach(hide);
  const ages=[...new Set(N.map(n=>n.since).filter(a=>a!=null))].sort((a,b)=>a-b),gap=reduce?0:900,step=(a,i)=>tm.push(setTimeout(()=>{ac.textContent=a===null?"as long as she can remember":`age ${a}`;
    N.filter(n=>n.since===a||(a===null&&n.since==null)).forEach((n,j)=>{const g=ng[n.id];if(reduce)g.classList.remove("off");else tm.push(setTimeout(()=>g.classList.remove("off"),j*70))});
    tm.push(setTimeout(()=>lines.forEach(l=>{const A=ng[l.dataset.a],B=ng[l.dataset.b]||pg[l.dataset.b];if(A&&!A.classList.contains("off")&&B&&!B.classList.contains("off")&&l.classList.contains("off"))reveal(l)}),reduce?0:350))},i*gap));
  step(null,0);ages.forEach((a,i)=>step(a,i+1));
  tm.push(setTimeout(()=>{ac.textContent="Clara at 65 — hover a node";show(CYCLE[0]);cyc=0;if(reduce)return;timer=setInterval(()=>{if(Date.now()<hold)return;cyc=(cyc+1)%CYCLE.length;show(CYCLE[cyc])},3600)},(ages.length+1)*gap+600))}
document.getElementById("preplay").onclick=play;
if("IntersectionObserver" in window){const io=new IntersectionObserver(es=>{if(es.some(e=>e.isIntersecting)){io.disconnect();play()}},{threshold:.35});io.observe(svg)}else play();
})();
"""

v1 = ND["val1"]
legend = "".join(f'<span><i style="background:{c}"></i>{k}</span>' for k, c in KINDS.items() if k != "rule")
def cell(x): return f'<td class="{x[0]}">{x[1]}</td>' if isinstance(x, tuple) else f"<td>{x}</td>"
# page 1: a text personality vs a psyche (Yann, 6 Nov.). The last row changes in 1.3, when card / PNG export carries the
# psyche (hunt finding H5-09) — docs/roadmap.md.
TXT_ROWS = [
    ("what it is", "a few paragraphs", "nodes: convictions with a strength, dates, reasons, links to memories"),
    ("to write", ("y", "minutes — anyone can"), ("n", "longer — a tool proposes nodes from your text, you tick; a generator and an assisted mode are on the 1.3 roadmap")),
    ("what the model receives", ("n", "the whole text, every time"), ("y", "only the nodes the preset holds, with their strength")),
    ("time", ("n", "one snapshot: rewrite it for every age"), ("y", "since, until: the same character at 20 and at 45, with a psyche that changed")),
    ("several uses — work, intimate, all audiences", ("n", "one copy per use, drifting apart"), ("y", "presets that select from one set")),
    ("<i>why</i>", ("n", "implicit — the model improvises"), ("y", "a fear points to the memory that explains it")),
    ("privacy", ("n", "all or nothing"), ("y", "secret, guarded, personal: what a user lived stays theirs")),
    ("works with", ("y", "every app and every model"), ("n", "COF tools; others get it as text (<code>SOUL.md</code>) — card and PNG export do not carry it yet")),
]
TXT_CMP = "".join(f"<tr><th>{r[0]}</th>{cell(r[1])}{cell(r[2])}</tr>" for r in TXT_ROWS)


INDEX = head("AI characters now have an inner life — COF 1.2",
             "COF 1.2 gives AI characters a psyche you can read, edit and take with you: values, beliefs, wants, needs, fears, wounds, each tied to the memory that made it — in the same open file as their face, voice and rights.",
             "AI characters now have an inner life",
             "A psyche you can read, edit and take with you — every conviction tied to the memory that made it.",
             HERO_INDEX, "") + f"""
<header class="hero">
  {TOPI}
  <div class="text">
    <h1>AI characters now have an inner life</h1>
    <div class="rule"></div>
    <p class="sub">A psyche you can read, edit and take with you — every conviction tied to the memory that made it.</p>
    <p class="voice">“Simplicity is a form of respect.”<small>— Clara, a COF character</small></p>
  </div>
  <div class="kicker">COF · CHARACTER OPEN FILE</div>
</header>

<main>
<p class="lede">With memories, an AI character got a past. What it was still missing is what it made of that past: what it values, what it believes, what it wants and fears, the wound it does not talk about, and the things it believes about itself that are not true.</p>
<p>COF 1.2 gives characters a psyche. Not a list of adjectives in a prompt — a set of convictions, each with a weight, a date, a reason, and the memory it comes from. It lives in the same open file as the rest: looks, voice, body, rights, memories. One <code>.cof</code>, readable by any tool, that you can keep, copy, and take elsewhere.</p>

<h2>A conviction, not an adjective</h2>
<p>This is one of the twenty-three nodes of Clara's psyche. Clara is a fictional designer from Lyon, the example character that ships with the format.</p>
<figure class="node">
  <div class="nk"><b>{v1['l']}</b><span class="pill k" style="background:{KINDS['value']}">value</span><span class="pill">core</span></div>
  <p class="gist">{v1['g']}</p>
  <dl class="facts">
    <dt>strength</dt><dd>{v1['s']} out of 100 — it weighs on almost every decision</dd>
    <dt>stability</dt><dd>core — it does not bend in one conversation</dd>
    <dt>since</dt><dd>age {v1['since']}</dd>
    <dt>because</dt><dd>the agency years (a wound) · the first morning in her own studio (a memory)</dd>
    <dt>disclosure</dt><dd>open — she says it freely</dd>
  </dl>
</figure>
<p class="cap">The node as the file holds it: a sentence in each of Clara's languages, a weight, a stability, a date, and links to where it comes from.</p>
<p>“Eco-conscious” in a prompt is an adjective; the model has to guess what it means and when it matters. This is a conviction with a weight, a date and a reason. An agent can bring it up when the conversation turns to work and leave it aside otherwise; it knows a core value does not bend in one conversation; and when you ask <i>why</i>, it has an answer that is not invented on the spot.</p>

<h2>A psyche, as a map</h2>
<figure class="wide graph pgraph" aria-label="Clara's psyche at 65, as a graph">
  <div class="gwrap"><svg id="psvg" viewBox="0 0 1200 660" role="img" aria-label="Clara's psyche: twenty-three nodes hanging under the memories they come from"></svg></div>
  <span class="agec" id="pagec"></span><button class="replay" id="preplay" type="button">▶ replay her life</button>
  <div class="legend">{legend}<span><i style="background:transparent;border:1.5px dashed #eef3f1"></i>held without knowing it</span></div>
  <div class="pfocus" id="pfocus"><div class="vis"></div><div><p class="gist">Hover a node, or let her life play.</p><p class="meta"></p></div></div>
  <figcaption>Clara's psyche, the nodes coming in the order of her life. Above, the memories they hang on; at the bottom, the convictions held for as long as she can remember. Teal lines say <i>because</i>, rose dotted lines <i>conflicts</i>, grey ones <i>supports</i> or <i>about</i>.</figcaption>
</figure>
<p>Eleven kinds of nodes — wound, value, belief, want, need, fear, stance, taste, habit, contradiction, rule — linked to each other and to the memories: <i>because</i>, <i>about</i>, <i>supports</i>, <i>conflicts</i>. And to the people, places and objects of a life: a value learned from a grandmother, a habit that comes with a notebook, a guitar picked up at night. Readers put the rest together: what she thinks of someone, what a place still means, what changed at forty-five.</p>

<h2>Why this changes what a character is</h2>
<h3>The why</h3>
<p>A list of opinions is flat. “She hates heavy interfaces — because of four years at an agency shipping them too fast” is a character.</p>
<blockquote class="quote">Memories without a psyche stay anecdotes; a psyche without memories stays slogans.</blockquote>
<p>Together, each gives the other its meaning — and a character can explain itself instead of improvising an explanation.</p>

<h3>What it hides, and what it doesn't know</h3>
<p>Some convictions are told freely, some only when it matters, some never. And some the character acts on without knowing them. Clara believes, deep down, that <i>if she slows down, she disappears</i>. She would never say it — she doesn't know it. The file does, so an agent can play it the way a good actor would: in what she does, never in what she says.</p>

<h3>What changes, and what doesn't</h3>
<p>A core value holds; a fragile one may move within a conversation. Convictions have a beginning and sometimes an end: at forty-five, “if I slow down, I disappear” gives way to “slowing down is not disappearing”. And how a character stands toward someone — toward you — is a node like the others, with a warmth that can grow, recorded, dated, and yours to take away. No platform exports that today.</p>

<h3>Lies the character believes</h3>
<p>The author can mark a belief as false but held: the character lives by it, the reader knows better. That is where stories come from.</p>

<ul class="axes">
  <li><span>weight</span><div>a strength from 0 to 100, and a stability: core, settled, shifting, fragile</div></li>
  <li><span>time</span><div>since when, and until when — a psyche moves with the character's age</div></li>
  <li><span>self</span><div>open, guarded or secret toward others; aware, half aware or unaware of itself</div></li>
</ul>

<h2>Carefully</h2>
<p>Fiction needs villains, so COF stays permissive: a character may hold ugly beliefs. But a node can be marked inappropriate or dangerous by its author, an agent that acts — with tools, with data — never loads a dangerous node, and the file says what it contains. A tool can <i>propose</i> a psyche from a character sheet; nothing enters the file without the author ticking it. And what a character became with one user is marked personal, and leaves the file only if you ask it to.</p>

<h2>Open, like the rest of COF</h2>
<p>The psyche is a public specification, with a reference implementation and tools that read it today. No account, no platform, no lock-in: the file is yours.</p>
<div class="tools">
  <a href="../viewer/#clara/psyche"><b>Explorer</b><span>Clara's psyche as a graph, with a cursor through her life — nothing uploaded</span></a>
  <a href="../builder/"><b>Builder</b><span>a Psyche step: write the inner life of your own character</span></a>
  <a href="https://github.com/yannsouetre/cof/blob/main/rfcs/0004-psyche-graph.md"><b>RFC 0004</b><span>the psyche, with the reasoning behind each choice — and RFC 0005, people, places and objects</span></a>
  <a href="https://github.com/yannsouetre/ComfyUI-COF"><b>ComfyUI nodes</b><span>a COF Psyche node: who the character is, as text, for your workflows</span></a>
</div>
<p class="cap" style="margin-top:14px">Agents get it as text: <code>cof export --format agent</code> writes a <code>SOUL.md</code> whose « Who she is » is rendered from the nodes. Every 1.0 and 1.1 file stays valid.</p>

<h2>A text personality, or a psyche?</h2>
<p>Most characters today live in a few paragraphs: a JSON card, a system prompt. That works, and it is not going away. Here is what changes when the same character gets a psyche.</p>
<table class="cmp"><thead><tr><th></th><th>a text personality<br><span class="hint">a card, a system prompt</span></th><th>a COF psyche</th></tr></thead><tbody>{TXT_CMP}</tbody></table>
<p class="cap">Complementary, not rivals: the psyche ends up as text too — but chosen, dated text, with its reasons.</p>

<h2>How many convictions make a person?</h2>
<p>Natural questions follow. How many nodes does a character need — and a person? What are the popular profiles worth, the Big Five, a Myers-Briggs type, an Enneagram number, a sign? And isn't the real future of a character in a model's weights rather than in a file? A companion page starts from one refusal of Clara's and asks <i>why</i> five times, down to the four years that began at twenty-four. Then it gives what psychology has actually counted, with its sources, a simulator to test your own numbers, and the three ways of keeping a mind side by side — a description, a graph, weights — with what each can and cannot do.</p>
<p class="btns" style="margin:18px 0 0"><a class="btn main" href="{COMPANION}">How many convictions make a person? →</a></p>
</main>

<section class="close">
  <p class="voice">She knows why she works the way she does. She does not know yet what she will think of you.</p>
  <div class="btns row3">
    <a class="btn main" href="../viewer/#clara/psyche">Open Clara's psyche</a>
    <a class="btn" href="https://github.com/yannsouetre/cof/blob/main/rfcs/0004-psyche-graph.md">Read the specification</a>
    <a class="btn" href="../builder/">Give your character an inner life</a>
  </div>
</section>
""" + tail("<script>" + GRAPH_JS.replace("__N__", json.dumps(N, ensure_ascii=False)).replace("__M__", json.dumps(MEM, ensure_ascii=False)).replace("__K__", json.dumps(KINDS)) + "</script>")

# ---------------------------------------------------------------------------------------------------- why.html
def card(i, n, why, img=None, cls="", color=None):
    extra = []
    if n.get("aw") == "no": extra.append("unaware — she never says it")
    if n.get("fb"): extra.append("false, but held")
    if n.get("va") is not None: extra.append(f"valence {n['va']:+d}")
    m = meta(n) + ("" if not extra else " · " + " · ".join(extra))
    return f"""<div class="step{(' ' + cls) if cls else ''}" hidden><div class="dot" style="background:{color or KINDS.get(n['k'], '#ccc')}">{i}</div><div class="card"><p class="t">{n['l']}</p><p class="m">{m}</p><p class="g">{n['g']}</p>{f'<img src="{img}" alt="">' if img else ''}<p class="why">{why}</p></div></div>"""

ep1, ev2 = MEM["ep1"], MEM["ev2"]
STEPS = "\n".join([
    card(1, ND["taste2"], "The first answer is a taste: what she cannot stand. Strong, and quick — but a taste alone would only make her grumble, not refuse."),
    card(2, ND["val1"], "Under it, a value, at the core of who she is. This is what turns a dislike into a no. It has a date, 28 — and two reasons.", "../memories/img/ev2.jpg"),
    card(3, ND["wound1"], "The first reason is a wound. Four years she does not tell as a story, but that shapes how she works."),
    f"""<div class="step" hidden><div class="dot" style="background:#a98ae8">4</div><div class="card"><p class="t">{ep1['l'].capitalize()}</p><p class="m">memory · a period · age {ep1['a']}–{ep1['b']}</p><p class="g">{ep1['g']}</p><p class="why">And under the wound, the memory itself. Here the chain ends: not in an adjective, in a life.</p></div></div>""",
    card(5, ND["bel3"], "One more layer, which she could not give you herself. Clara believes, without knowing it, that if she slows down she disappears. It is why she offers the faster option first, and why she works at night. An agent reading the file plays it — in what she does, never in what she says.", cls="hidden-layer"),
])

CMP_ROWS = [
    ("what it holds", "a portrait in a few lines", "convictions, with weights, dates, reasons and the memories behind them", "habits of speech, reflexes, a style no text pins down"),
    ("can you read it?", ("y", "yes"), ("y", "yes — node by node"), ("n", "no — millions of numbers")),
    ("can you correct it by hand?", ("y", "yes"), ("y", "yes, one node at a time"), ("n", "only by training again")),
    ("can it answer <i>why</i>?", ("n", "rarely — it improvises"), ("y", "yes, link by link"), ("n", "no — it can only act")),
    ("can it keep a secret, or not know itself?", ("n", "everything is on the page"), ("y", "open, guarded, secret; aware or not"), ("n", "not on purpose")),
    ("does it move with time?", ("n", "one snapshot"), ("y", "since, until, revisions"), ("n", "one training run")),
    ("size", "about a kilobyte", "Clara: 12 KB for 23 nodes; a whole modelled life, a few hundred KB", "tens to hundreds of megabytes"),
    ("what it takes to make", "writing it by hand", "writing it by hand, or a tool that proposes and you tick", "data, GPUs, hours of training"),
    ("works with", "any model", "any model, today", "one model family"),
]
CMP = "".join(f"<tr><th>{r[0]}</th>{cell(r[1])}{cell(r[2])}{cell(r[3])}</tr>" for r in CMP_ROWS)

WHY_JS = """
(function(){const steps=[...document.querySelectorAll(".chain .step")],b=document.getElementById("whyb"),r=document.getElementById("whyr"),end=document.getElementById("whyend");let i=0;
const L=["Why?","Why?","And why?","Where does that come from?","Is that all?"];
function go(){if(i>=steps.length)return;const s=steps[i];s.hidden=false;requestAnimationFrame(()=>requestAnimationFrame(()=>s.classList.add("on")));i++;
  if(i<steps.length)b.textContent=L[i]||"Why?";else{b.disabled=true;b.textContent="That is the whole chain";end.hidden=false;requestAnimationFrame(()=>end.classList.add("on"))}
  s.scrollIntoView({behavior:"smooth",block:"nearest"})}
b.onclick=go;r.onclick=()=>{steps.forEach(s=>{s.hidden=true;s.classList.remove("on")});end.hidden=true;end.classList.remove("on");i=0;b.disabled=false;b.textContent=L[0]};
})();
"""

# ---------------------------------------------------------------------------------------------------- how-many.html
# Measures of Clara's psyche, read from example 10: what one node weighs, how long a gist is, how many hang on a memory.
PSY_FILES = sum((EX / "elements/psyche" / vid / "psyche-node.json").stat().st_size for vid in PV)
PSY_MAN = sum(len(json.dumps({vid: v}, ensure_ascii=False).encode()) for vid, v in PV.items())
_G = [json.loads((EX / "elements/psyche" / vid / "psyche-node.json").read_text("utf-8")).get("gist") or {} for vid in PV]
LANGS = sorted({k for g in _G for k in g})
GIST = sum(len(g.get(l, "").encode()) for g in _G for l in LANGS) / (len(_G) * len(LANGS))   # bytes of one gist in one language
GIST_EN = sum(len(g.get("en", "")) for g in _G) / len(_G)                                    # characters of the English gist
PER_NODE = (PSY_FILES + PSY_MAN) / len(PV)                                                   # node file + its manifest entry
FIXED = PER_NODE - len(LANGS) * (GIST + 12)                                                  # what does not depend on the languages
TIED = sum(1 for n in N if any(to.startswith("memories/") for _, to in n["links"])) / len(N)
LINKS = sum(len(n["links"]) for n in N)
WEDDING = (EX / "elements/memories/ev5/ev5.jpg").stat().st_size
COF_FILE = (ROOT / "viewer/samples/clara-mercier.cof").stat().st_size
CLARA_AGE = 65
CLARA_CURVE = [[t, sum(1 for n in N if (n["since"] is None or n["since"] <= t) and (n["until"] is None or t < n["until"])),
                sum(1 for n in N if n["until"] is not None and n["until"] <= t)] for t in range(CLARA_AGE + 1)]
HELD_65 = CLARA_CURVE[-1][1]
# « Who she is » as `cof psyche text --preset en-agent` renders it: 1,943 characters for 22 nodes, i.e. a header of about
# 430 characters and, per node, its gist plus about 8 characters of list marks and markers (measured 4 Nov. 2026).
TEXT_HEAD, TEXT_PER = 430, 8

SIM = {"F": round(FIXED), "LX": 12, "G": round(GIST), "GEN": round(GIST_EN), "HEAD": TEXT_HEAD, "PER": TEXT_PER,
       "PSY": PSY_FILES + PSY_MAN, "WED": WEDDING, "COF": COF_FILE, "CLARA": CLARA_CURVE, "N": len(N)}

HOWMANY_CSS = """
/* the companion page: tiles, the ladder of counts, the simulator (same language as memories/how-much.html) */
.tiles{display:grid;grid-template-columns:repeat(4,1fr);gap:12px;margin:26px 0 8px}
.tile{background:var(--panel);border:1px solid var(--line);border-radius:14px;padding:16px 16px 14px}
.tile b{display:block;font:700 30px/1 Bricolage,sans-serif;color:var(--teal);letter-spacing:-.02em;margin-bottom:8px}
.tile span{font-size:13.5px;color:var(--muted);line-height:1.4;display:block}
.ladder{list-style:none;margin:26px 0 6px;padding:18px 18px 10px;background:var(--panel);border:1px solid var(--line);border-radius:18px}
.ladder li{display:grid;grid-template-columns:230px 1fr 92px;gap:12px;align-items:center;padding:6px 0}
.ladder .l{font-size:14.5px;color:#d9e0dd;line-height:1.25}.ladder .l small{display:block;font:500 11.5px PlexMono,monospace;color:#8b9b97;margin-top:2px}
.ladder .tr{position:relative;height:14px;border-radius:7px;background:repeating-linear-gradient(90deg,transparent 0,transparent calc(20% - 1px),#2a3533 calc(20% - 1px),#2a3533 20%)}
.ladder .tr i{position:absolute;top:2px;height:10px;border-radius:5px;background:#35a38b;min-width:10px}
.ladder li.me .tr i{background:#9a7ae0}.ladder li.me .l{color:#cbbcf0}
.ladder .v{font:500 13px PlexMono,monospace;color:var(--mint);text-align:right}
.ladder .ax{display:grid;grid-template-columns:230px 1fr 92px;gap:12px;font:500 11px PlexMono,monospace;color:#7d8d89;padding:6px 0 0;border-top:1px solid var(--line);margin-top:6px}
.ladder .ax span{position:relative;height:14px}.ladder .ax b{position:absolute;top:0;transform:translateX(-50%);font-weight:500;white-space:nowrap}.ladder .ax b:first-child{transform:none}.ladder .ax b:last-child{transform:translateX(-100%)}
.sim{background:var(--panel);border:1px solid var(--line);border-radius:18px;padding:22px;margin:28px 0 10px}
.sim .row{display:grid;grid-template-columns:1fr 1fr;gap:18px}
.sim fieldset{border:1px solid var(--line);border-radius:12px;padding:12px 14px 14px;margin:0 0 14px;min-width:0}
.sim legend{font:500 12px PlexMono,monospace;color:var(--mint);letter-spacing:.06em;text-transform:uppercase;padding:0 6px}
.sim label{display:block;font-size:13.5px;color:var(--muted);margin:8px 0 3px}.sim label b{color:var(--ink);font-weight:500}
.sim input[type=number],.sim select{width:100%;padding:7px 9px;border:1px solid var(--line);border-radius:8px;background:var(--bg);color:var(--ink);font:500 14px PlexMono,monospace}
.sim input[type=range]{width:100%;accent-color:var(--teal)}
.sim .g2{display:grid;grid-template-columns:1fr 1fr;gap:10px}.sim .g2>div{display:flex;flex-direction:column;justify-content:flex-end}
.sim .hint{font-size:12.5px;color:#7d8d89;margin:6px 0 0}
.scen{display:flex;flex-wrap:wrap;gap:8px;margin:0 0 18px}
.scen button{font:500 13px Plex,sans-serif;color:var(--ink);background:var(--bg);border:1px solid var(--line);border-radius:999px;padding:7px 13px;cursor:pointer}
.scen button:hover,.scen button:focus-visible,.scen button.on{border-color:var(--teal);color:var(--teal);outline:none}
/* wide view of the simulator (Yann, 7 Nov.): the panel moves into a full-width overlay, controls left, results right; the cross or Escape puts it back */
.wbtn{position:absolute;top:10px;right:10px;width:32px;height:32px;display:flex;align-items:center;justify-content:center;font:500 16px/1 PlexMono,monospace;color:var(--muted);background:var(--bg);border:1px solid var(--line);border-radius:999px;padding:0;cursor:pointer}.scen{padding-right:44px}.wbtn:hover,.wbtn:focus-visible{color:var(--teal);border-color:var(--teal);outline:none}
.wover{position:fixed;inset:0;z-index:60;background:rgba(5,8,12,.78);backdrop-filter:blur(6px);overflow:auto;padding:3vh 3vw;display:flex;align-items:flex-start;justify-content:center}
.wover .wpanel{width:min(1560px,94vw);margin:auto;display:grid;grid-template-columns:minmax(360px,5fr) minmax(0,7fr);gap:26px;align-items:start;padding:26px 28px 24px;position:relative}
.wover .wpanel .row{grid-template-columns:1fr}.wover .wpanel .wl,.wover .wpanel .wr{min-width:0}.wover .wpanel .wbtn{display:none}
.wclose{position:absolute;top:10px;right:12px;width:36px;height:36px;border-radius:50%;border:1px solid var(--line);background:var(--bg);color:var(--ink);font:500 20px/1 Plex,sans-serif;cursor:pointer}.wclose:hover,.wclose:focus-visible{border-color:var(--teal);color:var(--teal);outline:none}
@media (max-width:1000px){.wover .wpanel{grid-template-columns:1fr}}

.res{background:linear-gradient(135deg,#102a25,#0f1d2b);border:1px solid var(--line);border-radius:14px;padding:18px 20px;margin-bottom:12px}
.res .t{font:700 44px/1 Bricolage,sans-serif;color:var(--ink);letter-spacing:-.02em}.res .t small{font:500 16px Plex,sans-serif;color:var(--muted);letter-spacing:0;margin-left:8px}
.res .s{font-size:13.5px;color:var(--muted);margin-top:8px}
.kpis{display:grid;grid-template-columns:repeat(4,1fr);gap:10px;margin-bottom:14px}
.kpi{background:var(--bg);border:1px solid var(--line);border-radius:10px;padding:10px 12px}
.kpi b{display:block;font:700 20px/1.1 Bricolage,sans-serif;color:var(--ink)}.kpi span{font-size:12px;color:var(--muted);line-height:1.35;display:block;margin-top:3px}
.simchart{position:relative;background:var(--bg);border:1px solid var(--line);border-radius:12px;padding:10px 10px 4px}
.simchart svg{display:block;width:100%;height:230px;font-family:Plex,system-ui,sans-serif;outline:none}
.simchart svg:focus-visible{box-shadow:0 0 0 2px var(--teal);border-radius:8px}
.simchart .lg{display:flex;flex-wrap:wrap;gap:4px 16px;font-size:12.5px;color:var(--muted);margin:2px 4px 6px}
.simchart .lg i{display:inline-block;width:14px;height:3px;border-radius:2px;margin-right:6px;vertical-align:3px}
.simchart .tip{position:absolute;pointer-events:none;background:#0b100f;border:1px solid var(--line);border-radius:8px;padding:6px 9px;font:500 12px/1.5 PlexMono,monospace;color:var(--ink);white-space:nowrap;opacity:0;transition:opacity .15s}
.simchart .tip.on{opacity:1}
.sbars{margin-top:16px}.sbars h4{font:500 12px PlexMono,monospace;color:var(--mint);letter-spacing:.06em;text-transform:uppercase;margin:14px 0 6px}
.sbars .b{display:grid;grid-template-columns:190px 1fr 84px;gap:10px;align-items:center;font-size:13px;color:var(--muted);margin:6px 0}
.sbars .b .t{height:12px;background:var(--bg);border-radius:4px;overflow:hidden}.sbars .b .f{display:block;height:100%;background:#3a4a47;border-radius:0 4px 4px 0}
.sbars .b.me{color:var(--teal)}.sbars .b.me .f{background:var(--teal)}.sbars .b .x{text-align:right;font:500 12px PlexMono,monospace}
table.prof{width:100%;border-collapse:collapse;margin:22px 0 8px;font-size:14.5px}
table.prof th,table.prof td{text-align:left;vertical-align:top;padding:9px 8px;border-bottom:1px solid var(--line)}
table.prof thead th{font:500 12px PlexMono,monospace;color:var(--mint);letter-spacing:.05em;text-transform:uppercase}
table.prof tbody th{font-weight:500;color:var(--ink);width:22%}
.refs{font-size:14px;color:var(--muted)}.refs p{margin:0 0 9px;color:var(--muted)}.refs a{word-break:break-word}
.refs h3{font:500 13px PlexMono,monospace;color:var(--mint);letter-spacing:.06em;text-transform:uppercase;margin:22px 0 8px}
@media (max-width:720px){.tiles{grid-template-columns:1fr 1fr}.sim .row{grid-template-columns:1fr}.kpis{grid-template-columns:1fr 1fr}
 .ladder li,.ladder .ax{grid-template-columns:1fr 70px}.ladder .l{grid-column:1/-1}.ladder .ax>span:first-child,.ladder .ax b.odd{display:none}.hero .top .crumb{display:none}
 .sbars .b{grid-template-columns:118px 1fr 70px}.res .t{font-size:36px}table.prof{font-size:13px}table.prof th,table.prof td{padding:7px 4px}}
"""

# ---- the ladder: what has been counted, on one logarithmic axis (1 to 100,000) — not counts of the same thing
LADDER = [
    ("The Big Five", "five broad domains of personality", 5, 5, False),
    ("Basic human values", "Schwartz 1992: ten · 2012: nineteen", 10, 19, False),
    ("“Who am I?”", "the Twenty Statements Test asks for twenty", 20, 20, False),
    ("Clara, as written", f"example 10 of the format · {len(N)} nodes", len(N), len(N), True),
    ("Facets of the NEO PI-R", "six under each of the five domains", 30, 30, False),
    ("The Rokeach Value Survey", "18 terminal + 18 instrumental values", 36, 36, False),
    ("A main character, written with care", "our estimate", 50, 150, True),
    ("A whole life, modelled", "our estimate, with what began and ended", 300, 600, True),
    ("The upper bound we tested", "the tools still draw it", 1000, 1000, True),
    ("English words for stable traits", "Allport & Odbert 1936, “column I”", 4504, 4504, False),
    ("English words about personality", "Allport & Odbert 1936, all four columns", 17953, 17953, False),
]
def _lx(v): return __import__("math").log10(v) / 5 * 100
def _ladder_row(l, s, lo, hi, me):
    a, b = _lx(lo), _lx(hi)
    val = f"{lo:,}" if lo == hi else f"{lo:,}–{hi:,}"
    return (f'<li class="{"me" if me else ""}"><span class="l">{l}<small>{s}</small></span>'
            f'<span class="tr" title="{l}: {val}"><i style="left:calc({a:.2f}% - 5px);width:calc({b - a:.2f}% + 10px)"></i></span><span class="v">{val}</span></li>')
LADDER_HTML = ('<ul class="ladder" aria-label="Counts that psychology and fiction writing have produced, and COF\'s estimates, on a logarithmic scale">'
               + "".join(_ladder_row(*r) for r in LADDER)
               + '<li class="ax" aria-hidden="true"><span></span><span>' + "".join(f'<b style="left:{i * 20}%"{" class=odd" if i in (1, 3) else ""}>{t}</b>' for i, t in enumerate(["1", "10", "100", "1 k", "10 k", "100 k"])) + '</span><span></span></li></ul>')

PROFILES = [
    ("Big Five", "five scores, 0–100: openness, conscientiousness, extraversion, agreeableness, neuroticism",
     "the best-validated model in personality psychology; links to life outcomes largely replicate",
     "a score of 70 or more, or 30 or less, proposes one or two candidates for that pole"),
    ("Myers-Briggs type", "four letters, sixteen types",
     "the four scales track four of the Big Five; the types themselves are not well supported, and a letter near the middle often flips on retest",
     "three or four common readings of the type: a value, a taste, a habit, a fear or a want"),
    ("Enneagram", "one type out of nine, with its basic fear and desire",
     "mixed evidence of reliability and validity; the nine types are not recovered as nine factors",
     "the basic fear, the basic desire, a value and a habit of the type"),
    ("Astrology", "a sun sign, twelve",
     "no predictive validity in controlled, double-blind tests",
     "three or four traits commonly attached to the sign"),
]
PROF_HTML = "".join(f"<tr><th>{a}</th><td>{b}</td><td>{c}</td><td>{d}</td></tr>" for a, b, c, d in PROFILES)

WIDE_JS = '(function(){const P=document.getElementById("sim");if(!P)return;P.style.position="relative";const LEFT=[".scen",".row"];const b=document.createElement("button");b.type="button";b.className="wbtn";b.textContent="⤢";b.setAttribute("aria-label","Open the simulator in a wide view");P.appendChild(b);let over=null,order=null,ph=null;function redraw(){window.dispatchEvent(new Event("resize"));const i=P.querySelector("input");if(i)i.dispatchEvent(new Event("input",{bubbles:true}))}function open(){if(over)return;order=[...P.children];ph=document.createComment("sim");P.parentNode.insertBefore(ph,P);over=document.createElement("div");over.className="wover";over.setAttribute("role","dialog");over.setAttribute("aria-modal","true");over.setAttribute("aria-label","Simulator, wide view");const wl=document.createElement("div");wl.className="wl";const wr=document.createElement("div");wr.className="wr";for(const c of order){if(c===b)continue;(LEFT.some(s=>c.matches(s))?wl:wr).appendChild(c)}P.classList.add("wpanel");P.appendChild(wl);P.appendChild(wr);const x=document.createElement("button");x.type="button";x.className="wclose";x.innerHTML="&times;";x.setAttribute("aria-label","Close the wide view");x.onclick=close;P.appendChild(x);over.appendChild(P);document.body.appendChild(over);document.body.style.overflow="hidden";over.addEventListener("click",e=>{if(e.target===over)close()});setTimeout(()=>{redraw();x.focus()},30)}function close(){if(!over)return;const x=P.querySelector(".wclose");if(x)x.remove();for(const c of order)P.appendChild(c);P.querySelectorAll(":scope>.wl,:scope>.wr").forEach(e=>e.remove());P.classList.remove("wpanel");ph.parentNode.insertBefore(P,ph);ph.remove();over.remove();over=null;document.body.style.overflow="";setTimeout(()=>{redraw();b.focus()},30)}b.addEventListener("click",open);document.addEventListener("keydown",e=>{if(e.key==="Escape"&&over)close()})})();'

SIM_JS = """
(function(){
const D=__SIM__,$=s=>document.querySelector(s);
const nf=n=>Math.round(n).toLocaleString("en-US");
function fb(b){if(!isFinite(b)||b<=0)return "0 KB";if(b<1e6)return (b/1e3).toLocaleString("en-US",{maximumFractionDigits:b<1e4?1:0})+" KB";if(b<1e9)return (b/1e6).toLocaleString("en-US",{maximumFractionDigits:b<1e7?1:0})+" MB";return (b/1e9).toLocaleString("en-US",{maximumFractionDigits:1})+" GB"}
function ft(t){return t<1e4?nf(t):(t/1e3).toLocaleString("en-US",{maximumFractionDigits:t<1e5?1:0})+" k"}
const LEN={short:D.G,sentence:150,paragraph:300};
/* expected numbers, year by year: new convictions from age 5 at a steady rate; each held one is let go with the same
   yearly probability h; a share r of those let go are revised into a new node (derives_from), which joins the pool */
function run(A,R,h,r){let held=0,ever=0,end=0;const rows=[[0,0,0]];for(let t=0;t<A;t++){const e=held*h;held-=e;end+=e;const nw=(t>=5?R/10:0)+e*r;held+=nw;ever+=nw;rows.push([t+1,held,end])}return {held,ever,end,rows}}
function solve(A,R,p,r){if(p<=0)return run(A,R,0,r);let lo=0,hi=1;for(let i=0;i<48;i++){const m=(lo+hi)/2,s=run(A,R,m,r);if(s.ever>0&&s.end/s.ever<p)lo=m;else hi=m}return run(A,R,lo,r)}
const num=(id,lo,hi,def)=>{let v=parseFloat($("#"+id).value);if(!isFinite(v))v=def;return Math.min(hi,Math.max(lo,v))};
let S=null,cur=null;
function calc(){
 const A=Math.round(num("sAge",1,120,65)),R=num("sRate",0,500,4),p=num("sEnd",0,60,9)/100,r=num("sRev",0,100,50)/100,L=Math.round(num("sLang",1,12,2)),g=LEN[$("#sLen").value]||D.G,m=num("sMem",0,100,39)/100,k=Math.round(num("sTurn",1,200,8));
 $("#sEndV").textContent=Math.round(p*100)+" %";$("#sRevV").textContent=Math.round(r*100)+" %";$("#sMemV").textContent=Math.round(m*100)+" %";
 S=solve(A,R,p,r);const per=D.F+L*(g+D.LX),bytes=S.ever*per,gt=g*D.GEN/D.G,tokAll=(D.HEAD+S.held*(gt+D.PER))/4,tokTurn=Math.min(k,S.held)*(gt+D.PER)/4;
 $("#oHeld").firstChild.textContent=nf(S.held);
 $("#oSub").textContent=`at ${A}: ${nf(S.ever)} formed in all (${nf(S.ever-S.end*r)} new, ${nf(S.end*r)} revision${Math.round(S.end*r)===1?"":"s"}), ${nf(S.end)} let go — every one stays in the file, closed by its until`;
 $("#oSize").textContent=fb(bytes);$("#oAll").textContent=ft(tokAll);$("#oTurn").textContent=ft(tokTurn);$("#oMem").textContent=nf(S.ever*m);
 $("#oSizeS").textContent=`${nf(S.ever)} nodes × ${nf(per)} bytes, ${L} language${L>1?"s":""}`;
 $("#oTurnS").textContent=`the ${Math.min(k,Math.round(S.held))} nodes the moment calls for`;
 draw();bars(bytes,tokAll,tokTurn)}
/* ---- held and let go over the years, Clara's own curve when it fits */
const svg=$("#simsvg"),tip=$("#simtip"),NS="http://www.w3.org/2000/svg";
function draw(){const W=Math.max(280,svg.clientWidth||680),H=230,l=44,rt=W-14,tp=14,b=H-28;svg.setAttribute("viewBox",`0 0 ${W} ${H}`);
 const rows=S.rows,A=rows.length-1,top=Math.max(4,...rows.map(x=>Math.max(x[1],x[2])));const clara=top<=120&&A>=20;const ymax=niceMax(Math.max(top,clara?Math.max(...D.CLARA.map(c=>c[1])):0));
 const x=a=>l+(a/Math.max(1,A))*(rt-l),y=v=>b-(v/ymax)*(b-tp);
 const dv=ymax/Math.pow(10,Math.floor(Math.log10(ymax)))===2?4:5;let s="";for(let i=0;i<=dv;i++){const v=ymax*i/dv;s+=`<line x1="${l}" x2="${rt}" y1="${y(v)}" y2="${y(v)}" stroke="${i?"#222c2a":"#3a4a47"}" stroke-width="1"/><text x="${l-8}" y="${y(v)+4}" text-anchor="end" style="font:500 11px PlexMono,monospace;fill:#7d8d89">${nf(v)}</text>`}
 const step=A>60?20:A>24?10:5;for(let a=0;a<=A;a+=step)if(x(a)<rt-34)s+=`<text x="${x(a)}" y="${b+18}" text-anchor="middle" style="font:500 11px PlexMono,monospace;fill:#7d8d89">${a}</text>`;
 s+=`<text x="${rt}" y="${b+18}" text-anchor="end" style="font:500 11px PlexMono,monospace;fill:#7d8d89">age</text>`;
 const pth=k=>rows.map((q,i)=>(i?"L":"M")+x(q[0]).toFixed(1)+" "+y(q[k]).toFixed(1)).join(" ");
 s+=`<path d="${pth(1)} L${x(A)} ${b} L${x(0)} ${b} Z" fill="rgba(53,163,139,.16)"/><path d="${pth(1)}" fill="none" stroke="#35a38b" stroke-width="2"/>`;
 s+=`<path d="${pth(2)}" fill="none" stroke="#c08528" stroke-width="2" stroke-dasharray="6 4"/>`;
 if(clara){const c=D.CLARA.filter(q=>q[0]<=A);s+=`<path d="${c.map((q,i)=>(i?"L":"M")+x(q[0]).toFixed(1)+" "+y(q[1]).toFixed(1)).join(" ")}" fill="none" stroke="#9a7ae0" stroke-width="2" stroke-dasharray="2 3"/>`}
 $("#lgClara").hidden=!clara;
 const last=rows[A];s+=`<text x="${x(A)-4}" y="${y(last[1])-8}" text-anchor="end" style="font:500 12px Plex,sans-serif;fill:#dfe8e5">held · ${nf(last[1])}</text>`;
 if(last[2]>=.5)s+=`<text x="${x(A)-4}" y="${Math.min(b-6,y(last[2])+16)}" text-anchor="end" style="font:500 12px Plex,sans-serif;fill:#dfe8e5">let go · ${nf(last[2])}</text>`;
 s+=`<line id="simx" x1="0" x2="0" y1="${tp}" y2="${b}" stroke="#93a39e" stroke-width="1" opacity="0"/><rect x="${l}" y="${tp}" width="${rt-l}" height="${b-tp}" fill="transparent" id="simhit"/>`;
 svg.innerHTML=s;svg.setAttribute("aria-label",`Convictions held and let go from birth to age ${A}: ${nf(last[1])} held, ${nf(last[2])} let go at the end.`);
 const hit=$("#simhit");const at=a=>{a=Math.max(0,Math.min(A,Math.round(a)));cur=a;const q=rows[a],X=x(a);const ln=$("#simx");ln.setAttribute("x1",X);ln.setAttribute("x2",X);ln.setAttribute("opacity",".7");
  const cl=clara&&a<=D.CLARA.length-1?`<br>Clara · ${D.CLARA[a][1]}`:"";tip.innerHTML=`age ${a}<br>held · ${nf(q[1])}<br>let go · ${nf(q[2])}${cl}`;tip.classList.add("on");
  const bw=svg.getBoundingClientRect().width,sx=bw/W;tip.style.left=Math.min(bw-tip.offsetWidth-4,Math.max(4,X*sx+12))+"px";tip.style.top="18px"};
 hit.addEventListener("pointermove",e=>{const r=svg.getBoundingClientRect(),sx=W/r.width;at(((e.clientX-r.left)*sx-l)/(rt-l)*A)});
 hit.addEventListener("pointerleave",()=>{tip.classList.remove("on");$("#simx").setAttribute("opacity","0")});
 svg.onkeydown=e=>{if(!["ArrowLeft","ArrowRight","Home","End"].includes(e.key))return;e.preventDefault();const a=cur==null?A:cur;at(e.key==="Home"?0:e.key==="End"?A:a+(e.key==="ArrowLeft"?-1:1))};
 svg.onblur=()=>{tip.classList.remove("on");const v=$("#simx");if(v)v.setAttribute("opacity","0")}}
function niceMax(v){const p=Math.pow(10,Math.floor(Math.log10(v))),n=v/p;return (n<=1?1:n<=2?2:n<=2.5?2.5:n<=5?5:10)*p}
/* ---- the weight and the tokens, against things one knows */
function bars(bytes,all,turn){const mk=(el,list,f,lo,hi)=>{el.innerHTML="";list.sort((a,b)=>a[1]-b[1]).forEach(r=>{const me=r[0].startsWith("→"),w=Math.max(1.5,Math.min(100,(Math.log10(Math.max(r[1],1))-lo)/(hi-lo)*100));
  const d=document.createElement("div");d.className="b"+(me?" me":"");d.innerHTML='<span></span><span class="t"><i class="f"></i></span><span class="x"></span>';d.firstChild.textContent=r[0];d.querySelector(".f").style.width=w+"%";d.lastChild.textContent=f(r[1]);el.appendChild(d)})};
 mk($("#bSize"),[["Clara's whole psyche",D.PSY],["One picture of her wedding",D.WED],["Clara's whole file (.cof)",D.COF],["→ this psyche",bytes]],fb,3,Math.max(8,Math.log10(bytes)+.5));
 mk($("#bTok"),[["→ per turn, a handful",turn],["→ all of it, as text",all],["Clara's « Who she is »",(D.HEAD+(D.N-1)*(D.GEN+D.PER))/4],["A 128,000-token context",128000]],ft,1,Math.max(5.5,Math.log10(all)+.5))}
const SC={clara:{sAge:65,sRate:3.7,sEnd:9,sRev:50,sLang:2,sLen:"short",sMem:39,sTurn:8},
 novel:{sAge:45,sRate:25,sEnd:20,sRev:50,sLang:2,sLen:"sentence",sMem:40,sTurn:10},
 life:{sAge:80,sRate:60,sEnd:35,sRev:60,sLang:2,sLen:"sentence",sMem:50,sTurn:12},
 bound:{sAge:90,sRate:95,sEnd:35,sRev:60,sLang:2,sLen:"sentence",sMem:50,sTurn:12}};
document.querySelectorAll("#simscen button").forEach(b=>b.onclick=()=>{const s=SC[b.dataset.s];for(const k in s)$("#"+k).value=s[k];document.querySelectorAll("#simscen button").forEach(x=>{x.classList.toggle("on",x===b);x.setAttribute("aria-pressed",x===b)});calc()});
document.querySelectorAll("#sim input,#sim select").forEach(i=>i.addEventListener("input",()=>{document.querySelectorAll("#simscen button").forEach(x=>{x.classList.remove("on");x.setAttribute("aria-pressed","false")});calc()}));
let rz;window.addEventListener("resize",()=>{clearTimeout(rz);rz=setTimeout(draw,120)});
calc();
})();
"""

SIM_HTML = f"""<div class="sim" id="sim">
  <div class="scen" id="simscen" role="group" aria-label="Presets">
    <button type="button" data-s="clara" class="on" aria-pressed="true">Clara, as written</button>
    <button type="button" data-s="novel" aria-pressed="false">A novel's main character</button>
    <button type="button" data-s="life" aria-pressed="false">A whole life, modelled</button>
    <button type="button" data-s="bound" aria-pressed="false">The upper bound we tested</button>
  </div>
  <div class="row">
    <div>
      <fieldset><legend>A life</legend>
        <div class="g2">
          <div><label for="sAge">Age</label><input id="sAge" type="number" min="1" max="120" value="65"></div>
          <div><label for="sRate">New convictions per decade</label><input id="sRate" type="number" min="0" max="500" step="0.1" value="3.7"></div>
        </div>
        <p class="hint">Formed at a steady rate from the age of five. Clara's author wrote about four a decade; a novelist knows far more.</p>
      </fieldset>
      <fieldset><legend>What changes</legend>
        <label for="sEnd">Share let go by now: <b id="sEndV">9 %</b></label>
        <input id="sEnd" type="range" min="0" max="60" step="1" value="9">
        <label for="sRev">Of those, revised into a new conviction rather than dropped: <b id="sRevV">50 %</b></label>
        <input id="sRev" type="range" min="0" max="100" step="5" value="50">
        <p class="hint">Clara at 45 let go of two: one revised (“if I slow down, I disappear” became “slowing down is not disappearing”), one dropped. People underestimate how much they will still change (Quoidbach et al., 2013).</p>
      </fieldset>
    </div>
    <div>
      <fieldset><legend>The file</legend>
        <label for="sLen">Each conviction says</label><select id="sLen"><option value="short">a short line, like Clara's</option><option value="sentence">a full sentence</option><option value="paragraph">a short paragraph</option></select>
        <div class="g2">
          <div><label for="sLang">Languages</label><input id="sLang" type="number" min="1" max="12" value="2"></div>
          <div><label for="sTurn">Nodes loaded per turn</label><input id="sTurn" type="number" min="1" max="200" value="8"></div>
        </div>
        <label for="sMem">Tied to a memory by <code>because</code>: <b id="sMemV">39 %</b></label>
        <input id="sMem" type="range" min="0" max="100" step="1" value="39">
        <p class="hint">Sized on Clara: {PER_NODE:.0f} bytes per node with {len(LANGS)} languages and gists of about {GIST:.0f} characters; text at about 4 characters per token.</p>
      </fieldset>
    </div>
  </div>
  <div class="res" aria-live="polite"><div class="s">Convictions held now</div><div class="t" id="oHeld">–<small>nodes</small></div><div class="s" id="oSub">–</div></div>
  <div class="kpis">
    <div class="kpi"><b id="oSize">–</b><span>in the file, unpacked<br><i id="oSizeS" style="font-style:normal"></i></span></div>
    <div class="kpi"><b id="oAll">–</b><span>tokens to read all the held ones, as text</span></div>
    <div class="kpi"><b id="oTurn">–</b><span>tokens per turn<br><i id="oTurnS" style="font-style:normal"></i></span></div>
    <div class="kpi"><b id="oMem">–</b><span>can say <i>why</i> down to a memory</span></div>
  </div>
  <div class="simchart">
    <div class="lg" aria-hidden="true"><span><i style="background:#35a38b"></i>held</span><span><i style="background:repeating-linear-gradient(90deg,#c08528 0 6px,transparent 6px 10px)"></i>let go, in all</span><span id="lgClara"><i style="background:repeating-linear-gradient(90deg,#9a7ae0 0 2px,transparent 2px 5px)"></i>Clara, as written</span></div>
    <svg id="simsvg" role="img" tabindex="0" aria-label="Convictions held and let go over the years"></svg>
    <div class="tip" id="simtip" aria-hidden="true"></div>
  </div>
  <div class="sbars"><h4>What it weighs</h4><div id="bSize"></div><h4>What it costs a model to read</h4><div id="bTok"></div></div>
  <p class="hint" style="margin-top:10px">Logarithmic scales. 1 KB = 1,000 bytes. Expected values of a simple model, not a measurement of anyone: hover or focus the chart and use the arrow keys to read it year by year.</p>
</div>"""

def L(href, text): return f'<a href="{href}">{text}</a>'
DOI = lambda d: f"https://doi.org/{d}"

HOWMANY = head("How many convictions make a person? — COF 1.2",
               "Psychology has never counted a person's convictions. What it has counted instead — values, traits, the levels of personality — a simulator to test your own numbers, what the Big Five, Myers-Briggs types, the Enneagram and astrology are worth, and three ways to keep a mind.",
               "How many convictions make a person?",
               "Nobody has counted. What psychology measured instead, a simulator to test your own, and what the popular profiles are worth.",
               HERO_HOW_MANY, COMPANION) + f"""
<header class="hero">
  {TOPH.replace('<span>· Character Open File · 1.2</span>', '<span>·</span><a href="./">psyche</a><span class="crumb">·</span><span class="crumb">how many?</span>')}
  <div class="text">
    <h1>How many convictions<br>make a person?</h1>
    <div class="rule"></div>
    <p class="sub">Nobody has counted. Here is what psychology measured instead, what a character's file needs, and a simulator to test your own numbers.</p>
    <p class="voice">“I could give you twenty reasons for the way I work. Three of them matter.”<small>CLARA MERCIER · IF YOU ASKED HER</small></p>
  </div>
  <div class="kicker">COF · CHARACTER OPEN FILE</div>
</header>

<main>
<p class="lede">COF 1.2 gives AI characters a psyche: values, beliefs, wants, needs, fears, wounds, each a node with a weight, a date and a reason, tied to the memories that made it. The obvious question is how many of them a character needs — and how many a person has. This page starts with one refusal, follows it down to where it comes from, then says what the research does and does not know, lets you test your own numbers, and is honest about the popular shortcuts.</p>

<div class="tiles">
  <div class="tile"><b>none</b><span>studies that count the convictions of one person: psychology measures dimensions, not lists</span></div>
  <div class="tile"><b>10 → 19</b><span>basic human values in Schwartz's theory, recognised across cultures</span></div>
  <div class="tile"><b>≈ 4,500</b><span>English words for stable traits, found in the dictionary in 1936</span></div>
  <div class="tile"><b>50 – 150</b><span>nodes for a main character written with care — our estimate, to be argued with</span></div>
</div>
<p class="cap">Orders of magnitude, not measurements. Every figure on this page says where it comes from.</p>

<h2>Why did she say no?</h2>
<p>Clara is a fictional designer from Lyon, the example character of the COF format. A prospective client writes to her. Here is the exchange — invented for this page, but played from her file. Then ask her <i>why</i>, as many times as it takes.</p>

<div class="chain">
<div class="chat">
  <p><span class="who">client</span>Could you ship our whole new site by Friday? Autoplay video on the home page, a chat bubble, push notifications — the works.</p>
  <p class="her"><span class="who">Clara</span>No. Not like that. I can give you a lighter site by Friday, or this one in a month. But I won't ship something heavy and fast again.</p>
</div>
{STEPS}
<div class="step" id="whyend" hidden><div class="dot" style="background:#eef3f1">✓</div><div class="card"><p class="t">Five questions, from a sentence to four years that began at twenty-four.</p><p class="why">Every answer above is a node of Clara's file, linked to the next — <i>supports</i>, <i>because</i> — written once by her author, readable by any tool, the same in every model that plays her. Nothing here was improvised.</p></div></div>
</div>
<div class="whyb"><button id="whyb" type="button">Why?</button><button id="whyr" class="ghost" type="button">start again</button></div>
<p style="margin-top:26px">Five nodes answered. Clara's file holds {len(N)}, with {LINKS} links between them and to her memories. Is that a person? Clearly not all of one. So how many would it take?</p>

<h2>How many? What has been counted</h2>
<p>No study has counted the convictions of a person, and none could: “a conviction” is not a unit the mind keeps. What psychology has counted is the number of <em>dimensions</em> it takes to describe how people differ. Those numbers are small, and they are the closest thing to an answer.</p>

<h3>Values: a few dozen at most</h3>
<p>Milton Rokeach separated beliefs, attitudes and values, and argued that a person holds far fewer values than attitudes: values are the few central beliefs the rest are organised around. His survey asks people to rank <b>36</b> of them, 18 ends and 18 means ({L("https://en.wikipedia.org/wiki/Rokeach_Value_Survey", "Rokeach, 1973")}). Shalom Schwartz then proposed <b>ten</b> basic values recognised across cultures — security, benevolence, achievement and the rest — arranged in a circle of compatible and conflicting motivations, and tested the structure in twenty countries ({L(DOI("10.1016/S0065-2601(08)60281-6"), "Schwartz, 1992")}); the refined theory distinguishes <b>nineteen</b>, confirmed in fifteen samples from ten countries ({L(DOI("10.1037/a0029393"), "Schwartz et al., 2012")}). A person is not ten values: a person is an order among them. That is why COF's <code>value</code> nodes carry a strength, and why the RFC names Schwartz's list as an optional vocabulary, never as a form to fill.</p>

<h3>Traits: thousands of words, five dimensions</h3>
<p>The lexical hypothesis holds that whatever matters in how people differ ends up as a word. Gordon Allport and Henry Odbert went through Webster's dictionary — about 400,000 entries — and kept <b>17,953</b> terms that describe personality or behaviour, <b>4,504</b> of them for stable traits ({L("https://en.wikipedia.org/wiki/Lexical_hypothesis", "Allport &amp; Odbert, 1936")}). Decades of factor analysis condensed that vocabulary into <b>five</b> broad domains — the Big Five — which the standard questionnaire measures through <b>30</b> facets, six per domain, with 240 items ({L("https://dlab.sauder.ubc.ca/sjdm/dmidi/NEO%20PI-R.html", "Costa &amp; McCrae, 1992")}). And when sociologists asked people simply to answer “Who am I?”, they gave them <b>twenty</b> lines to fill ({L(DOI("10.2307/2088175"), "Kuhn &amp; McPartland, 1954")}) — a format, not a ceiling, but a telling one.</p>

{LADDER_HTML}
<p class="cap">What has been counted, on one logarithmic scale — <b>not counts of the same thing</b>: dimensions to describe everyone, items of a questionnaire, words of a language, and in violet COF's own numbers. The range of a novel's or a life's psyche sits between what a questionnaire asks and what a dictionary holds.</p>

<h3>Three levels, and where a psyche sits</h3>
<p>Dan McAdams answered the question “what do we know when we know a person?” with three levels ({L(DOI("10.1111/j.1467-6494.1995.tb00500.x"), "McAdams, 1995")}; {L(DOI("10.1037/0003-066X.61.3.204"), "McAdams &amp; Pals, 2006")}). <b>Traits</b>, broad and context-free: the Big Five, which give the “psychology of the stranger”. <b>Characteristic adaptations</b>: goals, values, concerns, coping strategies, tied to a time, a place, a role. And <b>narrative identity</b>: the evolving story a person makes of their life, joining the remembered past to the imagined future ({L(DOI("10.1177/0963721413475622"), "McAdams &amp; McLean, 2013")}).</p>
<p>COF's psyche lives on the second and third levels. Traits stay where they were in 1.0, an optional annex of scores. A node is a characteristic adaptation — a want, a fear, a stance toward someone — and its <code>because</code> link to a memory is a piece of the life story. Memory research describes the same two-way tie: in Martin Conway's self-memory system, what we remember is selected and shaped by the goals of the current self, and the self in turn is grounded in what we remember ({L(DOI("10.1037/0033-295X.107.2.261"), "Conway &amp; Pleydell-Pearce, 2000")}; {L(DOI("10.1016/j.jml.2005.08.005"), "Conway, 2005")}). Memories without a psyche stay anecdotes; a psyche without memories stays slogans.</p>

<h3>What writers count</h3>
<p>Fiction has its own counts, and they are small at the core. John Truby builds a character on a weakness and a <em>need</em> the hero does not see, a <em>desire</em> the hero pursues, and often a <em>ghost</em> — “the event from the past still haunting the hero in the present” (<i>The Anatomy of Story</i>, 2007). K. M. Weiland adds the <em>lie</em> the character believes, formed by that ghost and undone by the story ({L("https://www.helpingwritersbecomeauthors.com/character-arcs-3/", "Weiland, on want and need")}; {L("https://www.vidlit.com/articles/whats-the-difference-your-characters-ghost-vs-wound-vs-lie-vs-weakness/", "ghost, wound, lie, weakness")}). One wound, one lie, one want, one need: four nodes carry an arc. COF has a kind for each — <code>wound</code>, <code>belief</code> marked false but held, <code>want</code>, <code>need</code> — and everything a novelist knows besides: the tastes, habits, stances that make a character recognisable in a scene where the arc is not at stake.</p>

<h3>And it moves</h3>
<p>A person's psyche is not a snapshot. A meta-analysis of 92 longitudinal samples found that personality traits keep changing through adulthood, most between twenty and forty, some into old age ({L(DOI("10.1037/0033-2909.132.1.1"), "Roberts, Walton &amp; Viechtbauer, 2006")}). And more than 19,000 people, asked about their personality, their values and their preferences, recalled a lot of change over the past ten years and predicted little over the next ten, at every age — the end of history illusion ({L(DOI("10.1126/science.1229294"), "Quoidbach, Gilbert &amp; Wilson, 2013")}). That is why a node has a <code>since</code> and an <code>until</code>, and why a conviction that changes leaves its earlier self in the file.</p>

<h3>Our estimate</h3>
<p>So there is no number to take from the literature, only bounds: a handful of dimensions to describe anyone, a few dozen values at most, thousands of words for the rest. Here is ours, from building Clara and from load tests of the tools — an estimate, labelled as one.</p>
<ul class="orders">
  <li><b>{len(N)}</b><div>Clara today: enough for an agent to play her consistently, and to answer <i>why</i>.</div></li>
  <li><b>50 – 150</b><div>a main character written with care: what a novelist would know about her.</div></li>
  <li><b>300 – 600</b><div>a whole life modelled, with what began and ended along the way.</div></li>
  <li><b>1,000</b><div>the upper bound we tested: the tools still draw it, a conversation never needs it all.</div></li>
</ul>

<h2>Test your own</h2>
<p>Every assumption is a control. The presets reproduce the estimate above; Clara's is fitted on her file — {len(N)} nodes written by hand, {HELD_65} held at {CLARA_AGE}, two let go at forty-five. Change any of it.</p>
{SIM_HTML}
<p>Two things stand out whatever the settings. The file stays small: a thousand convictions in two languages weigh under a megabyte — three pictures like the one of her wedding, a seventeenth of her file. And what a model must read <i>per turn</i> barely moves: an agent picks the core nodes and the handful the moment calls for — by tag, by the person or memory the conversation touches, by strength — and leaves the rest on disk. Size is not the constraint; writing them is.</p>

<h2>Popular profiles: what they are worth</h2>
<p>Many authors do not start from a blank page but from a type: “she's an INFJ”, “a Four”, “very open, not very agreeable”, “a Virgo”. COF's tools take all four as starting points. Their scientific standing is very different, and it is worth saying so plainly — without contempt for anyone who finds them useful. A shorthand that helps someone think about a character is doing a job.</p>

<h3>The Big Five</h3>
<p>The five domains that came out of the dictionary — openness, conscientiousness, extraversion, agreeableness, neuroticism — are the best-validated model in personality psychology. They are scores, not boxes: everyone is somewhere on each. Their links to what happens in a life hold up: a large replication of 78 published associations between traits and life outcomes reproduced about 87 % of them, though usually with smaller effects than first reported ({L(DOI("10.1177/0956797619831612"), "Soto, 2019")}). Their limit, for a character, is that they say <i>how much</i>, never <i>about what</i>: a high neuroticism score does not say what she is afraid of.</p>

<h3>Myers-Briggs types</h3>
<p>Four letters for sixteen types, from Jung's theory, hugely popular in workplaces and online. Research finds that the four scales behind the letters measure something real — four of the five Big Five domains — but not types: the scores are not bimodal, they do not split people into two camps on each scale ({L(DOI("10.1111/j.1467-6494.1989.tb00759.x"), "McCrae &amp; Costa, 1989")}). Near the middle a letter is decided by a few answers, and it often flips: among people with intermediate scores, a quarter to a third got the other letter on a given scale when retested a month later (Howes &amp; Carskadon, 1979, reviewed by {L(DOI("10.1037/1065-9293.57.3.210"), "Pittenger, 2005")}). A four-letter type is a less stable summary than the scores beneath it.</p>

<h3>The Enneagram</h3>
<p>Nine types, each defined by a basic fear and a basic desire, widely used in coaching and spiritual direction. A systematic review of 104 samples found mixed evidence of reliability and validity: some subscales relate to the Big Five in the expected ways and several studies report that people find it helpful for personal growth, but factor analyses usually recover fewer than nine factors, and little supports the wings and movements between types ({L(DOI("10.1002/jclp.23097"), "Hook et al., 2021")}).</p>

<h3>Astrology</h3>
<p>A sun sign is the oldest personality shorthand there is. In controlled tests it has no predictive power. In a double-blind experiment published in <i>Nature</i>, astrologers matched birth charts to one of three personality profiles from a standard questionnaire, and got it right about one time in three — what chance gives ({L(DOI("10.1038/318419a0"), "Carlson, 1985")}). A review of more than forty controlled studies found astrologers doing no better than chance, and people born minutes apart showed none of the similarities astrology predicts ({L("https://www.ingentaconnect.com/content/imp/jcs/2003/00000010/f0020006/art00010", "Dean &amp; Kelly, 2003")}). One finding matters for a character, though: the sign can still shape the person. In a sample of 2,324 adults, people born under the odd-numbered signs scored as more extraverted on a standard questionnaire, just as astrology says ({L(DOI("10.1080/00224545.1978.9924119"), "Mayo, White &amp; Eysenck, 1978")}) — and the effect disappeared among people who did not know what their sign was supposed to make them ({L("https://search.worldcat.org/title/8347924", "Eysenck &amp; Nias, 1982")}). The horoscope had done the work: a belief about oneself, repeated, becomes behaviour. In a story, a character who reads hers every morning is a fact about her — a node, often <i>aware: no</i>, with a <code>because</code> on the habit.</p>

<table class="prof"><thead><tr><th></th><th>what it gives</th><th>what the evidence says</th><th>what COF proposes from it</th></tr></thead><tbody>{PROF_HTML}</tbody></table>

<h3>Only starting points</h3>
<p>So COF uses all four the same way: as a <b>proposal</b>, never as a field of the format. Give the builder or <code>cof psyche propose</code> a sign, a four-letter type, an Enneagram number or five scores, and it offers a few ordinary nodes — strength 50, stability <i>shifting</i>, tagged with where they came from — every one unticked until the author reads it and decides. There is no “type” field to fill: millions of people share a sign or a type, and a type cannot say why. A person is a graph with reasons. The shorthand is a fine place to start the graph, and a poor place to stop.</p>

<h2>Three ways to keep a mind</h2>
<p>There are three ways to tell a model who a character is. A <b>description</b>: a few lines in a prompt. A <b>graph</b>: the psyche of COF, convictions linked to each other and to memories. <b>Weights</b>: a model fine-tuned on the character, or a LoRA — the character dissolved in a latent space.</p>
<table class="cmp"><thead><tr><th></th><th>a description</th><th>a graph</th><th>weights</th></tr></thead><tbody>{CMP}</tbody></table>
<p class="cap">Orders of magnitude, not measurements. The size of weights depends on the model and the method; the graph's on how much of the life is written.</p>
<p>The honest ranking is not a ladder. A graph is better than a description: it can be selected from, it answers <i>why</i>, it keeps secrets and moves with time. It is less rich than a latent space, which holds what no list of convictions can — the way a sentence turns, a hesitation, a kind of humour. But a graph is the only one of the three that <b>anyone can make</b> with a pen or a tool that proposes, <b>read</b> node by node, <b>edit</b> one conviction at a time, and <b>carry to any model</b>, today and in ten years.</p>

<h2>Not instead of weights</h2>
<p>Weights are richer, and nothing on this page competes with that. But they are mute about themselves: they can produce the no, never the <i>why</i>. You cannot read them, correct one conviction, keep one secret, or take them to another model.</p>
<p>So the two are not rivals. A graph is the score; weights are a performance of it. The score can be read, argued with, versioned, carried to any orchestra — and one day it can be what a model is tuned from, and what its performance is checked against. Until then, it is the only one of the three that you can write by hand tonight, and that every model can read tomorrow.</p>
<p>In practice the two work best together. Weights give the voice its grain; the graph gives it something to hold on to — buoys in a channel: the current does the moving, the buoys keep it from drifting. Prompt the graph into a model you fine-tuned on the same character, and each corrects the other's failure mode: the weights stop improvising convictions the file never gave, the graph stops reading like a list.</p>

<h2>An open question: the score and the performance</h2>
<p>That last sentence is a research question, and we would like someone to take it on. Can a psyche graph be the <b>supervision signal</b> for a character's weights — and can it be the <b>evaluation set</b>?</p>
<p>Each node already reads like a test. A core value with strength 95 predicts a refusal; a fragile stance predicts a change of mind within one conversation; a node marked <i>aware: no</i> predicts behaviour the character never names; a <code>because</code> chain predicts the answer to “why?”. So here is the study. Take a few dozen characters with authored graphs of a hundred nodes or so. Turn each node into situations — a client in a hurry, a friend who asks for help — with the expected behaviour derived from its kind, strength and stability. Then measure three things. Whether a model prompted with the graph behaves as the nodes predict, and how that degrades as only a selection of nodes is loaded. Whether an adapter trained on dialogue generated from the graph recovers the <i>because</i> chains when asked, without being shown them. And whether editing one node and retraining changes only the behaviours that node predicts, and nothing else. If the answers are good, the graph becomes what the reference images of a face already are for a LoRA in COF: the readable source a model is derived from, regenerated when the source changes.</p>

<div class="btns">
  <a class="btn main" href="../viewer/#clara/psyche">Open Clara's psyche</a>
  <a class="btn" href="../builder/">Write a psyche</a>
  <a class="btn" href="https://github.com/yannsouetre/cof/blob/main/rfcs/0004-psyche-graph.md">Read RFC 0004</a>
  <a class="btn" href="./">AI characters now have an inner life</a>
</div>

<h2>Sources</h2>
<div class="refs">
  <h3>Values</h3>
  <p>Rokeach, M. (1973). <i>The Nature of Human Values</i>. Free Press — {L("https://en.wikipedia.org/wiki/Rokeach_Value_Survey", "the Rokeach Value Survey")}.</p>
  <p>Schwartz, S. H. (1992). Universals in the content and structure of values: theoretical advances and empirical tests in 20 countries. <i>Advances in Experimental Social Psychology</i>, 25, 1–65. {L(DOI("10.1016/S0065-2601(08)60281-6"), "doi:10.1016/S0065-2601(08)60281-6")}</p>
  <p>Schwartz, S. H. et al. (2012). Refining the theory of basic individual values. <i>Journal of Personality and Social Psychology</i>, 103(4), 663–688. {L(DOI("10.1037/a0029393"), "doi:10.1037/a0029393")}</p>
  <h3>Traits and the self</h3>
  <p>Allport, G. W. &amp; Odbert, H. S. (1936). Trait-names: a psycho-lexical study. <i>Psychological Monographs</i>, 47(1). Summary: {L("https://en.wikipedia.org/wiki/Lexical_hypothesis", "the lexical hypothesis")}.</p>
  <p>Costa, P. T. &amp; McCrae, R. R. (1992). <i>NEO PI-R Professional Manual</i>. Psychological Assessment Resources — {L("https://dlab.sauder.ubc.ca/sjdm/dmidi/NEO%20PI-R.html", "description of the instrument")}.</p>
  <p>Kuhn, M. H. &amp; McPartland, T. S. (1954). An empirical investigation of self-attitudes. <i>American Sociological Review</i>, 19(1), 68–76. {L(DOI("10.2307/2088175"), "doi:10.2307/2088175")}</p>
  <p>McAdams, D. P. (1995). What do we know when we know a person? <i>Journal of Personality</i>, 63(3), 365–396. {L(DOI("10.1111/j.1467-6494.1995.tb00500.x"), "doi:10.1111/j.1467-6494.1995.tb00500.x")}</p>
  <p>McAdams, D. P. &amp; Pals, J. L. (2006). A new Big Five: fundamental principles for an integrative science of personality. <i>American Psychologist</i>, 61(3), 204–217. {L(DOI("10.1037/0003-066X.61.3.204"), "doi:10.1037/0003-066X.61.3.204")}</p>
  <p>McAdams, D. P. &amp; McLean, K. C. (2013). Narrative identity. <i>Current Directions in Psychological Science</i>, 22(3), 233–238. {L(DOI("10.1177/0963721413475622"), "doi:10.1177/0963721413475622")}</p>
  <p>Conway, M. A. &amp; Pleydell-Pearce, C. W. (2000). The construction of autobiographical memories in the self-memory system. <i>Psychological Review</i>, 107(2), 261–288. {L(DOI("10.1037/0033-295X.107.2.261"), "doi:10.1037/0033-295X.107.2.261")}</p>
  <p>Conway, M. A. (2005). Memory and the self. <i>Journal of Memory and Language</i>, 53(4), 594–628. {L(DOI("10.1016/j.jml.2005.08.005"), "doi:10.1016/j.jml.2005.08.005")}</p>
  <h3>Change</h3>
  <p>Roberts, B. W., Walton, K. E. &amp; Viechtbauer, W. (2006). Patterns of mean-level change in personality traits across the life course: a meta-analysis of longitudinal studies. <i>Psychological Bulletin</i>, 132(1), 1–25. {L(DOI("10.1037/0033-2909.132.1.1"), "doi:10.1037/0033-2909.132.1.1")}</p>
  <p>Quoidbach, J., Gilbert, D. T. &amp; Wilson, T. D. (2013). The end of history illusion. <i>Science</i>, 339(6115), 96–98. {L(DOI("10.1126/science.1229294"), "doi:10.1126/science.1229294")}</p>
  <h3>Writing characters</h3>
  <p>Truby, J. (2007). <i>The Anatomy of Story: 22 Steps to Becoming a Master Storyteller</i>. Faber and Faber.</p>
  <p>Weiland, K. M. (2016). <i>Creating Character Arcs</i>. PenForASword — and, online, {L("https://www.helpingwritersbecomeauthors.com/character-arcs-3/", "the thing your character wants vs. the thing your character needs")} and {L("https://www.vidlit.com/articles/whats-the-difference-your-characters-ghost-vs-wound-vs-lie-vs-weakness/", "your character's ghost vs. wound vs. lie vs. weakness")}.</p>
  <h3>Popular profiles</h3>
  <p>Soto, C. J. (2019). How replicable are links between personality traits and consequential life outcomes? The Life Outcomes of Personality Replication Project. <i>Psychological Science</i>, 30(5), 711–727. {L(DOI("10.1177/0956797619831612"), "doi:10.1177/0956797619831612")}</p>
  <p>McCrae, R. R. &amp; Costa, P. T. (1989). Reinterpreting the Myers-Briggs Type Indicator from the perspective of the five-factor model of personality. <i>Journal of Personality</i>, 57(1), 17–40. {L(DOI("10.1111/j.1467-6494.1989.tb00759.x"), "doi:10.1111/j.1467-6494.1989.tb00759.x")}</p>
  <p>Pittenger, D. J. (2005). Cautionary comments regarding the Myers-Briggs Type Indicator. <i>Consulting Psychology Journal: Practice and Research</i>, 57(3), 210–221. {L(DOI("10.1037/1065-9293.57.3.210"), "doi:10.1037/1065-9293.57.3.210")}</p>
  <p>Hook, J. N. et al. (2021). The Enneagram: a systematic review of the literature and directions for future research. <i>Journal of Clinical Psychology</i>, 77(4), 865–883. {L(DOI("10.1002/jclp.23097"), "doi:10.1002/jclp.23097")}</p>
  <p>Carlson, S. (1985). A double-blind test of astrology. <i>Nature</i>, 318, 419–425. {L(DOI("10.1038/318419a0"), "doi:10.1038/318419a0")}</p>
  <p>Mayo, J., White, O., &amp; Eysenck, H. J. (1978). An empirical study of the relation between astrological factors and personality. <i>The Journal of Social Psychology</i>, 105(2), 229–236. {L(DOI("10.1080/00224545.1978.9924119"), "doi:10.1080/00224545.1978.9924119")}</p>
  <p>Eysenck, H. J., &amp; Nias, D. K. B. (1982). <i>Astrology: Science or Superstition?</i> Maurice Temple Smith, London. The self-attribution reanalysis: the sign–extraversion link holds only among people who know what their sign predicts.</p>
  <p>Dean, G. &amp; Kelly, I. W. (2003). Is astrology relevant to consciousness and psi? <i>Journal of Consciousness Studies</i>, 10(6–7), 175–198. {L("https://www.ingentaconnect.com/content/imp/jcs/2003/00000010/f0020006/art00010", "ingentaconnect")}</p>
  <h3>Counting tokens</h3>
  <p>OpenAI Help Center, {L("https://help.openai.com/en/articles/4936856-what-are-tokens-and-how-to-count-them", "What are tokens and how to count them?")} — “1 token ≈ 4 characters in English”, the rule the simulator uses (the same as <code>cof tokens</code> without a tokenizer).</p>
  <h3>Measured on the format</h3>
  <p>Clara's psyche, <code>spec/examples/10-clara-mercier</code>, COF 1.2: {len(N)} nodes, {PSY_FILES / 1000:.1f} KB of node files, {(PSY_FILES + PSY_MAN) / 1000:.1f} KB with their manifest entries, {LINKS} links, {round(TIED * len(N))} nodes tied to a memory; her « Who she is » as <code>cof psyche text --preset en-agent</code> renders it, 1,943 characters. The upper bound: generated psyches of 150, 500 and 1,000 nodes, opened in the explorer (load tests, 3 November 2026).</p>
</div>
</main>

<section class="close">
  <p class="voice">She said no because of four years she does not talk about. Now you know why. So does any tool that opens her file.</p>
  <div class="btns row3">
    <a class="btn main" href="./">AI characters now have an inner life</a>
    <a class="btn" href="../viewer/#clara/psyche">Open Clara's psyche</a>
    <a class="btn" href="../builder/">Write a psyche</a>
  </div>
</section>
""" + tail("<script>" + WHY_JS + "</script>\n<script>" + SIM_JS.replace("__SIM__", json.dumps(SIM)) + "</script>\n<script>" + WIDE_JS + "</script>",
           " Myers-Briggs is a trademark of its owner, mentioned here descriptively, with no affiliation.")
HOWMANY = HOWMANY.replace("</style>", HOWMANY_CSS + "</style>", 1)

(ROOT / "psyche").mkdir(exist_ok=True)
(ROOT / "psyche/index.html").write_text(INDEX, "utf-8")
(ROOT / "psyche" / COMPANION).write_text(HOWMANY, "utf-8")
print("ok", len(INDEX), len(HOWMANY))
