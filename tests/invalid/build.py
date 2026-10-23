"""Build the negative conformance corpus: one rule violated per file.

    python tests/invalid/build.py        # regenerates tests/invalid/*.cof and cases.json

Every `.cof` here MUST be rejected by a conformant validator. The base file (`_base.cof`, valid) is a
shrunk copy of tests/fixtures/mixed-age: an adult preset with intimate content and a minor preset.
"""
from __future__ import annotations
import io, json, shutil, sys, tempfile, zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
OUT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / "cli"))
from cof_cli.container import MIMETYPE, pack, refresh_asset_index  # noqa: E402

def base(tmp: Path) -> Path:
    from PIL import Image
    d = tmp / "base"; shutil.copytree(ROOT / "tests/fixtures/mixed-age", d)
    for p in d.rglob("*"):
        if p.suffix.lower() in (".jpg", ".jpeg", ".png", ".webp"):
            im = Image.open(p).convert("RGB"); im.thumbnail((32, 32)); im.save(p, "JPEG" if p.suffix.lower() in (".jpg", ".jpeg") else "PNG")
    m = json.loads((d / "manifest.json").read_text("utf-8"))
    for k in ("completeness", "coverage"):
        m.pop(k, None)
    refresh_asset_index(d, m); save(d, m)
    return d

def load(d): return json.loads((d / "manifest.json").read_text("utf-8"))
def save(d, m): (d / "manifest.json").write_text(json.dumps(m, ensure_ascii=False, indent=2) + "\n", "utf-8")
def V(m, cat): return m["elements"][cat]["variants"]

CASES = []
def case(name, rule, section, expect):
    def deco(fn):
        CASES.append((name, rule, section, expect, fn)); return fn
    return deco

# ---------- manifest-level cases (mutate the folder, then pack) ----------
@case("version-0.5", "the format version must be 1.x (older files are migrated)", "§ 12", "cof migrate")
def _(d): m = load(d); m["cof"] = "0.5"; save(d, m)

@case("missing-id", "`id` is required", "§ 2", "'id' is a required property")
def _(d): m = load(d); m.pop("id"); save(d, m)

@case("unknown-variant-in-preset", "a preset slot must reference an existing variant", "§ 2.3", "z9")
def _(d): m = load(d); m["presets"]["default"]["slots"]["appearance"].append("z9"); save(d, m)

@case("face-without-age", "a face of a human-form character must carry an age", "§ 2.2 / § 9.4", "must declare an age")
def _(d): m = load(d); V(m, "appearance")["f1"].pop("age"); save(d, m)

@case("intimate-under-18", "intimate content requires an age ≥ 18", "§ 4.5 / § 9.4", "intimate")
def _(d): m = load(d); V(m, "appearance")["i1"]["age"] = {"value": 17, "unit": "years", "basis": "declared"}; save(d, m)

@case("minor-preset-offers-intimate", "a preset under 18 never OFFERS intimate content either (age rules cover slots ∪ alternatives)", "§ 2.3 / § 9.4", "intimate")
def _(d): m = load(d); m["presets"]["young"]["alternatives"] = {"appearance": ["i1"]}; save(d, m)

@case("primary-image-not-applied", "a preset's primary_image is an image of a variant the preset applies", "§ 2.3", "primary_image")
def _(d):
    m = load(d); adult = V(m, "appearance")["o1"]["images"][0]          # the adult outfit, not applied by "young"
    m["presets"]["young"]["primary_image"] = adult; save(d, m)

@case("alternative-in-library", "alternatives are not allowed on the libraries (posture, motion, files)", "§ 2.3", "alternatives")
def _(d): m = load(d); m["presets"]["default"]["alternatives"] = {"motion": ["z1"]}; save(d, m)

def two_characters(m):
    """Turn the base into a cast: the existing character + Marc, every element owned by its character."""
    root = {k: m[k] for k in ("name", "nickname", "summary", "fictional", "morphology") if m.get(k) is not None}
    m["identities"] = {"lea": root, "marc": {"name": "Marc", "fictional": True, "morphology": {"class": "human"}}}
    m["default_identity"] = "lea"
    for e in m["elements"].values():
        for v in e["variants"].values():
            v["identity"] = "lea"
    for p in m["presets"].values():
        p["identity"] = "lea"
    m["elements"]["personality"]["variants"]["p-marc"] = {"kind": "description", "label": "Marc", "text": "Marc, 40, a calm carpenter.", "language": "en", "identity": "marc"}
    m["presets"]["marc"] = {"label": "Marc", "identity": "marc", "age_override": {"value": 40, "unit": "years", "basis": "canonical"}, "slots": {"personality": ["p-marc"]}}
    return m

