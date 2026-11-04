"""The two announcement pages of COF 1.2 (the psyche): psyche/index.html and psyche/why.html.

    python3 tools/announce/build_psyche_pages.py

They reuse the style of the memories page (memories/index.html, same hero, column, fonts, share menu, footer) so the
site reads as one; the data of the graph and of the « why » chain is Clara's (spec/examples/10-clara-mercier), read
here, not copied by hand. Text in English, like the rest of the site. Decided with Yann on 3 Nov. 2026: title « AI
characters now have an inner life », subtitle « A psyche you can read, edit and take with you — every conviction tied
to the memory that made it. », and the companion page « Why did she say no? »."""
import json, re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
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


SRC = (ROOT / "memories/index.html").read_text("utf-8")
CSS = SRC[SRC.index("<style>"):SRC.index("</style>")]
SHARE_JS = re.findall(r"<script>([\s\S]*?)</script>", SRC)[1]
COUNTER = re.findall(r"(<!-- Visit counter[\s\S]*?</script>)", SRC)[0]
TOP = re.search(r'<div class="top">[\s\S]*?</div>', SRC).group(0)
FOOT = re.search(r"<footer>[\s\S]*?</footer>", SRC).group(0)

KINDS = {"wound": "#e8876b", "value": "#4cc2a8", "belief": "#a98ae8", "want": "#e3b04f", "need": "#7fb3e8", "fear": "#d9708f",
         "stance": "#cdb67f", "taste": "#9fd27c", "habit": "#9aaca7", "contradiction": "#eef3f1", "rule": "#bfeee2"}

EXTRA_CSS = """
/* 1.2: the psyche pages (same system as the memories pages) */
.hero::before{background:linear-gradient(90deg,rgba(7,11,18,.9) 0%,rgba(7,11,18,.78) 42%,rgba(7,11,18,.35) 72%,rgba(7,11,18,.2) 100%),linear-gradient(180deg,rgba(7,11,18,.55) 0%,rgba(7,11,18,0) 30%,rgba(7,11,18,0) 75%,rgba(13,19,18,1) 100%)}
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
.pgraph .replay{position:absolute;right:14px;top:12px;font:500 13px PlexMono,monospace;background:var(--panel);color:var(--ink);border:1px solid var(--line);border-radius:999px;padding:6px 12px;cursor:pointer}
.pgraph{position:relative}.pgraph .agec{position:absolute;left:18px;top:12px;font:500 13px PlexMono,monospace;color:var(--muted)}
.pgraph svg .n{cursor:pointer}.pgraph svg .n circle{transition:opacity .5s,transform .5s}.pgraph svg .off{opacity:0}
.pgraph svg .ln{transition:opacity .6s}.pgraph svg.hl .ln{opacity:.12}.pgraph svg.hl .ln.on{opacity:1}.pgraph svg.hl .n{opacity:.35}.pgraph svg.hl .n.on{opacity:1}
.pfocus{max-width:calc(var(--col) - 40px);margin:16px auto 0;min-height:118px;padding:16px 18px;border:1px solid var(--line);border-radius:14px;background:var(--panel)}
.pfocus .t{font:700 18px/1.3 Bricolage,Plex,sans-serif;margin:0 0 4px}.pfocus .m{font:500 12px PlexMono,monospace;color:var(--muted);margin:0 0 8px}
.pfocus .g{font:500 19px/1.45 Cormorant,Georgia,serif;color:#e4dfd6;margin:0}
table.cmp{width:100%;border-collapse:collapse;margin:22px 0 8px;font-size:15px}
table.cmp th,table.cmp td{text-align:left;vertical-align:top;padding:9px 10px;border-bottom:1px solid var(--line)}
table.cmp thead th{font:700 15px Bricolage,Plex,sans-serif;color:var(--ink)}table.cmp tbody th{color:var(--muted);font-weight:500;width:28%}
table.cmp td.y{color:var(--mint)}table.cmp td.n{color:#d9a0a0}
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
    css = CSS.replace("url(img/electric-sheep.jpg) center 70%/cover", f"url({img}) center 45%/cover")
    return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{title}</title>
<meta name="description" content="{desc}">
<meta property="og:title" content="{ogt}">
<meta property="og:description" content="{ogd}">
<meta property="og:image" content="https://yannsouetre.github.io/cof/psyche/img/og-psyche.jpg">
<meta property="og:image:width" content="1200"><meta property="og:image:height" content="630">
<meta name="twitter:card" content="summary_large_image">
<meta name="twitter:image" content="https://yannsouetre.github.io/cof/psyche/img/og-psyche.jpg">
<link rel="canonical" href="https://yannsouetre.github.io/cof/psyche/{url}">
<link rel="icon" type="image/svg+xml" href="../builder/icon/cof-icon-dark.svg">
{css}{EXTRA_CSS}</style>
</head>
<body>
"""


