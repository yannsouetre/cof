import json
import shutil
import zipfile
from pathlib import Path

import pytest

from cof_cli.container import ContainerError, pack, read_manifest, unpack
from cof_cli.convert import card_to_cof_dir, read_card_from_png, write_card_to_png
from cof_cli.validate import Report, validate_cof, validate_dir
from cof_cli import SPEC_VERSION

ROOT = Path(__file__).resolve().parents[2]
EXAMPLE = ROOT / "spec" / "examples" / "01-clara-text-only"


@pytest.fixture
def workdir(tmp_path):
    d = tmp_path / "clara"
    shutil.copytree(EXAMPLE, d)
    return d


def test_example_dir_is_valid(workdir):
    rep = Report()
    validate_dir(workdir, rep, recompute=False)
    assert rep.ok, rep.errors
    assert "chat-text" in rep.info["completeness"]["targets_ready"]


def test_pack_layout_and_validate(workdir, tmp_path):
    out = tmp_path / "clara.cof"
    pack(workdir, out)
    with zipfile.ZipFile(out) as z:
        infos = z.infolist()
        assert infos[0].filename == "mimetype" and infos[0].compress_type == zipfile.ZIP_STORED
        assert infos[1].filename == "manifest.json"
        assert z.read("mimetype") == b"application/vnd.cof.character+zip"
    rep = validate_cof(out)
    assert rep.ok, rep.errors
    m = read_manifest(out)
    assert m["completeness"]["score"] > 0


def test_unpack_matches(workdir, tmp_path):
    out = tmp_path / "clara.cof"
    pack(workdir, out)
    d = unpack(out, tmp_path / "x")
    a = json.loads((d / "elements/personality/p1/card.json").read_text("utf-8"))
    b = json.loads((workdir / "elements/personality/p1/card.json").read_text("utf-8"))
    assert a == b


def test_minor_with_sexual_permission_is_rejected(workdir):
    m = json.loads((workdir / "manifest.json").read_text("utf-8"))
    m["presets"]["default"]["age_override"] = {"value": 15, "unit": "years", "basis": "declared"}
    m["rights"]["permissions"]["allowSexualUsage"] = True
    (workdir / "manifest.json").write_text(json.dumps(m), "utf-8")
    rep = Report()
    validate_dir(workdir, rep)
    assert not rep.ok and any("effective allowSexualUsage" in e for e in rep.errors), rep.errors


def test_real_person_needs_consent(workdir):
    m = json.loads((workdir / "manifest.json").read_text("utf-8"))
    m["fictional"] = False
    (workdir / "manifest.json").write_text(json.dumps(m), "utf-8")
    rep = Report()
    validate_dir(workdir, rep)
    assert rep.ok and any("consent" in w for w in rep.warnings)        # a real person without consent is warned, not refused


def test_undeclared_script_is_rejected(workdir):
    (workdir / "extensions").mkdir()
    (workdir / "extensions" / "evil.js").write_text("alert(1)")
    rep = Report()
    validate_dir(workdir, rep)
    assert any("executable" in e for e in rep.errors)


def test_zip_slip_rejected(tmp_path):
    bad = tmp_path / "bad.cof"
    with zipfile.ZipFile(bad, "w") as z:
        z.writestr("mimetype", "application/vnd.cof.character+zip")
        z.writestr("manifest.json", "{}")
        z.writestr("../evil.txt", "x")
    with pytest.raises(ContainerError):
        unpack(bad, tmp_path / "out")


def test_png_card_roundtrip(workdir, tmp_path):
    from cof_cli.cli import _placeholder_png
    card = json.loads((workdir / "elements/personality/p1/card.json").read_text("utf-8"))
    png = write_card_to_png(_placeholder_png(None), card)
    back = read_card_from_png(png)
    assert back["spec"] == "chara_card_v3"
    assert back["data"] == card["data"]
    d = card_to_cof_dir(back, tmp_path / "imp", png=png, age=34, language="fr")
    rep = Report()
    validate_dir(d, rep)
    assert rep.ok, rep.errors


MODULAR = ROOT / "spec" / "examples" / "07-clara-modulaire"


def test_presets_resolve_and_inherit():
    from cof_cli.model import resolved, lowest_age, preset_age
    m = json.loads((MODULAR / "manifest.json").read_text("utf-8"))
    d = resolved(m, "default"); y = resolved(m, "young")
    assert d["personality"][0]["_id"] == "p1" and y["personality"][0]["_id"] == "p2"
    assert "appearance" not in y                            # 'young' is text-only (an explicit empty list overrides the inherited one)
    assert y["personality"][0].get("psyche")               # inherited via derives_from
    assert lowest_age(m) == 14 and preset_age(m, "young") == 14 and preset_age(m, "default") == 34


def test_preset_level_age_rules(tmp_path):
    """v0.5: a file may hold an adult preset WITH intimate and a minor preset WITHOUT; the minor preset refuses
    intimate, estimated body and effective allowSexualUsage; the adult preset may override allowSexualUsage to true."""
    d = tmp_path / "m"; shutil.copytree(MODULAR, d)
    m = json.loads((d / "manifest.json").read_text("utf-8"))
    V = m["elements"]["appearance"]["variants"]
    V["i1"] = {"kind": "intimate", "label": "Intime", "age": {"value": 34}}
    m["tags"]["content"] = ["nudity"]
    m["presets"]["default"]["slots"]["appearance"].append("i1")
    m["presets"]["default"]["permissions_override"] = {"allowSexualUsage": True}      # adult preset: fine
    (d / "manifest.json").write_text(json.dumps(m), "utf-8")
    rep = Report(); validate_dir(d, rep)
    assert rep.ok, rep.errors
    # same intimate combined in the 14-year-old preset → refused
    m["presets"]["young"]["slots"]["appearance"] = ["i1"]
    (d / "manifest.json").write_text(json.dumps(m), "utf-8")
    rep = Report(); validate_dir(d, rep)
    assert any("presets.young" in e and "intimate variant" in e for e in rep.errors), rep.errors
    # file-level allowSexualUsage true while a minor preset exists → refused for that preset
    m["presets"]["young"]["slots"]["appearance"] = []
    m["rights"]["permissions"]["allowSexualUsage"] = True
    (d / "manifest.json").write_text(json.dumps(m), "utf-8")
    rep = Report(); validate_dir(d, rep)
    assert any("presets.young" in e and "allowSexualUsage" in e for e in rep.errors), rep.errors
    # intimate itself under 18 or without age → refused wherever it is
    m["rights"]["permissions"]["allowSexualUsage"] = False
    V["i1"]["age"] = {"value": 17}
    (d / "manifest.json").write_text(json.dumps(m), "utf-8")
    rep = Report(); validate_dir(d, rep)
    assert any("(intimate): age 17" in e for e in rep.errors), rep.errors
    del V["i1"]["age"]
    (d / "manifest.json").write_text(json.dumps(m), "utf-8")
    rep = Report(); validate_dir(d, rep)
    assert any("(intimate): age required" in e for e in rep.errors), rep.errors


def test_unknown_slot_variant_is_error(tmp_path):
    d = tmp_path / "m"; shutil.copytree(MODULAR, d)
    m = json.loads((d / "manifest.json").read_text("utf-8"))
    m["presets"]["default"]["slots"]["appearance"] = ["f9"]
    (d / "manifest.json").write_text(json.dumps(m), "utf-8")
    rep = Report(); validate_dir(d, rep)
    assert any("unknown variant" in e for e in rep.errors)


def test_weights_need_base_model(tmp_path):
    d = tmp_path / "m"; shutil.copytree(MODULAR, d)
    w = d / "elements/identity_weights/l1/weights.json"
    j = json.loads(w.read_text("utf-8")); j["base_model"] = {}
    w.write_text(json.dumps(j), "utf-8")
    rep = Report(); validate_dir(d, rep)
    assert any("base_model" in e for e in rep.errors)


def test_derived_cannot_be_listed_as_image(tmp_path):
    d = tmp_path / "m"; shutil.copytree(ROOT / "spec" / "examples" / "03-clara-photos", d)
    m = json.loads((d / "manifest.json").read_text("utf-8"))
    der = next(a["id"] for a in m["assets"] if a["role"] == "derived")
    m["elements"]["appearance"]["variants"]["f1"]["images"].append(der)
    (d / "manifest.json").write_text(json.dumps(m), "utf-8")
    rep = Report(); validate_dir(d, rep)
    assert any("is a derived asset" in e for e in rep.errors)


def test_region_rules_and_single_kind(tmp_path):
    d = tmp_path / "m"; shutil.copytree(MODULAR, d)
    m = json.loads((d / "manifest.json").read_text("utf-8"))
    V = m["elements"]["appearance"]["variants"]
    V["o1"]["garment"] = "dress"
    V["o2"] = {"kind": "clothing", "label": "Jupe", "garment": "bottom"}       # legs/hips base conflicts with dress
    V["o3"] = {"kind": "clothing", "label": "Veste", "garment": "outerwear"}   # outer layer: OK
    V["f2"] = {"kind": "face", "label": "Visage 2"}                             # second face → single_per_kind error
    m["presets"]["default"]["slots"]["appearance"] = ["f1", "f2", "b1", "o1", "o2", "o3"]
    (d / "manifest.json").write_text(json.dumps(m), "utf-8")
    rep = Report(); validate_dir(d, rep)
    assert any("two variants of kind 'face'" in e for e in rep.errors)
    assert any("overlap" in w for w in rep.warnings)
    assert not any("'o3'" in w and "overlap" in w for w in rep.warnings)