@case("cross-character-element", "a preset only uses its own character's elements", "§ 2.1", "belongs to character")
def _(d): m = two_characters(load(d)); m["presets"]["marc"]["slots"]["appearance"] = ["b1"]; save(d, m)

@case("likeness-shared-between-characters", "a file carrying a likeness or a voice belongs to one character", "§ 2.1", "not neutral")
def _(d):
    m = two_characters(load(d)); img = V(m, "appearance")["b1"]["images"][0]
    V(m, "appearance")["b-marc"] = {"kind": "body", "label": "Marc", "identity": "marc", "age": {"value": 40, "unit": "years", "basis": "apparent"}, "images": [img]}
    m["presets"]["marc"]["slots"]["appearance"] = ["b-marc"]; save(d, m)

@case("face-marked-neutral", "a kind that carries the character (face, body, voice…) is never neutral", "§ 2.1", "never neutral")
def _(d): m = load(d); V(m, "appearance")["f1"]["neutral"] = True; save(d, m)

@case("element-without-character", "in a file with several characters, every element names its character", "§ 2.1", "no `identity`")
def _(d): m = two_characters(load(d)); V(m, "appearance")["b1"].pop("identity"); save(d, m)

@case("intimate-without-content-tag", "a file with intimate content flags it in tags.content", "§ 4.5", "nudity")
def _(d): m = load(d); m["tags"]["content"] = ["none"]; save(d, m)

@case("minor-preset-with-intimate", "a preset under 18 never contains intimate content", "§ 9.4", "intimate")
def _(d): m = load(d); m["presets"]["young"]["slots"]["appearance"] = ["f-young", "i1"]; save(d, m)

@case("minor-preset-sexual-usage", "a preset under 18 never has an effective allowSexualUsage", "§ 9.4", "allowSexualUsage")
def _(d): m = load(d); m["presets"]["young"]["permissions_override"] = {"allowSexualUsage": True}; save(d, m)

@case("two-faces-in-preset", "one variant per kind in a preset (except stackable kinds)", "§ 2.3", "face")
def _(d): m = load(d); V(m, "appearance")["f2"] = dict(V(m, "appearance")["f1"], label="second adult face"); m["presets"]["default"]["slots"]["appearance"].append("f2"); save(d, m)

@case("real-person-intimate-without-consent", "intimate content of a real person requires their explicit consent (scope intimate)", "§ 9.2", "consent scope 'intimate'")
def _(d): m = load(d); m["fictional"] = False; m.get("rights", {}).pop("consent", None); [i.update(fictional=False) for i in (m.get("identities") or {}).values()]; save(d, m)

@case("age-in-months", "ages are compared in years: 100 months is 8 years", "§ 2.2", "intimate variant combined")
def _(d): m = load(d); V(m, "appearance")["f-young"]["age"] = {"value": 100, "unit": "months", "basis": "canonical"}; m["presets"]["young"]["slots"]["appearance"] = ["f-young", "i1"]; m["presets"]["young"]["age_override"] = None; m["presets"]["young"].pop("age_override"); save(d, m)

@case("intimate-file-shared", "an intimate variant's files are its own (own folder, no other variant)", "§ 4.5", "files are its own")
def _(d): m = load(d); V(m, "appearance")["f1"]["images"].append("a-i1-placeholder"); save(d, m)

@case("same-file-minor-and-adult", "one file never represents both a person under 18 and an adult", "§ 9.4", "represents both a person under")
def _(d): m = load(d); V(m, "appearance")["f-young"]["images"] = ["a-head-front-closeup"]; save(d, m)

@case("intimate-age-any-morphology", "with an intimate element, every body representation of the preset carries an age, whatever the morphology", "§ 9.4", "whatever the morphology class")
def _(d):
    m = load(d); m["morphology"]["class"] = "other"
    for i in (m.get("identities") or {}).values():
        i.setdefault("morphology", {})["class"] = "other"
    V(m, "appearance")["f-young"].pop("age"); m["presets"]["young"]["slots"]["appearance"] = ["f-young", "i1"]; m["presets"]["young"].pop("age_override", None); save(d, m)

@case("extends-cycle", "preset inheritance has no cycle", "§ 2.3", "extends cycle")
def _(d): m = load(d); m["presets"]["default"]["extends"] = "young"; save(d, m)