def tail(scripts):
    return f"""{FOOT.replace("Clara Mercier and the Martian are fictional example characters; their images are AI-generated.", "Clara Mercier is a fictional example character; her images are AI-generated, her psyche is written by hand.")}
<script>{SHARE_JS}</script>
{scripts}
{COUNTER}
</body>
</html>
"""


TOP12 = TOP.replace("· 1.1</span>", "· 1.2</span>")
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
/* layout: the memories Clara's nodes hang on, left to right by age, each with its nodes below; the nodes tied to no memory in a band at the bottom */
const PIV=["ev1","ep1","ev2","ev3","ev4"],PX={ev1:120,ep1:355,ev2:590,ev3:825,ev4:1060},PY=128;
const hang={};N.forEach(n=>{const m=n.links.find(l=>l[1].startsWith("memories/")&&PIV.includes(l[1].slice(9)));n.p=m?m[1].slice(9):null;if(n.p)(hang[n.p]=hang[n.p]||[]).push(n)});
const pos={};PIV.forEach(p=>{pos["m:"+p]={x:PX[p],y:PY};(hang[p]||[]).forEach((n,i)=>{pos[n.id]={x:PX[p]+(i%2?44:-44)*(hang[p].length>1?1:0),y:PY+92+i*62}})});
const free=N.filter(n=>!n.p),per=Math.ceil(free.length/2);free.forEach((n,i)=>{const r=Math.floor(i/per),c=i%per;pos[n.id]={x:95+c*155+(r?78:0),y:505+r*82}});
const el=(t,a,p)=>{const e=document.createElementNS(NS,t);for(const k in a)e.setAttribute(k,a[k]);(p||svg).appendChild(e);return e};
const gl=el("g",{}),gn=el("g",{});
el("text",{x:20,y:468,fill:"#93a39e","font-size":12,"font-family":"PlexMono,monospace"},svg).textContent="not tied to one memory — held for as long as she can remember, or learned along the way";
const lines=[];
N.forEach(n=>{n.links.forEach(([t,to])=>{const [c,id]=to.split("/");const b=c==="memories"?pos["m:"+id]:pos[id];if(!b)return;const a=pos[n.id],mx=(a.x+b.x)/2,my=(a.y+b.y)/2-30;
  const l=el("path",{d:`M${a.x},${a.y} Q${mx},${my} ${b.x},${b.y}`,fill:"none",stroke:t==="conflicts"?"#d9708f":t==="because"?"#4cc2a8":"#93a39e","stroke-width":t==="because"?1.6:1.1,"stroke-dasharray":t==="about"?"4 4":t==="conflicts"?"2 4":"","class":"ln off"},gl);l.dataset.a=n.id;l.dataset.b=c==="memories"?"m:"+id:id;l.dataset.t=t;lines.push(l)})});
const pg={};PIV.forEach(p=>{const m=MEM[p],P=pos["m:"+p],g=el("g",{class:"n piv"},gn);g.dataset.id="m:"+p;
  el("circle",{cx:P.x,cy:P.y,r:30,fill:"#2b2440",stroke:"#a98ae8","stroke-width":2},g);
  if(!m.per){el("clipPath",{id:"pc-"+p},g).appendChild(Object.assign(document.createElementNS(NS,"circle"),{}));g.lastChild.firstChild.setAttribute("cx",P.x);g.lastChild.firstChild.setAttribute("cy",P.y);g.lastChild.firstChild.setAttribute("r",28);
    el("image",{href:"../memories/img/"+p+"-t.jpg",x:P.x-28,y:P.y-28,width:56,height:56,preserveAspectRatio:"xMidYMid slice","clip-path":`url(#pc-${p})`},g)}
  else el("text",{x:P.x,y:P.y+4,"text-anchor":"middle",fill:"#eef3f1","font-size":11},g).textContent="period";
  const t=el("text",{x:P.x,y:P.y-40,"text-anchor":"middle",fill:"#eef3f1","font-size":13,"font-family":"Plex,sans-serif"},g);t.textContent=m.l;
  const s=el("text",{x:P.x,y:P.y+46,"text-anchor":"middle",fill:"#93a39e","font-size":11,"font-family":"PlexMono,monospace"},g);s.textContent=m.b?`age ${m.a}–${m.b}`:`age ${m.a}`;pg["m:"+p]=g});
