"""v0.2 → v0.3 migration: sections/appearance/… → elements/<type>/<v1>/…, implicit preset 'default', asset ids."""
from __future__ import annotations

import json
import re
import shutil
from pathlib import Path


def _aid(path: str) -> str:
    return "a-" + re.sub(r"[^a-z0-9-]+", "-", path.lower().rsplit("/", 1)[-1].rsplit(".", 1)[0]).strip("-")


def migrate_dir(src: Path) -> dict:
    m = json.loads((src / "manifest.json").read_text("utf-8"))
    if not str(m.get("cof", "")).startswith("0.2"):
        raise ValueError("ce manifeste n'est pas en v0.2")
    sec = m.pop("sections", {}) or {}
    comp = m.pop("completeness", None)
    assets = m.get("assets", [])
    elements, slots = {}, {}

    def move(rel: str, newrel: str):
        s, d = src / rel, src / newrel
        if s.is_file():
            d.parent.mkdir(parents=True, exist_ok=True)
            shutil.move(str(s), str(d))
        for a in assets:
            if a.get("path") == rel:
                a["path"] = newrel
            if a.get("transcript") == rel:
                a["transcript"] = newrel
        return newrel

    # ids on assets
    for a in assets:
        a.setdefault("id", _aid(a.get("path") or a.get("uri") or "asset"))
    ids = {}
    for a in assets:
        base = a["id"]; n = 1
        while a["id"] in ids:
            n += 1; a["id"] = f"{base}-{n}"
        ids[a["id"]] = a

    # personality
    if sec.get("character"):
        v = {"label": m.get("name"), "card": move(sec["character"], "elements/personality/p1/card.json")}
        if sec.get("psyche"):
            v["psyche"] = move(sec["psyche"], "elements/personality/p1/psyche.json")
        if sec.get("story"):
            v["story"] = move(sec["story"], "elements/personality/p1/story.md")
        if sec.get("lorebook"):
            v["lorebook"] = move(sec["lorebook"], "elements/personality/p1/lorebook.json")
        if m.get("profiles"):
            v["profiles"] = m.pop("profiles")
        elements["personality"] = {"variants": {"p1": v}}
        slots["personality"] = "p1"

    # appearance → face / body (+ hair/outfit when files exist)
    app = sec.get("appearance", {}) or {}
    views = [a for a in assets if a.get("role") in ("view", "expression", "reference")]
    head = [a for a in views if a.get("subject") == "head"]
    body = [a for a in views if a.get("subject") != "head"]
    for a in head:
        a["path"] = move(a["path"], "elements/face/f1/" + a["path"].rsplit("/", 1)[-1])
    for a in body:
        a["path"] = move(a["path"], "elements/body/b1/" + a["path"].rsplit("/", 1)[-1])
    if head or app.get("face"):
        f = {"label": "Visage", "images": [a["id"] for a in head]}
        if app.get("face"):
            f["params"] = move(app["face"], "elements/face/f1/face.json")
        elements["face"] = {"variants": {"f1": f}}; slots["face"] = "f1"
    if body or app.get("body"):
        b = {"label": "Corps", "images": [a["id"] for a in body]}
        if app.get("body"):
            b["params"] = move(app["body"], "elements/body/b1/body.json")
        elements["body"] = {"variants": {"b1": b}}; slots["body"] = "b1"
    if app.get("hair"):
        elements["hair"] = {"variants": {"h1": {"label": "Cheveux", "code": move(app["hair"], "elements/hair/h1/hair.json")}}}; slots["hair"] = "h1"
    for i, o in enumerate(app.get("outfits", []) or [], 1):
        elements.setdefault("outfit", {"variants": {}})["variants"][f"o{i}"] = {"label": f"Tenue {i}", "spec": move(o, f"elements/outfit/o{i}/outfit.json")}
        slots.setdefault("outfit", f"o{i}")

    # derived_from: path → asset id
    by_path_tail = {}
    for a in assets:
        if a.get("path"):
            by_path_tail[a["path"].rsplit("/", 1)[-1]] = a["id"]
    for a in assets:
        df = a.get("derived_from")
        if isinstance(df, str) and "/" in df:
            a["derived_from"] = by_path_tail.get(df.rsplit("/", 1)[-1], a["id"])

    # line maps → derived
    derived_ids = []
    for a in assets:
        if a.get("role") == "line-map":
            a["role"] = "derived"
            src_view = a.pop("source_view", None)
            a["source"] = next((x["id"] for x in assets if x.get("path") == src_view or x.get("path", "").endswith("/" + (src_view or "").rsplit("/", 1)[-1])), a.get("id"))
            etype = "face" if "head." in a["path"] else "body"
            a["path"] = move(a["path"], f"derived/{etype}/{'f1' if etype == 'face' else 'b1'}/" + a["path"].rsplit("/", 1)[-1])
            derived_ids.append((etype, a["id"]))
    for etype, aid in derived_ids:
        vid = "f1" if etype == "face" else "b1"
        if etype in elements:
            elements[etype]["variants"][vid].setdefault("derived", []).append(aid)

    # voice / attitude / avatar / motion
    if sec.get("voice"):
        v = {"label": "Voix", "profile": move(sec["voice"], "elements/voice/v1/profile.json"),
             "samples": [a["id"] for a in assets if a.get("role") == "voice-sample"]}
        if sec.get("voice_vec"):
            v["vec"] = move(sec["voice_vec"], "elements/voice/v1/voice.vec.json")
        elements["voice"] = {"variants": {"v1": v}}; slots["voice"] = "v1"
    if sec.get("physique"):
        elements["attitude"] = {"variants": {"m1": {"spec": move(sec["physique"], "elements/attitude/m1/attitude.json")}}}; slots["attitude"] = "m1"
    vol = sec.get("volume", {}) or {}
    if vol.get("avatar"):
        elements["avatar"] = {"variants": {"av1": {"path": move(vol["avatar"], "elements/avatar/av1/" + vol["avatar"].rsplit("/", 1)[-1]),
                                                   "rig": m.get("mapping_vocabularies", {}).get("skeleton", "VRMC_vrm-1.0")}}}; slots["avatar"] = "av1"
    mot = sec.get("motion", {}) or {}
    clips = [a["id"] for a in assets if a.get("role") == "motion-clip"]
    if clips or mot.get("visemes"):
        mo = {"clips": clips}
        if mot.get("visemes"):
            mo["visemes"] = move(mot["visemes"], "elements/motion/mo1/visemes.json")
        elements["motion"] = {"variants": {"mo1": mo}}; slots["motion"] = "mo1"

    # remove now-empty v0.2 dirs
    for d in ("character", "appearance", "voice", "physique", "volume", "motion"):
        p = src / d
        if p.is_dir() and not any(p.rglob("*")):
            shutil.rmtree(p)
        elif p.is_dir():
            for sub in sorted(p.rglob("*"), reverse=True):
                if sub.is_dir() and not any(sub.iterdir()):
                    sub.rmdir()
            if not any(p.rglob("*")):
                shutil.rmtree(p)

    m["cof"] = "0.3"
    m["elements"] = elements
    m["presets"] = {"default": {"label": "Défaut", "slots": slots}}
    m["default_preset"] = "default"
    m.setdefault("priorities", {"visual": ["identity_weights", "images", "avatar", "descriptive"], "voice": ["samples", "described"]})
    m.pop("injection_order", None)
    m["tags"]["auto"] = [t for t in m.get("tags", {}).get("auto", []) if t not in ("line-maps", "vector-face")]
    # reorder keys for readability
    order = ["cof", "id", "name", "nickname", "age", "languages", "summary", "fictional", "morphology", "tags", "thumbnail",
             "elements", "presets", "default_preset", "priorities", "completeness", "coverage", "mapping_vocabularies",
             "assets", "size_class", "container", "rights", "provenance", "metadata", "extensions"]
    m = {k: m[k] for k in order if k in m} | {k: v for k, v in m.items() if k not in order}
    (src / "manifest.json").write_text(json.dumps(m, ensure_ascii=False, indent=2) + "\n", "utf-8")
    return m


