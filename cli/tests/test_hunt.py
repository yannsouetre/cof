"""Regressions of the 1.2 bug hunt (5 Nov. 2026, tests/hunt in the release notes): every test rebuilds the hostile case a
hunter found on a copy of tests/fixtures/mixed-age (adult preset `default` with intimate i1, minor preset `young` at 14) and
checks the fixed behaviour. Images are generated per asset id, so that no two assets share bytes by accident."""
import hashlib
import json
import shutil
import zipfile
from pathlib import Path

import pytest

from cof_cli.container import ContainerError, SAFE_PATH, pack, read_manifest, refresh_asset_index
from cof_cli.validate import Report, validate_dir

ROOT = Path(__file__).resolve().parents[2]


def load(d): return json.loads((d / "manifest.json").read_text("utf-8"))
def save(d, m): (d / "manifest.json").write_text(json.dumps(m, ensure_ascii=False, indent=2) + "\n", "utf-8")
def V(m, cat): return m["elements"].setdefault(cat, {"variants": {}})["variants"]


def base(tmp_path) -> Path:
    d = tmp_path / "base"
    shutil.copytree(ROOT / "tests/fixtures/mixed-age", d)
    m = load(d); m["cof"] = "1.2"
    for k in ("completeness", "coverage"):
        m.pop(k, None)
    save(d, m)
    return d


def image(d: Path, m: dict, aid: str, rel: str, role="memory-media", data: bytes | None = None):
    from PIL import Image
    p = d / rel; p.parent.mkdir(parents=True, exist_ok=True)
    if data is None:
        h = hashlib.sha256(aid.encode()).digest()
        im = Image.new("RGB", (48, 48), (h[0], h[1], h[2])); im.putpixel((2, 2), (h[3], h[4], h[5])); im.save(p, "JPEG")
    else:
        p.write_bytes(data)
    m.setdefault("assets", []).append({"id": aid, "path": rel, "role": role, "mediaType": "image/jpeg", "license": "CC0-1.0"})


def node(d: Path, rel: str, obj: dict):
    p = d / rel; p.parent.mkdir(parents=True, exist_ok=True); p.write_text(json.dumps(obj, ensure_ascii=False), "utf-8")


def memory(d, m, vid, gist, media=None, age=None, preset="default", **nd):
    node(d, f"elements/memories/{vid}/memory.json", {"gist": {"en": gist}, **nd})
    v = {"kind": "moment", "label": vid, "memory": f"elements/memories/{vid}/memory.json"}
    if media:
        v["media"] = media
    if age is not None:
        v["age"] = {"value": age, "unit": "years", "basis": "canonical"}
    V(m, "memories")[vid] = v
    if preset:
        m["presets"][preset]["slots"].setdefault("memories", []).append(vid)
    return v


def errors(d) -> list[str]:
    m = load(d); refresh_asset_index(d, m); save(d, m)
    rep = Report(); validate_dir(d, rep, recompute=False)
    return rep.errors


def test_nan_age_is_not_json(tmp_path):
    """H1-01 / H4-01: an age written NaN (Python's parser takes it) no longer hides a minor."""
    d = base(tmp_path)
    (d / "manifest.json").write_text((d / "manifest.json").read_text("utf-8").replace('"value": 34', '"value": NaN', 1), "utf-8")
    rep = Report(); validate_dir(d, rep, recompute=False)
    assert not rep.ok and any("NaN is not valid JSON" in e for e in rep.errors)
    from cof_cli.model import _age_value
    assert _age_value({"value": float("nan")}) == 0.0 and _age_value({"value": float("inf")}) == 0.0


def test_borrowed_child_picture_in_explicit_memory(tmp_path):
    """H1-03: an explicit adult memory borrowing (media_from) the picture of the character at 10."""
    d = base(tmp_path); m = load(d)
    image(d, m, "a-child", "elements/memories/ev1/child.jpg")
    memory(d, m, "ev1", "Age ten, the garden.", media=["a-child"], age=10, preset=None, who=[{"identity": "self", "shown": True}], when={"age": {"value": 10}})
    memory(d, m, "ev2", "A night at thirty.", age=30, who=[{"identity": "self", "shown": True}], when={"age": {"value": 30}}, explicit="nudity")
    V(m, "memories")["ev2"].update(media_from="memories/ev1", nudity=True)
    m["tags"]["content"] = sorted(set(m["tags"]["content"]) - {"none"} | {"nudity", "sexual"}); save(d, m)
    errs = errors(d)
    assert any("declared as a person under 18" in e and "a-child" in e for e in errs), errs