@case("thumbnail-missing", "manifest.thumbnail names an existing file", "§ 1.1", "manifest.thumbnail")
def _(d): m = load(d); m["thumbnail"] = "Thumbnails/missing.png"; save(d, m)

@case("age-unknown-unit", "an age whose unit is not understood is unknown and never counts as adult", "§ 2.2", "intimate variant combined")
def _(d): m = load(d); m["cof"] = "1.3"; V(m, "appearance")["f-young"]["age"] = {"value": 500, "unit": "weeks", "basis": "canonical"}; m["presets"]["young"]["slots"]["appearance"] = ["f-young", "i1"]; save(d, m)

@case("nested-archive-pickle", "archives are inspected with their nested archives (pickles refused at any depth)", "§ 9.3", "pickle file refused inside archive")
def _(d):
    import io as _io
    m = load(d); inner = _io.BytesIO()
    with zipfile.ZipFile(inner, "w") as z:
        z.writestr("model.pkl", b"\x80\x02}q\x00.")
    p = d / "elements/files/x1/bundle.zip"; p.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(p, "w") as z:
        z.writestr("inner.dat", inner.getvalue())
    m["assets"].append({"id": "a-bundle", "path": "elements/files/x1/bundle.zip", "role": "archive", "mediaType": "application/zip", "license": "CC-BY-4.0"})
    m["elements"]["files"] = {"variants": {"x1": {"kind": "other", "files": ["a-bundle"]}}}; refresh_asset_index(d, m); save(d, m)

@case("nudity-in-minor-preset", "no nudity of any kind in a preset under 18", "§ 9.4", "shows nudity in a preset under")
def _(d): m = load(d); V(m, "appearance")["f-young"]["nudity"] = True; m["tags"]["content"] = ["nudity"]; save(d, m)

@case("nudity-without-content-flag", "a variant marked nudity requires tags.content nudity", "§ 4.5", "tags.content must include 'nudity'")
def _(d):
    m = load(d); V(m, "appearance").pop("i1"); m["presets"]["default"]["slots"]["appearance"].remove("i1")
    V(m, "appearance")["b1"]["nudity"] = True; V(m, "appearance")["o1"]["nudity"] = True; m["tags"]["content"] = ["none"]; save(d, m)

@case("nude-file-reused-unmarked", "a file showing nudity is used only by variants marked nudity (or intimate)", "§ 4.5", "show(s) nudity or intimate content")
def _(d): m = load(d); V(m, "appearance")["b1"]["nudity"] = True; save(d, m)

@case("real-person-nudity-without-consent", "nudity of a real person requires their explicit consent (scope nudity or intimate)", "§ 9.2", "consent scope 'nudity'")
def _(d):
    m = load(d); m["fictional"] = False; [i.update(fictional=False) for i in (m.get("identities") or {}).values()]
    V(m, "appearance").pop("i1"); m["presets"]["default"]["slots"]["appearance"].remove("i1"); m["elements"]["appearance"]["variants"]["b1"]["nudity"] = True; m["elements"]["appearance"]["variants"]["o1"]["nudity"] = True
    m["rights"]["consent"] = {"subject_is_real_person": True, "scope": ["likeness-image"], "granted": "2026-10-10", "jurisdictions": ["FR"], "proof": [{"type": "signed-document"}]}; save(d, m)

@case("cast-nudity-borrowed-consent", "in a cast, each real person's consent is their own (the root consent belongs to the default character)", "§ 9.2", "consent scope 'nudity'")
def _(d):
    from PIL import Image
    m = two_characters(load(d)); cons = {"subject_is_real_person": True, "scope": ["likeness-image", "nudity"], "granted": "2026-10-10", "jurisdictions": ["FR"], "proof": [{"type": "signed-document"}]}
    m["rights"]["consent"] = cons; m["fictional"] = False
    m["identities"]["lea"].update(fictional=False, consent=cons); m["identities"]["marc"].update(fictional=False)
    p = d / "elements/appearance/b-marc/body.front.jpg"; p.parent.mkdir(parents=True, exist_ok=True); Image.new("RGB", (32, 64), (120, 90, 60)).save(p, "JPEG")
    m["assets"].append({"id": "a-marc-body", "path": "elements/appearance/b-marc/body.front.jpg", "role": "reference", "mediaType": "image/jpeg", "license": "CC0-1.0", "subject": "body", "angle": "front", "framing": "full"})
    V(m, "appearance")["b-marc"] = {"kind": "body", "identity": "marc", "nudity": True, "images": ["a-marc-body"], "age": {"value": 40, "unit": "years", "basis": "declared"}}
    m["presets"]["marc"]["slots"]["appearance"] = ["b-marc"]; refresh_asset_index(d, m); save(d, m)

