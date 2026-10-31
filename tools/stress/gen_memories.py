"""Stress file for the memories views: N moments, P periods, links everywhere, people and places as hubs (a few frequent, many rare), no media, minimal gists, normal labels.
Usage: python3 tools/stress/gen_memories.py 100 10 out-dir  (then `cof pack out-dir -o x.cof`). Not an example: a test input for the explorer graph and the builder lists.
Periods split ages 3–63 evenly (fractional bounds when P > 60); moments get one decimal of age so that short periods still hold some."""
import json, random, shutil, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "cli"))
from cof_cli.selfdesc import memory_add
N, P, out = int(sys.argv[1]), int(sys.argv[2]), Path(sys.argv[3])
random.seed(N)
if out.exists(): shutil.rmtree(out)
shutil.copytree(Path(__file__).resolve().parents[2] / "spec/examples/01-clara-text-only", out)
W = "matin soir quai jardin gare atelier pluie neige lettre fenêtre train velo cafe river lampe rue plage cahier musique silence".split()
label = lambda: " ".join(random.choice(W) for _ in range(random.randint(2, 5))).capitalize()
NAMES = "Léo Théo Anna Marc Inès Paul Jade Hugo Lina Noé Rose Yann Zoé Malo Elsa Tom Iris Sacha Lou Nina".split()
PEOPLE = [NAMES[i % len(NAMES)] + ("" if i < len(NAMES) else f" {i // len(NAMES) + 1}") for i in range(max(6, N // 20))]
PLACES = [f"{w.capitalize()} {i + 1}" for i, w in enumerate((W * (1 + N // 400))[:max(4, N // 40)])]
zipf = lambda pool: random.choices(pool, weights=[1 / (i + 1) for i in range(len(pool))])[0]   # a few people / places are everywhere, most are rare
periods = []
for i in range(P):
    span = 60 / P; a = round(3 + i * span, 2); b = round(a + span - (1 if span >= 2 else 0.01), 2); a = int(a) if a == int(a) else a; b = int(b) if b == int(b) else b
    vid = memory_add(out, identity=None, kind="period", gists={"fr": f"Période {i+1}.", "en": f"Period {i+1}."}, label=f"Les années {a}–{b} / The {a}–{b} years", age=a, lang="fr", fidelity="faded")
    n = json.loads((out / "elements/memories" / vid / "memory.json").read_text("utf-8")); n["when"]["to"] = {"age": {"value": b, "unit": "years"}}
    (out / "elements/memories" / vid / "memory.json").write_text(json.dumps(n, ensure_ascii=False, indent=2), "utf-8"); periods.append((vid, a, b))
moments = []
for i in range(N):
    age = round(random.uniform(3, 62.9), 1); lab = label()
    who = sorted({zipf(PEOPLE) for _ in range(random.choice([0, 1, 1, 2, 3]))}); where = zipf(PLACES) if random.random() < .7 else None
    vid = memory_add(out, identity=None, kind="moment", gists={"fr": f"Souvenir {i+1}.", "en": f"Memory {i+1}."}, label=lab + " / " + lab.lower(), age=age, who=who, where=where, approx=random.random() < .3, lang="fr", fidelity=random.choice(["vivid", "clear", "faded"]), salience=random.randint(10, 95), tags=[random.choice(W)])
    moments.append((vid, age))
mp = {v: json.loads((out / "elements/memories" / v / "memory.json").read_text("utf-8")) for v, _ in moments}
for i, (v, age) in enumerate(moments):
    links = []
    per = [p for p, a, b in periods if a <= age <= b]
    if per and random.random() < .7: links.append({"to": f"memories/{per[0]}", "type": "part-of"})
    older = [w for w, ag in moments[:i] if ag < age]
    for _ in range(random.choice([0, 1, 1, 2, 3])):
        if older: links.append({"to": f"memories/{random.choice(older)}", "type": random.choice(["after", "about", "because", "same-event"])})
    if links: mp[v]["links"] = links
    (out / "elements/memories" / v / "memory.json").write_text(json.dumps(mp[v], ensure_ascii=False, indent=2), "utf-8")
m = json.loads((out / "manifest.json").read_text("utf-8")); m["name"] = f"Stress {N}+{P}"
(out / "manifest.json").write_text(json.dumps(m, ensure_ascii=False, indent=2), "utf-8")
print("ok", N, P)