def test_backstage_nude_minor_and_nudity_hiding_intimate(tmp_path):
    """H1-04 / H1-05: a backstage variant at 10 marked nudity; a nudity-only psyche node reusing an intimate picture."""
    d = base(tmp_path); m = load(d)
    image(d, m, "a-bx", "elements/appearance/bx/body.jpg", role="reference")
    V(m, "appearance")["bx"] = {"kind": "body", "label": "bx", "images": ["a-bx"], "nudity": True, "age": {"value": 10, "unit": "years", "basis": "declared"}}
    m["tags"]["content"] = sorted(set(m["tags"]["content"]) - {"none"} | {"nudity"}); save(d, m)
    assert any("no nudity of any kind under 18, in a preset or backstage" in e for e in errors(d))
    d2 = base(tmp_path / "b"); m = load(d2)
    image(d2, m, "a-x", "elements/memories/ev9/x.jpg")
    memory(d2, m, "ev9", "Thirty-four.", media=["a-x"], age=34, who=[{"identity": "self", "shown": True}], when={"age": {"value": 34}}, explicit="intimate")
    V(m, "memories")["ev9"]["nudity"] = True
    node(d2, "elements/psyche/w1/psyche-node.json", {"gist": {"en": "To be seen."}, "who": [{"identity": "self", "shown": True}]})
    V(m, "psyche")["w1"] = {"kind": "want", "label": "w1", "node": "elements/psyche/w1/psyche-node.json", "media": ["a-x"], "nudity": True, "age": {"value": 34, "unit": "years", "basis": "canonical"}}
    m["presets"]["default"]["slots"]["psyche"] = ["w1"]
    m["tags"]["content"] = sorted(set(m["tags"]["content"]) - {"none"} | {"nudity", "sexual"}); save(d2, m)
    errs = errors(d2)
    assert any("psyche.w1 (nudity) uses a-x, shown as intimate content elsewhere" in e for e in errs), errs


def test_age_travels_with_the_picture(tmp_path):
    """H1-06: an accessory (no age) showing the 14-year-old's face in the adult intimate preset."""
    d = base(tmp_path); m = load(d)
    face = next(a for a in m["assets"] if a["id"] == "a-young-head-front")
    V(m, "appearance")["x1"] = {"kind": "accessory", "label": "photo", "images": [face["id"]]}
    m["presets"]["default"]["slots"]["appearance"].append("x1"); save(d, m)
    errs = errors(d)
    assert any("appearance.x1 uses a-young-head-front, declared as a person under 18" in e for e in errs), errs


def test_single_character_real_person_intimate_memory(tmp_path):
    """H1-07: a real person's explicit: intimate memory needs scope intimate, single-character file too."""
    d = base(tmp_path); m = load(d)
    m["fictional"] = False
    m["rights"]["consent"] = {"subject_is_real_person": True, "scope": ["likeness-image", "nudity", "conversational-persona"], "granted": "2026-10-10", "jurisdictions": ["FR"], "proof": [{"type": "signed-document"}]}
    image(d, m, "a-x", "elements/memories/ev9/x.jpg")
    memory(d, m, "ev9", "Thirty-four.", media=["a-x"], age=34, who=[{"identity": "self", "shown": True}], when={"age": {"value": 34}}, explicit="intimate", factual=True)
    V(m, "memories")["ev9"]["nudity"] = True
    m["tags"]["content"] = sorted(set(m["tags"]["content"]) - {"none"} | {"nudity", "sexual"}); save(d, m)
    assert any("explicit node (intimate) shows the real person 'self' without consent scope intimate" in e for e in errors(d))


def _personal_file(tmp_path) -> Path:
    """A canon memory borrowing a personal memory's photo; a canon stance about a personal psyche node; a canon node
    derived from a personal one; a card still holding a chat."""
    d = base(tmp_path); m = load(d)
    image(d, m, "a-user", "elements/memories/ev1/user.jpg")
    memory(d, m, "ev1", "The user's divorce (Alice, Lyon).", media=["a-user"], visibility="personal", origin="lived")
    memory(d, m, "ev2", "A face.")
    V(m, "memories")["ev2"]["media_from"] = "memories/ev1"
    node(d, "elements/psyche/s1/psyche-node.json", {"gist": {"en": "I worry about the user's diagnosis."}, "visibility": "personal"})
    node(d, "elements/psyche/s2/psyche-node.json", {"gist": {"en": "Warm toward what the user lives."}, "about": {"node": "psyche/s1"}})
    image(d, m, "a-user2", "elements/psyche/s1/u.jpg")
    V(m, "psyche")["s1"] = {"kind": "stance", "label": "SECRET-LABEL Alice Martin", "node": "elements/psyche/s1/psyche-node.json", "media": ["a-user2"]}
    V(m, "psyche")["s2"] = {"kind": "stance", "label": "warmth", "node": "elements/psyche/s2/psyche-node.json"}
    node(d, "elements/psyche/s3/psyche-node.json", {"gist": {"en": "Still warm."}})
    V(m, "psyche")["s3"] = {"kind": "stance", "label": "s3", "derives_from": "s1", "node": "elements/psyche/s3/psyche-node.json"}
    m["presets"]["default"]["slots"]["psyche"] = ["s1", "s2", "s3"]
    card = json.loads((d / "elements/personality/p1/card.json").read_text("utf-8"))
    card.setdefault("data", {}).setdefault("extensions", {})["chat_history"] = [{"role": "user", "content": "my PIN is 4242"}]
    (d / "elements/personality/p1/card.json").write_text(json.dumps(card), "utf-8")
    save(d, m)
    m = load(d); refresh_asset_index(d, m); save(d, m)
    return d