const ng={};N.forEach(n=>{const P=pos[n.id],r=7+n.s/10,g=el("g",{class:"n off",tabindex:0},gn);g.dataset.id=n.id;
  el("circle",{cx:P.x,cy:P.y,r:r,fill:K[n.k]||"#ccc","fill-opacity":n.k==="contradiction"?0:.9,stroke:n.k==="contradiction"?"#eef3f1":n.aw==="no"?"#eef3f1":"none","stroke-width":n.aw==="no"?2:1.5,"stroke-dasharray":n.aw==="no"||n.k==="contradiction"?"3 3":""},g);
  if(n.st==="core")el("circle",{cx:P.x,cy:P.y,r:r+4,fill:"none",stroke:K[n.k],"stroke-opacity":.6,"stroke-width":1.2},g);
  const t=el("text",{x:P.x,y:P.y+r+14,"text-anchor":"middle",fill:"#dfe8e5","font-size":11.5,"font-family":"Plex,sans-serif"},g);t.textContent=n.l.length>24?n.l.slice(0,23)+"…":n.l;ng[n.id]=g});
function show(id){const on=new Set([id]);lines.forEach(l=>{const h=l.dataset.a===id||l.dataset.b===id;l.classList.toggle("on",h);if(h){on.add(l.dataset.a);on.add(l.dataset.b)}});
  Object.entries({...ng,...pg}).forEach(([k,g])=>g.classList.toggle("on",on.has(k)));svg.classList.add("hl");
  if(id.startsWith("m:")){const m=MEM[id.slice(2)];fc.innerHTML=`<p class="t">${m.l}</p><p class="m">memory · ${m.b?`age ${m.a}–${m.b}`:`age ${m.a}`}</p><p class="g">${m.g}</p>`;return}
  const n=N.find(x=>x.id===id),x=[];if(n.aw==="no")x.push("she acts on it without knowing it — never says it");if(n.aw==="partly")x.push("she is only half aware of it");if(n.fb)x.push("false, but held");if(n.va!=null)x.push(`valence ${n.va>0?"+":""}${n.va}`);
  fc.innerHTML=`<p class="t">${n.l}</p><p class="m">${n.k} · strength ${n.s} · ${n.st}${n.since!=null?` · since age ${n.since}`:""}${n.until!=null?` · until about ${n.until}`:""}${x.length?" · "+x.join(" · "):""}</p><p class="g">${n.g}</p>`}
function clear(){svg.classList.remove("hl");lines.forEach(l=>l.classList.remove("on"));Object.values({...ng,...pg}).forEach(g=>g.classList.remove("on"))}
Object.entries({...ng,...pg}).forEach(([k,g])=>{g.addEventListener("mouseenter",()=>show(k));g.addEventListener("focus",()=>show(k));g.addEventListener("click",()=>show(k))});
svg.addEventListener("mouseleave",clear);
/* arrival: the nodes come in the order of her life — those without a date first, then age by age up to 45 (the 65-year-old Clara) */
let tm=[];function play(){tm.forEach(clearTimeout);tm=[];clear();Object.values(ng).forEach(g=>g.classList.add("off"));lines.forEach(l=>l.classList.add("off"));
  const ages=[...new Set(N.map(n=>n.since).filter(a=>a!=null))].sort((a,b)=>a-b),step=(a,i)=>tm.push(setTimeout(()=>{ac.textContent=a===null?"as long as she can remember":`age ${a}`;
    N.filter(n=>n.since===a||(a===null&&n.since==null)).forEach(n=>ng[n.id].classList.remove("off"));
    lines.forEach(l=>{const A=ng[l.dataset.a],B=ng[l.dataset.b]||pg[l.dataset.b];if(A&&!A.classList.contains("off")&&B&&!B.classList.contains("off"))l.classList.remove("off")})},i*900));
  step(null,0);ages.forEach((a,i)=>step(a,i+1));tm.push(setTimeout(()=>{ac.textContent="Clara at 65 — hover a node";show("val1")},(ages.length+1)*900+300))}