def test_merge_and_extract(tmp_path):
    from cof_cli.ops import merge_dirs, extract_preset
    out = tmp_path / "merged"
    merge_dirs([MODULAR, ROOT / "spec" / "examples" / "04-martien"], out)
    rep = Report(); validate_dir(out, rep)
    assert rep.ok, rep.errors
    m = json.loads((out / "manifest.json").read_text("utf-8"))
    assert len(m["identities"]) == 2 and m["name"] == "Clara Mercier"
    ex = tmp_path / "ext"; extract_preset(out, ex, "m1-default")
    rep2 = Report(); validate_dir(ex, rep2)
    assert rep2.ok, rep2.errors
    e = json.loads((ex / "manifest.json").read_text("utf-8"))
    assert e["name"] == "Martien" and "personality" not in e["elements"]


def test_libraries_and_attitude_in_motion(tmp_path):
    """posture/motion are libraries: several variants of the same kind in one preset is NOT a single-kind error;
    attitude.json is admitted under motion as well as posture."""
    d = tmp_path / "m"; shutil.copytree(MODULAR, d)
    m = json.loads((d / "manifest.json").read_text("utf-8"))
    m["elements"]["posture"] = {"variants": {"ps1": {"kind": "openpose", "label": "A"}, "ps2": {"kind": "openpose", "label": "B"}}}
    (d / "elements/motion/mo1").mkdir(parents=True)
    (d / "elements/motion/mo1/attitude.json").write_text(json.dumps({"notation": "LMA-Effort-1.0"}), "utf-8")
    m["elements"]["motion"] = {"variants": {"mo1": {"kind": "attitude", "label": "Signature", "spec": "elements/motion/mo1/attitude.json"},
                                            "mo2": {"kind": "description", "label": "D", "text": "marche lente"}}}
    m["presets"]["default"]["slots"]["posture"] = ["ps1", "ps2"]
    m["presets"]["default"]["slots"]["motion"] = ["mo1", "mo2"]
    m["presets"]["default"]["defaults"] = {"motion": "mo1"}
    (d / "manifest.json").write_text(json.dumps(m), "utf-8")
    rep = Report(); validate_dir(d, rep)
    assert not any("two variants" in e for e in rep.errors), rep.errors
    assert rep.ok, rep.errors
    assert rep.info["completeness"]["layers"]["motion"] >= 30


def test_age_on_representation(tmp_path):
    """v0.5: no age on the identity; face/body/sheet/reference must carry one for human-form morphologies;
    a face declined at 14 makes its preset a minor preset; a text-only preset may have no age at all."""
    from cof_cli.model import lowest_age, preset_age
    d = tmp_path / "m"; shutil.copytree(EXAMPLE, d)
    m = json.loads((d / "manifest.json").read_text("utf-8"))
    assert "age" not in m and all("age" not in i for i in m.get("identities", {}).values())
    m["presets"]["default"].pop("age_override", None)
    (d / "manifest.json").write_text(json.dumps(m), "utf-8")
    rep = Report(); validate_dir(d, rep)
    assert rep.ok and preset_age(m, "default") is None, rep.errors     # text only, no age: valid
    m["elements"]["appearance"] = {"variants": {"f-young": {"kind": "face", "label": "À 14 ans", "age": {"value": 14}},
                                                "f-noage": {"kind": "face", "label": "Sans âge"}}}
    m["presets"]["default"]["slots"]["appearance"] = ["f-young"]
    m["presets"]["p2"] = {"label": "p2", "slots": {"personality": ["p1"], "appearance": ["f-noage"]}}
    (d / "manifest.json").write_text(json.dumps(m), "utf-8")
    rep = Report(); validate_dir(d, rep)
    assert lowest_age(m) == 14 and preset_age(m, "default") == 14
    assert any("f-noage (face) must declare an age" in e for e in rep.errors), rep.errors
    # a mechanical morphology does not need ages on faces
    m["morphology"] = {"class": "mechanical", "species": "robot"}
    for i in m.get("identities", {}).values():
        i["morphology"] = m["morphology"]
    (d / "manifest.json").write_text(json.dumps(m), "utf-8")
    rep = Report(); validate_dir(d, rep)
    assert not any("must declare an age" in e for e in rep.errors), rep.errors


def test_subfile_schemas(tmp_path):
    """Step 7: sub-files (psyche, weights, attitude, hair, body, voice profile, visemes, consent) are validated against their schemas."""
    d = tmp_path / "m"; shutil.copytree(MODULAR, d)
    ps = d / "elements/personality/p1/psyche.json"
    j = json.loads(ps.read_text("utf-8")); j["traits"]["big5"]["openness"] = 1.7
    ps.write_text(json.dumps(j), "utf-8")
    rep = Report(); validate_dir(d, rep)
    assert any("psyche.schema" in e and "openness" in e for e in rep.errors), rep.errors
    # attitude under motion + hair code + consent inline
    j["traits"]["big5"]["openness"] = 0.7; ps.write_text(json.dumps(j), "utf-8")
    m = json.loads((d / "manifest.json").read_text("utf-8"))
    (d / "elements/motion/mo1").mkdir(parents=True)
    (d / "elements/motion/mo1/attitude.json").write_text(json.dumps({"notation": "LMA-Effort-1.0", "effort": {"space": 2}}), "utf-8")
    m["elements"]["motion"] = {"variants": {"mo1": {"kind": "attitude", "label": "A", "spec": "elements/motion/mo1/attitude.json"}}}
    (d / "elements/appearance/h1").mkdir(parents=True)
    (d / "elements/appearance/h1/hair.json").write_text(json.dumps({"model": "COF-HAIR-1", "length": 12}), "utf-8")
    m["elements"]["appearance"]["variants"]["h1"] = {"kind": "hair", "label": "H", "code": "elements/appearance/h1/hair.json"}
    (d / "manifest.json").write_text(json.dumps(m), "utf-8")
    rep = Report(); validate_dir(d, rep)
    assert any("attitude.schema" in e and "space" in e for e in rep.errors), rep.errors
    assert any("hair.schema" in e and "length" in e for e in rep.errors), rep.errors
    # inline consent is checked by the manifest schema first; the consent schema applies once the manifest passes
    m["rights"]["consent"] = {"subject_is_real_person": True, "scope": ["voice-synthesis"], "granted": "2026-10-10", "jurisdictions": ["FR"], "proof": [{"type": "signed-document"}]}
    (d / "manifest.json").write_text(json.dumps(m), "utf-8")
    rep = Report(); validate_dir(d, rep)
    assert not any("consent" in e for e in rep.errors), rep.errors


def test_examples_agent_and_mixed():
    """08: agent-runtime ready (skill + memory). Mixed-age fixture: adult preset with intimate + minor preset without is valid;
    moving the intimate variant into the minor preset is refused."""
    for ex in ("spec/examples/08-agent-skills", "tests/fixtures/mixed-age"):
        rep = Report(); validate_dir(ROOT / ex, rep, recompute=False)
        assert rep.ok, (ex, rep.errors)
    from cof_cli.completeness import compute_preset
    m8 = json.loads((ROOT / "spec/examples/08-agent-skills/manifest.json").read_text("utf-8"))
    assert "agent-runtime" in compute_preset(m8, "default")["targets_ready"]


def test_example_mixed_refuses_intimate_in_minor_preset(tmp_path):
    d = tmp_path / "m"; shutil.copytree(ROOT / "tests/fixtures/mixed-age", d)
    m = json.loads((d / "manifest.json").read_text("utf-8"))
    m["presets"]["young"]["slots"]["appearance"].append("i1")
    (d / "manifest.json").write_text(json.dumps(m), "utf-8")
    rep = Report(); validate_dir(d, rep)
    assert any("presets.young" in e and "intimate variant" in e for e in rep.errors), rep.errors


def test_preset_tags_and_extract_tag(tmp_path):
    """Tags live at container level, a preset may carry several; extract --tag keeps the intersection."""
    from cof_cli.ops import extract_tag
    src = ROOT / "spec/examples/10-clara-mercier"
    rep = Report(); validate_dir(src, rep, recompute=False); assert rep.ok, rep.errors
    out = tmp_path / "fr"; extract_tag(src, out, ["fr"])
    rep = Report(); validate_dir(out, rep); assert rep.ok, rep.errors
    m = json.loads((out / "manifest.json").read_text("utf-8"))
    assert set(m["presets"]) == {"fr", "fr-manga", "fr-12", "fr-65", "fr-futur", "fr-agent"} and m["default_preset"] == "fr"
    assert "extends" not in m["presets"]["fr"]                       # parent (default) outside the selection → flattened
    assert {v["language"] for v in m["elements"]["voice"]["variants"].values()} == {"fr"}
    assert {t["id"] for t in m["preset_tags"]} == {"fr", "age-12", "age-29", "age-65", "agent", "photo-realistic", "manga", "combatant"}   # tags kept, restricted
    out2 = tmp_path / "en12"; extract_tag(src, out2, ["en", "age-12"])
    m2 = json.loads((out2 / "manifest.json").read_text("utf-8"))
    assert list(m2["presets"]) == ["en-12"]
    rep = Report(); validate_dir(out2, rep); assert rep.ok, rep.errors
    # unknown preset in a tag is refused
    d = tmp_path / "bad"; shutil.copytree(src, d)
    mm = json.loads((d / "manifest.json").read_text("utf-8"))
    mm["preset_tags"][0]["presets"].append("nope")
    (d / "manifest.json").write_text(json.dumps(mm), "utf-8")
    rep = Report(); validate_dir(d, rep)
    assert any("unknown preset 'nope'" in e for e in rep.errors), rep.errors


