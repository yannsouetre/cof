"""Writes the round-trip fixture of builder 0.14.2 (hunt H3-08 / 09 / 10 / 11 / 12 / 13): example 07 (linked LoRA under
its own asset id, outfit.json, token profiles, legacy psyche.json with custom traits, horizons, intensities) plus
everything the 1.2.0 builder used to lose — story.md, lorebook.json, variant tags, neutral, derived assets, unknown keys
at every level, a voice profile with unknown keys, mapping_vocabularies, a child preset default on an inherited category.
Usage: python tests/builder/make_fixture_keep.py out.cof   (run from cli/ with PYTHONPATH=. so that cof-cli 1.2 packs it)"""
import hashlib, json, shutil, subprocess, sys, tempfile
from pathlib import Path
from PIL import Image

ROOT = Path(__file__).resolve().parents[2]
out = Path(sys.argv[1]).resolve()
with tempfile.TemporaryDirectory() as tmp:
    d = Path(tmp) / "src"
    shutil.copytree(ROOT / "spec" / "examples" / "07-clara-modulaire", d)
    m = json.loads((d / "manifest.json").read_text("utf-8"))
    E = m["elements"]
    # --- H3-08: story, lorebook, tags, neutral on variants
    (d / "elements/personality/p1/story.md").write_text("# Backstory\n\nClara grew up in Lyon.\n", "utf-8")
    (d / "elements/personality/p1/lorebook.json").write_text(json.dumps({"entries": [{"keys": ["Lyon"], "content": "Her city."}]}, indent=1), "utf-8")
    E["personality"]["variants"]["p1"]["story"] = "elements/personality/p1/story.md"
    E["personality"]["variants"]["p1"]["lorebook"] = "elements/personality/p1/lorebook.json"
    E["personality"]["variants"]["p1"]["tags"] = ["canon", "lyon"]
    E["appearance"]["variants"]["o1"]["neutral"] = False
    # --- H3-10: unknown keys everywhere
    m["x-studio"] = {"pipeline": "nightly", "n": 3}
    m["identities"] = {"clara": {k: m[k] for k in ("name", "nickname", "summary", "fictional", "morphology") if k in m}}
    m["default_identity"] = "clara"
    m["cof"] = "1.1"   # identities.<id>.language is a 1.1 addition
    m["identities"]["clara"]["x-casting"] = {"agency": "none"}
    m["identities"]["clara"]["tags"] = {"mood": "calm"}
    m["identities"]["clara"]["language"] = "fr"
    m["presets"]["default"]["x-render"] = {"seed": 42}
    m["presets"]["default"]["style_tags"] = ["warm-light"]
    E["appearance"]["variants"]["f1"]["x-note"] = "keep me"
    E["appearance"]["variants"]["f1"]["estimated"] = True
    m["rights"]["permissions"]["x-house-rule"] = "no-ads"
    m["provenance"]["x-batch"] = "b-17"
    m["mapping_vocabularies"] = {"garments": "garments-1.0", "x-moods": "moods-0.1"}
    m["priorities"]["by_target"]["x-kiosk"] = {"visual": ["images"]}
    # --- H3-11: derived assets on a variant
    Image.new("RGB", (32, 32), (10, 20, 30)).save(d / "elements/appearance/f1/head.front.canny.png", "PNG")
    b = (d / "elements/appearance/f1/head.front.canny.png").read_bytes()
    m["assets"].append({"id": "a-head-front-canny", "path": "elements/appearance/f1/head.front.canny.png", "role": "derived", "method": "canny",
                        "source": "a-head-front", "mediaType": "image/png", "bytes": len(b), "sha256": hashlib.sha256(b).hexdigest(),
                        "license": "CC-BY-4.0"})
    E["appearance"]["variants"]["f1"]["derived"] = ["a-head-front-canny"]
    (d / "elements/appearance/f1/face.json").write_text(json.dumps({"model": "COF-FACE-1", "eyes": "green"}), "utf-8")
    E["appearance"]["variants"]["f1"]["code"] = "elements/appearance/f1/face.json"
    # --- voice profile with unknown keys and an engine with an extra field
    (d / "elements/voice/v1").mkdir(parents=True)
    (d / "elements/voice/v1/profile.json").write_text(json.dumps({
        "canonical": {"gender_presentation": "feminine", "age_perceived": "adult", "accent": "fr-FR", "pitch": {"range": "medium", "hz": [180, 220]}, "rate": "medium", "timbre": ["warm"]},
        "speech_style": {"register": "casual", "x-pauses": "long"},
        "engines": [{"engine": "xtts", "version": "2.0", "voice_id": "clara-fr", "x-temperature": 0.6}],
        "x-studio": {"take": 3}}, indent=1), "utf-8")
    E["voice"] = {"variants": {"v1": {"kind": "described", "label": "Voix décrite", "language": "fr", "profile": "elements/voice/v1/profile.json", "x-recorded": False}}}
    m["presets"]["default"]["slots"]["voice"] = ["v1"]
    # --- H3-12: a child preset default on an inherited category
    m["presets"]["young"]["defaults"] = {"appearance": "f1"}
    m["presets"]["young"]["slots"].pop("appearance", None)   # inherits f1, b1, o1 from default
    m["presets"]["young"]["slots"]["voice"] = []           # the 14-year-old preset keeps no adult voice
    (d / "manifest.json").write_text(json.dumps(m, indent=1, ensure_ascii=False), "utf-8")
    subprocess.run([sys.executable, "-m", "cof_cli.cli", "pack", str(d), "-o", str(out), "--force"], check=True)
    subprocess.run([sys.executable, "-m", "cof_cli.cli", "validate", str(out)], check=True)
print("written", out)