def test_personal_data_stays_home(tmp_path):
    """H1-09/10/12/13, H4-02/03/05: agent export, extract, SOUL.md, card export and the propose bundle."""
    from cof_cli.cli import main
    d = _personal_file(tmp_path)
    ag = tmp_path / "agent"
    assert main(["export", str(d), "--format", "agent", "-o", str(ag)]) == 0
    assert not (ag / "memories/ev2").exists()                                   # the borrowed personal photo stays
    soul = (ag / "SOUL.md").read_text("utf-8")
    assert "SECRET-LABEL" not in soul and "a private matter" in soul               # a stance about a personal node never names it
    ex = tmp_path / "ex"
    assert main(["extract", str(d), "--preset", "default", "-o", str(ex)]) == 0
    m = load(ex)
    assert "a-user" not in {a["id"] for a in m["assets"]} and "a-user2" not in {a["id"] for a in m["assets"]}
    assert "media" not in (V(m, "psyche").get("s3") or {})                        # derived from a personal node: words kept, images not
    s2 = json.loads((ex / "elements/psyche/s2/psyche-node.json").read_text("utf-8"))
    assert "about" not in s2                                                       # no dangling subject
    assert "chat_history" not in (ex / "elements/personality/p1/card.json").read_text("utf-8")
    rep = Report(); validate_dir(ex, rep, recompute=False)
    assert rep.ok, rep.errors
    out = tmp_path / "c.json"
    assert main(["export", str(d), "--format", "card", "-o", str(out)]) == 0
    assert "4242" not in out.read_text("utf-8")
    from cof_cli import propose as P
    b = P.build_bundle(d, load(d))
    assert all("divorce" not in x["gist"] for x in b["memories"]) and all(x["id"] != "s1" for x in b["psyche"])
    assert b.get("personal_left_out") == 2


def test_all_audiences_takes_the_lora_file(tmp_path):
    """H1-16: `extract --all-audiences` removes a nude LoRA variant AND its file."""
    from cof_cli.cli import main
    d = base(tmp_path); m = load(d)
    V(m, "identity_weights")["l1"]["nudity"] = True
    m["tags"]["content"] = sorted(set(m["tags"]["content"]) - {"none"} | {"nudity"}); save(d, m)
    ex = tmp_path / "ex"
    assert main(["extract", str(d), "--preset", "default", "-o", str(ex), "--all-audiences"]) == 0
    assert not (ex / "elements/identity_weights/l1").exists()


def test_container_names_and_manifest_shape(tmp_path):
    """H4-04 / H4-07 / H4-09: a trailing newline is not part of the path grammar; symlinks refused; manifest is an object."""
    assert SAFE_PATH.match("tools/run.py") and not SAFE_PATH.match("tools/run.py\n")
    from cof_cli.container import inspect
    from cof_cli import MIMETYPE
    cof = tmp_path / "x.cof"
    with zipfile.ZipFile(cof, "w") as z:
        zi = zipfile.ZipInfo("mimetype"); z.writestr(zi, MIMETYPE)
        z.writestr("manifest.json", "[]")
        zi = zipfile.ZipInfo("link"); zi.create_system = 3; zi.external_attr = 0o120777 << 16; z.writestr(zi, "/etc/passwd")
    st = inspect(cof)
    assert any("symbolic link" in e for e in st["errors"])
    with pytest.raises(ContainerError):
        read_manifest(cof)


def test_propose_answers_never_crash():
    """H4-11 / H4-12: a null node, an Infinity strength, a bare list, prose after the JSON."""
    from cof_cli import propose as P
    assert P.parse_answer([{"kind": "value"}]) == {"nodes": [{"kind": "value"}]}
    assert P.parse_answer('Here: {"nodes": []} (see {note})') == {"nodes": []}
    with pytest.raises(ValueError):
        P.parse_answer('{"nodes": [{"strength": Infinity}]}')
    merged = P.merge(P.normalize({"nodes": [None]}))
    errs, _ = P.validate(P.normalize(merged), {"languages": ["en"]})
    assert errs


def test_derived_node_keeps_its_own_strength(tmp_path):
    """H5-19: RFC 0004's recipe — a node that changes is a second node with derives_from, its own node file, its own
    strength — no longer fails on the parent's mirrored strength."""
    d = tmp_path / "c"; shutil.copytree(ROOT / "spec/examples/10-clara-mercier", d)
    m = load(d); P = V(m, "psyche")
    pid, pv = next((k, x) for k, x in P.items() if "strength" in x)
    node(d, f"elements/psyche/{pid}-2/psyche-node.json", {"gist": {"en": "It changed.", "fr": "Cela a changé."}, "strength": max(0, int(pv["strength"]) - 40)})
    P[f"{pid}-2"] = {"derives_from": pid, "node": f"elements/psyche/{pid}-2/psyche-node.json"}
    save(d, m)
    rep = Report(); validate_dir(d, rep, recompute=False)
    assert not any("differs from the node's" in e for e in rep.errors), rep.errors