def test_legacy_preset_groups_migrate_to_tags(tmp_path):
    """builder 0.8.0 wrote preset_groups: validation warns, `cof migrate` turns them into tags."""
    from cof_cli.migrate import migrate_any
    d = tmp_path / "c"; shutil.copytree(ROOT / "spec/examples/10-clara-mercier", d)
    m = json.loads((d / "manifest.json").read_text("utf-8")); m.pop("preset_tags")
    m["preset_groups"] = [{"id": "fr", "label": "Français", "presets": ["fr", "fr-12"]}]
    (d / "manifest.json").write_text(json.dumps(m), "utf-8")
    rep = Report(); validate_dir(d, rep, recompute=False); assert any("preset_groups" in w for w in rep.warnings)
    m = migrate_any(d)
    assert "preset_groups" not in m and m["preset_tags"] == [{"id": "fr", "label": "Français", "presets": ["fr", "fr-12"]}]
    rep = Report(); validate_dir(d, rep, recompute=False); assert rep.ok and not any("preset_groups" in w for w in rep.warnings)


def test_enum_errors_list_every_value(tmp_path):
    """Agents fix files from validator messages: an enum error must list all allowed values, untruncated."""
    d = tmp_path / "c"; shutil.copytree(ROOT / "spec/examples/08-agent-skills", d)
    m = json.loads((d / "manifest.json").read_text("utf-8"))
    m["assets"][0]["role"] = "description"
    (d / "manifest.json").write_text(json.dumps(m), "utf-8")
    rep = Report(); validate_dir(d, rep, recompute=False)
    msg = next(e for e in rep.errors if "'description'" in e)
    assert "skill-file" in msg and "voice-sample" in msg and "file" in msg.split("allowed values:")[1]


def test_pack_recomputes_after_new_assets(tmp_path):
    """New assets without sha256/bytes must not block the recompute of coverage / completeness at pack time."""
    import subprocess, sys
    d = tmp_path / "c"; shutil.copytree(ROOT / "spec/examples/01-clara-text-only", d)
    (d / "elements/files/f9").mkdir(parents=True)
    (d / "elements/files/f9/SKILL.md").write_text("---\nname: t\ndescription: t\n---\nok\n", "utf-8")
    m = json.loads((d / "manifest.json").read_text("utf-8"))
    m["elements"]["files"] = {"variants": {"f9": {"kind": "skill", "files": ["s9"], "entry": "elements/files/f9/SKILL.md", "target": "agent-skills"}}}
    m.setdefault("assets", []).append({"id": "s9", "path": "elements/files/f9/SKILL.md", "role": "skill-file", "mediaType": "text/markdown", "license": "CC-BY-4.0"})
    (d / "manifest.json").write_text(json.dumps(m), "utf-8")
    out = tmp_path / "o.cof"
    r = subprocess.run([sys.executable, "-c", "import sys; from cof_cli.cli import main; sys.exit(main())", "pack", str(d), "-o", str(out), "--force"], capture_output=True, text=True)
    assert r.returncode == 0, r.stderr
    pm = json.loads(zipfile.ZipFile(out).read("manifest.json"))
    assert "files" in pm["coverage"]["elements"]
    rep = validate_cof(out); assert rep.ok, rep.errors


def test_environment_variants_and_self_contained_3d(tmp_path):
    """environment: stackable, ageless, in appearance and volume3d; 3D must be one self-contained file."""
    d = tmp_path / "c"; shutil.copytree(ROOT / "spec/examples/10-clara-mercier", d)
    m = json.loads((d / "manifest.json").read_text("utf-8"))
    img = next(a for a in m["assets"] if a.get("role") in ("reference", "view"))
    for i, use in ((1, "background"), (2, "location")):
        (d / f"elements/appearance/tenv{i}").mkdir(parents=True)
        shutil.copy(d / img["path"], d / f"elements/appearance/tenv{i}/place.jpg")
        m["assets"].append({"id": f"a-env-{i}", "path": f"elements/appearance/tenv{i}/place.jpg", "role": "environment", "mediaType": "image/jpeg", "license": "CC-BY-4.0", "bytes": 0, "sha256": "0" * 64})
        m["elements"]["appearance"]["variants"][f"tenv{i}"] = {"kind": "environment", "use": use, "label": f"place {i}", "images": [f"a-env-{i}"]}
    m["presets"]["default"]["slots"]["appearance"] = m["presets"]["default"]["slots"]["appearance"] + ["tenv1", "tenv2"]
    (d / "manifest.json").write_text(json.dumps(m), "utf-8")
    from cof_cli.container import refresh_asset_index
    refresh_asset_index(d, m); (d / "manifest.json").write_text(json.dumps(m), "utf-8")
    rep = Report(); validate_dir(d, rep, recompute=False); assert rep.ok, rep.errors
    # OBJ and glTF with external buffers are refused, a self-contained glTF passes
    for name, body, ok in (("avatar.obj", "v 0 0 0\n", False),
                           ("avatar.gltf", json.dumps({"asset": {"version": "2.0"}, "buffers": [{"uri": "avatar.bin", "byteLength": 4}]}), False),
                           ("avatar.gltf", json.dumps({"asset": {"version": "2.0"}, "buffers": [{"uri": "data:application/octet-stream;base64,AAAAAA==", "byteLength": 4}]}), True)):
        mm = json.loads(json.dumps(m)); (d / "elements/volume3d/m1").mkdir(parents=True, exist_ok=True)
        (d / "elements/volume3d/m1" / name).write_text(body, "utf-8")
        mm["assets"].append({"id": "a-3d", "path": f"elements/volume3d/m1/{name}", "role": "mesh", "mediaType": "model/gltf+json", "license": "CC-BY-4.0", "bytes": 0, "sha256": "0" * 64})
        mm["elements"]["volume3d"] = {"variants": {"m1": {"kind": "environment", "path": f"elements/volume3d/m1/{name}"}}}
        refresh_asset_index(d, mm); (d / "manifest.json").write_text(json.dumps(mm), "utf-8")
        rep = Report(); validate_dir(d, rep, recompute=False)
        assert any("not self-contained" in e or "external resources" in e for e in rep.errors) != ok, (name, rep.errors)
        (d / "elements/volume3d/m1" / name).unlink()


def test_escape_hatches_and_thumbnail_source(tmp_path):
    """self_contained:false turns the OBJ refusal into a warning; weights by link are valid (warned);
    thumbnail_source picks the OS thumbnail."""
    import subprocess, sys
    d = tmp_path / "c"; shutil.copytree(ROOT / "spec/examples/10-clara-mercier", d)
    m = json.loads((d / "manifest.json").read_text("utf-8"))
    (d / "elements/volume3d/m1").mkdir(parents=True); (d / "elements/volume3d/m1/avatar.obj").write_text("v 0 0 0\n", "utf-8")
    m["assets"].append({"id": "a-3d", "path": "elements/volume3d/m1/avatar.obj", "role": "mesh", "mediaType": "model/obj", "license": "CC-BY-4.0"})
    m["elements"]["volume3d"] = {"variants": {"m1": {"kind": "mesh", "path": "elements/volume3d/m1/avatar.obj", "self_contained": False, "age": {"value": 29, "unit": "years", "basis": "canonical"}}}}
    (d / "elements/identity_weights/w1").mkdir(parents=True)
    (d / "elements/identity_weights/w1/weights.json").write_text(json.dumps({"kind": "lora", "base_model": {"name": "FLUX.1-dev", "family": "flux"}, "format": "safetensors", "file": "a-w1", "storage": "link"}), "utf-8")
    m["assets"].append({"id": "a-w1", "uri": "https://huggingface.co/x/y/resolve/main/clara.safetensors", "role": "weights", "mediaType": "application/octet-stream", "license": "CC-BY-4.0", "base_model": "FLUX.1-dev"})
    m["elements"]["identity_weights"] = {"variants": {"w1": {"kind": "lora", "spec": "elements/identity_weights/w1/weights.json", "age": {"value": 29, "unit": "years", "basis": "canonical"}}}}
    sheet = next(a for a in m["assets"] if a["path"].startswith("elements/appearance/a3/"))
    m["thumbnail_source"] = sheet["id"]
    (d / "manifest.json").write_text(json.dumps(m), "utf-8")
    out = tmp_path / "o.cof"
    r = subprocess.run([sys.executable, "-c", "import sys; from cof_cli.cli import main; sys.exit(main())", "pack", str(d), "-o", str(out)], capture_output=True, text=True)
    assert r.returncode == 0, r.stdout + r.stderr
    rep = validate_cof(out); assert rep.ok, rep.errors
    assert any("not self-contained" in w for w in rep.warnings) and any("without sha256" in w for w in rep.warnings)
    pm = json.loads(zipfile.ZipFile(out).read("manifest.json"))
    assert next(a for a in pm["assets"] if a["id"] == "thumbnail")["source"] == sheet["id"]