@case("nudity-without-age", "a preset applying a nude element has a known age (18 or over)", "§ 4.5", "has no known age")
def _(d):
    m = load(d); V(m, "appearance").pop("i1"); V(m, "appearance")["o1"]["nudity"] = True; V(m, "appearance")["b1"]["nudity"] = True
    m["presets"]["default"]["slots"]["appearance"] = ["o1"]; m["presets"]["default"].pop("age_override", None); m["presets"]["default"]["slots"]["identity_weights"] = []; save(d, m)

@case("nude-thumbnail", "the file thumbnail (thumbnail_source, default primary image) never shows nudity or intimate content", "§ 1.1", "shows nudity or intimate content")
def _(d): m = load(d); V(m, "appearance")["b1"]["nudity"] = True; V(m, "appearance")["o1"]["nudity"] = True; m["thumbnail_source"] = "a-body-front"; save(d, m)

@case("cast-root-consent-mismatch", "in a cast, rights.consent is a copy of the default character's record", "§ 9.2", "must be a copy of identities")
def _(d):
    m = two_characters(load(d)); cons = {"subject_is_real_person": True, "scope": ["likeness-image", "nudity"], "granted": "2026-10-10", "jurisdictions": ["FR"], "proof": [{"type": "signed-document"}]}
    m["identities"]["marc"].update(fictional=False, consent=cons); m["rights"]["consent"] = cons; save(d, m)

@case("weights-without-base-model", "identity weights declare their base model", "§ 4.6", "base_model")
def _(d):
    m = load(d)
    w = V(m, "identity_weights")["l1"]; spec = d / w["spec"]; j = json.loads(spec.read_text("utf-8")); j.pop("base_model", None); spec.write_text(json.dumps(j), "utf-8")

@case("pickle-file", "pickles (.pt/.pth/.ckpt/.pkl) are always refused", "§ 9.3", "pickle")
def _(d):
    m = load(d); p = d / "elements/identity_weights/l1/weights.pt"; p.parent.mkdir(parents=True, exist_ok=True); p.write_bytes(b"\x80\x02}q\x00.")
    m["assets"].append({"id": "a-pt", "path": "elements/identity_weights/l1/weights.pt", "role": "other", "mediaType": "application/octet-stream", "license": "CC-BY-4.0"}); refresh_asset_index(d, m); save(d, m)

@case("invalid-safetensors", "a .safetensors file has a readable header that fits the file (a renamed pickle is refused)", "§ 4.6", "invalid safetensors")
def _(d):
    m = load(d); p = d / "elements/identity_weights/l1/fake.safetensors"; p.parent.mkdir(parents=True, exist_ok=True); p.write_bytes(b"\x80\x04K\x01.")
    m["assets"].append({"id": "a-st", "path": "elements/identity_weights/l1/fake.safetensors", "role": "weights", "mediaType": "application/octet-stream", "license": "CC-BY-4.0", "base_model": "FLUX.1-dev"}); refresh_asset_index(d, m); save(d, m)

@case("undeclared-script", "scripts require container.executableContent", "§ 9.3", "undeclared executable content")
def _(d):
    m = load(d); p = d / "elements/files/f9/run.py"; p.parent.mkdir(parents=True); p.write_text("print('hi')\n", "utf-8")
    m["assets"].append({"id": "a-py", "path": "elements/files/f9/run.py", "role": "skill-file", "mediaType": "text/x-python", "license": "CC-BY-4.0"})
    m["elements"]["files"] = {"variants": {"f9": {"kind": "skill", "files": ["a-py"]}}}; refresh_asset_index(d, m); save(d, m)

@case("obj-not-self-contained", "3D variants are single self-contained files (unless self_contained: false)", "§ 2.2", "not self-contained")
def _(d):
    m = load(d); p = d / "elements/volume3d/m1/avatar.obj"; p.parent.mkdir(parents=True); p.write_text("v 0 0 0\n", "utf-8")
    m["assets"].append({"id": "a-obj", "path": "elements/volume3d/m1/avatar.obj", "role": "mesh", "mediaType": "model/obj", "license": "CC-BY-4.0"})
    m["elements"]["volume3d"] = {"variants": {"m1": {"kind": "mesh", "path": "elements/volume3d/m1/avatar.obj", "age": {"value": 34, "unit": "years", "basis": "declared"}}}}; refresh_asset_index(d, m); save(d, m)

