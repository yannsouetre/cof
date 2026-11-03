"""Stress file for the psyche views: N psyche nodes (RFC 0004) added to a character file over a life of A years.
Usage: python3 tools/stress/gen_psyche.py 500 stress-500.cof stress-psyche-500.cof [--life 50]
       (the source and the output may be a .cof or a folder; a .cof source is unpacked, a .cof output is packed with `cof pack`).
Not an example: a test input for the explorer's Psyche tab and the builder's lists, with a realistic shape rather than good text.
Proportions (weights, rounded to N): values 4 %, beliefs 15 %, wants 10 %, needs 5 %, fears 8 %, wounds 3 %, stances 20 %, tastes 15 %,
habits 12 %, contradictions 4 %, rules 4 %. `since` spread over the life by kind (values and wounds early, habits later); about 25 %
of the nodes end (`until`), half of those with a successor of the same kind (`derives_from`, since = the predecessor's until);
`aware` partly / no on about 15 %; `valence` on every stance and taste; `because` to memories (about 40 %, a memory not later than
the node) and to earlier nodes (no cycle); `supports` between nodes; `who` / `where` / `what` on about 20 %, reusing the memories'
people, places and objects; stances toward the memories' people, a few free subjects and one toward the user; contradictions last,
each with exactly two `conflicts` to nodes held together at some age; rules `core`; one or two nodes of risk `inappropriate`
(and the file-level tag); labels « FR / EN », gists in fr and en from templates. A preset « psyche » (the default preset) shows the
character at the age A and holds the nodes held at A (since ≤ A < until, a contradiction only with both sides) and the memories up to A."""
import argparse, json, os, random, shutil, subprocess, sys, tempfile, zipfile
from pathlib import Path
ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "cli"))
from cof_cli.psyche import ID_PREFIX
ap = argparse.ArgumentParser(description="stress file for the psyche views")
ap.add_argument("nodes", type=int); ap.add_argument("src", help=".cof or folder (a memories stress file, or any character)"); ap.add_argument("out", help=".cof or folder")
ap.add_argument("--life", type=int, default=50, help="the character's age at the psyche preset (default 50)")
ap.add_argument("--seed", type=int, default=None)
args = ap.parse_args()
N, A, src, out = args.nodes, args.life, Path(args.src), Path(args.out)
random.seed(args.seed if args.seed is not None else N * 1000 + A)
work = Path(tempfile.mkdtemp()) / "c" if out.suffix == ".cof" else out
if work.exists(): shutil.rmtree(work)
if src.is_dir(): shutil.copytree(src, work)
else:
    with zipfile.ZipFile(src) as z: z.extractall(work)
m = json.loads((work / "manifest.json").read_text("utf-8"))
E = m.setdefault("elements", {})
if (E.get("psyche") or {}).get("variants"): sys.exit("the source already has psyche nodes")
# the memories: age, people, places, objects (the pools the nodes reuse)
age_of = lambda p: (p or {}).get("age", {}).get("value") if isinstance((p or {}).get("age"), dict) else None
mems, who, where, what = [], {}, {}, {}
for vid, v in ((E.get("memories") or {}).get("variants") or {}).items():
    n = json.loads((work / v["memory"]).read_text("utf-8")) if v.get("memory") else {}
    w = n.get("when") or {}; a = age_of(w) if age_of(w) is not None else age_of(w.get("from"))
    mems.append((vid, v.get("kind"), a))
    for x in n.get("who") or []: lab = next(iter((x.get("label") or {}).values()), None); who[lab] = who.get(lab, 0) + 1 if lab else 0
    lab = next(iter(((n.get("where") or {}).get("label") or {}).values()), None)
    if lab: where[lab] = where.get(lab, 0) + 1
    for x in n.get("what") or []:
        lab = next(iter((x.get("label") or {}).values()), None)
        if lab: what[lab] = what.get(lab, 0) + 1