def test_voice_engines_daz_and_pickles(tmp_path):
    """Voice embeddings tied to a model; Daz content with category, age for characters; pickles always refused."""
    import io as _io, numpy as np
    d = tmp_path / "c"; shutil.copytree(ROOT / "spec/examples/10-clara-mercier", d)
    m = json.loads((d / "manifest.json").read_text("utf-8"))
    from cof_cli.container import refresh_asset_index
    # XTTS speaker embedding as numeric .npz
    (d / "elements/voice/v6/engines").mkdir(parents=True)
    np.savez(d / "elements/voice/v6/engines/xtts-speaker.npz", gpt_cond_latent=np.zeros((1, 32, 1024), "float32"), speaker_embedding=np.zeros((1, 512, 1), "float32"))
    m["assets"].append({"id": "a-xtts-v6", "path": "elements/voice/v6/engines/xtts-speaker.npz", "role": "engine-artifact", "mediaType": "application/octet-stream", "license": "CC-BY-NC-4.0"})
    prof = json.loads((d / "elements/voice/v6/profile.json").read_text("utf-8"))
    prof["engines"] = [{"engine": "xtts", "version": "2.0.3", "model": "coqui/XTTS-v2", "kind": "speaker-embedding", "files": ["a-xtts-v6"]},
                       {"engine": "elevenlabs", "version": "v3", "kind": "cloud-voice-id", "voice_id": "abc123"}]
    (d / "elements/voice/v6/profile.json").write_text(json.dumps(prof), "utf-8")
    # Daz character without age → error; with age → ok (+ licence warning)
    (d / "elements/volume3d/z1").mkdir(parents=True); (d / "elements/volume3d/z1/clara.duf").write_text('{"file_version":"0.6.0.0"}', "utf-8")
    m["assets"].append({"id": "a-daz-z1", "path": "elements/volume3d/z1/clara.duf", "role": "mesh", "mediaType": "application/json", "license": "CC-BY-4.0"})
    m["elements"]["volume3d"] = {"variants": {"z1": {"kind": "daz", "daz_category": "characters", "figure": "Genesis 9", "files": ["a-daz-z1"], "entry": "elements/volume3d/z1/clara.duf",
                                                     "requires": [{"name": "Genesis 9 Starter Essentials", "url": "https://www.daz3d.com/genesis-9-starter-essentials"}]}}}
    m["presets"]["default"]["slots"]["volume3d"] = ["z1"]
    refresh_asset_index(d, m); (d / "manifest.json").write_text(json.dumps(m), "utf-8")
    rep = Report(); validate_dir(d, rep, recompute=False)
    assert any("z1" in e and "must declare an age" in e for e in rep.errors), rep.errors
    m["elements"]["volume3d"]["variants"]["z1"]["age"] = {"value": 29, "unit": "years", "basis": "canonical"}
    (d / "manifest.json").write_text(json.dumps(m), "utf-8")
    rep = Report(); validate_dir(d, rep, recompute=False); assert rep.ok, rep.errors
    assert any("Daz licence" in w for w in rep.warnings)
    # pickles: refused even with executable content declared; a raw .bin is fine; object .npy refused
    m["container"]["executableContent"] = "scripts"; (d / "manifest.json").write_text(json.dumps(m), "utf-8")
    (d / "elements/voice/v6/engines/se.pth").write_bytes(b"\x80\x02}q\x00.")
    (d / "elements/voice/v6/engines/raw.bin").write_bytes(b"\x00\x00\x80\x3f")
    np.save(d / "elements/voice/v6/engines/bad.npy", np.array([{"a": 1}], dtype=object), allow_pickle=True)
    rep = Report(); validate_dir(d, rep, recompute=False)
    assert any("se.pth" in e for e in rep.errors) and any("bad.npy" in e for e in rep.errors) and not any("raw.bin" in e for e in rep.errors), rep.errors


def test_daz_archive_and_voice_embedding_kind(tmp_path):
    """Daz content travels as an archive (scripts inside are flagged); voice embeddings are their own kind."""
    import zipfile as _z, numpy as np
    from cof_cli.container import refresh_asset_index
    d = tmp_path / "c"; shutil.copytree(ROOT / "spec/examples/10-clara-mercier", d)
    m = json.loads((d / "manifest.json").read_text("utf-8"))
    (d / "elements/volume3d/z1").mkdir(parents=True)
    with _z.ZipFile(d / "elements/volume3d/z1/clara-g9.zip", "w") as z:
        z.writestr("Content/People/Genesis 9/Clara.duf", "{}"); z.writestr("Content/Scripts/fix.dsa", "// script")
    m["assets"].append({"id": "a-daz", "path": "elements/volume3d/z1/clara-g9.zip", "role": "archive", "mediaType": "application/zip", "license": "LicenseRef-Daz-EULA"})
    m["elements"]["volume3d"] = {"variants": {"z1": {"kind": "daz", "daz_category": "props", "files": ["a-daz"], "requires": [{"name": "Genesis 9 Starter Essentials"}]}}}
    (d / "elements/voice/v11").mkdir(parents=True); np.savez(d / "elements/voice/v11/xtts.npz", e=np.zeros(4, "float32"))
    (d / "elements/voice/v11/profile.json").write_text(json.dumps({"engines": [{"engine": "xtts", "version": "2.0.3", "model": "coqui/XTTS-v2", "kind": "speaker-embedding", "files": ["a-x11"]}]}), "utf-8")
    m["assets"].append({"id": "a-x11", "path": "elements/voice/v11/xtts.npz", "role": "engine-artifact", "mediaType": "application/octet-stream", "license": "CC-BY-NC-4.0"})
    m["elements"]["voice"]["variants"]["v11"] = {"kind": "embedding", "language": "en", "derives_from": "v6", "profile": "elements/voice/v11/profile.json"}
    refresh_asset_index(d, m); (d / "manifest.json").write_text(json.dumps(m), "utf-8")
    rep = Report(); validate_dir(d, rep, recompute=False); assert rep.ok, rep.errors
    assert any("fix.dsa" in w for w in rep.warnings)


def test_version_gate_1_0(tmp_path):
    """1.0 is the format; 0.5 must be migrated; a newer 1.x minor is read with a warning."""
    from cof_cli.migrate import migrate_any
    d = tmp_path / "c"; shutil.copytree(ROOT / "spec/examples/01-clara-text-only", d)
    m = json.loads((d / "manifest.json").read_text("utf-8")); assert m["cof"] == "1.0"
    m["cof"] = "0.5"; (d / "manifest.json").write_text(json.dumps(m), "utf-8")
    rep = Report(); validate_dir(d, rep, recompute=False); assert not rep.ok and any("cof migrate" in e for e in rep.errors)
    assert migrate_any(d)["cof"] == "1.0"
    rep = Report(); validate_dir(d, rep, recompute=False); assert rep.ok, rep.errors
    m = json.loads((d / "manifest.json").read_text("utf-8")); m["cof"] = "1.7"; (d / "manifest.json").write_text(json.dumps(m), "utf-8")
    rep = Report(); validate_dir(d, rep, recompute=False); assert rep.ok and any("newer" in w for w in rep.warnings)


def test_published_schemas_match_spec():
    """schemas/<current minor> (served by GitHub Pages at the $id URLs) and the CLI copies equal spec/schemas."""
    for f in (ROOT / "spec/schemas").glob("*.json"):
        assert (ROOT / "schemas" / SPEC_VERSION / f.name).read_bytes() == f.read_bytes(), f.name
        assert (ROOT / "cli/cof_cli/schemas" / f.name).read_bytes() == f.read_bytes(), f.name
        sid = json.loads(f.read_text("utf-8")).get("$id")
        assert sid is None or sid == f"https://yannsouetre.github.io/cof/schemas/{SPEC_VERSION}/{f.name}"


def test_negative_corpus():
    """tests/invalid: the base is valid, every case is rejected with the expected error."""
    corpus = ROOT / "tests/invalid"
    assert validate_cof(corpus / "_base.cof").ok
    cases = json.loads((corpus / "cases.json").read_text("utf-8"))["cases"]
    assert len(cases) >= 20
    for c in cases:
        rep = validate_cof(corpus / c["file"])
        assert not rep.ok, c["file"]
        assert any(c["expect"].lower() in e.lower() for e in rep.errors), (c["file"], rep.errors)


