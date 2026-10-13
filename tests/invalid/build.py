"""Build the negative conformance corpus: one rule violated per file.

    python tests/invalid/build.py        # regenerates tests/invalid/*.cof and cases.json

Every `.cof` here MUST be rejected by a conformant validator. The base file (`_base.cof`, valid) is a
shrunk copy of spec/examples/09-mixte-adulte-mineur: an adult preset with intimate content and a minor preset.
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
    d = tmp / "base"; shutil.copytree(ROOT / "spec/examples/09-mixte-adulte-mineur", d)
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

@case("real-person-without-consent", "a non-fictional character requires consent", "§ 9.2", "consent")
def _(d): m = load(d); m["fictional"] = False; m.get("rights", {}).pop("consent", None); [i.update(fictional=False) for i in (m.get("identities") or {}).values()]; save(d, m)

@case("weights-without-base-model", "identity weights declare their base model", "§ 4.6", "base_model")
def _(d):
    m = load(d)
    w = V(m, "identity_weights")["l1"]; spec = d / w["spec"]; j = json.loads(spec.read_text("utf-8")); j.pop("base_model", None); spec.write_text(json.dumps(j), "utf-8")

@case("pickle-file", "pickles (.pt/.pth/.ckpt/.pkl) are always refused", "§ 9.3", "pickle")
def _(d):
    m = load(d); p = d / "elements/identity_weights/l1/weights.pt"; p.parent.mkdir(parents=True, exist_ok=True); p.write_bytes(b"\x80\x02}q\x00.")
    m["assets"].append({"id": "a-pt", "path": "elements/identity_weights/l1/weights.pt", "role": "other", "mediaType": "application/octet-stream", "license": "CC-BY-4.0"}); refresh_asset_index(d, m); save(d, m)

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