document.getElementById("preplay").onclick=play;
const io=new IntersectionObserver(es=>{if(es.some(e=>e.isIntersecting)){io.disconnect();play()}},{threshold:.35});io.observe(svg);
})();
"""

v1 = ND["val1"]
legend = "".join(f'<span><i style="background:{c}"></i>{k}</span>' for k, c in KINDS.items() if k != "rule")
INDEX = head("AI characters now have an inner life — COF 1.2",
             "COF 1.2 gives AI characters a psyche you can read, edit and take with you: values, beliefs, wants, needs, fears, wounds, each tied to the memory that made it — in the same open file as their face, voice and rights.",
             "AI characters now have an inner life",
             "A psyche you can read, edit and take with you — every conviction tied to the memory that made it.",
             "../memories/img/ev2.jpg", "") + f"""
<header class="hero">
  {TOP12}
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
<figure class="wide pgraph" aria-label="Clara's psyche at 65, as a graph">
  <div class="gwrap"><svg id="psvg" viewBox="0 0 1200 660" role="img" aria-label="Clara's psyche: twenty-three nodes hanging under the memories they come from"></svg></div>
  <span class="agec" id="pagec"></span><button class="replay" id="preplay" type="button">▶ replay her life</button>
  <div class="legend">{legend}<span><i style="background:transparent;border:1.5px dashed #eef3f1"></i>held without knowing it</span></div>
  <div class="pfocus" id="pfocus"><p class="g">Hover a node, or let her life play.</p></div>
  <figcaption>Clara's psyche, the nodes coming in the order of her life. Above, the memories they hang on; at the bottom, the convictions held for as long as she can remember. Teal lines say <i>because</i>, rose dotted lines <i>conflicts</i>, grey ones <i>supports</i> or <i>about</i>.</figcaption>
</figure>
<p>Eleven kinds of nodes — wound, value, belief, want, need, fear, stance, taste, habit, contradiction, rule — linked to each other and to the memories: <i>because</i>, <i>about</i>, <i>supports</i>, <i>conflicts</i>. And to the people, places and objects of a life: a value learned from a grandmother, a habit that comes with a notebook, a guitar picked up at night. Readers put the rest together: what she thinks of someone, what a place still means, what changed at forty-five.</p>

<h2>Why this changes what a character is</h2>
<h3>The why</h3>
<p>A list of opinions is flat. “She hates heavy interfaces — because of four years at an agency shipping them too fast” is a character. Memories without a psyche stay anecdotes; a psyche without memories stays slogans. Together, each gives the other its meaning — and a character can explain itself instead of improvising an explanation.</p>

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

<h2>Why did she say no?</h2>
<p>A natural question follows: is a graph really better than a paragraph — and isn't the real future of a character in a model's weights, a latent space, rather than in a file? A companion page takes one refusal of Clara's and asks <i>why</i> five times, down to the four years that began at twenty-four. Then it puts the three ways of keeping a mind side by side — a description, a graph, weights — and says honestly what each can and cannot do.</p>
<p class="btns" style="margin:18px 0 0"><a class="btn main" href="why.html">Why did she say no? →</a></p>
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
    ("what it takes to make", "a pen", "a pen, or a tool that proposes and you tick", "data, GPUs, hours of training"),
    ("works with", "any model", "any model, today", "one model family"),
]
def cell(x): return f'<td class="{x[0]}">{x[1]}</td>' if isinstance(x, tuple) else f"<td>{x}</td>"
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