def test_slots_alternatives_and_primary_image(tmp_path):
    """slots = applied by default; alternatives = offered for that preset only. Age/minor rules cover both,
    region and kind rules only the applied set; primary_image must be applied; extract/merge keep alternatives."""
    from cof_cli.model import preset_alternatives, preset_primary_image, resolved_all, preset_age
    from cof_cli.ops import extract_presets, merge_dirs
    src = ROOT / "spec/examples/10-clara-mercier"
    m = json.loads((src / "manifest.json").read_text("utf-8"))
    assert preset_alternatives(m, "fr") == {"appearance": ["c1", "c2", "c3", "c4"]}          # inherited from default
    assert preset_alternatives(m, "fr-12") == {"appearance": ["c5", "c6", "c7", "c8"]}       # child replaces the list
    assert preset_primary_image(m, "fr") == m["presets"]["default"]["primary_image"]
    d = tmp_path / "c"; shutil.copytree(src, d)
    V = m["elements"]["appearance"]["variants"]
    # two overlapping tops offered: no warning (offered ≠ worn); applied: region warning
    V["c13"] = {**V["c2"], "label": "second top"}
    m["presets"]["en-12"]["alternatives"]["appearance"].append("c13")
    (d / "manifest.json").write_text(json.dumps(m), "utf-8")
    rep = Report(); validate_dir(d, rep, recompute=False); assert rep.ok, rep.errors
    assert not any("presets.en-12" in w and "overlap" in w for w in rep.warnings), rep.warnings
    m["presets"]["en-12"]["slots"]["appearance"] += ["c6", "c13"]
    (d / "manifest.json").write_text(json.dumps(m), "utf-8")
    rep = Report(); validate_dir(d, rep, recompute=False)
    assert any("presets.en-12" in w and "overlap" in w for w in rep.warnings), rep.warnings
    m["presets"]["en-12"]["slots"]["appearance"] = ["a2", "e4"]
    # an intimate element OFFERED in a minor preset is refused like an applied one
    V["i1"] = {"kind": "intimate", "label": "x", "age": {"value": 29, "unit": "years", "basis": "apparent"}}
    m["tags"]["content"] = list(set(m["tags"].get("content") or []) | {"nudity"})
    m["presets"]["en-12"]["alternatives"]["appearance"].append("i1")
    (d / "manifest.json").write_text(json.dumps(m), "utf-8")
    rep = Report(); validate_dir(d, rep, recompute=False)
    assert any("presets.en-12" in e and "intimate variant" in e for e in rep.errors), rep.errors
    # offered variants are part of the age computation (applied ∪ offered)
    m["presets"]["en-12"]["alternatives"]["appearance"] = ["c5", "c6", "c7", "c8"]
    assert preset_age(m, "en-12") == 12 and "a2" in [v["_id"] for v in resolved_all(m, "en-12")["appearance"]]
    # primary_image must come from an applied variant; head-only framing without clothing warns
    m["presets"]["en-12"]["primary_image"] = m["presets"]["en-65"]["primary_image"]
    (d / "manifest.json").write_text(json.dumps(m), "utf-8")
    rep = Report(); validate_dir(d, rep, recompute=False)
    assert any("presets.en-12.primary_image" in e and "not an image of a variant applied" in e for e in rep.errors), rep.errors
    m["presets"]["en-12"]["primary_image"] = m["presets"]["en-12"]["primary_image"] = V["a2"]["images"][0]
    pa = next(a for a in m["assets"] if a["id"] == V["a2"]["images"][0]); pa["subject"], pa["framing"] = "head", "head"
    (d / "manifest.json").write_text(json.dumps(m), "utf-8")
    rep = Report(); validate_dir(d, rep, recompute=False)
    assert any("presets.en-12" in w and "default outfit is undefined" in w for w in rep.warnings), rep.warnings
    # vehicle as an accessory type → hint to use accessory_use
    V["x3"]["accessory"] = "vehicle"
    (d / "manifest.json").write_text(json.dumps(m), "utf-8")
    rep = Report(); validate_dir(d, rep, recompute=False)
    assert any("x3" in w and "ignored" in w for w in rep.warnings), rep.warnings
    # extract one child preset: alternatives and primary image flattened from the dropped parent
    out = tmp_path / "fr"; extract_presets(src, out, ["fr"])
    e = json.loads((out / "manifest.json").read_text("utf-8"))
    assert e["presets"]["fr"]["alternatives"] == {"appearance": ["c1", "c2", "c3", "c4"]}
    assert e["presets"]["fr"]["primary_image"] == m["presets"]["default"]["primary_image"]
    assert "c1" in e["elements"]["appearance"]["variants"]
    rep = Report(); validate_dir(out, rep); assert rep.ok, rep.errors
    # merge keeps them
    mg = tmp_path / "mg"; merge_dirs([out, ROOT / "spec" / "examples" / "04-martien"], mg)
    g = json.loads((mg / "manifest.json").read_text("utf-8"))
    assert g["presets"]["fr"]["alternatives"] == {"appearance": ["c1", "c2", "c3", "c4"]}
    rep = Report(); validate_dir(mg, rep); assert rep.ok, rep.errors


def test_backstage_and_facet_navigation(tmp_path):
    """Variants referenced by no preset are 'backstage' (warned, kept); derives_from parents count as referenced.
    Facet navigation: switching the language tag lands on the preset with the same tags in the other facets."""
    from cof_cli.model import backstage, facet_switch
    src = ROOT / "spec/examples/10-clara-mercier"
    m = json.loads((src / "manifest.json").read_text("utf-8"))
    assert backstage(m) == []
    T = {t["id"]: t for t in m["preset_tags"]}
    for pid in m["presets"]:                       # the Clara grid: each preset has exactly one sibling per language
        for lang in ("en", "fr"):
            assert len(facet_switch(m, pid, lang)) == 1, (pid, lang, facet_switch(m, pid, lang))
    assert facet_switch(m, "en-12", "fr") == ["fr-12"] and facet_switch(m, "fr-agent", "en") == ["en-agent"]
    assert facet_switch(m, "en-12", "age-65") == ["en-65"]
    d = tmp_path / "c"; shutil.copytree(src, d)
    V = m["elements"]["appearance"]["variants"]
    V["c13"] = {**V["c2"], "label": "orphan top"}                       # orphan → backstage warning
    V["c14"] = {"derives_from": "c3", "kind": "clothing", "label": "child of c3", "garment": "bottom"}
    m["presets"]["en-12"]["alternatives"]["appearance"].append("c14")
    (d / "manifest.json").write_text(json.dumps(m), "utf-8")
    rep = Report(); validate_dir(d, rep, recompute=False); assert rep.ok, rep.errors
    assert any("appearance.c13 is backstage" in w for w in rep.warnings), rep.warnings
    assert not any("appearance.c3 is backstage" in w for w in rep.warnings)   # parent of an offered variant
    assert backstage(m) == [("appearance", "c13")]


def test_duplicate_image_warning_and_pack_date(tmp_path):
    """The same picture embedded twice (reduced copy + original) is warned; front/back views are not."""
    from PIL import Image
    import subprocess, sys
    d = tmp_path / "c"; shutil.copytree(ROOT / "spec/examples/10-clara-mercier", d)
    m = json.loads((d / "manifest.json").read_text("utf-8"))
    rep = Report(); validate_dir(d, rep, recompute=False)
    assert not any("same image" in w for w in rep.warnings), [w for w in rep.warnings if "same image" in w]
    src = d / "elements/appearance/a1/body.front.jpg"
    im = Image.open(src); im.resize((im.width * 2, im.height * 2)).save(d / "elements/appearance/a1/body.big.jpg", quality=95)
    m["assets"].append({"id": "a-big", "path": "elements/appearance/a1/body.big.jpg", "role": "reference", "mediaType": "image/jpeg", "license": "CC-BY-4.0"})
    m["elements"]["appearance"]["variants"]["a1"]["images"].append("a-big")
    from cof_cli.container import refresh_asset_index
    refresh_asset_index(d, m); (d / "manifest.json").write_text(json.dumps(m), "utf-8")
    rep = Report(); validate_dir(d, rep, recompute=False)
    assert any("same image at two resolutions" in w and "a-big" in w for w in rep.warnings), rep.warnings
    before = m["provenance"]["modified"]
    r = subprocess.run([sys.executable, "-m", "cof_cli.cli", "pack", str(d), "-o", str(tmp_path / "o.cof")], capture_output=True, text=True)
    from cof_cli.container import read_manifest
    assert read_manifest(tmp_path / "o.cof")["provenance"]["modified"] != before, r.stderr


def test_characters_are_logical_containers(tmp_path):
    """Several characters: each element and preset belongs to one; likeness files are never shared (neutral ones may
    be); rights and default preset per character; extract --identity carries the character's rights; merge keeps them."""
    from cof_cli.model import effective_permissions, preset_owner
    from cof_cli.ops import extract_identity
    src = ROOT / "spec/examples/11-duo-clara-martien"
    rep = Report(); validate_dir(src, rep, recompute=False); assert rep.ok, rep.errors
    m = json.loads((src / "manifest.json").read_text("utf-8"))
    assert preset_owner(m, "fr") == "clara-mercier" and preset_owner(m, "m1-default") == "martien"
    assert effective_permissions(m, "default")["allowRedistribution"] is False and effective_permissions(m, "m1-default")["allowRedistribution"] is True
    V = m["elements"]["appearance"]["variants"]
    assert V["env-martien"]["images"] == V["e1"]["images"][:1]           # neutral file stored once, two elements
    d = tmp_path / "c"; shutil.copytree(src, d)
    def check(mut, needle):
        mm = json.loads(json.dumps(m)); mut(mm); (d / "manifest.json").write_text(json.dumps(mm), "utf-8")
        r = Report(); validate_dir(d, r, recompute=False)
        assert any(needle in e for e in r.errors), (needle, r.errors)
    check(lambda mm: mm["presets"]["m1-default"]["slots"]["appearance"].append("a1"), "belongs to character clara-mercier")
    check(lambda mm: mm["elements"]["appearance"]["variants"]["f1"].__setitem__("images", V["a1"]["images"][:1]), "is not neutral")
    check(lambda mm: mm["presets"]["fr"].__setitem__("extends", "m1-default"), "another character")
    check(lambda mm: mm["identities"]["martien"].__setitem__("default_preset", "default"), "belongs to character clara-mercier")
    out = tmp_path / "martien"; e = extract_identity(src, out, "martien")
    assert list(e["presets"]) == ["m1-default"] and e["rights"]["permissions"]["allowRedistribution"] is True and e["name"] == "Martien"
    assert (out / "elements/appearance/e1/background.desktop.jpg").is_file()  # the shared file travels with the character
    r = Report(); validate_dir(out, r); assert r.ok, r.errors


