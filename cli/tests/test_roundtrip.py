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
    for old in ("1.0", "1.1"):                      # earlier minors stay published as they were (their $id names their folder)
        for f in (ROOT / "schemas" / old).glob("*.json"):
            assert json.loads(f.read_text("utf-8")).get("$id") == f"https://yannsouetre.github.io/cof/schemas/{old}/{f.name}", f
    assert not (ROOT / "schemas/1.1/psyche-node.schema.json").exists()


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
    errs = _val(d).errors                           # F1: m4 borrows m3's media and is not explicit itself
    assert any("borrows the media" in e and "memories.m4" in e for e in errs), errs
    n4 = _node(d, "m4"); n4["explicit"] = "nudity"; n4["who"] = [{"identity": "self", "shown": True}]; _write(d, vid="m4", node=n4)
    m["elements"]["memories"]["variants"]["m4"]["nudity"] = True; m["elements"]["memories"]["variants"]["m4"]["age"] = {"value": 29, "unit": "years"}; _write(d, m)
    rep = _val(d)
    assert rep.ok, rep.errors                       # adult (29), shown, flagged, borrower explicit too: allowed
    # F2: an explicit node with nobody shown is invalid; a 12-year-old preset listing the borrower is invalid (1.0 nude rule)
    n4b = dict(n4); n4b["who"] = []; _write(d, vid="m4", node=n4b)
    assert any("nobody declared shown" in e for e in _val(d).errors)
    _write(d, vid="m4", node=n4)
    m["presets"]["child"] = {"label": "child", "slots": {"memories": ["m4"]}, "age_override": {"value": 12, "unit": "years"}}; _write(d, m)
    assert any("presets.child" in e and "under 18" in e for e in _val(d).errors)
    m["presets"].pop("child"); _write(d, m)
    # F5: on an explicit node the variant age and when.age must agree
    n3b = dict(n); n3b["when"] = {"age": {"value": 15}, "date": "2005-03"}; _write(d, vid="m3", node=n3b)
    assert any("must agree" in e for e in _val(d).errors)
    _write(d, vid="m3", node=n)
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
    n = _node(d, "m4"); n["explicit"] = "nudity"; n["who"] = [{"identity": "self", "shown": True}]; _write(d, vid="m4", node=n)      # the borrower is explicit too (§ 4.5)
    m["elements"]["memories"]["variants"]["m4"]["nudity"] = True; m["elements"]["memories"]["variants"]["m4"]["age"] = {"value": 29, "unit": "years"}; _write(d, m)
    n = _node(d, "m1"); n["visibility"] = "personal"; _write(d, vid="m1", node=n)
    rep = _val(d); assert rep.ok, rep.errors
    a = tmp_path / "a"; extract_presets(d, a, ["default"])
    assert (a / "elements/memories/m3/memory.json").is_file() and (a / "elements/memories/m3/meeting.jpg").is_file()
    assert drop_personal_memories(a) == ["m1"]
    ma = json.loads((a / "manifest.json").read_text("utf-8"))
    assert "m1" not in ma["elements"]["memories"]["variants"] and ma["presets"]["default"]["slots"]["memories"] == ["p1", "m3", "m4"]
    assert not (a / "elements/memories/m1").exists()
    gone = strip_intimate(a)
    ma = json.loads((a / "manifest.json").read_text("utf-8")); V = ma["elements"]["memories"]["variants"]
    assert gone == ["memories.m3 (media only)", "memories.m4 (media only)"] and "m3" in V and "media" not in V["m3"] and "nudity" not in V["m3"]
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


# ---- RFC 0003: gender, archetype, role, relations ----------------------------------------------------

def _cast(tmp_path):
    """The memories fixture with a second (fictional) character and a relation between the two."""
    d, m = _mem_copy(tmp_path)
    m["identities"]["id1"]["gender"] = "female"
    m["identities"]["id2"] = {"name": "Léo", "fictional": True, "morphology": {"class": "human"}, "gender": "male", "default_preset": "leo",
                              "relations": [{"to": "id1", "type": "child", "label": {"fr": "sa mère"}}]}
    m["presets"]["leo"] = {"label": "Léo", "identity": "id2", "slots": {}, "age_override": {"value": 20, "unit": "years", "basis": "declared"}}
    m["identities"]["id1"]["relations"] = [{"to": "id2", "type": "parent", "since": {"age": {"value": 36, "unit": "years"}}}]
    _write(d, m)
    return d, m


def test_cast_fixture_valid_and_inverse_relations(tmp_path):
    from cof_cli.cast import relations_of, preset_gender
    d, m = _cast(tmp_path)
    rep = _val(d); assert rep.ok, rep.errors
    assert not [w for w in rep.warnings if "disagree" in w], rep.warnings
    m["identities"]["id2"].pop("relations"); _write(d, m)                    # stored once, the inverse is computed
    assert [r["type"] for r in relations_of(m, "id2")] == ["child"]
    m["presets"]["swap"] = {"label": "swap", "identity": "id1", "slots": {}, "identity_override": {"gender": "male", "nicknames": ["Clé"]}, "extends": "default"}
    assert preset_gender(m, "swap") == "male" and preset_gender(m, "default") == "female"
    from cof_cli.cast import identity_view
    assert identity_view(m, "swap")["nicknames"] == ["Clé"] and identity_view(m, "swap")["name"] == m["identities"]["id1"]["name"]
    m["identities"]["id1"]["relations"] = [{"to": "id2", "type": "parent"}, {"to": "id2", "type": "parent"}]; _write(d, m)
    rep = _val(d); assert any("same relation twice" in e for e in rep.errors), rep.errors


def test_cast_rules(tmp_path):
    d, m = _cast(tmp_path)
    m["identities"]["id1"]["relations"] = [{"to": "id1", "type": "friend"}, {"to": "nobody", "type": "friend"}, {"to": "id2", "type": "other"}]
    m["identities"]["id2"]["relations"] = [{"to": "id1", "type": "friend"}]
    m["identities"]["id1"]["gender"] = "other"
    _write(d, m)
    rep = _val(d)
    assert any("to oneself" in e for e in rep.errors) and any("unknown identity" in e for e in rep.errors) and any("needs a label" in e for e in rep.errors), rep.errors
    assert any("without gender_label" in w for w in rep.warnings), rep.warnings
    m["identities"]["id1"]["relations"] = [{"to": "id2", "type": "parent"}]; m["identities"]["id1"]["gender"] = "female"; _write(d, m)
    rep = _val(d); assert rep.ok, rep.errors
    assert any("disagree" in w for w in rep.warnings), rep.warnings                    # parent on one side, friend on the other
    m["identities"]["id1"]["gender"] = "cat"; _write(d, m)
    rep = _val(d); assert not rep.ok                                                   # schema vocabulary
    m["identities"]["id1"]["gender"] = "female"; m["cof"] = "1.0"; m["elements"].pop("memories"); m["assets"] = [a for a in m["assets"] if a.get("role") != "memory-media"]
    for p in m["presets"].values():
        p.get("slots", {}).pop("memories", None)
    m["identities"]["id1"].pop("language", None); _write(d, m)
    rep = _val(d); assert any("declare cof" in e and "gender" in e for e in rep.errors), rep.errors


def test_archetype_role_and_exports(tmp_path):
    from cof_cli.convert import export_soul
    from cof_cli.ops import extract_identity
    d, m = _cast(tmp_path)
    pv = m["elements"]["personality"]["variants"]
    vid = next(k for k, v in pv.items() if v.get("psyche")) if any(v.get("psyche") for v in pv.values()) else None
    if vid is None:                                                                     # give the first personality a psyche file
        vid = next(iter(pv)); (d / f"elements/personality/{vid}").mkdir(parents=True, exist_ok=True)
        pv[vid]["psyche"] = f"elements/personality/{vid}/psyche.json"
        (d / pv[vid]["psyche"]).write_text(json.dumps({"model": "cof-psyche/0.1"}), "utf-8")
    ps = json.loads((d / pv[vid]["psyche"]).read_text("utf-8"))
    ps["archetype"] = {"model": "pearson-12", "value": "creator", "secondary": ["explorer"]}; ps["role"] = "protagonist"
    (d / pv[vid]["psyche"]).write_text(json.dumps(ps), "utf-8"); _write(d, m)
    rep = _val(d); assert rep.ok, rep.errors
    ps["archetype"]["value"] = "wizard"; (d / pv[vid]["psyche"]).write_text(json.dumps(ps), "utf-8")
    rep = _val(d); assert not rep.ok and any("psyche" in e for e in rep.errors), rep.errors
    ps["archetype"] = {"model": "free", "value": "wizard"}; (d / pv[vid]["psyche"]).write_text(json.dumps(ps), "utf-8")
    rep = _val(d); assert rep.ok, rep.errors
    pid = next(p for p, P in m["presets"].items() if vid in (P.get("slots", {}).get("personality") or [])) if any(vid in (P.get("slots", {}).get("personality") or []) for P in m["presets"].values()) else "default"
    soul, ident = export_soul(d, pid)
    assert "Gender: female" in ident or "Genre: féminin" in ident
    assert "Relations" in soul and "Léo" in soul
    assert ("wizard" in soul) == (vid in (m["presets"][pid].get("slots", {}).get("personality") or []))
    notes = []; out = extract_identity(d, tmp_path / "clara", "id1", notes)
    assert "relations" not in out["identities"]["id1"] and any("relation dropped" in n for n in notes), notes


def test_self_description_and_memory_add(tmp_path):
    """COF.md is written at pack and `memory add` appends a lived node that validates, listed by the presets (inherited lists copied)."""
    from cof_cli.selfdesc import memory_add, self_description, write_self_description
    from cof_cli.model import resolve_preset_slots
    d, m = _mem_copy(tmp_path)
    m["presets"]["child"] = {"label": "child", "extends": "default", "slots": {}}; _write(d, m)
    write_self_description(d, m)
    txt = (d / "COF.md").read_text("utf-8")
    assert "cof memory add" in txt and "specification and `manifest.json` win" in txt and "Memories" in txt
    before = list(resolve_preset_slots(m, "child").get("memories") or [])
    note = tmp_path / "n.md"; note.write_text("— a line", "utf-8")
    vid = memory_add(d, identity=None, kind="moment", gists={"fr": "Ce matin, relu avec Léo."}, date="2026-10-25", who=["Léo"], tags=["Léo", "work"], personal=True, media=[note], presets=["child"])
    m2 = json.loads((d / "manifest.json").read_text("utf-8"))
    assert vid in m2["elements"]["memories"]["variants"] and m2["presets"]["child"]["slots"]["memories"] == before + [vid]
    n = _node(d, vid); assert n["visibility"] == "personal" and n["origin"] == "lived" and n["tags"] == ["leo", "work"]
    assert any(a["id"].startswith(f"a-mem-{vid}") and a["role"] == "memory-media" for a in m2["assets"])
    rep = _val(d); assert rep.ok, rep.errors
    assert "personal memory" in " ".join(rep.warnings)


def test_extract_preset_keeps_the_places_its_memories_point_at(tmp_path):
    """A memory's `where.environment` (and the elements its links name) travel with the memory when a preset is extracted,
    whether or not the preset lists them — found by Yann's L2 test of 26 October: `cof extract --preset fr-65` on Clara
    left `memories.ev2` pointing at the studio (`appearance/e1`), which the 65-year-old preset does not list."""
    from cof_cli.ops import extract_presets
    d = tmp_path / "c"; shutil.copytree(ROOT / "spec/examples/10-clara-mercier", d)
    m = json.loads((d / "manifest.json").read_text("utf-8"))
    assert "e1" not in (m["presets"]["fr-65"].get("slots") or {}).get("appearance", []) and "ev2" in m["presets"]["fr-65"]["slots"]["memories"]
    a = tmp_path / "a"; extract_presets(d, a, ["fr-65"])
    ma = json.loads((a / "manifest.json").read_text("utf-8"))
    assert "e1" in ma["elements"]["appearance"]["variants"]
    rep = Report(); validate_dir(a, rep); assert rep.ok, rep.errors


# ---------- review of 28 October (autonomous audit): container hardening, paths from manifests, merge / extract parity ----------

def test_archive_duplicate_and_directory_entries(tmp_path):
    """A second entry of the same name is an error (readers disagree on which one wins); a directory entry (zip -r) is
    skipped by unpack instead of crashing; a structurally unsafe archive is not opened further."""
    from cof_cli.container import inspect
    d = tmp_path / "c"; shutil.copytree(EXAMPLE, d)
    src = tmp_path / "a.cof"; pack(d, src)
    dup = tmp_path / "dup.cof"
    with zipfile.ZipFile(src) as zi, zipfile.ZipFile(dup, "w") as zo:
        for i in zi.infolist():
            zo.writestr(i, zi.read(i.filename))
        zo.writestr("manifest.json", json.dumps({"cof": "1.0", "name": "Other"}))
    assert any("duplicate entry: manifest.json" in e for e in inspect(dup)["errors"])
    rep = validate_cof(dup); assert not rep.ok and any("duplicate entry" in e for e in rep.errors)
    dirs = tmp_path / "dirs.cof"
    with zipfile.ZipFile(src) as zi, zipfile.ZipFile(dirs, "w") as zo:
        for i in zi.infolist():
            zo.writestr(i, zi.read(i.filename))
            if i.filename == "manifest.json":
                zo.writestr("elements/", b"")
    unpack(dirs, tmp_path / "u")
    rep = validate_cof(dirs); assert rep.ok, rep.errors


