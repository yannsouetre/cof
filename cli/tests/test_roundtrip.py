import json
import shutil
import zipfile
from pathlib import Path

import pytest

from cof_cli.container import ContainerError, pack, read_manifest, unpack
from cof_cli.convert import card_to_cof_dir, read_card_from_png, write_card_to_png
from cof_cli.validate import Report, validate_cof, validate_dir

ROOT = Path(__file__).resolve().parents[2]
EXAMPLE = ROOT / "spec" / "examples" / "01-lea-text-only"


@pytest.fixture
def workdir(tmp_path):
    d = tmp_path / "lea"
    shutil.copytree(EXAMPLE, d)
    return d


def test_example_dir_is_valid(workdir):
    rep = Report()
    validate_dir(workdir, rep, recompute=False)
    assert rep.ok, rep.errors
    assert "chat-text" in rep.info["completeness"]["targets_ready"]


def test_pack_layout_and_validate(workdir, tmp_path):
    out = tmp_path / "lea.cof"
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
    out = tmp_path / "lea.cof"
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
    assert not rep.ok and any("allowSexualUsage effectif" in e for e in rep.errors), rep.errors


def test_real_person_needs_consent(workdir):
    m = json.loads((workdir / "manifest.json").read_text("utf-8"))
    m["fictional"] = False
    (workdir / "manifest.json").write_text(json.dumps(m), "utf-8")
    rep = Report()
    validate_dir(workdir, rep)
    assert any("consent" in e for e in rep.errors)


def test_undeclared_script_is_rejected(workdir):
    (workdir / "extensions").mkdir()
    (workdir / "extensions" / "evil.js").write_text("alert(1)")
    rep = Report()
    validate_dir(workdir, rep)
    assert any("exécutable" in e for e in rep.errors)


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


MODULAR = ROOT / "spec" / "examples" / "07-lea-modulaire"


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
    assert any("presets.young" in e and "intime" in e for e in rep.errors), rep.errors
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
    assert any("(intimate) : âge 17" in e for e in rep.errors), rep.errors
    del V["i1"]["age"]
    (d / "manifest.json").write_text(json.dumps(m), "utf-8")
    rep = Report(); validate_dir(d, rep)
    assert any("(intimate) : âge obligatoire" in e for e in rep.errors), rep.errors


def test_unknown_slot_variant_is_error(tmp_path):
    d = tmp_path / "m"; shutil.copytree(MODULAR, d)
    m = json.loads((d / "manifest.json").read_text("utf-8"))
    m["presets"]["default"]["slots"]["appearance"] = ["f9"]
    (d / "manifest.json").write_text(json.dumps(m), "utf-8")
    rep = Report(); validate_dir(d, rep)
    assert any("déclinaison inconnue" in e for e in rep.errors)


def test_weights_need_base_model(tmp_path):
    d = tmp_path / "m"; shutil.copytree(MODULAR, d)
    w = d / "elements/identity_weights/l1/weights.json"
    j = json.loads(w.read_text("utf-8")); j["base_model"] = {}
    w.write_text(json.dumps(j), "utf-8")
    rep = Report(); validate_dir(d, rep)
    assert any("base_model" in e for e in rep.errors)


def test_derived_cannot_be_listed_as_image(tmp_path):
    d = tmp_path / "m"; shutil.copytree(ROOT / "spec" / "examples" / "03-femme-moderne", d)
    m = json.loads((d / "manifest.json").read_text("utf-8"))
    der = next(a["id"] for a in m["assets"] if a["role"] == "derived")
    m["elements"]["appearance"]["variants"]["f1"]["images"].append(der)
    (d / "manifest.json").write_text(json.dumps(m), "utf-8")
    rep = Report(); validate_dir(d, rep)
    assert any("dérivé" in e for e in rep.errors)


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
    assert any("deux déclinaisons de type 'face'" in e for e in rep.errors)
    assert any("se recouvrent" in w for w in rep.warnings)
    assert not any("'o3'" in w and "se recouvrent" in w for w in rep.warnings)


def test_merge_and_extract(tmp_path):
    from cof_cli.ops import merge_dirs, extract_preset
    out = tmp_path / "merged"
    merge_dirs([MODULAR, ROOT / "spec" / "examples" / "04-martien"], out)
    rep = Report(); validate_dir(out, rep)
    assert rep.ok, rep.errors
    m = json.loads((out / "manifest.json").read_text("utf-8"))
    assert len(m["identities"]) == 2 and m["name"] == "Léa Marchand"
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
    assert not any("deux déclinaisons" in e for e in rep.errors), rep.errors
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
    assert any("f-noage (face) doit déclarer un âge" in e for e in rep.errors), rep.errors
    # a mechanical morphology does not need ages on faces
    m["morphology"] = {"class": "mechanical", "species": "robot"}
    for i in m.get("identities", {}).values():
        i["morphology"] = m["morphology"]
    (d / "manifest.json").write_text(json.dumps(m), "utf-8")
    rep = Report(); validate_dir(d, rep)
    assert not any("doit déclarer un âge" in e for e in rep.errors), rep.errors
