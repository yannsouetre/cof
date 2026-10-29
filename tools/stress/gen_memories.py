"""Stress file for the memories views: N moments, P periods, links everywhere, no media, minimal gists, normal labels.
Usage: python3 tools/stress/gen_memories.py 100 10 out-dir  (then `cof pack out-dir -o x.cof`). Not an example: a test input for the explorer graph and the builder lists."""
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
periods = []
for i in range(P):
    a = 3 + i * (60 // P); b = a + 60 // P - 1
    vid = memory_add(out, identity=None, kind="period", gists={"fr": f"Période {i+1}.", "en": f"Period {i+1}."}, label=f"Les années {a}–{b} / The {a}–{b} years", age=a, lang="fr", fidelity="faded")
    n = json.loads((out / "elements/memories" / vid / "memory.json").read_text("utf-8")); n["when"]["to"] = {"age": {"value": b, "unit": "years"}}
    (out / "elements/memories" / vid / "memory.json").write_text(json.dumps(n, ensure_ascii=False, indent=2), "utf-8"); periods.append((vid, a, b))
moments = []
for i in range(N):
    age = random.randint(3, 62); lab = label()
    vid = memory_add(out, identity=None, kind="moment", gists={"fr": f"Souvenir {i+1}.", "en": f"Memory {i+1}."}, label=lab + " / " + lab.lower(), age=age, approx=random.random() < .3, lang="fr", fidelity=random.choice(["vivid", "clear", "faded"]), salience=random.randint(10, 95), tags=[random.choice(W)])
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