# ---------------- v0.3 → v0.4 : categories + kind, multi-slots ----------------

V3_TO_V4 = {  # old element type → (category, kind, extra)
    "personality": ("personality", "card", {}), "face": ("appearance", "face", {}), "hair": ("appearance", "hair", {}),
    "facial_hair": ("appearance", "pilosity", {"area": "face"}), "body": ("appearance", "body", {}), "body_hair": ("appearance", "pilosity", {"area": "body"}),
    "intimate": ("appearance", "intimate", {}), "outfit": ("appearance", "clothing", {"garment": "full-outfit"}), "accessories": ("appearance", "accessory", {}),
    "identity_weights": ("identity_weights", "lora", {}), "voice": ("voice", "samples", {}), "attitude": ("posture", "attitude", {}),
    "avatar": ("volume3d", "mesh", {}), "motion": ("motion", "clips", {}),
}


def migrate_v3_to_v4(src: Path) -> dict:
    m = json.loads((src / "manifest.json").read_text("utf-8"))
    if str(m.get("cof", "")) != "0.3":
        raise ValueError("ce manifeste n'est pas en v0.3")
    old = m.get("elements", {}) or {}
    new: dict = {}
    remap: dict[tuple[str, str], tuple[str, str]] = {}
    for etype, e in old.items():
        if etype not in V3_TO_V4:
            continue
        cat, kind, extra = V3_TO_V4[etype]
        for vid, v in (e.get("variants") or {}).items():
            nv = {"kind": kind, **extra, **v}
            if etype == "personality" and nv.get("card") is None:
                nv["kind"] = "description"
            if etype == "voice" and not nv.get("samples"):
                nv["kind"] = "described"
            if etype == "identity_weights":
                try:
                    w = json.loads((src / nv["spec"]).read_text("utf-8")) if nv.get("spec") else {}
                    nv["kind"] = w.get("kind", "lora"); nv["covers"] = w.get("covers", [])
                except Exception:
                    pass
            # move files to the new folder
            for fld in ("card", "psyche", "story", "lorebook", "params", "code", "spec", "profile", "vec", "visemes", "path", "skeleton"):
                rel = nv.get(fld)
                if isinstance(rel, str) and rel.startswith(f"elements/{etype}/"):
                    newrel = rel.replace(f"elements/{etype}/", f"elements/{cat}/", 1)
                    s_, d_ = src / rel, src / newrel
                    if s_.is_file():
                        d_.parent.mkdir(parents=True, exist_ok=True); shutil.move(str(s_), str(d_))
                    nv[fld] = newrel
            new.setdefault(cat, {"variants": {}})["variants"][vid] = nv
            remap[(etype, vid)] = (cat, vid)
    # asset paths under elements/<old>/ → elements/<cat>/
    for a in m.get("assets", []):
        for fld in ("path", "transcript"):
            rel = a.get(fld)
            if isinstance(rel, str) and rel.startswith("elements/"):
                parts = rel.split("/")
                if parts[1] in V3_TO_V4:
                    newrel = "/".join([parts[0], V3_TO_V4[parts[1]][0]] + parts[2:])
                    s_, d_ = src / rel, src / newrel
                    if s_.is_file():
                        d_.parent.mkdir(parents=True, exist_ok=True); shutil.move(str(s_), str(d_))
                    a[fld] = newrel
    for d in list((src / "elements").glob("*")) if (src / "elements").is_dir() else []:
        if d.is_dir() and not any(d.rglob("*")):
            shutil.rmtree(d)
    # presets: slots → lists per category
    for pid, p in (m.get("presets") or {}).items():
        slots: dict[str, list] = {}
        for etype, vid in (p.get("slots") or {}).items():
            cat = V3_TO_V4.get(etype, (etype,))[0]
            slots.setdefault(cat, []).append(vid)
        p["slots"] = slots
    m["cof"] = "0.4"; m["elements"] = new
    if m.get("morphology", {}).get("class") == "humanoid" and (m["morphology"].get("species") or "human") == "human":
        m["morphology"]["class"] = "human"
    (src / "manifest.json").write_text(json.dumps(m, ensure_ascii=False, indent=2) + "\n", "utf-8")
    return m


