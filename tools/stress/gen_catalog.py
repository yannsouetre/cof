"""Stress file for the element and preset lists: N clothing / accessory variants (one small generated image each) and P presets.
Usage: python3 tools/stress/gen_catalog.py 300 200 out-dir  (then `cof pack out-dir -o x.cof`). A test input for the builder's pages, not an example."""
import json, random, shutil, sys, hashlib
from pathlib import Path
from PIL import Image, ImageDraw
N, P, out = int(sys.argv[1]), int(sys.argv[2]), Path(sys.argv[3])
random.seed(N * 7 + P)
if out.exists(): shutil.rmtree(out)
shutil.copytree(Path(__file__).resolve().parents[2] / "spec/examples/01-clara-text-only", out)
m = json.loads((out / "manifest.json").read_text("utf-8"))
m["cof"] = "1.1"; m["name"] = f"Catalogue {N}+{P}"
W = "pull veste robe manteau jupe chemise cape écharpe bonnet gilet bottes sandales".split()
C = "crème bleu nuit vert sauge rouille gris perle noir ocre lavande".split()
G = ["outerwear", "top", "bottom", "dress", "shoes", "headwear"]
var = m["elements"].setdefault("appearance", {"variants": {}})["variants"]
assets = m.setdefault("assets", [])
for i in range(N):
    vid = f"c{i+1}"; w = random.choice(W); c = random.choice(C)
    d = out / "elements/appearance" / vid; d.mkdir(parents=True, exist_ok=True)
    im = Image.new("RGB", (256, 256), tuple(random.randint(40, 220) for _ in range(3))); dr = ImageDraw.Draw(im)
    dr.rectangle([48, 64, 208, 224], fill=tuple(random.randint(0, 255) for _ in range(3))); dr.text((60, 20), f"{w} {i+1}", fill="white")
    pf = d / "front.png"; im.save(pf, "PNG"); data = pf.read_bytes()
    aid = f"a-cl-{vid}"
    assets.append({"id": aid, "path": f"elements/appearance/{vid}/front.png", "role": "reference", "mediaType": "image/png", "bytes": len(data),
                   "sha256": hashlib.sha256(data).hexdigest(), "license": "CC-BY-4.0", "digitalSourceType": "trainedAlgorithmicMedia", "view": "front"})
    kind = "accessory" if i % 5 == 4 else "clothing"
    v = {"kind": kind, "label": f"{w.capitalize()} {c} {i+1} / {w} {c} {i+1}", "style": "photo-realistic", "images": [aid]}
    if kind == "clothing": v["garment"] = random.choice(G)
    else: v["accessory"] = random.choice(["bag", "glasses", "jewellery", "hat"])
    var[vid] = v
ids = list(var)
pres = m["presets"]
base = pres["default"]
for j in range(P):
    pid = f"pr{j+1}"
    pres[pid] = {"label": f"Preset {j+1} — {random.choice(C)} / preset {j+1}", "slots": {"personality": ["p1"], "appearance": random.sample(ids, 1)},
                 "alternatives": {"appearance": random.sample(ids, random.randint(0, 4))},
                 "age_override": {"value": random.randint(18, 70), "unit": "years", "basis": "declared"}}
(out / "manifest.json").write_text(json.dumps(m, ensure_ascii=False, indent=2), "utf-8")
print("ok", N, "variants", P, "presets")