@case("tag-unknown-preset", "every preset listed by a tag exists", "§ 2.3", "unknown preset")
def _(d): m = load(d); m["preset_tags"] = [{"id": "x", "label": "X", "presets": ["nope"]}]; save(d, m)

@case("illegal-coherence-finding", "a coherence finding of severity `illegal` makes the file invalid", "§ 11.2 / § 9.4", "illegal")
def _(d): m = load(d); m["presets"]["young"]["coherence"] = {"score": 0, "method": "human", "computed_by": "negative-corpus", "issues": [{"severity": "illegal", "message": "suggestive pose in a preset under 18 (test case, no image involved)"}]}; save(d, m)


# ---------- memories (RFC 0002, 1.1): the base gains one memory node, then one rule is violated per file ----------
def with_memory(d, node=None, variant=None):
    """Add a memory node `m1` to the base (cof 1.1); the default adult preset lists it."""
    m = load(d); m["cof"] = "1.1"
    nd = {"gist": {"en": "The summer I was eight: the house and the garden."}, "when": {"age": {"value": 8}}, "fidelity": "faded"}
    if node:
        nd.update(node)
    (d / "elements/memories/m1").mkdir(parents=True, exist_ok=True)
    (d / "elements/memories/m1/memory.json").write_text(json.dumps(nd), "utf-8")
    v = {"kind": "moment", "label": "Grandmother's house", "memory": "elements/memories/m1/memory.json"}
    if variant:
        v.update(variant)
    m["elements"]["memories"] = {"variants": {"m1": v}}
    m["presets"]["default"]["slots"]["memories"] = ["m1"]
    save(d, m); return m

@case("memory-in-a-1.0-file", "a file declares the lowest minor that defines what it uses: memories need cof 1.1", "RFC 0002 § 7", "declare cof")
def _(d): m = with_memory(d); m["cof"] = "1.0"; save(d, m)

@case("memory-without-node-file", "a memory variant names its node file", "RFC 0002 § 4.1", "node file")
def _(d): m = with_memory(d); V(m, "memories")["m1"].pop("memory"); save(d, m)

@case("memory-without-gist", "the gist is the only required field of a node", "RFC 0002 § 3", "gist")
def _(d): with_memory(d); (d / "elements/memories/m1/memory.json").write_text(json.dumps({"when": {"age": {"value": 8}}}), "utf-8")

@case("memory-link-unresolved", "a link points to an existing node, qualified <category>/<id>", "RFC 0002 § 3.1", "unknown node")
def _(d): with_memory(d, node={"links": [{"to": "memories/zz", "type": "about"}]})

@case("memory-period-with-point-when", "a period's when has from / to, a moment's is a point", "RFC 0002 § 4.2", "period's `when`")
def _(d): with_memory(d, variant={"kind": "period"})

@case("memory-explicit-without-nudity-flag", "an explicit node also carries the 1.0 flag nudity: true and the file tags.content", "RFC 0002 § 5.3", "nudity: true")
def _(d): with_memory(d, node={"explicit": "nudity", "who": [{"identity": "self", "shown": True}]}, variant={"age": {"value": 34, "unit": "years"}})

@case("memory-explicit-shows-minor", "every person shown in an explicit node has a known age of 18 or more", "RFC 0002 § 5.4", "under 18")
def _(d): with_memory(d, node={"explicit": "nudity", "who": [{"identity": "self", "shown": True}]}, variant={"age": {"value": 8, "unit": "years"}, "nudity": True})

@case("memory-explicit-shown-unknown-age", "an unknown age never counts as adult: an explicit node needs every shown person's age", "RFC 0002 § 5.4", "known age of 18")
def _(d): with_memory(d, node={"explicit": "nudity", "who": [{"identity": "self", "shown": True}, {"label": {"en": "a friend"}, "shown": True}]}, variant={"age": {"value": 34, "unit": "years"}, "nudity": True})

@case("memory-explicit-real-third-party", "a real person shown nude must be a consenting identity of the file", "RFC 0002 § 5.5", "real person")
def _(d): with_memory(d, node={"explicit": "nudity", "who": [{"identity": "self", "shown": True}, {"label": {"en": "my ex"}, "real": True, "shown": True, "age": {"value": 40}}]}, variant={"age": {"value": 34, "unit": "years"}, "nudity": True})