who.pop(None, None)
pool = lambda d, dflt: (list(d), list(d.values())) if d else (dflt, [1] * len(dflt))
WHO, WHOW = pool(who, ["Léo", "Anna", "Marc"]); WHERE, WHEREW = pool(where, ["la maison", "le quai", "l'atelier"]); WHAT, WHATW = pool(what, ["le carnet", "la guitare", "le vélo rouge", "la tasse ébréchée"])
moments = [(v, a) for v, k, a in mems if k != "period" and a is not None]
# words and templates per kind: (fr, en) pairs, a label pattern and a gist pattern in each language
W = {
    "value": ["l'honnêteté|honesty", "la liberté|freedom", "la loyauté|loyalty", "la lenteur|slowness", "la justice|fairness", "la curiosité|curiosity", "la sobriété|sobriety", "la beauté|beauty", "la famille|family", "le travail bien fait|work well done"],
    "belief": ["on ne peut compter que sur soi|one can only count on oneself", "le monde récompense la patience|the world rewards patience", "les gens finissent par partir|people end up leaving", "tout se répare|everything can be mended", "il faut mériter sa place|one has to earn one's place", "la vérité finit par sortir|the truth comes out in the end"],
    "want": ["ouvrir un atelier|open a workshop", "voyager seule|travel alone", "écrire un livre|write a book", "retrouver mon frère|find my brother again", "vivre à la campagne|live in the country", "être reconnue|be recognised"],
    "need": ["être écoutée|being heard", "du calme|quiet", "appartenir à un groupe|belonging", "comprendre|understanding", "se sentir utile|feeling useful"],
    "fear": ["le vide|emptiness", "l'abandon|abandonment", "l'échec en public|failing in public", "la maladie|illness", "devenir comme mon père|becoming like my father", "les foules|crowds"],
    "wound": ["le départ de ma mère|my mother leaving", "la trahison d'un ami|a friend's betrayal", "l'humiliation à l'école|humiliation at school", "le licenciement|being laid off", "le deuil|a bereavement"],
    "stance": [],
    "taste": ["le café noir|black coffee", "la pluie d'été|summer rain", "les vieux films|old films", "le jazz|jazz", "la mer en hiver|the sea in winter", "les marchés|markets", "la cuisine épicée|spicy food", "les trains de nuit|night trains"],
    "habit": ["marcher tôt le matin|walking early in the morning", "noter tout dans un carnet|writing everything down", "ranger quand je suis inquiète|tidying when worried", "appeler ma sœur le dimanche|calling my sister on Sundays", "relire avant de dormir|rereading before sleep", "arriver en avance|arriving early"],
    "rule": ["ne jamais mentir à un enfant|never lie to a child", "ne pas frapper|never strike", "tenir parole|keep my word", "ne pas trahir un secret|never betray a secret"],
}
FREE = ["les réseaux sociaux|social media", "la ville|the city", "les médecins|doctors", "l'argent|money", "la politique|politics"]
G = {"value": ("Ce qui compte avant tout : {f}.", "What matters above all: {e}."), "belief": ("Elle croit que {f}.", "She believes {e}."),
     "want": ("Elle voudrait {f}.", "She wants to {e}."), "need": ("Elle a besoin de {f}.", "She needs {e}."), "fear": ("Elle redoute {f}.", "She fears {e}."),
     "wound": ("Elle porte encore {f}.", "She still carries {e}."), "stance": ("Envers {f} : une position qui a pris le temps de se former.", "Toward {e}: a stance that took time to form."),
     "taste": ("Elle aime {f}.", "She likes {e}."), "habit": ("Elle a l'habitude de {f}.", "Her habit: {e}."), "rule": ("Une règle qu'elle garde : {f}.", "A rule she keeps: {e}."),
     "contradiction": ("Entre {f} : les deux tiennent ensemble.", "Between {e}: both hold at once.")}
WEIGHTS = {"value": 4, "belief": 15, "want": 10, "need": 5, "fear": 8, "wound": 3, "stance": 20, "taste": 15, "habit": 12, "contradiction": 4, "rule": 4}
SINCE = {"value": (4, 25), "belief": (6, A), "want": (10, A), "need": (3, A), "fear": (3, A), "wound": (4, 30), "stance": (8, A), "taste": (3, A), "habit": (12, A), "rule": (10, 35)}
raw = {k: N * w / 100 for k, w in WEIGHTS.items()}; cnt = {k: int(x) for k, x in raw.items()}
for k in sorted(raw, key=lambda k: raw[k] - cnt[k], reverse=True)[:N - sum(cnt.values())]: cnt[k] += 1
pair = lambda s: s.split("|")
nodes, var, used = {}, {}, {}
pt = lambda a: {"age": {"value": a, "unit": "years"}}
def label(kind, fr, en):
    k = (fr, en); used[k] = used.get(k, 0) + 1; s = f" ({used[k]})" if used[k] > 1 else ""
    return f"{fr[0].upper() + fr[1:]}{s} / {en[0].upper() + en[1:]}{s}"
