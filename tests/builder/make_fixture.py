"""Writes a .cof that declares a later 1.x minor and carries a category the builder does not know
(`sketches`: two variants, one sub-file, one media asset, listed by the default preset).
Usage: python tests/builder/make_fixture.py out.cof   (needs cof-cli and Pillow)"""
import hashlib, json, os, shutil, subprocess, sys, tempfile
from pathlib import Path
from PIL import Image

ROOT = Path(__file__).resolve().parents[2]
out = Path(sys.argv[1]).resolve()
with tempfile.TemporaryDirectory() as tmp:
    d = Path(tmp) / "src"
    shutil.copytree(ROOT / "spec" / "examples" / "01-clara-text-only", d)
    m = json.loads((d / "manifest.json").read_text("utf-8"))
    m["cof"] = "1.9"
    (d / "elements/sketches/n1").mkdir(parents=True)
    (d / "elements/sketches/n1/sketch.json").write_text(json.dumps({"gist": {"fr": "test"}, "custom": {"deep": [1, 2, 3]}}), "utf-8")
    Image.new("RGB", (64, 48), (200, 120, 80)).save(d / "elements/sketches/n1/pic.jpg", "JPEG")
    b = (d / "elements/sketches/n1/pic.jpg").read_bytes()
    m["elements"]["sketches"] = {"variants": {
        "n1": {"kind": "note", "label": "One", "sketch": "elements/sketches/n1/sketch.json", "media": ["a-n1"], "extra_field": True},
        "n2": {"kind": "note", "label": "Two", "media_from": "sketches/n1"}}}
    m["assets"].append({"id": "a-n1", "path": "elements/sketches/n1/pic.jpg", "role": "other", "mediaType": "image/jpeg",
                        "bytes": len(b), "sha256": hashlib.sha256(b).hexdigest(), "license": "CC-BY-4.0", "digitalSourceType": "trainedAlgorithmicMedia"})
    m["presets"]["default"]["slots"]["sketches"] = ["n1", "n2"]
    (d / "manifest.json").write_text(json.dumps(m, indent=1), "utf-8")
    subprocess.run(["cof", "pack", str(d), "-o", str(out), "--force"], check=True)
print("written", out)