def test_neutral_elements_may_share_files(tmp_path):
    """Neutral by kind (places, BVH clips…) or by choice (skills by default, clothes) may share a file between
    characters; memories, documents (default) and anything marked neutral: false may not."""
    from cof_cli.model import is_neutral, neutrality
    assert neutrality("files", {"kind": "skill"}) == (True, True) and neutrality("files", {"kind": "memory"}) == (False, True)
    assert neutrality("appearance", {"kind": "environment"}) == (True, False) and neutrality("appearance", {"kind": "face"}) == (False, False)
    assert neutrality("volume3d", {"kind": "daz", "daz_category": "props"}) == (True, False) and not is_neutral("volume3d", {"kind": "daz", "daz_category": "characters"})
    src = ROOT / "spec/examples/11-duo-clara-martien"
    d = tmp_path / "c"; shutil.copytree(src, d)
    m = json.loads((d / "manifest.json").read_text("utf-8"))
    (d / "elements/files/sk").mkdir(parents=True); (d / "elements/files/sk/SKILL.md").write_text("---\nname: x\ndescription: y\n---\nhi\n", "utf-8")
    m["assets"].append({"id": "a-sk", "path": "elements/files/sk/SKILL.md", "role": "skill-file", "mediaType": "text/markdown", "license": "CC0-1.0"})
    m["elements"]["files"] = {"variants": {
        "sk-clara": {"kind": "skill", "identity": "clara-mercier", "files": ["a-sk"], "entry": "elements/files/sk/SKILL.md"},
        "sk-mar": {"kind": "skill", "identity": "martien", "files": ["a-sk"], "entry": "elements/files/sk/SKILL.md"}}}
    m["presets"]["default"]["slots"]["files"] = ["sk-clara"]; m["presets"]["m1-default"]["slots"]["files"] = ["sk-mar"]
    from cof_cli.container import refresh_asset_index
    def run(mut=None):
        mm = json.loads(json.dumps(m))
        if mut: mut(mm)
        refresh_asset_index(d, mm); (d / "manifest.json").write_text(json.dumps(mm), "utf-8")
        r = Report(); validate_dir(d, r, recompute=False); return r
    r = run(); assert r.ok, r.errors                                       # a skill is neutral by default
    r = run(lambda mm: mm["elements"]["files"]["variants"]["sk-mar"].__setitem__("neutral", False))
    assert any("is not neutral" in e and "sk-mar" in e for e in r.errors), r.errors
    r = run(lambda mm: [v.__setitem__("kind", "memory") for v in mm["elements"]["files"]["variants"].values()])
    assert any("is not neutral" in e for e in r.errors), r.errors          # memories carry the character


def test_export_agent_no_intimate_voice_consent_auto_tags(tmp_path):
    """export --format agent builds a workspace; extract --no-intimate makes a safe slice; cloning a real person's voice
    without consent scope voice-synthesis is warned; tags.auto is computed."""
    from cof_cli.convert import export_agent
    from cof_cli.ops import extract_presets, strip_intimate
    from cof_cli.validate import auto_tags
    out = tmp_path / "ws"; done = export_agent(ROOT / "spec/examples/10-clara-mercier", out, "en-agent")
    assert done["skills"] == ["accessible-color-palette"] and (out / "skills/accessible-color-palette/SKILL.md").is_file()
    assert (out / "SOUL.md").read_text("utf-8").startswith("# SOUL.md — Clara Mercier") and (out / "COF.md").is_file()
    assert "Avatar: avatar." in (out / "IDENTITY.md").read_text("utf-8")
    sfw = tmp_path / "sfw"; extract_presets(ROOT / "tests/fixtures/mixed-age", sfw, ["default"]); gone = strip_intimate(sfw)
    m = json.loads((sfw / "manifest.json").read_text("utf-8"))
    assert gone == ["i1"] and "i1" not in m["elements"]["appearance"]["variants"] and m["rights"]["permissions"]["allowSexualUsage"] is False
    rep = Report(); validate_dir(sfw, rep); assert rep.ok, rep.errors
    t = auto_tags(json.loads((ROOT / "spec/examples/10-clara-mercier/manifest.json").read_text("utf-8")))
    assert {"child", "adult", "elder", "has-minor-preset", "fr", "en", "has-skills"} <= set(t)
    d = tmp_path / "real"; shutil.copytree(ROOT / "spec/examples/01-clara-text-only", d)
    mm = json.loads((d / "manifest.json").read_text("utf-8"))
    mm["fictional"] = False
    mm["rights"]["consent"] = {"subject_is_real_person": True, "scope": ["conversational-persona"], "granted": "2026-10-01", "jurisdictions": ["FR"], "proof": [{"type": "other", "uri": "https://example.org/consent"}]}
    mm["rights"]["permissions"]["allowVoiceCloning"] = True
    (d / "manifest.json").write_text(json.dumps(mm), "utf-8")
    rep = Report(); validate_dir(d, rep, recompute=False)
    assert any("voice-synthesis" in w for w in rep.warnings), rep.warnings          # warned (decided 14 Oct): the author is responsible
    mm["rights"]["consent"]["scope"].append("voice-synthesis"); (d / "manifest.json").write_text(json.dumps(mm), "utf-8")
    rep = Report(); validate_dir(d, rep, recompute=False)
    assert not any("allowVoiceCloning" in w for w in rep.warnings), rep.warnings


def _safetensors(path, ok=True):
    import struct
    h = json.dumps({"__metadata__": {"refmod.mode": "full"}, "t": {"dtype": "F16", "shape": [1], "data_offsets": [0, 2]}}).encode()
    path.write_bytes(struct.pack("<Q", len(h)) + h + (b"\x00\x00" if ok else b""))


def test_reference_latent_and_safetensors_header(tmp_path):
    """A pre-encoded reference (e.g. MiniMax H3 RefMod) is identity_weights kind reference-latent; it should
    name its source images; any .safetensors must have a readable header that fits the file."""
    d = tmp_path / "c"; shutil.copytree(ROOT / "spec/examples/10-clara-mercier", d)
    m = json.loads((d / "manifest.json").read_text("utf-8"))
    img = next(a for a in m["assets"] if a["path"].startswith("elements/appearance/") and a.get("mediaType", "").startswith("image/"))
    (d / "elements/identity_weights/r1").mkdir(parents=True)
    _safetensors(d / "elements/identity_weights/r1/clara.refmod.safetensors")
    spec = {"kind": "reference-latent", "base_model": {"name": "MiniMax H3", "family": "minimax-h3"}, "file": "a-r1",
            "encoding": {"method": "minimax-h3-refmod", "mode": "full", "frames": 1, "resolution": 512, "sources": [img["id"]]},
            "recommended_weight": 1.0, "covers": ["face"]}
    (d / "elements/identity_weights/r1/weights.json").write_text(json.dumps(spec), "utf-8")
    import hashlib
    st = (d / "elements/identity_weights/r1/clara.refmod.safetensors").read_bytes()
    m["assets"].append({"id": "a-r1", "path": "elements/identity_weights/r1/clara.refmod.safetensors", "role": "weights", "mediaType": "application/octet-stream", "license": "CC-BY-4.0", "base_model": "MiniMax H3", "bytes": len(st), "sha256": hashlib.sha256(st).hexdigest()})
    m["elements"]["identity_weights"] = {"variants": {"r1": {"kind": "reference-latent", "spec": "elements/identity_weights/r1/weights.json", "age": {"value": 29, "unit": "years", "basis": "canonical"}}}}
    (d / "manifest.json").write_text(json.dumps(m), "utf-8")
    rep = Report(); validate_dir(d, rep)
    assert rep.ok, rep.errors
    assert not any("reference-latent" in w for w in rep.warnings)
    spec["encoding"].pop("sources"); (d / "elements/identity_weights/r1/weights.json").write_text(json.dumps(spec), "utf-8")
    rep = Report(); validate_dir(d, rep)
    assert rep.ok and any("cannot be re-encoded" in w for w in rep.warnings)
    _safetensors(d / "elements/identity_weights/r1/clara.refmod.safetensors", ok=False)
    rep = Report(); validate_dir(d, rep)
    assert any("invalid safetensors" in e and "truncated" in e for e in rep.errors)
    (d / "elements/identity_weights/r1/clara.refmod.safetensors").write_bytes(b"\x80\x04K\x01.")   # a pickle renamed
    rep = Report(); validate_dir(d, rep)
    assert any("invalid safetensors" in e for e in rep.errors)


def test_age_units_and_inheritance():
    """Ages are compared in years; age_override is inherited through extends, permissions_override is not."""
    from cof_cli.model import preset_age, effective_permissions, _age_value
    assert _age_value({"value": 100, "unit": "months"}) == 100 / 12
    m = {"presets": {"kid": {"slots": {}, "age_override": {"value": 12}}, "kid2": {"extends": "kid", "slots": {}},
                     "adult": {"slots": {}, "age_override": {"value": 30}, "permissions_override": {"allowSexualUsage": True}},
                     "child": {"extends": "adult", "slots": {}, "age_override": {"value": 10}}},
         "rights": {"permissions": {"allowSexualUsage": False}}}
    assert preset_age(m, "kid2") == 12 and preset_age(m, "child") == 10
    assert effective_permissions(m, "child").get("allowSexualUsage") is False