def new(kind, fr, en, since=None, pred=None, lab=None):
    vid = f"{ID_PREFIX[kind]}{sum(1 for v in var.values() if v['kind'] == kind) + 1}"
    n = {"gist": {"fr": G[kind][0].format(f=fr), "en": G[kind][1].format(e=en)}, "strength": random.randint(30, 95) if kind in ("value", "wound", "rule") else random.randint(15, 90)}
    n["stability"] = "core" if kind == "rule" else random.choices(["core", "settled", "shifting", "fragile"], [15, 50, 25, 10])[0]
    if since is not None: n["since"] = pt(since)
    if kind in ("stance", "taste"): n["valence"] = random.randint(-80, 90) if kind == "stance" else random.choice([random.randint(40, 95), random.randint(-90, -30)])
    if kind == "belief" and random.random() < .1: n["false_but_held"] = True
    r = random.random()
    if kind != "rule" and r < .15: n["aware"] = "partly" if r < .1 else "no"
    n.update({"origin": "authored", "visibility": "canon", "disclosure": "guarded" if random.random() < .1 else "open"})
    v = {"kind": kind, "label": label(kind, *(lab or (fr, en))), "node": f"elements/psyche/{vid}/psyche-node.json", "strength": n["strength"]}
    if pred: v["derives_from"] = pred
    nodes[vid], var[vid] = n, v
    return vid
def span(vid):
    n = nodes[vid]; return (age_of(n.get("since")) or 0, age_of(n.get("until")) if n.get("until") else A + 1)
# the nodes of each kind but contradictions; about 25 % end, half of those with a successor
for kind in [k for k in WEIGHTS if k != "contradiction"]:
    made = 0
    while made < cnt[kind]:
        if kind == "stance":
            r = random.random()
            subj = ("user" if not any(nodes[v].get("about", {}).get("user") for v in nodes) else None) or (random.choice(FREE) if r < .15 else random.choices(WHO, WHOW)[0])
            fr, en = (("l'utilisateur", "the user") if subj == "user" else pair(subj) if "|" in subj else (subj, subj))
        else:
            fr, en = pair(random.choice(W[kind]))
        lo, hi = SINCE[kind]; since = None if random.random() < .08 else random.randint(lo, max(lo, hi - 1))
        prev = None
        while made < cnt[kind]:
            vid = new(kind, fr, en, since, prev, (f"envers {fr}", f"toward {en}") if kind == "stance" else None); made += 1
            if kind == "stance": nodes[vid]["about"] = {"user": True} if subj == "user" else {"label": {"fr": fr, "en": en} if fr != en else {"fr": fr}}
            s0 = since if since is not None else 0
            if kind == "rule" or s0 >= A - 1 or random.random() >= .3: break
            until = random.randint(s0 + 1, A); nodes[vid]["until"] = pt(until)
            if random.random() >= .5: break
            prev, since = vid, until                                  # a successor: the same kind, from the age the predecessor was let go
order = list(nodes)
# links: because to a memory not later than the node (~40 %, every wound), because / supports to earlier nodes, who / where / what (~20 %)
for i, vid in enumerate(order):
    n, kind = nodes[vid], var[vid]["kind"]; s0 = age_of(n.get("since"))
    L = []
    if moments and (kind == "wound" or random.random() < .4):
        early = [v for v, a in moments if s0 is None or a <= s0 + .9] or [min(moments, key=lambda x: x[1])[0]]
        for t in random.sample(early, min(len(early), random.choice([1, 1, 2]))): L.append({"to": f"memories/{t}", "type": "because"})
    if i and random.random() < .15: L.append({"to": f"psyche/{random.choice(order[:i])}", "type": "because"})
    if i and random.random() < .08:
        t = random.choice(order[:i])
        if t != vid: L.append({"to": f"psyche/{t}", "type": "supports"})
    if L: n["links"] = L
    if random.random() < .2:
        r = random.random()
        if r < .5: n["who"] = [{"label": {"fr": x}} for x in sorted({random.choices(WHO, WHOW)[0] for _ in range(random.choice([1, 1, 2]))})]
        elif r < .8: n["where"] = [{"label": {"fr": random.choices(WHERE, WHEREW)[0]}}]
        else: n["what"] = [{"label": {"fr": random.choices(WHAT, WHATW)[0]}}]
    n["tags"] = [random.choice(["self", "work", "family", "body", "senses", "others", "past"])]
