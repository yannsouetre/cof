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
    # --- hunt 1.2.2 (BUILDER-03/04/06/07/08): an unknown psyche kind, x- keys on memory entries and on category objects, a motion clips
    # variant without visemes.json, preset lists equal to the inherited ones, an explicit identity on a memory, a card with an empty creator
    m["cof"] = "1.3"   # a later minor: its unknown psyche kind is a warning for cof validate (D-H1)
    (d / "elements/memories/ev1").mkdir(parents=True)
    (d / "elements/memories/ev1/memory.json").write_text(json.dumps({"gist": {"fr": "Le marché de la Croix-Rousse.", "en": "The Croix-Rousse market."}, "origin": "authored", "visibility": "canon", "disclosure": "open", "fidelity": "clear", "nature": ["experienced"]}), "utf-8")
    E["memories"] = {"variants": {"ev1": {"kind": "moment", "label": "Marché", "memory": "elements/memories/ev1/memory.json", "identity": "clara", "x-mood": "blue"}}, "x-index": "v2"}
    (d / "elements/psyche/val1").mkdir(parents=True); (d / "elements/psyche/dream1").mkdir(parents=True)
    (d / "elements/psyche/val1/psyche-node.json").write_text(json.dumps({"gist": {"fr": "La sobriété.", "en": "Sobriety."}, "strength": 80, "origin": "authored", "visibility": "canon", "disclosure": "open", "stability": "settled"}), "utf-8")
    (d / "elements/psyche/dream1/psyche-node.json").write_text(json.dumps({"gist": {"en": "A recurring dream of a flooded library."}, "strength": 40, "origin": "authored", "visibility": "canon", "disclosure": "open"}), "utf-8")
    E["psyche"] = {"variants": {"val1": {"kind": "value", "label": "Sobriété", "node": "elements/psyche/val1/psyche-node.json", "identity": "clara", "strength": 80},
                                "dream1": {"kind": "x-dream", "label": "Rêve", "node": "elements/psyche/dream1/psyche-node.json", "identity": "clara", "strength": 40}},
                   "x-graph-layout": {"seed": 7}}
    m["presets"]["default"]["slots"]["memories"] = ["ev1"]
    m["presets"]["default"]["slots"]["psyche"] = ["val1", "dream1"]
    m["presets"]["young"]["slots"]["psyche"] = ["val1", "dream1"]   # equal to the inherited list, declared: kept verbatim; young declares no memories list
    (d / "elements/motion/m1/clips").mkdir(parents=True)
    bvh = b"HIERARCHY\nROOT Hips\n{\n OFFSET 0 0 0\n CHANNELS 3 Xrotation Yrotation Zrotation\n End Site\n {\n  OFFSET 0 1 0\n }\n}\nMOTION\nFrames: 1\nFrame Time: 0.033333\n0 0 0\n"
    (d / "elements/motion/m1/clips/wave.bvh").write_bytes(bvh)
    m["assets"].append({"id": "a-mo-m1-wave", "path": "elements/motion/m1/clips/wave.bvh", "role": "motion-clip", "mediaType": "application/x-bvh", "bytes": len(bvh), "sha256": hashlib.sha256(bvh).hexdigest(), "license": "CC-BY-4.0", "rig": "custom"})
    E["motion"] = {"variants": {"m1": {"kind": "clips", "label": "Wave", "clips": ["a-mo-m1-wave"], "rig": "custom"}}}
    m["presets"]["default"]["slots"]["motion"] = ["m1"]
    cj = json.loads((d / "elements/personality/p2/card.json").read_text("utf-8")); cj.setdefault("data", {})["creator"] = ""
    (d / "elements/personality/p2/card.json").write_text(json.dumps(cj, ensure_ascii=False, indent=1), "utf-8")
    (d / "manifest.json").write_text(json.dumps(m, indent=1, ensure_ascii=False), "utf-8")
    subprocess.run([sys.executable, "-m", "cof_cli.cli", "pack", str(d), "-o", str(out), "--force"], check=True)
    subprocess.run([sys.executable, "-m", "cof_cli.cli", "validate", str(out)], check=True)
print("written", out)