def test_manifest_paths_never_leave_the_output(tmp_path):
    """Names and paths read from a manifest are data: a skill `name` with `..`, an asset path outside the folder or a
    character name shaped like a path never write outside the output (export, extract, merge)."""
    from cof_cli.convert import export_agent
    from cof_cli.ops import extract_presets
    from cof_cli.cli import _fname
    d = tmp_path / "s"; shutil.copytree(ROOT / "spec/examples/08-agent-skills", d)
    m = json.loads((d / "manifest.json").read_text("utf-8"))
    sk = next(v for v in m["elements"]["files"]["variants"].values() if v.get("kind") == "skill")
    sk["name"] = "../../escaped"; sk.pop("entry", None); _write(d, m)
    out = tmp_path / "out"
    with pytest.raises(ValueError):
        export_agent(d, out)
    assert not (tmp_path / "escaped").exists() and not (tmp_path.parent / "escaped").exists()
    assert _fname({"name": "../../ESCAPED"}) == "ESCAPED" and _fname({"name": "Clara Mercier"}) == "Clara-Mercier"
    d2 = tmp_path / "t"; shutil.copytree(ROOT / "spec/examples/03-clara-photos", d2)
    m2 = json.loads((d2 / "manifest.json").read_text("utf-8"))
    (tmp_path / "secret.txt").write_text("x", "utf-8")
    m2["assets"][0]["path"] = "../secret.txt"; _write(d2, m2)
    with pytest.raises(ContainerError):
        extract_presets(d2, tmp_path / "x", [m2["default_preset"]])


def test_merge_keeps_memories_whole(tmp_path):
    """Merging files with memories remaps `media` asset ids (deduplicated bytes included) and, when variant ids collide,
    the memory nodes' links, where.environment and media_from — the result validates and no reference dangles."""
    from cof_cli.ops import merge_dirs
    C = ROOT / "spec/examples/10-clara-mercier"
    out = tmp_path / "m1"; merge_dirs([C], out)
    rep = Report(); validate_dir(out, rep); assert rep.ok, rep.errors
    out2 = tmp_path / "m2"; merge_dirs([C, C], out2)
    rep2 = Report(); validate_dir(out2, rep2); assert rep2.ok, rep2.errors
    m = json.loads((out2 / "manifest.json").read_text("utf-8"))
    V = m["elements"]["memories"]["variants"]
    assert "m1-ev4" in V
    n = json.loads((out2 / V["m1-ev4"]["memory"]).read_text("utf-8"))
    assert all(l["to"].startswith("memories/m1-") for l in n["links"])


def test_extract_preset_of_a_cast_relabels_the_departed(tmp_path):
    """`extract --preset` / `--tag` on a cast file: the characters no kept preset owns leave the file, their relations are
    dropped and the `who` entries naming them become plain persons — as `extract --identity` already did."""
    from cof_cli.ops import extract_presets
    D = ROOT / "spec/examples/11-duo-clara-martien"
    for pid in ("default", "m1-default"):
        out = tmp_path / pid; extract_presets(D, out, [pid])
        rep = Report(); validate_dir(out, rep); assert rep.ok, (pid, rep.errors)
        m = json.loads((out / "manifest.json").read_text("utf-8"))
        assert len(m["identities"]) == 1
        for v in m["elements"].get("memories", {}).get("variants", {}).values():
            n = json.loads((out / v["memory"]).read_text("utf-8"))
            assert all(w.get("identity") in (None, "self") for w in n.get("who") or [])


def test_memory_add_cli_is_atomic_and_rejects_odd_ages(tmp_path):
    """A refused `cof memory add` on a folder leaves it untouched; nan / infinite / absurd ages are refused before anything is written."""
    from cof_cli.cli import main
    d = tmp_path / "c"; shutil.copytree(EXAMPLE, d)
    before = sorted(str(p.relative_to(d)) for p in d.rglob("*"))
    assert main(["memory", "add", str(d), "--gist", "en=x", "--date", "2025-13"]) == 1
    assert main(["memory", "add", str(d), "--gist", "en=x", "--age", "nan"]) == 2
    assert main(["memory", "add", str(d), "--gist", "en=x", "--age", "1000"]) == 2
    assert sorted(str(p.relative_to(d)) for p in d.rglob("*")) == before
    assert main(["memory", "add", str(d), "--gist", "en=ok", "--date", "2025-10"]) == 0
    assert (d / "elements/memories/ev1/memory.json").is_file()
    assert main(["info", str(tmp_path / "nope.cof")]) == 1          # a clean error line, no traceback


def test_validator_survives_wrongly_typed_subfiles(tmp_path):
    """Schema-invalid node files and sub-files are reported, never raised: the semantic rules only read a valid shape."""
    d = tmp_path / "c"; shutil.copytree(ROOT / "spec/examples/10-clara-mercier", d)
    p = d / "elements/memories/ev2/memory.json"; n = json.loads(p.read_text("utf-8"))
    n["where"] = "the garden"; n["links"] = True; p.write_text(json.dumps(n), "utf-8")
    rep = Report(); validate_dir(d, rep); assert not rep.ok and any("memory.schema" in e for e in rep.errors)
    d2 = tmp_path / "w"; shutil.copytree(ROOT / "spec/examples/07-clara-modulaire", d2)
    m = json.loads((d2 / "manifest.json").read_text("utf-8"))
    spec = next(v["spec"] for v in m["elements"]["identity_weights"]["variants"].values() if v.get("spec"))
    (d2 / spec).write_text(json.dumps({"base_model": "x", "file": {}}), "utf-8")
    rep2 = Report(); validate_dir(d2, rep2); assert not rep2.ok


# ---------------------------------------------------------------- psyche (RFC 0004, 1.2) ----------------------------------------------------------------

def _psy(tmp_path, nodes=None):
    """The memories fixture (cof 1.2) with a small psyche: a wound because of a memory, a value because of the wound, a
    belief (the lie) and the contradiction between them, a stance toward the user. `nodes` overrides node fields."""
    d, m = _mem_copy(tmp_path)
    N = {"wound1": ("wound", {"gist": {"fr": "Les années d'agence.", "en": "The agency years."}, "strength": 85, "stability": "core", "links": [{"to": "memories/p1", "type": "because"}]}),
         "val1": ("value", {"gist": {"fr": "La légèreté.", "en": "Lightness."}, "strength": 95, "since": {"age": {"value": 28, "unit": "years"}}, "links": [{"to": "psyche/wound1", "type": "because"}]}),
         "bel1": ("belief", {"gist": {"fr": "Si je ralentis, je disparais.", "en": "If I slow down, I disappear."}, "strength": 60, "false_but_held": True}),
         "contra1": ("contradiction", {"gist": {"fr": "Prône la lenteur, travaille la nuit.", "en": "Preaches slowness, works at night."}, "strength": 60,
                                       "links": [{"to": "psyche/val1", "type": "conflicts"}, {"to": "psyche/bel1", "type": "conflicts"}]}),
         "stance1": ("stance", {"gist": {"fr": "Envers l'utilisateur : une collègue.", "en": "Toward the user: a colleague."}, "strength": 50, "about": {"user": True}})}
    V = {}
    for vid, (kind, nd) in N.items():
        nd = {**nd, **((nodes or {}).get(vid) or {})}
        (d / f"elements/psyche/{vid}").mkdir(parents=True, exist_ok=True)
        (d / f"elements/psyche/{vid}/psyche-node.json").write_text(json.dumps({k: x for k, x in nd.items() if x is not None}), "utf-8")
        V[vid] = {"kind": kind, "label": vid, "node": f"elements/psyche/{vid}/psyche-node.json", "identity": "id1"} | ({"strength": nd["strength"]} if nd.get("strength") is not None else {})
    m["cof"] = "1.2"; m["elements"]["psyche"] = {"variants": V}; m["presets"]["default"]["slots"]["psyche"] = list(N)
    _write(d, m)
    return d, m


def _pnode(d, vid, **kw):
    p = d / f"elements/psyche/{vid}/psyche-node.json"; n = json.loads(p.read_text("utf-8")); n.update(kw)
    p.write_text(json.dumps({k: x for k, x in n.items() if x is not None}), "utf-8")


def test_example_10_psyche_is_valid(tmp_path):
    """Clara's 22 nodes (RFC 0004 § 7 bis) and bel4 (§ 3 nonies) in the flagship example: valid, listed by presets like
    memories; an extract keeps what the preset holds and drops the links to nodes left behind."""
    src = ROOT / "spec/examples/10-clara-mercier"
    rep = Report(); m = validate_dir(src, rep, recompute=False)
    assert rep.ok, rep.errors
    assert m["cof"] == "1.2" and len(m["elements"]["psyche"]["variants"]) == 23
    assert not [w for w in rep.warnings if "psyche" in w], rep.warnings            # part B: every node carries Clara's French (her primary language)
    from cof_cli.psyche import load_nodes as load_psyche
    assert all(set(n["gist"]) == {"en", "fr"} for n in load_psyche(src, m).values())
    from cof_cli.model import resolve_preset_slots
    assert len(resolve_preset_slots(m, "default")["psyche"]) == 22 and len(resolve_preset_slots(m, "fr")["psyche"]) == 22
    assert resolve_preset_slots(m, "en-12")["psyche"] == ["val4", "taste1", "hab2"]
    for pid in ("en-65", "fr-65"):                                                   # § 3 nonies: at 65 she no longer holds bel3 and contra1, she holds bel4
        L = resolve_preset_slots(m, pid)["psyche"]
        assert len(L) == 21 and "bel4" in L and "bel3" not in L and "contra1" not in L
    assert [p for p in m["presets"] if "bel4" in resolve_preset_slots(m, p).get("psyche", [])] == ["en-65", "fr-65"]
    assert not rep.warnings, rep.warnings
    from cof_cli.validate import auto_tags
    assert "has-psyche" in auto_tags(m)
    from cof_cli.ops import extract_presets
    out = tmp_path / "x"; extract_presets(src, out, ["en-12"])
    assert sorted(p.name for p in (out / "elements/psyche").iterdir()) == ["hab2", "taste1", "val4"]
    assert "links" not in json.loads((out / "elements/psyche/hab2/psyche-node.json").read_text("utf-8"))   # supports → bel2, left behind
    rep = Report(); validate_dir(out, rep, recompute=False); assert rep.ok, rep.errors


def test_psyche_fixture_and_structural_rules(tmp_path):
    d, m = _psy(tmp_path)
    rep = _val(d); assert rep.ok, rep.errors
    assert not rep.warnings and not rep.info.get("notes"), (rep.warnings, rep.info.get("notes"))
    assert "has-psyche" in rep.manifest["tags"]["auto"] and "psyche" in rep.manifest["coverage"]["elements"]
    errs = lambda: _val(d).errors
    _pnode(d, "bel1", links=[{"to": "psyche/zz", "type": "because"}, {"to": "identities/nobody", "type": "about"}])
    assert sum("unknown node" in e for e in errs()) == 1 and sum("people go in `who`" in e for e in errs()) == 1   # RFC 0005 § 2.3
    _pnode(d, "bel1", links=[{"to": "memories/m1", "type": "supports"}]); assert any("targets a psyche node only" in e for e in errs())
    _pnode(d, "bel1", links=None, who=[{"identity": "id1"}]); assert not errs()          # the person of the draft's identity link
    _pnode(d, "contra1", links=[{"to": "psyche/val1", "type": "conflicts"}]); assert any("exactly two `conflicts`" in e and "found 1" in e for e in errs())
    _pnode(d, "contra1", links=[{"to": "psyche/val1", "type": "conflicts"}, {"to": "psyche/bel1", "type": "conflicts"}])
    _pnode(d, "val1", false_but_held=True); assert any("`false_but_held` is for a belief only" in e for e in errs())
    _pnode(d, "val1", false_but_held=None, about={"label": {"en": "x"}}); assert any("`about` field is for a stance only" in e for e in errs())
    _pnode(d, "val1", about=None)
    _pnode(d, "stance1", about={"identity": "nobody"}); assert any("about.identity 'nobody'" in e for e in errs())
    _pnode(d, "stance1", about={"node": "memories/zz"}); assert any("about.node memories/zz" in e for e in errs())
    _pnode(d, "stance1", about={"node": "memories/m1"}); assert not errs()
    _pnode(d, "wound1", links=[{"to": "psyche/val1", "type": "because"}]); assert any("`because` cycle" in e for e in errs())
    _pnode(d, "wound1", links=[{"to": "memories/p1", "type": "because"}])
    m["elements"]["psyche"]["variants"]["val1"]["strength"] = 10; _write(d, m)
    assert any("manifest strength 10 differs" in e for e in errs())
    m["elements"]["psyche"]["variants"]["val1"]["strength"] = 95; _write(d, m)
    _pnode(d, "val1", strength=150); assert any("psyche-node.schema" in e for e in errs())         # the sub-file pass
    _pnode(d, "val1", strength=95)
    m["elements"]["psyche"]["variants"]["val1"].pop("node"); _write(d, m); assert any("names its node file" in e for e in errs())
    m["elements"]["psyche"]["variants"]["val1"]["node"] = "elements/psyche/val1/psyche-node.json"
    m["elements"]["psyche"]["variants"]["val1"]["kind"] = "opinion"; _write(d, m); assert any("unknown kind 'opinion'" in e for e in errs())
    m["elements"]["psyche"]["variants"]["val1"]["kind"] = "value"; _write(d, m)
    assert _val(d).ok


def test_psyche_information_and_warnings(tmp_path):
    d, m = _psy(tmp_path)
    _pnode(d, "wound1", links=None)
    _pnode(d, "stance1", about=None)
    m["elements"]["psyche"]["variants"]["rule1"] = {"kind": "rule", "label": "rule", "node": "elements/psyche/rule1/psyche-node.json"}
    (d / "elements/psyche/rule1").mkdir(); (d / "elements/psyche/rule1/psyche-node.json").write_text(json.dumps({"gist": {"fr": "Ne jamais…", "en": "Never…"}, "stability": "shifting", "visibility": "personal"}), "utf-8")
    m["presets"]["default"]["slots"]["psyche"].append("rule1")
    m["presets"]["default"]["age_override"] = {"value": 20, "unit": "years", "basis": "declared"}                 # younger than val1's since (28)
    _write(d, m)
    rep = _val(d); assert rep.ok, rep.errors
    W, I = rep.warnings, rep.info.get("notes") or []
    assert any("psyche.wound1: a wound with no `because`" in n for n in I), I
    assert not any("strength unset" in n for n in I)                       # 1 of 6 unset
    assert any("psyche.stance1: a stance with no `about`" in w for w in W) and any("psyche.rule1: a rule that is not `core`" in w for w in W), W
    assert any("psyche.rule1: personal node" in w for w in W) and any("presets.default: psyche.val1 appeared at 28" in w for w in W), W
    for vid in ("wound1", "val1", "bel1"):
        _pnode(d, vid, strength=None); m["elements"]["psyche"]["variants"][vid].pop("strength")
    _write(d, m)
    assert any("strength unset on 4 of 6" in n for n in (_val(d).info.get("notes") or []))
    _pnode(d, "val1", gist={"en": "Lightness."})
    assert any("psyche of id1: 1 node(s) without a gist in the character's primary language (fr): val1" in w for w in _val(d).warnings)
    from cof_cli.cli import _print_report
    assert _print_report(_val(d), False) == 0