def test_freeze_rules_consent_exec_forward_compat(tmp_path):
    """Real person: intimate needs scope 'intimate' (error), likeness needs its scope (warning);
    scripts in SVG and executables inside archives are refused; a later 1.x enum value is a warning."""
    import zipfile as _z
    d = tmp_path / "c"; shutil.copytree(ROOT / "tests/fixtures/mixed-age", d)
    m = json.loads((d / "manifest.json").read_text("utf-8"))
    m["fictional"] = False
    for i in (m.get("identities") or {}).values():
        i["fictional"] = False
    cons = {"subject_is_real_person": True, "scope": ["likeness-image"], "granted": "2026-10-10", "jurisdictions": ["FR"], "proof": [{"type": "signed-document"}]}
    m["rights"]["consent"] = cons
    for i in (m.get("identities") or {}).values():
        i["consent"] = cons
    (d / "manifest.json").write_text(json.dumps(m), "utf-8")
    rep = Report(); validate_dir(d, rep, recompute=False)
    assert any("consent scope 'intimate'" in e for e in rep.errors), rep.errors
    assert any("consent scope 'conversational-persona'" in w for w in rep.warnings)
    d2 = tmp_path / "e"; shutil.copytree(ROOT / "spec/examples/01-clara-text-only", d2)
    (d2 / "elements/files").mkdir(parents=True, exist_ok=True)
    (d2 / "elements/files/x.svg").write_text('<svg xmlns="http://www.w3.org/2000/svg" onload="alert(1)"/>', "utf-8")
    with _z.ZipFile(d2 / "elements/files/pack.zip", "w") as z:
        z.writestr("tool.exe", b"MZ"); z.writestr("w.pt", b"\x80\x02.")
    rep = Report(); validate_dir(d2, rep, recompute=False)
    assert any("x.svg carries script" in e for e in rep.errors), rep.errors
    assert any("inside archive" in e and "tool.exe" in e for e in rep.errors) and any("pickle file refused inside archive" in e for e in rep.errors)
    d3 = tmp_path / "f"; shutil.copytree(ROOT / "spec/examples/01-clara-text-only", d3)
    m = json.loads((d3 / "manifest.json").read_text("utf-8")); m["cof"] = "1.3"; m["tags"]["content"] = ["future-flag"]
    (d3 / "manifest.json").write_text(json.dumps(m), "utf-8")
    rep = Report(); validate_dir(d3, rep, recompute=False)
    assert rep.ok, rep.errors
    assert any("later 1.x" in w for w in rep.warnings)
    m.pop("presets"); m.pop("default_preset"); m["cof"] = "1.0"; (d3 / "manifest.json").write_text(json.dumps(m), "utf-8")
    rep = Report(); validate_dir(d3, rep, recompute=False)
    assert any("at least one preset" in e for e in rep.errors), rep.errors


def test_adult_fictional_nudity_is_allowed(tmp_path):
    """Nudity without genitals (variant flag `nudity`) is fine for an adult fictional character once flagged."""
    d = tmp_path / "c"; shutil.copytree(ROOT / "tests/fixtures/mixed-age", d)
    m = json.loads((d / "manifest.json").read_text("utf-8"))
    V = m["elements"]["appearance"]["variants"]
    V["b1"]["nudity"] = True; V["o1"]["nudity"] = True
    (d / "manifest.json").write_text(json.dumps(m), "utf-8")
    rep = Report(); validate_dir(d, rep, recompute=False)
    assert rep.ok, rep.errors


def test_age_tags_only_for_human_shapes():
    """Age buckets are tagged for human-shaped characters only: a robot declared 3 years old is no child."""
    from cof_cli.validate import auto_tags
    t = auto_tags(json.loads((ROOT / "tests/fixtures/robot-age-3/manifest.json").read_text("utf-8")))
    assert "child" not in t and "has-minor-preset" not in t and "mechanical" in t
    t2 = auto_tags(json.loads((ROOT / "spec/examples/02-ecoliere/manifest.json").read_text("utf-8")))
    assert "child" in t2


def _with_later_category(m: dict, cat: str) -> dict:
    """Add a category this validator does not know, with two variants of one kind, listed by the default preset."""
    m["elements"][cat] = {"variants": {"n1": {"kind": "note", "label": "One"}, "n2": {"kind": "note", "label": "Two"}}}
    m["presets"]["default"].setdefault("slots", {})[cat] = ["n1", "n2"]
    return m


def test_later_minor_category_is_a_warning_and_a_library(workdir):
    """SPEC § 12: a validator of an earlier minor treats what a later 1.x adds as a warning, never a reason to refuse;
    SPEC § 2.3: categories it does not know are libraries (several variants of one kind are allowed)."""
    mp = workdir / "manifest.json"
    m = _with_later_category(json.loads(mp.read_text("utf-8")), "sketches")
    m["cof"] = "1.9"
    mp.write_text(json.dumps(m), "utf-8")
    rep = Report()
    validate_dir(workdir, rep, recompute=False)
    assert rep.ok, rep.errors
    assert any("sketches" in w and "later 1.x" in w for w in rep.warnings), rep.warnings


def test_x_category_is_a_library(workdir):
    """`x-` categories are accepted by the 1.0 schema and are libraries unless an RFC says otherwise (SPEC § 2.3)."""
    mp = workdir / "manifest.json"
    m = _with_later_category(json.loads(mp.read_text("utf-8")), "x-notes")
    mp.write_text(json.dumps(m), "utf-8")
    rep = Report()
    validate_dir(workdir, rep, recompute=False)
    assert rep.ok, rep.errors


def test_unknown_category_in_a_1_0_file_is_an_error(workdir):
    """A file that declares 1.0 cannot use a category the 1.0 schema does not define."""
    mp = workdir / "manifest.json"
    m = _with_later_category(json.loads(mp.read_text("utf-8")), "sketches")
    mp.write_text(json.dumps(m), "utf-8")
    rep = Report()
    validate_dir(workdir, rep, recompute=False)
    assert not rep.ok and any("sketches" in e for e in rep.errors)


MEM = ROOT / "tests" / "fixtures" / "memories"


def _mem_copy(tmp_path):
    d = tmp_path / "mem"
    shutil.copytree(MEM, d)
    return d, json.loads((d / "manifest.json").read_text("utf-8"))


def _node(d, vid):
    return json.loads((d / f"elements/memories/{vid}/memory.json").read_text("utf-8"))


def _write(d, m=None, vid=None, node=None):
    if m is not None:
        (d / "manifest.json").write_text(json.dumps(m), "utf-8")
    if vid is not None:
        (d / f"elements/memories/{vid}/memory.json").write_text(json.dumps(node), "utf-8")


def _val(d):
    rep = Report()
    rep.manifest = validate_dir(d, rep, recompute=True)
    return rep


def test_memories_fixture_is_valid_and_tagged(tmp_path):
    d, _ = _mem_copy(tmp_path)
    rep = _val(d)
    assert rep.ok, rep.errors
    m = rep.manifest
    assert "has-memories" in m["tags"]["auto"] and "memories" in m["coverage"]["elements"]


def test_memories_need_cof_1_1(tmp_path):
    d, m = _mem_copy(tmp_path)
    m["cof"] = "1.0"; _write(d, m)
    rep = _val(d)
    assert any("declare cof" in e for e in rep.errors), rep.errors


def test_memory_link_must_resolve_and_part_of_targets_a_period(tmp_path):
    d, _ = _mem_copy(tmp_path)
    n = _node(d, "m4"); n["links"] = [{"to": "memories/zz", "type": "about"}]; _write(d, vid="m4", node=n)
    assert any("unknown node" in e for e in _val(d).errors)
    n["links"] = [{"to": "memories/m3", "type": "part-of"}]; _write(d, vid="m4", node=n)
    assert any("part-of points to a period" in e for e in _val(d).errors)


def test_memory_when_shape_follows_kind(tmp_path):
    d, _ = _mem_copy(tmp_path)
    n = _node(d, "p1"); n["when"] = {"age": {"value": 20}}; _write(d, vid="p1", node=n)
    assert any("period's `when`" in e for e in _val(d).errors)


def test_explicit_memory_rules(tmp_path):
    d, m = _mem_copy(tmp_path)
    n = _node(d, "m3"); n["explicit"] = "nudity"; _write(d, vid="m3", node=n)
    errs = _val(d).errors
    assert any("nudity: true" in e for e in errs) and any("tags.content" in e for e in errs), errs
    m["elements"]["memories"]["variants"]["m3"]["nudity"] = True; m["tags"]["content"] = ["nudity"]; _write(d, m)
    rep = _val(d)
    assert rep.ok, rep.errors                       # adult (29), shown, flagged: allowed
    m["elements"]["memories"]["variants"]["m3"]["age"] = {"value": 16, "unit": "years"}; _write(d, m)
    errs = _val(d).errors
    assert any("under 18" in e for e in errs), errs   # the node rule and the preset rule both fire
    n["who"].append({"label": {"en": "a friend"}, "shown": True}); _write(d, vid="m3", node=n)
    m["elements"]["memories"]["variants"]["m3"]["age"] = {"value": 29, "unit": "years"}; _write(d, m)
    assert any("known age of 18" in e for e in _val(d).errors)


def test_memory_showing_a_minor_makes_the_preset_a_minor_preset(tmp_path):
    """RFC 0002 § 5.2: a memory whose media show the character carries an age that enters the preset's lowest age."""
    d, m = _mem_copy(tmp_path)
    m["elements"]["memories"]["variants"]["m3"]["age"] = {"value": 9, "unit": "years", "basis": "canonical"}; _write(d, m)
    rep = _val(d)
    assert rep.ok, rep.errors
    assert "has-minor-preset" in rep.manifest["tags"]["auto"]


def test_media_from_cycle_and_exclusivity(tmp_path):
    d, m = _mem_copy(tmp_path)
    m["elements"]["memories"]["variants"]["m3"]["media_from"] = "memories/m4"; _write(d, m)
    errs = _val(d).errors
    assert any("exclusive" in e for e in errs) or any("cycle" in e for e in errs), errs