# contradictions: two nodes held together at some age, never another contradiction
cands = [v for v in order if var[v]["kind"] in ("value", "belief", "want", "need", "habit", "taste", "fear")]
for _ in range(cnt["contradiction"]):
    for _try in range(200):
        a, b = random.sample(cands, 2); (sa, ua), (sb, ub) = span(a), span(b)
        if max(sa, sb) < min(ua, ub) and var[a]["label"].split(" (")[0] != var[b]["label"].split(" (")[0]: break
    fa, ea = var[a]["label"].split(" / "); fb, eb = var[b]["label"].split(" / ")
    cut = lambda t: (t[:21] + "…" if len(t) > 22 else t).lower()          # manifest labels are short: the gist says it in full
    vid = new("contradiction", f"« {fa.lower()} » et « {fb.lower()} »", f"“{ea.lower()}” and “{eb.lower()}”", max(sa, sb) or None, lab=(f"{cut(fa)} ↔ {cut(fb)}", f"{cut(ea)} ↔ {cut(eb)}"))
    nodes[vid]["links"] = [{"to": f"psyche/{a}", "type": "conflicts"}, {"to": f"psyche/{b}", "type": "conflicts"}]
    nodes[vid].pop("valence", None); nodes[vid]["tags"] = ["self"]
# one or two nodes of risk « inappropriate » (and the file-level tag)
for vid in random.sample([v for v in nodes if var[v]["kind"] in ("habit", "taste", "want")], 1 + (N >= 200)): nodes[vid]["risk"] = "inappropriate"
# write: node files, the manifest's variants, the preset at A, the 1.2 markers
for vid, n in nodes.items():
    d = work / "elements" / "psyche" / vid; d.mkdir(parents=True, exist_ok=True)
    (d / "psyche-node.json").write_text(json.dumps(n, ensure_ascii=False, indent=2) + "\n", "utf-8")
E["psyche"] = {"variants": var}
held = {v for v in nodes if (age_of(nodes[v].get("since")) or 0) <= A and (not nodes[v].get("until") or A < age_of(nodes[v]["until"]))}
held = [v for v in nodes if v in held and not (var[v]["kind"] == "contradiction" and any(l["to"].split("/")[1] not in held for l in nodes[v]["links"]))]
P = m.setdefault("presets", {}); base = P.get(m.get("default_preset")) or next(iter(P.values()), {})
mem_held = [v for v, k, a in mems if a is None or a <= A]
P["psyche"] = {"label": f"Psyché à {A} ans / Psyche at {A}", "slots": {**{k: list(x) for k, x in (base.get("slots") or {}).items() if k not in ("memories", "psyche")}, "memories": mem_held, "psyche": held}, "age_override": {"value": A, "unit": "years", "basis": "declared"}}
m["default_preset"] = "psyche"
m["cof"] = "1.2"
cov = m.setdefault("coverage", {}); cov["elements"] = sorted(set(cov.get("elements") or []) | {"psyche"})
tg = m.setdefault("tags", {}); auto = tg.setdefault("auto", [])
if "has-psyche" not in auto: auto.append("has-psyche")
tg["content"] = [t for t in (tg.get("content") or []) if t != "none"] + ["psyche-inappropriate"]
m["name"] = f"{m.get('name') or 'Stress'} + psyche {N}"
(work / "manifest.json").write_text(json.dumps(m, ensure_ascii=False, indent=2) + "\n", "utf-8")
kinds = {k: sum(1 for v in var.values() if v["kind"] == k) for k in WEIGHTS}
print("ok", N, "nodes:", " ".join(f"{k} {c}" for k, c in kinds.items()), f"· until {sum(1 for n in nodes.values() if n.get('until'))} · derives_from {sum(1 for v in var.values() if v.get('derives_from'))} · held at {A}: {len(held)}")
if out.suffix == ".cof":
    subprocess.run([sys.executable, "-c", "import sys;from cof_cli.cli import main;sys.argv=['cof','pack',sys.argv[1],'-o',sys.argv[2],'--force'];sys.exit(main())", str(work), str(out)], check=True, env={**os.environ, "PYTHONPATH": str(ROOT / "cli")})
    shutil.rmtree(work.parent)