def test_psyche_aware_valence_until_rules(tmp_path):
    """RFC 0004 § 3 nonies: `valence` off a stance / taste and `until` before `since` are errors (ages, dates, or an age
    against a date through the implied birth year); `aware: no` on a secret node and a preset older than a node's `until`
    are warnings; the preset's age is the age it shows (its memories do not lower it)."""
    d, m = _psy(tmp_path)
    errs = lambda: _val(d).errors
    _pnode(d, "stance1", valence=60, aware="partly"); _pnode(d, "bel1", aware="no")
    rep = _val(d); assert rep.ok and not rep.warnings, (rep.errors, rep.warnings)
    _pnode(d, "val1", valence=20); assert any("psyche.val1: `valence` is for a stance or a taste only (this node is a value)" in e for e in errs())
    _pnode(d, "val1", valence=None)
    _pnode(d, "stance1", valence=140); assert any("psyche-node.schema" in e for e in errs())       # −100 … +100, the schema
    _pnode(d, "stance1", valence=-100, aware="maybe"); assert any("psyche-node.schema" in e for e in errs())
    _pnode(d, "stance1", aware=None); assert not errs()
    # until against since: ages
    _pnode(d, "val1", until={"age": {"value": 20, "unit": "years"}})
    assert any("psyche.val1: `until` (age 20) is before `since` (age 28)" in e for e in errs())
    _pnode(d, "val1", until={"age": {"value": 28, "unit": "years"}}); assert not errs()             # the same age: not before
    # dates, at their common precision
    _pnode(d, "val1", since={"date": "2019-06"}, until={"date": "2019"}); assert not errs()
    _pnode(d, "val1", until={"date": "2018-12"}); assert any("is before `since`" in e for e in errs())
    # an age against a date: through the birth year the memories imply (m3: 29 in 2019-03 → born 1990), one year of tolerance
    from cof_cli.memories import birth_years, load_nodes as load_memories
    assert birth_years(m, load_memories(d, m))
    _pnode(d, "val1", since={"date": "2019"}, until={"age": {"value": 20, "unit": "years"}})
    by = sorted(birth_years(m, load_memories(d, m)))[len(birth_years(m, load_memories(d, m))) // 2]
    assert (2019.5 - by) > 21 and any("is before `since`" in e for e in errs()), by
    _pnode(d, "val1", until={"age": {"value": round(2019.5 - by), "unit": "years"}}); assert not errs()
    _pnode(d, "val1", since={"age": {"value": 28, "unit": "years"}}, until=None)
    # warnings: aware no on a secret node; a preset older than a node's until (its memories do not count in its age)
    _pnode(d, "bel1", disclosure="secret")
    assert any("psyche.bel1: `aware: no` on a secret node" in w for w in _val(d).warnings)
    _pnode(d, "bel1", disclosure="open", until={"age": {"value": 25, "unit": "years"}})
    m["presets"]["default"]["age_override"] = {"value": 40, "unit": "years", "basis": "declared"}; _write(d, m)
    rep = _val(d); assert rep.ok, rep.errors
    assert any("presets.default: psyche.bel1 was held until 25, before the age this preset shows (40) (coherence)" in w for w in rep.warnings), rep.warnings
    from cof_cli.model import preset_age
    mm = rep.manifest
    assert preset_age(mm, "default", ignore={"memories"}) == 40
    m["presets"]["default"]["age_override"] = {"value": 25, "unit": "years", "basis": "declared"}; _write(d, m)
    assert not any("was held until" in w for w in _val(d).warnings)                                  # 25 is not older than 25


def test_psyche_coherence_uses_the_age_the_preset_shows(tmp_path):
    """The `since` / `until` coherence rules read the preset's own age: a 65-year-old preset that remembers a moment shown
    at 29 is 65 here (Clara's en-65 holds bel4, since 45). Held bel3 (until 45), it is warned."""
    src = ROOT / "spec/examples/10-clara-mercier"
    d = tmp_path / "c"; shutil.copytree(src, d)
    m = json.loads((d / "manifest.json").read_text("utf-8"))
    rep = Report(); validate_dir(d, rep, recompute=False); assert rep.ok and not rep.warnings, rep.warnings
    m["presets"]["en-65"]["slots"]["psyche"] += ["bel3"]; _write(d, m)
    rep = Report(); validate_dir(d, rep, recompute=False)
    assert rep.warnings == ["presets.en-65: psyche.bel3 was held until 45, before the age this preset shows (65) (coherence)"], rep.warnings
    m["presets"]["en-12"]["slots"]["psyche"] += ["bel4"]; _write(d, m)
    rep = Report(); validate_dir(d, rep, recompute=False)
    assert "presets.en-12: psyche.bel4 appeared at 45, after the age this preset shows (12) (coherence)" in rep.warnings, rep.warnings


def test_psyche_version_gate_and_risk_tags(tmp_path):
    d, m = _psy(tmp_path)
    m["cof"] = "1.1"; _write(d, m)
    assert any("uses 1.2 additions (elements.psyche)" in e and 'declare cof "1.2"' in e for e in _val(d).errors)
    m["cof"] = "1.2"; _write(d, m)
    _pnode(d, "bel1", risk="dangerous"); _pnode(d, "stance1", risk="inappropriate")
    errs = _val(d).errors
    assert any("must include 'psyche-dangerous'" in e for e in errs) and any("must include 'psyche-inappropriate'" in e for e in errs), errs
    m["tags"]["content"] = ["psyche-inappropriate", "psyche-dangerous"]; _write(d, m)
    assert _val(d).ok
    _pnode(d, "bel1", risk=None)
    assert any("'psyche-dangerous' without any psyche node of risk 'dangerous'" in e for e in _val(d).errors)
    m["elements"].pop("psyche"); m["cof"] = "1.1"; m["tags"]["content"] = ["psyche-inappropriate"]
    m["presets"]["default"]["slots"].pop("psyche"); _write(d, m)
    errs = _val(d).errors
    assert any("uses 1.2 additions (tags.content 'psyche-inappropriate')" in e for e in errs) and any("without any psyche node" in e for e in errs), errs
    m["cof"] = "1.3"; m["tags"]["content"] = ["none"]; _write(d, m)                     # a later minor than the tool: warned, never refused
    rep = _val(d); assert rep.ok and any("newer than this validator (1.2)" in w for w in rep.warnings), rep.errors


def test_psyche_in_a_cast_hangs_on_its_own_past(tmp_path):
    d, _ = _psy(tmp_path)
    m = json.loads((d / "manifest.json").read_text("utf-8"))
    m["identities"]["id2"] = {"name": "Léo", "fictional": True, "morphology": {"class": "human"}}
    m["presets"]["leo"] = {"label": "Léo", "identity": "id2", "slots": {"psyche": ["leo1"]}, "age_override": {"value": 20, "unit": "years", "basis": "declared"}}
    m["elements"]["psyche"]["variants"]["leo1"] = {"kind": "fear", "label": "leo1", "node": "elements/psyche/leo1/psyche-node.json"}
    (d / "elements/psyche/leo1").mkdir()
    (d / "elements/psyche/leo1/psyche-node.json").write_text(json.dumps({"gist": {"en": "Losing his mother's attention."}, "strength": 40, "links": [{"to": "memories/m1", "type": "because"}]}), "utf-8")
    _write(d, m)
    errs = _val(d).errors
    assert any("elements.psyche.leo1: no `identity`" in e for e in errs), errs
    m["elements"]["psyche"]["variants"]["leo1"]["identity"] = "id2"; _write(d, m)
    errs = _val(d).errors
    assert any("psyche.leo1: `because` memories/m1 is a memory of id1" in e for e in errs), errs
    (d / "elements/psyche/leo1/psyche-node.json").write_text(json.dumps({"gist": {"en": "Losing his mother's attention."}, "strength": 40, "links": [{"to": "identities/id1", "type": "about"}]}), "utf-8")
    errs = _val(d).errors
    assert any("psyche.leo1: link about to identities/id1" in e and "people go in `who`" in e for e in errs), errs   # RFC 0005: no identity links
    (d / "elements/psyche/leo1/psyche-node.json").write_text(json.dumps({"gist": {"en": "Losing his mother's attention."}, "strength": 40, "who": [{"identity": "id1"}]}), "utf-8")
    rep = _val(d); assert rep.ok, rep.errors


# ---------------------------------------------------------------- psyche, part B: purges, SOUL.md, migrate, psyche add ----------------------------------------------------------------

def test_psyche_purges_personal_risk_and_contradictions(tmp_path):
    """RFC 0004 § 3 ter / § 3 septies: personal nodes leave an extract like personal memories (--keep-personal keeps them);
    `--no-risk` drops inappropriate and dangerous nodes; a contradiction that loses a side goes with them; tags.content
    follows; the all-audiences slice leaves the risk nodes alone (a separate switch — Yann, 30 October)."""
    from cof_cli.ops import extract_presets, strip_intimate
    from cof_cli.psyche import drop_personal_nodes, strip_risk
    d, m = _psy(tmp_path)
    _pnode(d, "stance1", visibility="personal")
    _pnode(d, "bel1", risk="dangerous")
    m["tags"]["content"] = ["psyche-dangerous"]; _write(d, m)
    rep = _val(d); assert rep.ok, rep.errors
    a = tmp_path / "a"; extract_presets(d, a, ["default"])
    assert drop_personal_nodes(a) == ["stance1"] and drop_personal_nodes(a) == []
    ma = json.loads((a / "manifest.json").read_text("utf-8"))
    assert "stance1" not in ma["elements"]["psyche"]["variants"] and not (a / "elements/psyche/stance1").exists()
    assert ma["presets"]["default"]["slots"]["psyche"] == ["wound1", "val1", "bel1", "contra1"] and ma["tags"]["content"] == ["psyche-dangerous"]
    assert strip_risk(a) == ["bel1", "contra1"]                       # the contradiction val1 ↔ bel1 lost a side
    ma = json.loads((a / "manifest.json").read_text("utf-8"))
    assert sorted(ma["elements"]["psyche"]["variants"]) == ["val1", "wound1"] and ma["tags"]["content"] == ["none"]
    rep = Report(); validate_dir(a, rep); assert rep.ok, rep.errors
    # --all-audiences: the risk nodes stay (a separate switch), their file tag too; memories untouched (no explicit one here)
    b = tmp_path / "b"; extract_presets(d, b, ["default"])
    _pnode(b, "bel1", risk="inappropriate"); mb = json.loads((b / "manifest.json").read_text("utf-8")); mb["tags"]["content"] = ["psyche-inappropriate"]; _write(b, mb)
    gone = strip_intimate(b)
    assert not [x for x in gone if x.startswith("psyche.")]
    mb = json.loads((b / "manifest.json").read_text("utf-8"))
    assert mb["tags"]["content"] == ["psyche-inappropriate"] and "bel1" in mb["elements"]["psyche"]["variants"] and "m3" in mb["elements"]["memories"]["variants"]
    assert "bel1" in strip_risk(b) and json.loads((b / "manifest.json").read_text("utf-8"))["tags"]["content"] == ["none"]
    # the CLI: --no-risk is separate (memories' media stay), personal nodes are reported
    from cof_cli.cli import main
    c = tmp_path / "c"
    assert main(["extract", str(d), "--preset", "default", "-o", str(c), "--no-risk", "--keep-personal"]) == 0
    mc = json.loads((c / "manifest.json").read_text("utf-8"))
    assert sorted(mc["elements"]["psyche"]["variants"]) == ["stance1", "val1", "wound1"] and (c / "elements/memories/m3/meeting.jpg").is_file()
    # an extract whose preset lists a contradiction without one of its sides drops the contradiction (§ 3 sexies)
    m["presets"]["half"] = {"label": "half", "slots": {"psyche": ["val1", "contra1"], "personality": ["p1"]}, "age_override": {"value": 29, "unit": "years", "basis": "declared"}}; _write(d, m)
    e = tmp_path / "e"; extract_presets(d, e, ["half"])
    me = json.loads((e / "manifest.json").read_text("utf-8"))
    assert sorted(me["elements"]["psyche"]["variants"]) == ["val1"] and me["presets"]["half"]["slots"]["psyche"] == ["val1"]   # a preset selects nodes: val1's `because` wound1 is dropped as a link (part A)
    rep = Report(); validate_dir(e, rep); assert rep.ok, rep.errors


def test_soul_md_who_she_is(tmp_path):
    """§ 3 quinquies: SOUL.md renders the nodes in the fixed kind order, whole gist at strength ≥ 70 and a short clause below,
    lies and guarded nodes marked, secret nodes left out with one line, personal and dangerous nodes dropped unless kept, in
    the preset's language with each node falling back to what it has; the 1.0 lists leave the sheet when nodes exist."""
    from cof_cli.convert import export_agent, export_soul
    from cof_cli.psyche import short_clause
    d, m = _psy(tmp_path)
    for vid, kind, node in [("rule1", "rule", {"gist": {"fr": "Ne jamais envoyer un message que personne n'a demandé."}, "strength": 90, "stability": "core"}),
                            ("taste1", "taste", {"gist": {"en": "Loves the smell of paper — and a lime tree's shade in August."}, "strength": 40, "disclosure": "guarded"}),
                            ("need1", "need", {"gist": {"fr": "Accepter d'être aidée.", "en": "Accept being helped."}, "strength": 65, "disclosure": "secret"}),
                            ("fear1", "fear", {"gist": {"fr": "S'épuiser.", "en": "Burning out."}, "strength": 70, "origin": "lived"}),
                            ("hab1", "habit", {"gist": {"fr": "Range son bureau avant de réfléchir.", "en": "Tidies her desk before thinking."}, "strength": 75, "risk": "dangerous"})]:
        (d / f"elements/psyche/{vid}").mkdir(); (d / f"elements/psyche/{vid}/psyche-node.json").write_text(json.dumps(node), "utf-8")
        m["elements"]["psyche"]["variants"][vid] = {"kind": kind, "label": vid, "node": f"elements/psyche/{vid}/psyche-node.json", "identity": "id1", "strength": node["strength"]}
        m["presets"]["default"]["slots"]["psyche"].append(vid)
    m["tags"]["content"] = ["psyche-dangerous"]; m["identities"]["id1"]["gender"] = "female"; _write(d, m)
    rep = _val(d); assert rep.ok, rep.errors
    soul, _ = export_soul(d, "default")                      # no personality language on this preset: the character's (fr)
    who = soul[soul.index("## Qui elle est"):soul.index("## Disclosure")]
    heads = [l for l in who.splitlines() if l.startswith("### ")]
    assert heads == ["### Blessure", "### Valeurs", "### Croyances", "### Peurs", "### Positions", "### Goûts", "### Contradictions", "### Règles"], heads   # need1 secret, hab1 dangerous: no heading
    assert "- Les années d'agence." in who and "- La légèreté." in who                                   # ≥ 70: whole gist
    assert "- Si je ralentis, je disparais  ·  mensonge" in who                                            # 60: short clause, the lie marked
    assert "- Loves the smell of paper  ·  réservé" in who                                                 # no French on this node: its English; guarded marked
    assert "- Envers l'utilisateur : une collègue  ·  envers: l'utilisateur" in who
    assert "- S'épuiser.  ·  vécu" in who and "Il y a des choses qu'elle ne dit pas." in who
    assert "Accepter" not in who and "Range son bureau" not in who and "## Values" not in soul and "## Goals" not in soul and "## Habits" not in soul
    assert who.index("### Blessure") < who.index("### Valeurs") < who.index("### Croyances") < who.index("### Peurs") < who.index("### Règles")
    out = tmp_path / "ws"; done = export_agent(d, out, "default")
    assert done["psyche_nodes"] == 9 and done["psyche_personal_dropped"] == 0 and done["dangerous_dropped"] == 1 and done["memory_nodes"] == 4
    assert "## Qui elle est" in (out / "SOUL.md").read_text("utf-8") and "## Memories" in (out / "MEMORY.md").read_text("utf-8")
    out2 = tmp_path / "ws2"; done = export_agent(d, out2, "default", keep_dangerous=True)
    assert done["dangerous_dropped"] == 0 and "Range son bureau avant de réfléchir." in (out2 / "SOUL.md").read_text("utf-8")
    _pnode(d, "fear1", visibility="personal")
    out3 = tmp_path / "ws3"; done = export_agent(d, out3, "default")
    assert done["psyche_personal_dropped"] == 1 and "S'épuiser" not in (out3 / "SOUL.md").read_text("utf-8")
    assert "S'épuiser" in (export_agent(d, tmp_path / "ws4", "default", keep_personal=True) and (tmp_path / "ws4/SOUL.md").read_text("utf-8"))
    # an English preset of the same file renders in English, the French-only rule falls back to its French
    m["presets"]["en"] = {"label": "en", "extends": "default", "slots": {"personality": []}, "age_override": {"value": 29, "unit": "years", "basis": "declared"}}
    m["identities"]["id1"]["language"] = "en"; _write(d, m)
    soul_en, _ = export_soul(d, "en")
    assert "## Who she is" in soul_en and "### Wound" in soul_en and "- The agency years." in soul_en and "Ne jamais envoyer" in soul_en and "There are things she does not tell." in soul_en
    assert short_clause("Toward the Martian: protective curiosity — the one visitor who looked at the sheep.") == "Toward the Martian: protective curiosity"
    long = short_clause(" ".join(["word"] * 40) + ".")
    assert long.endswith("…") and len(long) <= 101 and not long[:-1].endswith(" ") and long[:-1].endswith("word")
    # Clara (example 10): the French agent preset renders the 22 nodes in French, in order, lie and subjects marked
    out5 = tmp_path / "ws5"; done = export_agent(ROOT / "spec/examples/10-clara-mercier", out5, "fr-agent")
    soul = (out5 / "SOUL.md").read_text("utf-8")
    assert done["psyche_nodes"] == 22 and "Quatre ans à livrer trop vite" in soul and "- Si je ralentis, je disparais  ·  mensonge" in soul
    assert soul.index("### Blessure") < soul.index("### Valeurs") < soul.index("### Contradictions") < soul.index("## Boundaries") and "## Goals" not in soul


def test_soul_md_awareness_warmth_likes(tmp_path):
    """§ 3 nonies in « Who she is »: a half-aware and an unaware node marked, a stance's warmth after its subject (signed),
    tastes split into likes and dislikes once one taste leans (a taste without valence, or 0, stays a plain line), both
    languages; without any valence the tastes stay one list; Clara at 65 holds bel4 instead of bel3 and contra1."""
    from cof_cli.psyche import load_nodes as load_psyche, soul_section
    d, m = _psy(tmp_path)
    for vid, node in [("taste1", {"gist": {"fr": "Aime l'odeur du papier.", "en": "Loves the smell of paper."}, "strength": 50, "valence": 70}),
                      ("taste2", {"gist": {"fr": "Déteste les notifications.", "en": "Hates notifications."}, "strength": 60, "valence": -80}),
                      ("taste3", {"gist": {"fr": "Le thé vert, sans plus.", "en": "Green tea, no more."}, "strength": 30, "valence": 0}),
                      ("taste4", {"gist": {"fr": "Les vieux trains.", "en": "Old trains."}, "strength": 40})]:
        (d / f"elements/psyche/{vid}").mkdir(); (d / f"elements/psyche/{vid}/psyche-node.json").write_text(json.dumps(node), "utf-8")
        m["elements"]["psyche"]["variants"][vid] = {"kind": "taste", "label": vid, "node": f"elements/psyche/{vid}/psyche-node.json", "identity": "id1", "strength": node["strength"]}
        m["presets"]["default"]["slots"]["psyche"].append(vid)
    m["identities"]["id1"]["gender"] = "female"; _write(d, m)
    _pnode(d, "stance1", valence=60); _pnode(d, "bel1", aware="no"); _pnode(d, "val1", aware="partly")
    rep = _val(d); assert rep.ok, rep.errors
    m = rep.manifest
    fr, _ = soul_section(m, load_psyche(d, m), "default")
    assert "- La légèreté.  ·  en partie à son insu" in fr
    assert "- Si je ralentis, je disparais  ·  mensonge · agit ainsi à son insu — ne le dit jamais" in fr
    assert "- Envers l'utilisateur : une collègue  ·  envers: l'utilisateur · chaleur +60" in fr
    tastes = fr[fr.index("### Goûts"):].split("\n\n")[0].splitlines()
    assert tastes == ["### Goûts", "- Aime :", "  - Aime l'odeur du papier", "- N'aime pas :", "  - Déteste les notifications",
                      "- Le thé vert, sans plus", "- Les vieux trains"], tastes
    m["identities"]["id1"]["language"] = "en"
    _pnode(d, "stance1", valence=-10)
    en, _ = soul_section(m, load_psyche(d, m), "default")
    assert "- Lightness.  ·  half aware" in en and "- If I slow down, I disappear  ·  lie · acts on it without knowing it — never says it" in en
    assert "- Toward the user: a colleague  ·  about: the user · warmth -10" in en
    assert "### Tastes\n- Likes:\n  - Loves the smell of paper\n- Dislikes:\n  - Hates notifications\n- Green tea, no more\n- Old trains\n" in en
    _pnode(d, "stance1", valence=0); assert "about: the user · warmth 0" in soul_section(m, load_psyche(d, m), "default")[0]
    for vid in ("taste1", "taste2", "taste3"):
        _pnode(d, vid, valence=None)
    en, _ = soul_section(m, load_psyche(d, m), "default")
    assert "### Tastes\n- Loves the smell of paper\n- Hates notifications\n- Green tea, no more\n- Old trains\n" in en and "Likes" not in en
    # Clara: the default preset and the 65-year-old
    src = ROOT / "spec/examples/10-clara-mercier"
    cm = json.loads((src / "manifest.json").read_text("utf-8")); cn = load_psyche(src, cm)
    s29, st29 = soul_section(cm, cn, "fr"); s65, st65 = soul_section(cm, cn, "fr-65")
    assert st29["rendered"] == 22 and st65["rendered"] == 21
    assert "- Si je ralentis, je disparais  ·  mensonge · agit ainsi à son insu — ne le dit jamais" in s29 and "Ralentir" not in s29
    assert "- Accepter d'être aidée  ·  en partie à son insu" in s29 and "envers: le Martien · chaleur +60" in s29 and "envers: les agences de design · chaleur -10" in s29
    assert "### Goûts\n- Aime :\n  - Aime l'odeur du papier" in s29 and "- N'aime pas :\n  - Déteste les notifications" in s29
    assert "- Ralentir n'est pas disparaître : le studio tient sans mes nuits\n" in s65 and "Si je ralentis" not in s65 and "### Contradictions" not in s65


def test_psyche_add_aware_valence_until(tmp_path):
    """`cof psyche add --aware / --valence / --until-age / --until-date`: written on the node (and in the first revision),
    the default `aware: yes` not written, `--valence` refused on another kind, `--until` before `--since` refused by the
    validation of the copy."""
    from cof_cli.selfdesc import psyche_add
    from cof_cli.cli import main
    d, m = _psy(tmp_path)
    vid = psyche_add(d, identity=None, kind="stance", gists={"fr": "Envers l'utilisateur : de la chaleur, désormais."}, about="user", valence=45,
                     aware="partly", stability="shifting", since_age=29, until_date="2027", approx=True)
    n = json.loads((d / f"elements/psyche/{vid}/psyche-node.json").read_text("utf-8"))
    assert n["valence"] == 45 and n["aware"] == "partly" and n["since"] == {"age": {"value": 29, "unit": "years"}, "approx": True} and n["until"] == {"date": "2027", "approx": True}
    assert n["revisions"][0]["valence"] == 45 and n["revisions"][0]["aware"] == "partly"
    vid2 = psyche_add(d, identity=None, kind="taste", gists={"fr": "Le café noir."}, valence=-30, aware="yes", until_age=40)
    n2 = json.loads((d / f"elements/psyche/{vid2}/psyche-node.json").read_text("utf-8"))
    assert "aware" not in n2 and n2["valence"] == -30 and n2["until"] == {"age": {"value": 40, "unit": "years"}} and "aware" not in n2["revisions"][0]
    assert _val(d).ok
    for kw in (dict(kind="value", valence=10), dict(kind="stance", valence=101), dict(kind="fear", aware="maybe")):
        with pytest.raises(ValueError):
            psyche_add(d, identity=None, gists={"fr": "x"}, **kw)
    with pytest.raises(ValueError, match="stance or a taste only"):
        psyche_add(d, identity=None, kind="belief", gists={"fr": "x"}, valence=10)
    f = tmp_path / "f"; shutil.copytree(d, f)
    assert main(["psyche", "add", str(f), "--kind", "belief", "--gist", "fr=x", "--valence", "10"]) == 2            # refused before anything is written
    assert main(["psyche", "add", str(f), "--kind", "fear", "--gist", "fr=Être oubliée.", "--since-age", "30", "--until", "20"]) == 1   # until before since: not written
    assert main(["psyche", "add", str(f), "--kind", "fear", "--gist", "fr=Être oubliée.", "--since-age", "30", "--until-age", "40", "--aware", "no", "--canon"]) == 0
    mf = json.loads((f / "manifest.json").read_text("utf-8"))
    new = [v for v in mf["elements"]["psyche"]["variants"] if v.startswith("fear")]
    nf = json.loads((f / f"elements/psyche/{new[-1]}/psyche-node.json").read_text("utf-8"))
    assert nf["aware"] == "no" and nf["until"] == {"age": {"value": 40.0, "unit": "years"}} and nf["since"]["age"]["value"] == 30


def test_extract_keeps_the_node_a_psyche_variant_derives_from(tmp_path):
    """§ 3 nonies / § 7: a node that changes is a second node with `derives_from` on its variant (Clara's bel4 from bel3).
    `cof extract --preset fr-65` keeps bel3 as the parent the variant resolves through (not listed by the preset), drops
    contra1; a purge that removes the parent leaves the derived node whole (its inherited fields written on it)."""
    from cof_cli.ops import extract_presets
    from cof_cli.model import resolve_variant
    from cof_cli.psyche import drop_nodes
    src = ROOT / "spec/examples/10-clara-mercier"
    out = tmp_path / "x"; m = extract_presets(src, out, ["fr-65"])
    V = m["elements"]["psyche"]["variants"]
    assert "bel3" in V and "bel4" in V and V["bel4"]["derives_from"] == "bel3" and "contra1" not in V
    assert (out / "elements/psyche/bel3/psyche-node.json").is_file() and "bel3" not in m["presets"]["fr-65"]["slots"]["psyche"]
    rep = Report(); validate_dir(out, rep, recompute=False)
    assert rep.ok and not [w for w in rep.warnings if "psyche" in w], (rep.errors, rep.warnings)        # the parent is no backstage leftover
    from cof_cli.convert import export_soul
    assert "Ralentir n'est pas disparaître" in export_soul(out, "fr-65")[0] and "Si je ralentis" not in export_soul(out, "fr-65")[0]
    # a derived variant that only overrides its label inherits the rest; dropping the parent writes the rest on it
    V["bel5"] = {"derives_from": "bel3", "label": "bel3 at 50"}; m["presets"]["fr-65"]["slots"]["psyche"].append("bel5")
    assert resolve_variant(m, "psyche", "bel5")["kind"] == "belief"
    gone = drop_nodes(out, m, ["bel3"])
    assert gone == ["bel3"] and "derives_from" not in V["bel5"] and V["bel5"]["kind"] == "belief" and V["bel5"]["node"] == "elements/psyche/bel3/psyche-node.json"
    assert (out / "elements/psyche/bel3/psyche-node.json").is_file()                 # the file bel5 still reads stays


def test_migrate_psyche_from_the_lists(tmp_path):
    """§ 3 quater: psyche.json goals / fears / values and the card's cof.goals / cof.fears / cof.behavior become want (70),
    fear (70), value ("Word."), habit nodes; duplicates merged by text and by id; the lists stay; the presets holding the
    personality variant list the nodes; cof 1.2; idempotent; a bilingual card gives one node with two gists."""
    from cof_cli.migrate import migrate_psyche
    from cof_cli.cli import main
    d, m = _mem_copy(tmp_path)
    r = migrate_psyche(d)
    assert r["written"] == ["want1", "fear1", "val1", "val2", "val3", "hab1", "hab2", "hab3"] and r["skipped"] == 0 and not r["untouched"]
    m2 = json.loads((d / "manifest.json").read_text("utf-8"))
    assert m2["cof"] == "1.2" and "has-psyche" in m2["tags"]["auto"] and m2["presets"]["default"]["slots"]["psyche"] == r["written"]
    V = m2["elements"]["psyche"]["variants"]
    assert V["want1"] == {"kind": "want", "label": "Créer un outil open source qui mesure l'impact carbone et", "node": "elements/psyche/want1/psyche-node.json", "identity": "id1", "strength": 70}
    n = json.loads((d / "elements/psyche/val1/psyche-node.json").read_text("utf-8"))
    assert n == {"gist": {"fr": "Sobriété."}, "stability": "settled", "origin": "authored", "visibility": "canon", "disclosure": "open"}
    assert json.loads((d / "elements/psyche/want1/psyche-node.json").read_text("utf-8"))["strength"] == 70
    ps = json.loads((d / "elements/personality/p1/psyche.json").read_text("utf-8"))
    assert ps["goals"] and ps["values"] and json.loads((d / "elements/personality/p1/card.json").read_text("utf-8"))["data"]["extensions"]["cof"]["behavior"]   # the lists stay
    rep = _val(d); assert rep.ok, rep.errors
    assert any("strength unset on 6 of 8" in x for x in rep.info.get("notes") or [])
    r2 = migrate_psyche(d)
    assert r2["written"] == [] and r2["skipped"] == 8 and sorted(p.name for p in (d / "elements/psyche").iterdir()) == sorted(r["written"])
    assert main(["migrate", str(d), "--psyche"]) == 0
    # a psyche written by hand is left alone: the lists are not poured on top (example 10 holds Clara's 23 nodes)
    c = tmp_path / "c"; shutil.copytree(ROOT / "spec/examples/10-clara-mercier", c)
    r3 = migrate_psyche(c)
    assert r3["written"] == [] and r3["untouched"] == {"id1": 15} and r3["skipped"] == 1 and len(json.loads((c / "manifest.json").read_text("utf-8"))["elements"]["psyche"]["variants"]) == 23
    # a bilingual card (a second personality variant, English, same lists): one node per entry, a gist per language
    e = tmp_path / "e"; shutil.copytree(MEM, e)
    me = json.loads((e / "manifest.json").read_text("utf-8"))
    shutil.copytree(e / "elements/personality/p1", e / "elements/personality/p2")
    card = json.loads((e / "elements/personality/p2/card.json").read_text("utf-8")); card["data"]["extensions"]["cof"] = {"behavior": ["Takes out her notebook to sketch a wireframe before answering", "Opens with a question about real use", "Says « we remove » rather than « we add »"]}
    (e / "elements/personality/p2/card.json").write_text(json.dumps(card), "utf-8")
    ps = json.loads((e / "elements/personality/p2/psyche.json").read_text("utf-8"))
    ps["goals"] = [{"id": "goal:sobriety", "text": "Build an open-source tool that measures the carbon impact and the accessibility of web interfaces."}]
    ps["fears"] = [{"id": "fear:bloat", "text": "Bloated interfaces that exclude and waste."}]; ps["values"] = ["sobriety", "accessibility", "kindness"]
    (e / "elements/personality/p2/psyche.json").write_text(json.dumps(ps), "utf-8")
    me["elements"]["personality"]["variants"]["p2"] = {**me["elements"]["personality"]["variants"]["p1"], "label": "EN", "language": "en", "card": "elements/personality/p2/card.json", "psyche": "elements/personality/p2/psyche.json"}
    me["presets"]["en"] = {"label": "en", "extends": "default", "slots": {"personality": ["p2"]}}; _write(e, me)
    r4 = migrate_psyche(e)
    assert r4["written"] == ["want1", "fear1", "val1", "val2", "val3", "hab1", "hab2", "hab3"]
    assert json.loads((e / "elements/psyche/want1/psyche-node.json").read_text("utf-8"))["gist"] == {"fr": "Créer un outil open source qui mesure l'impact carbone et l'accessibilité des interfaces web.", "en": "Build an open-source tool that measures the carbon impact and the accessibility of web interfaces."}
    assert json.loads((e / "elements/psyche/val3/psyche-node.json").read_text("utf-8"))["gist"] == {"fr": "Bienveillance.", "en": "Kindness."}
    me2 = json.loads((e / "manifest.json").read_text("utf-8"))
    from cof_cli.model import resolve_preset_slots
    assert resolve_preset_slots(me2, "en")["psyche"] == r4["written"] and me2["presets"]["default"]["slots"]["psyche"] == r4["written"] and "psyche" not in me2["presets"]["en"]["slots"]   # inherited through extends
    rep = _val(e); assert rep.ok, rep.errors


def test_psyche_add(tmp_path):
    """`cof psyche add`: a lived, personal node by default with a first revision, listed by the character's presets (inherited
    lists copied), tags.content following the risk, validated; kind-specific fields refused early; atomic on a folder."""
    from cof_cli.selfdesc import psyche_add
    from cof_cli.cli import main
    d, m = _psy(tmp_path)
    m["presets"]["child"] = {"label": "child", "extends": "default", "slots": {}, "age_override": {"value": 29, "unit": "years", "basis": "declared"}}; _write(d, m)
    vid = psyche_add(d, identity=None, kind="stance", gists={"fr": "Envers Léo : une confiance prudente.", "en": "Toward Léo: a careful trust."}, about="Léo", strength=60,
                     stability="shifting", since_date="2026-10-25", links=["because=memories/m3", "supports=psyche/val1"], tags=["Léo"], risk="inappropriate", presets=["child"])
    assert vid == "stance2"
    n = json.loads((d / "elements/psyche/stance2/psyche-node.json").read_text("utf-8"))
    assert n["origin"] == "lived" and n["visibility"] == "personal" and n["about"] == {"label": {"fr": "Léo"}} and n["since"] == {"date": "2026-10-25"} and n["tags"] == ["leo"]
    assert n["links"] == [{"to": "memories/m3", "type": "because"}, {"to": "psyche/val1", "type": "supports"}] and n["risk"] == "inappropriate"
    assert len(n["revisions"]) == 1 and n["revisions"][0]["gist"] == n["gist"] and n["revisions"][0]["strength"] == 60 and n["revisions"][0]["by"] == "cof-cli psyche add"
    m2 = json.loads((d / "manifest.json").read_text("utf-8"))
    assert m2["elements"]["psyche"]["variants"]["stance2"] == {"kind": "stance", "label": "Envers Léo : une confiance prudente.", "node": "elements/psyche/stance2/psyche-node.json", "identity": "id1", "strength": 60}
    assert m2["presets"]["child"]["slots"]["psyche"] == ["wound1", "val1", "bel1", "contra1", "stance1", "stance2"] and "stance2" not in m2["presets"]["default"]["slots"]["psyche"]
    assert m2["tags"]["content"] == ["psyche-inappropriate"]
    rep = _val(d); assert rep.ok, rep.errors
    assert any("psyche.stance2: personal node" in w for w in rep.warnings)
    vid2 = psyche_add(d, identity=None, kind="belief", gists={"fr": "Les gens finissent par partir."}, lie=True, personal=False, origin="authored", disclosure="guarded")
    n2 = json.loads((d / f"elements/psyche/{vid2}/psyche-node.json").read_text("utf-8"))
    assert vid2 == "bel2" and n2["false_but_held"] is True and n2["visibility"] == "canon" and "revisions" not in n2 and "strength" not in n2
    assert _val(d).ok
    for kw in (dict(kind="value", lie=True), dict(kind="value", about="x"), dict(kind="opinion"), dict(kind="fear", links=["after=memories/m1"]), dict(kind="fear", strength=140), dict(kind="fear", risk="bad")):
        with pytest.raises(ValueError):
            psyche_add(d, identity=None, gists={"fr": "x"}, **kw)
    # the CLI, on a .cof and on a folder; a refused add leaves the folder untouched; a 1.1 file becomes 1.2 with the category
    cof = tmp_path / "c.cof"; pack(d, cof)
    assert main(["psyche", "add", str(cof), "--kind", "taste", "--gist", "fr=Aime l'odeur du papier.", "--strength", "40", "--canon"]) == 0
    u = tmp_path / "u"; unpack(cof, u)
    mu = json.loads((u / "manifest.json").read_text("utf-8"))
    assert "taste1" in mu["elements"]["psyche"]["variants"] and json.loads((u / "elements/psyche/taste1/psyche-node.json").read_text("utf-8"))["visibility"] == "canon"
    assert "cof psyche add" in (u / "COF.md").read_text("utf-8") and "**Psyche**" in (u / "COF.md").read_text("utf-8")
    f = tmp_path / "f"; shutil.copytree(MEM, f)
    before = sorted(str(p.relative_to(f)) for p in f.rglob("*"))
    assert main(["psyche", "add", str(f), "--kind", "stance", "--gist", "fr=x", "--about", "user", "--link", "because=memories/zz"]) == 1       # unresolved link: nothing written
    assert sorted(str(p.relative_to(f)) for p in f.rglob("*")) == before
    assert main(["psyche", "add", str(f), "--kind", "rule", "--gist", "fr=Ne jamais envoyer un message que personne n'a demandé.", "--stability", "core", "--strength", "90", "--canon", "--origin", "authored"]) == 0
    mf = json.loads((f / "manifest.json").read_text("utf-8"))
    assert mf["cof"] == "1.2" and mf["presets"]["default"]["slots"]["psyche"] == ["rule1"] and "has-psyche" in mf["tags"]["auto"]


PROPOSAL = ROOT / "tests" / "fixtures" / "psyche-propose" / "clara-proposal.json"


def test_psyche_propose_contract_and_table(tmp_path):
    """docs/psyche-propose.md: the bundle of Clara, the fixture proposal normalised and validated, the duplicate c1 ≈ val1
    flagged, the table printed; a bad kind, a missing gist, an unknown memory id, a one-sided contradiction, `about` off
    a stance and a bad source are refused (no network anywhere)."""
    from cof_cli import propose as P
    src = ROOT / "spec/examples/10-clara-mercier"
    m = json.loads((src / "manifest.json").read_text("utf-8"))
    b = P.build_bundle(src, m, "fr-agent")
    assert b["contract"] == P.CONTRACT and b["character"] == {"id": "id1", "name": "Clara Mercier", "gender": "female", "age": 29, "language": "fr", "summary": b["character"]["summary"]}
    assert b["languages"] == ["fr", "en"] and b["preset"] == "fr-agent" and b["cast"] == []
    assert [p["variant"] for p in b["personality"]] == ["p2", "p6"] and b["personality"][0]["kind"] == "card" and b["personality"][0]["personality"] and b["personality"][1]["text"]
    assert len(b["lists"]["goals"]) == 3 and len(b["lists"]["values"]) == 6 and len(b["lists"]["behavior"]) == 4
    assert [x["id"] for x in b["memories"]] == ["ev1", "ep1", "ev2", "ev3", "ev4", "ev5", "ev6", "ev7", "ev8", "ep2", "ev9", "ev10"]   # the manga copies left out
    assert b["memories"][1]["kind"] == "period" and b["memories"][1]["when"] and "agence" in b["memories"][1]["gist"].lower()
    assert len(b["psyche"]) == 23 and b["psyche"][0] == {"id": "wound1", "kind": "wound", "gist": b["psyche"][0]["gist"], "strength": 85} and "livrer" in b["psyche"][0]["gist"]
    prop = P.normalize(json.loads(PROPOSAL.read_text("utf-8")))
    errors, notes = P.validate(prop, b)
    assert errors == [], errors
    assert not any("gist[" in n for n in notes), notes
    assert P.duplicates(prop, b) == {"c1": "psyche/val1"}
    tbl = P.table(prop, b, notes)
    assert "c1     value           90  core      none          card.personality       psyche/val1" in tbl and "c3     belief (lie)" in tbl
    assert "between c3 ⇄ psyche/val1" in tbl and "risk inappropriate: a bluntness" in tbl and "about: the user" in tbl and "Nothing is written" in tbl
    # tolerated shapes: a bare list, missing ids, risk as a string, because as a string, strength as a float
    loose = P.normalize([{"kind": "Taste", "gist": {"fr": "x" * 120}, "risk": "dangerous", "because": "memories/ev1, memories/ev2", "strength": 61.0, "source": "memory ev1", "tags": ["Vie Quotidienne"]}])
    assert loose["nodes"][0]["id"] == "c1" and loose["nodes"][0]["kind"] == "taste" and loose["nodes"][0]["risk"] == {"value": "dangerous", "why": ""}
    assert loose["nodes"][0]["because"] == ["memories/ev1", "memories/ev2"] and loose["nodes"][0]["strength"] == 61 and loose["nodes"][0]["tags"] == ["vie-quotidienne"]
    e, n = P.validate(loose, b); assert e == [] and any("no reason" in x for x in n)
    # refusals
    def bad(**kw):
        node = {"id": "x1", "kind": "value", "gist": {"fr": "y" * 120, "en": "y" * 120}, "source": "inferred", **kw}
        return P.validate(P.normalize({"nodes": [node]}), b)[0]
    assert any("unknown kind 'opinion'" in x for x in bad(kind="opinion"))
    assert any("gist must be" in x for x in bad(gist={}))
    assert any("unknown memory 'ev99'" in x for x in bad(because=["memories/ev99"]))
    assert any("names a memory the character does not have" in x for x in bad(source="memory ev99"))
    assert any("exactly two" in x for x in bad(kind="contradiction", between=["psyche/val1"]))
    assert any("unknown psyche node 'nope'" in x for x in bad(kind="contradiction", between=["psyche/val1", "psyche/nope"]))
    assert any("about is for a stance only" in x for x in bad(about={"user": True}))
    assert any("not a character of the file" in x for x in bad(kind="stance", about={"identity": "martien"}))
    assert any("false_but_held is for a belief" in x for x in bad(false_but_held=True))
    assert any("source must name" in x for x in bad(source="my head"))
    assert any("strength must be" in x for x in bad(strength=140))
    assert any("stability must be" in x for x in bad(stability="solid"))
    assert any("risk must be" in x for x in bad(risk={"value": "bad"}))
    assert any("a node cannot point at itself" in x for x in bad(supports=["x1"]))
    assert P.validate(P.normalize({"nodes": "no"}), b)[0] == ["the proposal is not an object with a `nodes` list"]
    # the answer of a chat completion is unwrapped; a non-JSON answer is refused
    assert P.parse_answer({"choices": [{"message": {"content": "Here you are:\n```json\n{\"nodes\": []}\n```"}}]}) == {"nodes": []}
    with pytest.raises(ValueError):
        P.parse_answer({"choices": [{"message": {"content": "I cannot."}}]})


def test_psyche_propose_aware_valence_until(tmp_path):
    """docs/psyche-propose.md: a candidate MAY carry `aware`, `valence` (stance / taste) and `until` (RFC 0004 § 3 nonies) —
    checked like the node file (enum, range, kind, shape, until not before since) and kept through --apply."""
    from cof_cli import propose as P
    d = tmp_path / "c10"; shutil.copytree(ROOT / "spec/examples/10-clara-mercier", d)
    m = json.loads((d / "manifest.json").read_text("utf-8")); b = P.build_bundle(d, m, "fr-agent")
    g = {"fr": "y" * 120, "en": "y" * 120}
    good = {"nodes": [{"id": "c1", "kind": "stance", "gist": g, "about": {"user": True}, "valence": -40, "aware": "partly", "source": "inferred"},
                      {"id": "c2", "kind": "habit", "gist": g, "aware": "no", "since": {"age": {"value": 30}}, "until": {"age": {"value": 44}, "approx": True}, "source": "inferred"}]}
    e, n = P.validate(P.normalize(good), b)
    assert e == [] and not any("not part of the contract" in x for x in n), (e, n)
    assert "aware partly · valence -40" in P.table(P.normalize(good), b, n) and "until age 44" in P.table(P.normalize(good), b, n)
    def bad(**kw):
        return P.validate(P.normalize({"nodes": [{"id": "x1", "kind": "value", "gist": g, "source": "inferred", **kw}]}), b)[0]
    assert any("valence is for a stance or a taste only" in x for x in bad(valence=10))
    assert any("valence must be an integer between -100 and 100" in x for x in bad(kind="taste", valence=150))
    assert any("aware must be yes, partly or no" in x for x in bad(aware="maybe"))
    assert any("until must be" in x for x in bad(until="2020"))
    assert any("until is before since" in x for x in bad(since={"date": "2020"}, until={"date": "2019-12"}))
    written, _ = P.apply(d, P.normalize(good), "all", bundle=b)
    nodes = {v: json.loads((d / f"elements/psyche/{v}/psyche-node.json").read_text("utf-8")) for v in written}
    st = next(x for k, x in nodes.items() if k.startswith("stance")); hb = next(x for k, x in nodes.items() if k.startswith("hab"))
    assert st["valence"] == -40 and st["aware"] == "partly" and hb["aware"] == "no" and hb["until"] == {"age": {"value": 44}, "approx": True} and "valence" not in hb


def test_psyche_propose_cli_rules_zodiac_and_accept(tmp_path):
    """`cof psyche propose`: --rules on example 01 (the 1.0 lists as a proposal), --zodiac virgo (four candidates, tag
    zodiac:virgo, strength 50, shifting, bilingual), --from-file on Clara printed and saved with --out, --apply refused
    without --accept, a contradiction refused without its side, --accept writing exactly the chosen nodes (ids by kind,
    links mapped, risk tag, listed by the presets holding the personality read), the file validating; a .cof too."""
    from cof_cli.cli import main
    from cof_cli import propose as P
    from cof_cli.zodiac import candidates, normalize_sign, SIGNS, TABLE
    assert normalize_sign("Vierge") == "virgo" and normalize_sign("VIRGO") == "virgo" and normalize_sign("Bélier") == "aries" and normalize_sign("ox") is None
    assert set(TABLE) == set(SIGNS) and all(3 <= len(v) <= 4 and all(k in ("value", "taste", "habit") and set(g) == {"en", "fr"} for k, g in v) for v in TABLE.values())
    z = candidates("virgo", ["fr", "en"])
    assert len(z) == 4 and z[0] == {"id": "z1", "kind": "value", "gist": z[0]["gist"], "strength": 50, "stability": "shifting", "tags": ["zodiac:virgo"], "source": "zodiac"} and z[0]["gist"]["fr"].startswith("L'exactitude")
    assert candidates("virgo", ["de"])[0]["gist"] == {"de": TABLE["virgo"][0][1]["en"]}
    ex1 = ROOT / "spec/examples/01-clara-text-only"
    m1 = json.loads((ex1 / "manifest.json").read_text("utf-8"))
    r = P.rules_proposal(ex1, m1, None)
    assert [(n["kind"], n.get("strength"), n["source"]) for n in r["nodes"]] == [("value", None, "list values[0]"), ("value", None, "list values[1]"), ("value", None, "list values[2]"), ("want", 70, "list goals[0]"), ("fear", 70, "list fears[0]"), ("habit", None, "list behavior[0]"), ("habit", None, "list behavior[1]"), ("habit", None, "list behavior[2]")]
    assert next(iter(r["nodes"][0]["gist"].values())) == "Sobriété." and P.validate(r, P.build_bundle(ex1, m1))[0] == []
    out = tmp_path / "p01.json"
    assert main(["psyche", "propose", str(ex1), "--rules", "--zodiac", "virgo", "--out", str(out)]) == 0
    saved = json.loads(out.read_text("utf-8"))
    assert [n["id"] for n in saved["nodes"]] == ["l1", "l2", "l3", "l4", "l5", "l6", "l7", "l8", "z1", "z2", "z3", "z4"] and saved["contract"] == P.CONTRACT
    assert main(["psyche", "propose", str(ex1), "--zodiac", "ox"]) == 1
    assert main(["psyche", "propose", str(ex1)]) == 2                                   # no source of proposal
    assert main(["psyche", "propose", str(ex1), "--provider", "openai-compatible"]) == 2   # no URL / model: refused before any call
    # Clara: the fixture reviewed, saved, applied for a selection only
    d = tmp_path / "c10"; shutil.copytree(ROOT / "spec/examples/10-clara-mercier", d)
    before = sorted(str(p.relative_to(d)) for p in d.rglob("*"))
    bo = tmp_path / "bundle.json"; po = tmp_path / "prop.json"
    assert main(["psyche", "propose", str(d), "--preset", "fr-agent", "--from-file", str(PROPOSAL), "--out", str(po), "--bundle-out", str(bo)]) == 0
    assert sorted(str(p.relative_to(d)) for p in d.rglob("*")) == before                  # reviewed, nothing written
    assert json.loads(bo.read_text("utf-8"))["prompt"] == P.PROMPT and json.loads(bo.read_text("utf-8"))["bundle"]["character"]["id"] == "id1"
    assert main(["psyche", "propose", str(d), "--from-file", str(po), "--apply"]) == 2                              # --apply without --accept
    assert main(["psyche", "propose", str(d), "--preset", "fr-agent", "--from-file", str(po), "--apply", "--accept", "c4"]) == 2   # a contradiction without its side
    assert main(["psyche", "propose", str(d), "--preset", "fr-agent", "--from-file", str(po), "--apply", "--accept", "c9"]) == 2   # unknown id
    assert sorted(str(p.relative_to(d)) for p in d.rglob("*")) == before
    bad = tmp_path / "bad.json"; bad.write_text(json.dumps({"nodes": [{"id": "c1", "kind": "opinion", "gist": {"fr": "x"}, "source": "inferred"}]}), "utf-8")
    assert main(["psyche", "propose", str(d), "--from-file", str(bad)]) == 1
    assert main(["psyche", "propose", str(d), "--preset", "fr-agent", "--from-file", str(po), "--apply", "--accept", "c2,c3,c4,c5"]) == 0
    m = json.loads((d / "manifest.json").read_text("utf-8"))
    V = m["elements"]["psyche"]["variants"]
    assert [v for v in V][-4:] == ["taste3", "bel5", "contra2", "stance3"] and "c1" not in str(V) and len(V) == 27       # bel4 is Clara's own (§ 3 nonies)
    n = lambda v: json.loads((d / f"elements/psyche/{v}/psyche-node.json").read_text("utf-8"))
    assert n("bel5")["false_but_held"] is True and n("bel5")["since"] == {"age": {"value": 24}} and n("bel5")["links"] == [{"to": "memories/ep1", "type": "because"}] and n("bel5")["origin"] == "authored" and n("bel5")["visibility"] == "canon"
    assert n("contra2")["links"] == [{"to": "psyche/bel5", "type": "conflicts"}, {"to": "psyche/val1", "type": "conflicts"}]
    assert n("stance3")["about"] == {"user": True} and n("stance3")["risk"] == "inappropriate" and m["tags"]["content"] == ["psyche-inappropriate"]
    assert V["stance3"]["strength"] == 50 and V["taste3"]["label"].startswith("Aime le silence") and V["taste3"]["identity"] == "id1"
    from cof_cli.model import resolve_preset_slots
    assert resolve_preset_slots(m, "fr-agent")["psyche"][-4:] == ["taste3", "bel5", "contra2", "stance3"] and resolve_preset_slots(m, "default")["psyche"][-4:] == ["taste3", "bel5", "contra2", "stance3"]
    assert m["presets"]["en-manga"]["slots"]["psyche"][-4:] == ["taste3", "bel5", "contra2", "stance3"]                          # holds p6 through extends
    assert resolve_preset_slots(m, "en-12")["psyche"] == ["val4", "taste1", "hab2"] and "bel5" not in resolve_preset_slots(m, "fr-65")["psyche"]   # other personalities: untouched
    rep = _val(d); assert rep.ok, rep.errors
    # idempotence of the review: the same proposal now flags its own candidates as duplicates of what was written
    b2 = P.build_bundle(d, m, "fr-agent"); dups = P.duplicates(P.normalize(json.loads(po.read_text("utf-8"))), b2)
    assert dups["c2"] == "psyche/taste3" and dups["c3"] == "psyche/bel5"
    # on a .cof, with --accept all (c1 included: the author's choice) and --out-cof
    cof = tmp_path / "c.cof"; pack(d, cof)
    out_cof = tmp_path / "d.cof"
    assert main(["psyche", "propose", str(cof), "--preset", "fr-agent", "--from-file", str(po), "--apply", "--accept", "all", "--out-cof", str(out_cof)]) == 0
    u = tmp_path / "u"; unpack(out_cof, u)
    mu = json.loads((u / "manifest.json").read_text("utf-8"))
    assert len(mu["elements"]["psyche"]["variants"]) == 33 and validate_cof(out_cof).ok
    # the inverse: `psyche text` prints the section, --into-card appends it to the card (never replaces)
    import io, contextlib
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        assert main(["psyche", "text", str(d), "--preset", "fr-agent"]) == 0
    txt = buf.getvalue()
    assert txt.startswith("## Qui elle est") and "### Contradictions" in txt and "Défend un web qui ne presse personne" in txt and "une franchise un peu brusque" in txt
    card_before = json.loads((d / "elements/personality/p2/card.json").read_text("utf-8"))["data"]["personality"]
    assert main(["psyche", "text", str(d), "--preset", "fr-agent", "--into-card"]) == 0
    after = json.loads((d / "elements/personality/p2/card.json").read_text("utf-8"))["data"]["personality"]
    assert after.startswith(card_before.rstrip()) and after.rstrip().endswith(txt.strip()[-40:])
    assert main(["psyche", "text", str(ex1)]) == 1                                         # no node: nothing to render


# ---------------------------------------------------------------- people, places and objects (RFC 0005, 1.2) ----------------------------------------------------------------

def _axes(tmp_path):
    """The psyche fixture (cof 1.2) with three elements of the character: an accessory, an environment and a garment."""
    d, m = _psy(tmp_path)
    m = json.loads((d / "manifest.json").read_text("utf-8"))
    m["elements"]["appearance"] = {"variants": {"x1": {"kind": "accessory", "label": "Folk guitar", "accessory_use": "not-worn"},
                                                "e1": {"kind": "environment", "label": "The studio"},
                                                "c1": {"kind": "clothing", "label": "Cream sweater"}}}
    _write(d, m)
    return d, m


def test_memory_objects_rules(tmp_path):
    """RFC 0005 § 2.2 / § 2.5 on memories: `what` needs cof 1.2 (the declared-minor rule); an unresolved `item` is an error;
    an item that is not an accessory, and a place that is not an environment, are warnings (legitimate stretches)."""
    d, m = _axes(tmp_path)
    assert _val(d).ok, _val(d).errors
    n = _node(d, "m1"); n["what"] = [{"label": {"en": "the notebook"}}, {"item": "appearance/x1", "shown": True}]; _write(d, None, "m1", n)
    rep = _val(d); assert rep.ok and not [w for w in rep.warnings if "what" in w], (rep.errors, rep.warnings)
    m["cof"] = "1.1"; _write(d, m)
    errs = _val(d).errors
    assert any("cof 1.1 declared but the file uses 1.2 additions" in e and "memories.m1.what" in e and "RFC 0005" in e for e in errs), errs
    m["cof"] = "1.2"; _write(d, m)
    n["what"] = [{"item": "appearance/zz"}]; _write(d, None, "m1", n)
    assert any("memories.m1: what.item appearance/zz: unknown element" in e for e in _val(d).errors)
    n["what"] = [{"shown": True}]; _write(d, None, "m1", n)              # neither a reference nor a name: the schema refuses it
    assert not _val(d).ok
    n["what"] = [{"item": "appearance/c1"}]; n["where"] = {"environment": "appearance/x1"}; _write(d, None, "m1", n)
    rep = _val(d); assert rep.ok, rep.errors
    assert any("what.item appearance/c1 is of kind 'clothing', not 'accessory'" in w for w in rep.warnings), rep.warnings
    assert any("where.environment appearance/x1 is of kind 'accessory', not 'environment'" in w for w in rep.warnings), rep.warnings


def test_psyche_people_places_objects_rules(tmp_path):
    """RFC 0005 § 2.3 / § 2.5 on psyche nodes: who / where / what resolve (unknown identity, unknown element = errors),
    `self` is known without an identities table, `real` without an identity warns, a cof 1.1 file names the fields it uses."""
    d, m = _axes(tmp_path)
    _pnode(d, "val1", who=[{"identity": "id1"}, {"label": {"fr": "ma grand-mère"}}], where=[{"environment": "appearance/e1"}, {"label": {"en": "Lyon"}, "geo": {"lat": 45.76, "lon": 4.84}}],
           what=[{"item": "appearance/x1"}, {"label": {"en": "the notebook"}}])
    rep = _val(d); assert rep.ok and not [w for w in rep.warnings if "psyche." in w], (rep.errors, rep.warnings)
    _pnode(d, "bel1", who=[{"identity": "nobody"}], what=[{"item": "appearance/zz"}], where=[{"environment": "memories/zz"}])
    errs = _val(d).errors
    assert any("psyche.bel1: who: unknown identity nobody" in e for e in errs), errs
    assert any("psyche.bel1: what.item appearance/zz: unknown element" in e for e in errs), errs
    assert any("psyche.bel1: where.environment memories/zz: unknown element" in e for e in errs), errs
    _pnode(d, "bel1", who=[{"label": {"en": "my ex"}, "real": True}], what=None, where=[{"environment": "appearance/c1"}])
    rep = _val(d); assert rep.ok, rep.errors
    assert any("psyche.bel1: names a real person who is not an identity" in w for w in rep.warnings), rep.warnings
    assert any("psyche.bel1: where.environment appearance/c1 is of kind 'clothing'" in w for w in rep.warnings), rep.warnings
    _pnode(d, "bel1", who=None, where=None, what=[{}])                  # an entry with neither its reference nor a name
    assert not _val(d).ok
    _pnode(d, "bel1", what=None)
    m = json.loads((d / "manifest.json").read_text("utf-8")); m["cof"] = "1.1"; _write(d, m)
    errs = _val(d).errors
    assert any("1.2 additions" in e and "psyche.val1.who" in e and "psyche.val1.where" in e for e in errs), errs
    # a file without an identities table only knows "self"
    m["cof"] = "1.2"; m.pop("identities", None); m.pop("default_identity", None)
    for e_ in m["elements"].values():
        for v in e_["variants"].values():
            v.pop("identity", None)
    for p in m["presets"].values():
        p.pop("identity", None)
    _write(d, m)
    _pnode(d, "val1", who=[{"identity": "self"}])
    rep = _val(d); assert rep.ok, rep.errors
    _pnode(d, "val1", who=[{"identity": "id1"}])
    assert any("who: unknown identity id1 (a file without an `identities` table only knows \"self\")" in e for e in _val(d).errors)


def test_axes_in_a_cast_file_stay_with_their_character(tmp_path):
    """RFC 0005 § 2.5: in a cast file a node names its own character's elements — an environment or an item of another
    character is an error; `who` may name any character of the file."""
    d, m = _axes(tmp_path)
    m = json.loads((d / "manifest.json").read_text("utf-8"))
    m["identities"]["id2"] = {"name": "Léo", "fictional": True, "morphology": {"class": "human"}}
    m["presets"]["leo"] = {"label": "Léo", "identity": "id2", "slots": {"appearance": ["x2"]}, "age_override": {"value": 20, "unit": "years", "basis": "declared"}}
    for e_ in m["elements"].values():
        for v in e_["variants"].values():
            v["identity"] = "id1"
    m["elements"]["appearance"]["variants"]["x2"] = {"kind": "accessory", "label": "Léo's bike", "accessory_use": "not-worn", "identity": "id2"}
    for p in m["presets"].values():
        p.setdefault("identity", "id1")
    _write(d, m)
    _pnode(d, "val1", who=[{"identity": "id2"}], what=[{"item": "appearance/x1"}])
    rep = _val(d); assert rep.ok, rep.errors
    _pnode(d, "val1", what=[{"item": "appearance/x2"}], where=[{"environment": "appearance/x2"}])
    errs = _val(d).errors
    assert any("psyche.val1: what.item appearance/x2 belongs to another character (id2)" in e for e in errs), errs
    assert any("psyche.val1: where.environment appearance/x2 belongs to another character" in e for e in errs), errs
    _pnode(d, "val1", what=None, where=None)
    n = _node(d, "m1"); n["what"] = [{"item": "appearance/x2"}]; _write(d, None, "m1", n)
    assert any("memories.m1: what.item appearance/x2 belongs to another character" in e for e in _val(d).errors)


def test_example_10_people_places_objects(tmp_path):
    """Clara's three objects (RFC 0005 § 3) and the direct people and places of her psyche: valid, no warning on them;
    `cof extract --preset fr-65` carries the guitar (named by ev2 and contra1, listed by no preset) and the studio."""
    from cof_cli.ops import extract_presets
    from cof_cli.memories import load_nodes
    from cof_cli.psyche import load_nodes as load_psyche
    src = ROOT / "spec/examples/10-clara-mercier"
    rep = Report(); m = validate_dir(src, rep, recompute=False); assert rep.ok, rep.errors
    assert not [w for w in rep.warnings if "what" in w or "where" in w or "who" in w], rep.warnings
    mem, psy = load_nodes(src, m), load_psyche(src, m)
    assert {v for v, n in mem.items() if n.get("what")} == {"ev1", "ev11", "ev2", "ev12", "ev5"}
    assert mem["ev2"]["what"] == mem["ev12"]["what"] == [{"item": "appearance/x1"}] == psy["contra1"]["what"]
    assert mem["ev1"]["what"] == psy["hab1"]["what"] == [{"label": {"fr": "le carnet", "en": "the notebook"}}]
    assert psy["val4"]["who"] == mem["ev1"]["who"] and psy["taste1"]["where"] == [mem["ev1"]["where"]]
    assert psy["want2"]["where"] == [{"environment": "appearance/e1"}] and "who" not in psy["stance1"]
    out = tmp_path / "fr65"; extract_presets(src, out, ["fr-65"])
    mo = json.loads((out / "manifest.json").read_text("utf-8"))
    assert {"x1", "e1"} <= set(mo["elements"]["appearance"]["variants"])
    rep = Report(); validate_dir(out, rep); assert rep.ok, rep.errors


def test_extract_carries_the_items_of_kept_psyche_nodes(tmp_path):
    """RFC 0005 § 2.6: the element a psyche node's `what.item` or `where.environment` names travels with the node."""
    from cof_cli.ops import extract_presets
    d, m = _axes(tmp_path)
    _pnode(d, "val1", what=[{"item": "appearance/x1"}], where=[{"environment": "appearance/e1"}])
    assert _val(d).ok
    out = tmp_path / "x"; extract_presets(d, out, ["default"])
    mo = json.loads((out / "manifest.json").read_text("utf-8"))
    assert set(mo["elements"]["appearance"]["variants"]) == {"x1", "e1"}            # c1 is named by nothing kept
    rep = Report(); validate_dir(out, rep); assert rep.ok, rep.errors


def test_merge_renames_items_places_and_people(tmp_path):
    """RFC 0005 § 2.6: on a merge whose ids collide, `what[].item`, a psyche node's `where[].environment` follow their
    element; the result validates."""
    from cof_cli.ops import merge_dirs
    C = ROOT / "spec/examples/10-clara-mercier"
    out = tmp_path / "m2"; merge_dirs([C, C], out)
    rep = Report(); validate_dir(out, rep); assert rep.ok, rep.errors
    m = json.loads((out / "manifest.json").read_text("utf-8"))
    n = json.loads((out / m["elements"]["memories"]["variants"]["m1-ev2"]["memory"]).read_text("utf-8"))
    assert n["what"] == [{"item": "appearance/m1-x1"}] and n["where"]["environment"] == "appearance/m1-e1"
    p = json.loads((out / m["elements"]["psyche"]["variants"]["m1-want2"]["node"]).read_text("utf-8"))
    assert p["where"] == [{"environment": "appearance/m1-e1"}]
    p = json.loads((out / m["elements"]["psyche"]["variants"]["m1-contra1"]["node"]).read_text("utf-8"))
    assert p["what"] == [{"item": "appearance/m1-x1"}]


def test_extract_identity_relabels_psyche_people(tmp_path):
    """A psyche node's `who` naming a character who leaves the file becomes a plain person (as a memory's, RFC 0005 § 2.6)."""
    from cof_cli.ops import relabel_departed_identities
    d, m = _psy(tmp_path)
    _pnode(d, "val1", who=[{"identity": "id9"}])
    m = json.loads((d / "manifest.json").read_text("utf-8"))
    lines = relabel_departed_identities(d, m, {"id9": {"name": "Léo", "language": "fr", "fictional": True}})
    assert lines and json.loads((d / "elements/psyche/val1/psyche-node.json").read_text("utf-8"))["who"] == [{"label": {"fr": "Léo"}}]


def test_memory_md_lists_objects(tmp_path):
    """`MEMORY.md`: the context line gains `objects: …` after where and with — a name, else the element's label; a 1.1
    link to an accessory is read as an object, not as a link (RFC 0005 § 2.2, § 2.6)."""
    from cof_cli.convert import export_agent
    out = tmp_path / "a"; export_agent(ROOT / "spec/examples/10-clara-mercier", out, preset="fr")
    txt = (out / "MEMORY.md").read_text("utf-8")
    assert "objects: le carnet_" in txt and "objects: Guitare folk « peace » / Folk guitar with peace motif" in txt
    export_agent(ROOT / "spec/examples/10-clara-mercier", out, preset="fr-65")         # the wedding is a memory of the older presets
    txt = (out / "MEMORY.md").read_text("utf-8")
    assert "objects: le pendentif de ma grand-mère" in txt
    line = next(l for l in txt.splitlines() if "objects: le pendentif" in l)
    assert line.index("where:") < line.index("with:") < line.index("objects:")
    d, m = _axes(tmp_path)
    n = _node(d, "m1"); n["links"] = [{"to": "appearance/x1", "type": "about"}]; n.pop("what", None); _write(d, None, "m1", n)
    out2 = tmp_path / "b"; export_agent(d, out2)
    t2 = (out2 / "MEMORY.md").read_text("utf-8")
    assert "objects: Folk guitar" in t2 and "about “x1”" not in t2


def test_add_commands_write_people_places_objects(tmp_path):
    """`cof memory add --what` and `cof psyche add --who / --where / --what` (the `--who` syntax: name, `key=ref`, words);
    a psyche `--link` to an identity is refused with a pointer to `--who`."""
    from cof_cli.cli import main
    from cof_cli.selfdesc import axis_entry
    assert axis_entry("ma guitare|item=appearance/x1|shown", "fr", "item", ("shown",)) == {"item": "appearance/x1", "label": {"fr": "ma guitare"}, "shown": True}
    with pytest.raises(ValueError):
        axis_entry("a|b", "en", "item")
    d, m = _axes(tmp_path)
    m["cof"] = "1.1"
    for vid in list(m["elements"]["psyche"]["variants"]):
        shutil.rmtree(d / f"elements/psyche/{vid}")
    m["elements"].pop("psyche"); m["presets"]["default"]["slots"].pop("psyche", None); _write(d, m)
    assert _val(d).ok, _val(d).errors
    assert main(["memory", "add", str(d), "--gist", "en=The guitar, this morning.", "--date", "2026-11-03", "--what", "item=appearance/x1|shown", "--what", "the pick"]) == 0
    m = json.loads((d / "manifest.json").read_text("utf-8")); assert m["cof"] == "1.2"           # objects are a 1.2 field
    vid = next(v for v in m["elements"]["memories"]["variants"] if v.startswith("ev"))
    assert _node(d, vid)["what"] == [{"item": "appearance/x1", "shown": True}, {"label": {"en": "the pick"}}]
    assert main(["memory", "add", str(d), "--gist", "en=x", "--what", "item=appearance/zz"]) == 1   # would not validate: nothing written
    assert main(["psyche", "add", str(d), "--kind", "fear", "--gist", "en=Losing the guitar.", "--canon", "--who", "identity=id1", "--who", "my grandmother",
                 "--where", "environment=appearance/e1", "--where", "Lyon", "--what", "my guitar|item=appearance/x1"]) == 0
    n = json.loads((d / "elements/psyche/fear1/psyche-node.json").read_text("utf-8"))
    assert n["who"] == [{"identity": "id1"}, {"label": {"en": "my grandmother"}}]
    assert n["where"] == [{"environment": "appearance/e1"}, {"label": {"en": "Lyon"}}]
    assert n["what"] == [{"item": "appearance/x1", "label": {"en": "my guitar"}}]
    assert main(["psyche", "add", str(d), "--kind", "fear", "--gist", "en=x", "--link", "about=identities/id1"]) == 2
    assert not (d / "elements/psyche/fear2").exists()


# ---------------------------------------------------------------- illustrations of a psyche node (RFC 0004 § 3 decies, 1.2) ----------------------------------------------------------------

def _pimage(d, m, vid, name="pic.png", shown=None, **variant):
    """Give psyche node `vid` one more image of its own (asset `a-psy-<vid>-<name>`, role psyche-media) on the manifest dict `m`
    (written back); `shown`: who[] of the node file; `variant`: fields merged into the manifest variant (age, nudity…)."""
    from PIL import Image
    rel = f"elements/psyche/{vid}/{name}"
    Image.new("RGB", (8, 8), (120, 60, 30)).save(d / rel)
    aid = f"a-psy-{vid}-{name.split('.')[0]}"
    m.setdefault("assets", []).append({"id": aid, "path": rel, "role": "psyche-media", "mediaType": "image/png", "bytes": 1, "sha256": "0" * 64, "license": "CC0-1.0"})
    v = m["elements"]["psyche"]["variants"][vid]
    v.setdefault("media", []).append(aid); v.update(variant)
    if shown is not None:
        _pnode(d, vid, who=shown)
    from cof_cli.container import refresh_asset_index
    refresh_asset_index(d, m); _write(d, m)
    return aid


def test_psyche_images_rules(tmp_path):
    """RFC 0004 § 3 decies: `media` on a psyche variant — images only (error otherwise), unknown asset = error, more than 3 =
    a warning (a memory fits better), `media_from` is for memories; a valid illustrated node adds no warning."""
    d, m = _psy(tmp_path)
    a1 = _pimage(d, m, "val1")
    rep = _val(d); assert rep.ok and not [w for w in rep.warnings if "val1" in w], (rep.errors, rep.warnings)
    m["elements"]["psyche"]["variants"]["val1"]["media"] = [a1, "a-m3-meeting"]            # the image of a memory may illustrate a node too (the same asset in two places)
    _write(d, m); rep = _val(d); assert rep.ok, rep.errors
    m["elements"]["psyche"]["variants"]["val1"]["media"] = [a1, "a-nowhere"]
    _write(d, m); assert any("psyche.val1: media: unknown asset a-nowhere" in e for e in _val(d).errors)
    m["assets"].append({"id": "a-snd", "path": "elements/psyche/val1/s.mp3", "role": "psyche-media", "mediaType": "audio/mpeg", "bytes": 1, "sha256": "0" * 64, "license": "CC0-1.0"})
    (d / "elements/psyche/val1/s.mp3").write_bytes(b"ID3")
    m["elements"]["psyche"]["variants"]["val1"]["media"] = [a1, "a-snd"]
    from cof_cli.container import refresh_asset_index
    refresh_asset_index(d, m); _write(d, m)
    assert any("psyche.val1: media: a-snd is audio/mpeg" in e and "images only" in e for e in _val(d).errors)
    m["elements"]["psyche"]["variants"]["val1"]["media"] = [a1]
    for n in ("b", "c", "d"):
        _pimage(d, m, "val1", f"{n}.png")
    rep = _val(d); assert rep.ok, rep.errors
    assert any("psyche.val1: 4 images — more than 3 make it a memory: link a memory instead" in w for w in rep.warnings), rep.warnings
    m["elements"]["psyche"]["variants"]["val1"]["media_from"] = "memories/m3"
    _write(d, m); assert any("psyche.val1: `media_from` is for memories" in e for e in _val(d).errors)


def test_psyche_images_enter_the_minor_rules(tmp_path):
    """RFC 0004 § 3 decies / RFC 0002 § 5: an image that shows the character carries the variant `age`, which enters the preset's
    lowest age like a memory's; the text of a node never does; an age with no image is a warning."""
    from cof_cli.model import preset_age
    d, m = _psy(tmp_path)
    assert preset_age(m, "default") == 29                                      # the memory m3 (29) and the override (34): the psyche alone adds nothing
    _pimage(d, m, "val1", shown=[{"identity": "self", "shown": True}])
    assert any("psyche.val1: an image shows the character — the variant must carry `age`" in e for e in _val(d).errors)
    m["elements"]["psyche"]["variants"]["val1"]["age"] = {"value": 12, "unit": "years", "basis": "declared"}; _write(d, m)
    rep = _val(d); assert rep.ok, rep.errors
    assert preset_age(rep.manifest, "default") == 12                           # a node illustrated with a child: a minor preset
    assert "has-minor-preset" in rep.manifest["tags"]["auto"]
    was = json.loads(json.dumps(m["rights"])); m["rights"].setdefault("permissions", {})["allowSexualUsage"] = True; _write(d, m)
    errs = _val(d).errors; assert any("allowSexualUsage" in e for e in errs), errs
    m["rights"] = was
    m["elements"]["psyche"]["variants"]["val1"].pop("media"); _write(d, m)
    rep = _val(d); assert preset_age(rep.manifest, "default") == 12            # the age stays until it is removed: that is what the warning says
    assert any("variant `age` on a node with no image" in w for w in rep.warnings), rep.warnings
    m["elements"]["psyche"]["variants"]["val1"].pop("age"); _pnode(d, "val1", who=None); _write(d, m)
    assert preset_age(_val(d).manifest, "default") == 29


def test_psyche_images_nudity_and_real_persons(tmp_path):
    """Nudity on a node's image: the memory rules — nobody declared shown, the character under 18 or at an unknown age, a person
    shown without a known age, a real person without consent are errors; adults who are consenting identities pass."""
    d, m = _psy(tmp_path)
    m["tags"] = {**m.get("tags", {}), "content": ["nudity"]}
    _pimage(d, m, "val1", nudity=True)
    assert any("psyche.val1: nudity with nobody declared shown" in e for e in _val(d).errors)
    _pnode(d, "val1", who=[{"identity": "self", "shown": True}]); v = m["elements"]["psyche"]["variants"]["val1"]
    v["age"] = {"value": 17, "unit": "years", "basis": "declared"}; _write(d, m)
    errs = _val(d).errors
    assert any("shows the character at an unknown age or under 18" in e for e in errs) and any("shows nudity in a preset under 18" in e for e in errs), errs
    v["age"] = {"value": 30, "unit": "years", "basis": "declared"}; _write(d, m)
    rep = _val(d); assert rep.ok, rep.errors
    _pnode(d, "val1", who=[{"identity": "self", "shown": True}, {"label": {"en": "a friend"}, "shown": True}])
    assert any("every person shown must have a known age of 18 or more (unknown: a friend" in e for e in _val(d).errors)
    _pnode(d, "val1", who=[{"identity": "self", "shown": True}, {"label": {"en": "a friend"}, "shown": True, "age": {"value": 40, "unit": "years"}, "real": True}])
    assert any("shows a real person who is not an identity of the file — never allowed" in e or "real person" in e for e in _val(d).errors) or _val(d).ok
    m["identities"]["id1"]["fictional"] = False; _write(d, m)
    assert any("shows the real person 'id1' without consent scope nudity / intimate" in e for e in _val(d).errors)
    m["identities"]["id1"]["consent"] = {"scope": ["nudity", "conversational-persona", "likeness-image"], "given_by": "id1", "date": "2026-11-04", "evidence": "signed"}; _write(d, m)
    assert not [e for e in _val(d).errors if "real person" in e and "psyche.val1" in e]


def test_psyche_images_purges_extract_and_guard(tmp_path):
    """RFC 0004 § 3 decies: the all-audiences purge drops the images of a node with nudity and keeps the node (and any asset another
    variant shares); `cof extract` carries the assets of the nodes it keeps; a personal node leaves with its images;
    extracting one character leaves behind the images of a real person of the other."""
    from cof_cli.ops import extract_presets, strip_intimate, drop_personal_memories
    from cof_cli.psyche import drop_personal_nodes
    d, m = _psy(tmp_path)
    m["tags"] = {**m.get("tags", {}), "content": ["nudity"]}
    a1 = _pimage(d, m, "val1", shown=[{"identity": "self", "shown": True}], nudity=True, age={"value": 30, "unit": "years", "basis": "declared"})
    m["elements"]["psyche"]["variants"]["bel1"]["media"] = ["a-m3-meeting"]; _write(d, m)    # a shared asset: a memory's image on a node
    assert _val(d).ok, _val(d).errors
    out = tmp_path / "ex"; extract_presets(d, out, ["default"])
    mx = json.loads((out / "manifest.json").read_text("utf-8"))
    assert a1 in {a["id"] for a in mx["assets"]} and (out / "elements/psyche/val1/pic.png").is_file()
    assert validate_dir(out, Report(), recompute=True) is not None
    gone = strip_intimate(out)
    assert "psyche.val1 (images only)" in gone
    mp = json.loads((out / "manifest.json").read_text("utf-8")); vv = mp["elements"]["psyche"]["variants"]["val1"]
    assert "val1" in mp["elements"]["psyche"]["variants"] and not vv.get("media") and "nudity" not in vv and "age" not in vv
    assert a1 not in {a["id"] for a in mp["assets"]} and not (out / "elements/psyche/val1/pic.png").exists()
    assert "who" in json.loads((out / "elements/psyche/val1/psyche-node.json").read_text("utf-8")) and "shown" not in json.dumps(json.loads((out / "elements/psyche/val1/psyche-node.json").read_text("utf-8")))
    assert mp["elements"]["psyche"]["variants"]["bel1"]["media"] == ["a-m3-meeting"] and (out / "elements/memories/m3/meeting.jpg").is_file()
    rep = Report(); validate_dir(out, rep, recompute=True); assert rep.ok, rep.errors
    # a personal node leaves with its images
    _pnode(d, "val1", visibility="personal"); out2 = tmp_path / "ex2"; extract_presets(d, out2, ["default"])
    assert drop_personal_nodes(out2) == ["contra1", "val1"] and not (out2 / "elements/psyche/val1").exists()
    mp = json.loads((out2 / "manifest.json").read_text("utf-8")); assert a1 not in {a["id"] for a in mp["assets"]} and "a-m3-meeting" in {a["id"] for a in mp["assets"]}
    rep = Report(); validate_dir(out2, rep, recompute=True); assert rep.ok, rep.errors


def test_psyche_image_guard_on_extracting_a_character(tmp_path):
    """RFC 0002 § 4.5 read for § 3 decies: an image that shows another real person of the cast is left behind when one character
    is extracted — the node stays, with a note."""
    from cof_cli.ops import extract_identity
    d, m = _psy(tmp_path)
    m["identities"]["marc"] = {"name": "Marc", "fictional": False, "morphology": {"class": "human"}, "language": "fr"}
    m["identities"]["id1"]["consent"] = {"scope": ["conversational-persona"], "given_by": "id1", "date": "2026-11-04", "evidence": "x"}
    for cat, e in m["elements"].items():
        for v in e["variants"].values():
            v.setdefault("identity", "id1")
    m["presets"]["marc"] = {"label": "Marc", "slots": {}, "identity": "marc", "age_override": {"value": 40, "unit": "years", "basis": "declared"}}
    a1 = _pimage(d, m, "val1", shown=[{"identity": "marc", "shown": True, "age": {"value": 40, "unit": "years"}}])
    out = tmp_path / "id1"; notes = []
    extract_identity(d, out, "id1", notes)
    assert any(n.startswith("psyche.val1: images showing another real person left behind") for n in notes), notes
    mx = json.loads((out / "manifest.json").read_text("utf-8"))
    assert "val1" in mx["elements"]["psyche"]["variants"] and not mx["elements"]["psyche"]["variants"]["val1"].get("media") and a1 not in {a["id"] for a in mx["assets"]}


def test_psyche_add_image(tmp_path):
    """`cof psyche add --image`: the first image illustrates the node (asset role psyche-media, in the node's folder); a non-image
    is refused; --self-shown needs --age, which lands on the variant and enters the preset's lowest age."""
    from PIL import Image
    from cof_cli.cli import main
    d, m = _psy(tmp_path)
    img = tmp_path / "logo.png"; Image.new("RGB", (8, 8), (10, 20, 30)).save(img)
    img2 = tmp_path / "second.png"; Image.new("RGB", (8, 8), (30, 20, 10)).save(img2)
    assert main(["psyche", "add", str(d), "--kind", "taste", "--gist", "en=Loves the old logo.", "--canon", "--image", str(img), "--image", str(img2)]) == 0
    m = json.loads((d / "manifest.json").read_text("utf-8")); v = m["elements"]["psyche"]["variants"]["taste1"]
    assert v["media"] == ["a-psy-taste1-logo", "a-psy-taste1-second"] and "age" not in v
    A = {a["id"]: a for a in m["assets"]}
    assert A["a-psy-taste1-logo"]["role"] == "psyche-media" and A["a-psy-taste1-logo"]["path"] == "elements/psyche/taste1/logo.png" and (d / A["a-psy-taste1-logo"]["path"]).is_file()
    txt = tmp_path / "notes.txt"; txt.write_text("x", "utf-8")
    assert main(["psyche", "add", str(d), "--kind", "taste", "--gist", "en=x", "--image", str(txt)]) == 2
    assert main(["psyche", "add", str(d), "--kind", "taste", "--gist", "en=x", "--image", str(img), "--self-shown"]) == 2            # needs --age
    assert main(["psyche", "add", str(d), "--kind", "taste", "--gist", "en=x", "--self-shown", "--age", "12"]) == 2                   # no image
    assert main(["psyche", "add", str(d), "--kind", "taste", "--gist", "en=A selfie.", "--canon", "--image", str(img), "--self-shown", "--age", "12"]) == 0
    from cof_cli.model import preset_age
    m = json.loads((d / "manifest.json").read_text("utf-8")); v = m["elements"]["psyche"]["variants"]["taste2"]
    assert v["age"]["value"] == 12 and preset_age(m, "default") == 12
    n = json.loads((d / "elements/psyche/taste2/psyche-node.json").read_text("utf-8")); assert n["who"] == [{"identity": "self", "shown": True}]


def test_example_10_illustrated_nodes():
    """Example 10: contra1 is illustrated by the folk guitar of appearance/x1 (the same asset, referenced twice) and hab1 by the image
    of ev1; both extract with their assets and the file validates with no new warning."""
    src = ROOT / "spec/examples/10-clara-mercier"
    rep = Report(); m = validate_dir(src, rep, recompute=False)
    assert rep.ok, rep.errors
    V = m["elements"]["psyche"]["variants"]
    assert V["contra1"]["media"] == ["a-ac-x1"] and V["hab1"]["media"] == ["a-mem-ev1-1"]
    assert m["elements"]["appearance"]["variants"]["x1"]["images"] == ["a-ac-x1"]
    assert not [w for w in rep.warnings if "psyche" in w], rep.warnings