def test_real_person_memory_warns_without_factual(tmp_path):
    d, m = _mem_copy(tmp_path)
    m["identities"]["id1"]["fictional"] = False; m["fictional"] = False; _write(d, m)
    rep = _val(d)
    assert any("factual" in w for w in rep.warnings), rep.warnings
    assert any("conversational-persona" in w for w in rep.warnings + rep.errors)


def _add_mem(d, m, vid, node, kind="moment", **variant):
    (d / f"elements/memories/{vid}").mkdir(parents=True, exist_ok=True)
    (d / f"elements/memories/{vid}/memory.json").write_text(json.dumps(node), "utf-8")
    m["elements"]["memories"]["variants"][vid] = {"kind": kind, "label": vid, "memory": f"elements/memories/{vid}/memory.json", "identity": "id1", **variant}
    m["presets"]["default"]["slots"]["memories"].append(vid)


def test_memory_timeline_order_and_gist_language(tmp_path):
    """RFC 0002 § 4.3: by age, else by date (age derived from the birth year the file implies), else by links, else
    undated last. § 3: gist in the preset's language, else the identity's, else the first entry."""
    from cof_cli.memories import gist_text, load_nodes, timeline, when_label
    d, m = _mem_copy(tmp_path)
    _add_mem(d, m, "d1", {"gist": {"en": "A dated one."}, "when": {"date": "2003"}})                  # m3: age 29 in 2019-03 → born ~1990 → 2003 ≈ 13
    _add_mem(d, m, "l1", {"gist": {"en": "Linked only."}, "links": [{"to": "memories/m3", "type": "after"}]})
    _add_mem(d, m, "u1", {"gist": {"en": "Undated."}})
    _write(d, m)
    assert _val(d).ok
    nodes = load_nodes(d, m)
    order = timeline(m, nodes, m["presets"]["default"]["slots"]["memories"])
    assert order == ["m1", "d1", "p1", "m3", "l1", "m4", "u1"] or order == ["m1", "d1", "p1", "m3", "m4", "l1", "u1"], order
    assert order.index("m3") < order.index("l1") and order[-1] == "u1" and order[1] == "d1"
    assert gist_text(m, "m3", nodes["m3"], "default") == ("fr", "La rencontre avec le Martien.")       # identity language fr
    m["identities"]["id1"].pop("language"); _write(d, m)
    assert gist_text(m, "m3", nodes["m3"], "default")[0] == "fr"                                      # first entry
    assert when_label("moment", nodes["m3"], "fr") == "age 29, 2019-03" and when_label("period", nodes["p1"], "fr") == "age 18–23"


def test_export_agent_writes_memory_md(tmp_path):
    """§ 6.4: MEMORY.md = host memory file + the canon gists in timeline order with markers; media of non-explicit
    nodes in memories/<id>/; personal nodes dropped unless keep_personal; explicit media never exported."""
    from cof_cli.convert import export_agent
    d, m = _mem_copy(tmp_path)
    n = _node(d, "m1"); n["visibility"] = "personal"; _write(d, vid="m1", node=n)
    out = tmp_path / "ws"; done = export_agent(d, out, "default")
    md = (out / "MEMORY.md").read_text("utf-8")
    assert done["memory_nodes"] == 3 and done["personal_dropped"] == 1 and "MEMORY.md" in done["memories"]
    assert "## Memories" in md and "grand" not in md.lower()                                           # personal m1 gone
    assert md.index("p1") < md.index("m3  ·") < md.index("m4  ·") and "guarded" in md and "imagined" in md and "fragment" in md
    assert (out / "memories/m3/meeting.jpg").is_file() and (out / "memories/m4/meeting.jpg").is_file()   # m4 borrows m3's media
    out2 = tmp_path / "ws2"; export_agent(d, out2, "default", keep_personal=True)
    assert "grand" in (out2 / "MEMORY.md").read_text("utf-8").lower() or "m1  ·" in (out2 / "MEMORY.md").read_text("utf-8")
    # explicit node: gist exported, media withheld
    m["elements"]["memories"]["variants"]["m3"]["nudity"] = True; m["tags"]["content"] = ["nudity"]; _write(d, m)
    n = _node(d, "m3"); n["explicit"] = "nudity"; _write(d, vid="m3", node=n)
    out3 = tmp_path / "ws3"; export_agent(d, out3, "default")
    assert "media withheld" in (out3 / "MEMORY.md").read_text("utf-8") and not (out3 / "memories/m3").exists()
    # example 10 (the first 1.1 file) exports its five memories in French for the fr-agent preset
    out4 = tmp_path / "ws4"; done = export_agent(ROOT / "spec/examples/10-clara-mercier", out4, "fr-agent")
    md = (out4 / "MEMORY.md").read_text("utf-8")
    assert done["memory_nodes"] == 5 and "grand-mère" in md and md.index("grand-mère") < md.index("Martien")


def test_extract_purges_personal_and_explicit_memories(tmp_path):
    """§ 5.7: personal nodes leave unless kept; § 5.8: --all-audiences takes the media off explicit nodes, gist kept;
    the node file travels with the variant; media borrowed through media_from follow their source."""
    from cof_cli.ops import drop_personal_memories, extract_presets, strip_intimate
    d, m = _mem_copy(tmp_path)
    m["elements"]["memories"]["variants"]["m3"]["nudity"] = True; m["tags"]["content"] = ["nudity"]; _write(d, m)
    n = _node(d, "m3"); n["explicit"] = "nudity"; _write(d, vid="m3", node=n)
    n = _node(d, "m1"); n["visibility"] = "personal"; _write(d, vid="m1", node=n)
    assert _val(d).ok
    a = tmp_path / "a"; extract_presets(d, a, ["default"])
    assert (a / "elements/memories/m3/memory.json").is_file() and (a / "elements/memories/m3/meeting.jpg").is_file()
    assert drop_personal_memories(a) == ["m1"]
    ma = json.loads((a / "manifest.json").read_text("utf-8"))
    assert "m1" not in ma["elements"]["memories"]["variants"] and ma["presets"]["default"]["slots"]["memories"] == ["p1", "m3", "m4"]
    assert not (a / "elements/memories/m1").exists()
    gone = strip_intimate(a)
    ma = json.loads((a / "manifest.json").read_text("utf-8")); V = ma["elements"]["memories"]["variants"]
    assert gone == ["memories.m3 (media only)"] and "m3" in V and "media" not in V["m3"] and "nudity" not in V["m3"]
    assert "media_from" not in V["m4"] and not any(x.get("role") == "memory-media" for x in ma["assets"])
    assert not (a / "elements/memories/m3/meeting.jpg").exists() and "explicit" not in _node(a, "m3") and _node(a, "m3")["gist"]
    assert ma["tags"]["content"] == ["none"]
    rep = Report(); validate_dir(a, rep); assert rep.ok, rep.errors


def test_extract_identity_leaves_other_real_persons_media_behind(tmp_path):
    """§ 4.5: media showing another real person do not travel with one character; a media_from whose source
    leaves the file is flattened into a `media` list."""
    from cof_cli.ops import extract_identity
    d, m = _mem_copy(tmp_path)
    m["identities"]["id2"] = {"name": "Marc Real", "fictional": False, "morphology": {"class": "human", "species": "human"},
                              "consent": {"subject_is_real_person": True, "scope": ["conversational-persona", "likeness-image"], "granted": "2026-10-01", "jurisdictions": ["FR"], "proof": [{"type": "other", "uri": "https://example.org/c"}]}}
    m["presets"]["marc"] = {"label": "Marc", "identity": "id2", "slots": {"memories": ["x1"]}, "age_override": {"value": 40, "unit": "years", "basis": "declared"}}
    m["identities"]["id2"]["default_preset"] = "marc"
    (d / "elements/memories/x1").mkdir(); (d / "elements/memories/x1/memory.json").write_text(json.dumps({"gist": {"fr": "Le même soir, vu par Marc."}, "factual": True, "who": [{"identity": "self", "shown": True}], "links": [{"to": "memories/m3", "type": "same-event"}]}), "utf-8")
    m["elements"]["memories"]["variants"]["x1"] = {"kind": "moment", "label": "x1", "memory": "elements/memories/x1/memory.json", "identity": "id2", "media_from": "memories/m3", "age": {"value": 40, "unit": "years", "basis": "canonical"}}
    n = _node(d, "m3"); n["who"].append({"identity": "id2", "shown": True, "age": {"value": 40}}); _write(d, vid="m3", node=n)
    _write(d, m)
    rep = _val(d); assert rep.ok, rep.errors
    notes = []; out = extract_identity(d, tmp_path / "clara", "id1", notes)
    V = out["elements"]["memories"]["variants"]
    assert notes and "m3" in notes[0] and "media" not in V["m3"] and "media_from" not in V["m4"]       # Marc's likeness stays behind
    assert _node(tmp_path / "clara", "m3")["gist"] and "x1" not in V
    out2 = extract_identity(d, tmp_path / "marc", "id2")
    V2 = out2["elements"]["memories"]["variants"]
    assert V2["x1"].get("media") == ["a-m3-meeting"] and "media_from" not in V2["x1"] and "m3" not in V2   # flattened
    assert (tmp_path / "marc/elements/memories/m3/meeting.jpg").is_file()
    rep = Report(); validate_dir(tmp_path / "marc", rep); assert not [e for e in rep.errors if "x1" in e], rep.errors