AGE_KINDS_V5 = {"face", "body", "character-sheet", "reference-set", "intimate", "hair", "pilosity"}


def migrate_v4_to_v5(src: Path) -> dict:
    """v0.5: age leaves the identity. Identity ages become (a) `age` on the morphological variants that lack one
    (reserved variants take their identity's age, shared ones the default identity's) and (b) `age_override` on
    presets without one (floor for text-only presets). Intimate variants under 18 are NOT fixed: validation will fail."""
    m = json.loads((src / "manifest.json").read_text("utf-8"))
    if str(m.get("cof", "")) != "0.4":
        raise ValueError("ce manifeste n'est pas en v0.4")
    ids = m.get("identities") or {}
    root_age = m.pop("age", None)
    id_ages = {iid: i.pop("age", None) for iid, i in ids.items()}
    default_age = id_ages.get(m.get("default_identity")) or root_age
    for cat in ("appearance", "volume3d", "identity_weights"):
        for vid, v in (((m.get("elements") or {}).get(cat) or {}).get("variants") or {}).items():
            if cat == "appearance" and v.get("kind") not in AGE_KINDS_V5:
                continue
            if v.get("age") is None:
                a = id_ages.get(v.get("identity")) or default_age
                if a:
                    v["age"] = dict(a)
    for pid, p in (m.get("presets") or {}).items():
        if p.get("age_override") is None:
            a = id_ages.get(p.get("identity")) or default_age
            if a:
                p["age_override"] = dict(a)
    m["cof"] = "0.5"
    (src / "manifest.json").write_text(json.dumps(m, ensure_ascii=False, indent=2) + "\n", "utf-8")
    return m


def migrate_any(src: Path) -> dict:
    m = json.loads((src / "manifest.json").read_text("utf-8"))
    v = str(m.get("cof", ""))
    if v == "0.2":
        migrate_dir(src); v = "0.3"
    if v == "0.3":
        m = migrate_v3_to_v4(src); v = "0.4"
    if v == "0.4":
        m = migrate_v4_to_v5(src)
    return m