@case("memory-shows-self-without-age", "a node whose media show the character carries the character's age at the time", "RFC 0002 § 5.2", "must carry `age`")
def _(d): with_memory(d, node={"who": [{"identity": "self", "shown": True}]})

@case("memory-media-and-media-from", "media and media_from are exclusive", "RFC 0002 § 4.5", "exclusive")
def _(d):
    m = with_memory(d); V(m, "memories")["m2"] = {"kind": "moment", "label": "Two", "memory": "elements/memories/m1/memory.json", "media": ["a-head-front"], "media_from": "memories/m1"}; save(d, m)

@case("memory-showing-minor-with-intimate-preset", "a memory showing the character under 18 makes the preset a minor preset: no intimate content there", "RFC 0002 § 5.2", "intimate")
def _(d): with_memory(d, node={"who": [{"identity": "self", "shown": True}]}, variant={"age": {"value": 8, "unit": "years", "basis": "canonical"}})

# ---------- archive-level cases (pack the valid base, then tamper) ----------
def rewrite(src: Path, dst: Path, entries):
    with zipfile.ZipFile(dst, "w") as z:
        for name, data, ct in entries:
            zi = zipfile.ZipInfo(name, date_time=(1980, 1, 1, 0, 0, 0)); zi.compress_type = ct; z.writestr(zi, data)

def entries_of(cof: Path):
    with zipfile.ZipFile(cof) as z:
        return [(i.filename, z.read(i.filename), i.compress_type) for i in z.infolist()]

ARCHIVE = []
def acase(name, rule, section, expect):
    def deco(fn):
        ARCHIVE.append((name, rule, section, expect, fn)); return fn
    return deco

@acase("mimetype-not-first", "`mimetype` is the first entry", "§ 1.1", "mimetype")
def _(e): return [e[1], e[0]] + e[2:]

@acase("mimetype-compressed", "`mimetype` is stored without compression", "§ 1.1", "mimetype")
def _(e): return [(e[0][0], e[0][1], zipfile.ZIP_DEFLATED)] + e[1:]

@acase("wrong-mimetype", "`mimetype` contains application/vnd.cof.character+zip", "§ 1.1", "mimetype")
def _(e): return [(e[0][0], b"application/zip", zipfile.ZIP_STORED)] + e[1:]

@acase("path-traversal", "no `..` or absolute paths", "§ 1.1", "..")
def _(e): return e + [("../evil.txt", b"x", zipfile.ZIP_DEFLATED)]

@acase("hash-mismatch", "every asset matches its declared sha256", "§ 2.6", "sha256")
def _(e):
    i = next(k for k, x in enumerate(e) if x[0].endswith(".jpg"))
    return e[:i] + [(e[i][0], e[i][1] + b"\0", e[i][2])] + e[i + 1:]

@acase("asset-missing", "every declared asset is present", "§ 2.6", "missing")
def _(e):
    i = next(k for k, x in enumerate(e) if x[0].endswith(".jpg"))
    return e[:i] + e[i + 1:]

def main():
    sys.path.insert(0, str(ROOT / "cli"))
    from cof_cli.validate import validate_cof
    for f in OUT.glob("*.cof"):
        f.unlink()
    out = []
    with tempfile.TemporaryDirectory() as td:
        td = Path(td); b = base(td)
        pack(b, OUT / "_base.cof")
        assert validate_cof(OUT / "_base.cof").ok, validate_cof(OUT / "_base.cof").errors
        for name, rule, section, expect, fn in CASES:
            d = td / name; shutil.copytree(b, d); fn(d); pack(d, OUT / f"{name}.cof", refresh=False)
            out.append({"file": f"{name}.cof", "rule": rule, "spec": section, "expect": expect})
        base_entries = entries_of(OUT / "_base.cof")
        for name, rule, section, expect, fn in ARCHIVE:
            rewrite(None, OUT / f"{name}.cof", fn(list(base_entries)))
            out.append({"file": f"{name}.cof", "rule": rule, "spec": section, "expect": expect})
    (OUT / "cases.json").write_text(json.dumps({"base": "_base.cof (valid)", "cases": out}, ensure_ascii=False, indent=2) + "\n", "utf-8")
    bad = []
    for c in out:
        rep = validate_cof(OUT / c["file"])
        hit = any(c["expect"].lower() in e.lower() for e in rep.errors)
        print(("ok  " if (not rep.ok and hit) else "BAD ") + c["file"], "" if hit else rep.errors[:3])
        if rep.ok or not hit:
            bad.append(c["file"])
    sys.exit(1 if bad else 0)

if __name__ == "__main__":
    main()