WHY = head("Why did she say no? — COF 1.2",
           "One refusal of an AI character, asked why five times: from a sentence to the years that made her. And what a description, a graph and a model's weights can each keep of a mind.",
           "Why did she say no?",
           "Ask an AI character why, five times. Only one way of keeping a mind can answer.",
           "../memories/img/ev2.jpg", "why.html") + f"""
<header class="hero">
  {TOP12}
  <div class="text">
    <h1>Why did she say no?</h1>
    <div class="rule"></div>
    <p class="sub">Ask an AI character <i>why</i>, five times. A description improvises; weights can only act. A psyche you can read answers — down to the memory where it started.</p>
  </div>
  <div class="kicker">COF · CHARACTER OPEN FILE</div>
</header>

<main>
<p class="lede">Clara is a fictional designer from Lyon, the example character of the COF format. A prospective client writes to her. Here is the exchange — invented for this page, but played from her file.</p>

<div class="chain">
<div class="chat">
  <p><span class="who">client</span>Could you ship our whole new site by Friday? Autoplay video on the home page, a chat bubble, push notifications — the works.</p>
  <p class="her"><span class="who">Clara</span>No. Not like that. I can give you a lighter site by Friday, or this one in a month. But I won't ship something heavy and fast again.</p>
</div>
{STEPS}
<div class="step" id="whyend" hidden><div class="dot" style="background:#eef3f1">✓</div><div class="card"><p class="t">Five questions, from a sentence to four years that began at twenty-four.</p><p class="why">Every answer above is a node of Clara's file, linked to the next — <i>supports</i>, <i>because</i> — written once by her author, readable by any tool, the same in every model that plays her. Nothing here was improvised.</p></div></div>
</div>
<div class="whyb"><button id="whyb" type="button">Why?</button><button id="whyr" class="ghost" type="button">start again</button></div>

<h2>Three ways to keep a mind</h2>
<p>There are three ways to tell a model who a character is. A <b>description</b>: a few lines in a prompt. A <b>graph</b>: the psyche of COF, convictions linked to each other and to memories. <b>Weights</b>: a model fine-tuned on the character, or a LoRA — the character dissolved in a latent space.</p>
<table class="cmp"><thead><tr><th></th><th>a description</th><th>a graph</th><th>weights</th></tr></thead><tbody>{CMP}</tbody></table>
<p class="cap">Orders of magnitude, not measurements. The size of weights depends on the model and the method; the graph's on how much of the life is written.</p>

<h2>Not instead of weights</h2>
<p>Weights are richer. They hold what no text pins down — a turn of phrase, a hesitation, a way of being funny — and nothing on this page competes with that. But they are mute about themselves: they can produce the no, never the <i>why</i>. You cannot read them, correct one conviction, keep one secret, or take them to another model.</p>
<p>So the two are not rivals. A graph is the score; weights are a performance of it. The score can be read, argued with, versioned, carried to any orchestra — and one day it can be what a model is tuned from, and what its performance is checked against. Until then, it is the only one of the three that you can write by hand tonight, and that every model can read tomorrow.</p>

<h2>How many convictions make a person?</h2>
<p>Nobody has counted. Writers' guides and the psychology of personality give no number; here is ours, from building Clara and from load tests of the tools — an estimate, to be argued with.</p>
<ul class="orders">
  <li><b>23</b><div>Clara today: enough for an agent to play her consistently, and to answer <i>why</i>.</div></li>
  <li><b>50 – 150</b><div>a main character written with care: what a novelist would know about her.</div></li>
  <li><b>300 – 600</b><div>a whole life modelled, with what began and ended along the way.</div></li>
  <li><b>1,000</b><div>the upper bound we tested: the tools still draw it, a conversation never needs it all.</div></li>
</ul>
<p>Even at a thousand, the whole psyche is lighter than one photograph. What makes it useful is not its size but that an agent can pick, for each moment of a conversation, the handful of convictions that matter — and say where they come from.</p>
</main>

<section class="close">
  <p class="voice">She said no because of four years she does not talk about. Now you know why. So does any tool that opens her file.</p>
  <div class="btns row3">
    <a class="btn main" href="index.html">AI characters now have an inner life</a>
    <a class="btn" href="../viewer/#clara/psyche">Open Clara's psyche</a>
    <a class="btn" href="../builder/">Write a psyche</a>
  </div>
</section>
""" + tail("<script>" + WHY_JS + "</script>")

(ROOT / "psyche").mkdir(exist_ok=True)
(ROOT / "psyche/index.html").write_text(INDEX, "utf-8")
(ROOT / "psyche/why.html").write_text(WHY, "utf-8")
print("ok", len(INDEX), len(WHY))
