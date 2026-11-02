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
        raise ValueError("this manifest is not v0.2")
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
        f = {"label": "Face", "images": [a["id"] for a in head]}
        if app.get("face"):
            f["params"] = move(app["face"], "elements/face/f1/face.json")
        elements["face"] = {"variants": {"f1": f}}; slots["face"] = "f1"
    if body or app.get("body"):
        b = {"label": "Body", "images": [a["id"] for a in body]}
        if app.get("body"):
            b["params"] = move(app["body"], "elements/body/b1/body.json")
        elements["body"] = {"variants": {"b1": b}}; slots["body"] = "b1"
    if app.get("hair"):
        elements["hair"] = {"variants": {"h1": {"label": "Hair", "code": move(app["hair"], "elements/hair/h1/hair.json")}}}; slots["hair"] = "h1"
    for i, o in enumerate(app.get("outfits", []) or [], 1):
        elements.setdefault("outfit", {"variants": {}})["variants"][f"o{i}"] = {"label": f"Outfit {i}", "spec": move(o, f"elements/outfit/o{i}/outfit.json")}
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
        v = {"label": "Voice", "profile": move(sec["voice"], "elements/voice/v1/profile.json"),
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
    m["presets"] = {"default": {"label": "Default", "slots": slots}}
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
        raise ValueError("this manifest is not v0.3")
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
        raise ValueError("this manifest is not v0.4")
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
        m = migrate_v4_to_v5(src); v = "0.5"
    changed = False
    if v == "0.5":                                   # 0.5 → 1.0: version number only (structure frozen as is)
        m["cof"] = "1.0"; changed = True
    if m.get("preset_groups") is not None:          # builder 0.8.0 (short-lived) → preset_tags
        tags = m.setdefault("preset_tags", [])
        known = {t.get("id") for t in tags}
        for g in m.pop("preset_groups") or []:
            if g.get("id") not in known:
                tags.append({"id": g.get("id"), "label": g.get("label") or g.get("id"), "presets": list(g.get("presets") or [])})
        if not tags:
            m.pop("preset_tags")
        changed = True
    if not (m.get("presets") or {}) and len(m.get("identities") or {}) <= 1:
        # 1.0 requires a preset: 'default' applies every variant except intimate ones (never applied by default)
        slots = {}
        for cat, e in (m.get("elements") or {}).items():
            vids = [vid for vid, v in ((e or {}).get("variants") or {}).items() if not (cat == "appearance" and (v or {}).get("kind") == "intimate")]
            if vids:
                slots[cat] = vids
        m["presets"] = {"default": {"label": "Default", "slots": slots}}
        m["default_preset"] = "default"
        changed = True
    if changed:
        (src / "manifest.json").write_text(json.dumps(m, ensure_ascii=False, indent=2) + "\n", "utf-8")
    return m


# ---------------- 1.0 / 1.1 lists → psyche nodes (RFC 0004 § 3 quater) ----------------

def _norm(text: str) -> str:
    import unicodedata
    return " ".join(unicodedata.normalize("NFKD", str(text)).encode("ascii", "ignore").decode().lower().split()).rstrip(".")


def _value_gist(word: str) -> str:
    """A one-word value becomes a short gist the author completes: "sobriety" → "Sobriety." (§ 3 quater)."""
    w = " ".join(str(word).split())
    w = w[:1].upper() + w[1:]
    return w if w.endswith((".", "!", "?")) else w + "."


def _label(text: str, limit: int = 60) -> str:
    """A variant label from a gist: the whole text when short, else cut at a word boundary."""
    t = " ".join(str(text).split()).rstrip(" .")
    if len(t) <= limit:
        return t
    cut = t.rfind(" ", 0, limit)
    return (t[:cut] if cut > 20 else t[:limit]).rstrip(" ,;:—–")


def _lists_of(src: Path, m: dict, vid: str, v: dict) -> dict[str, list[tuple[str | None, str]]]:
    """The 1.0 lists of one personality variant as (id, text) pairs per target kind: psyche.json goals / fears / values,
    the card extensions cof.goals / cof.fears / cof.behavior. An extension entry that names a psyche.json id or repeats
    its text is the same item."""
    out: dict[str, list[tuple[str | None, str]]] = {"want": [], "fear": [], "value": [], "habit": []}
    ps, card = {}, {}
    try:
        ps = json.loads((src / v["psyche"]).read_text("utf-8")) if v.get("psyche") and (src / v["psyche"]).is_file() else {}
    except (OSError, ValueError):
        ps = {}
    try:
        card = (json.loads((src / v["card"]).read_text("utf-8")) if v.get("card") and (src / v["card"]).is_file() else {}).get("data") or {}
    except (OSError, ValueError):
        card = {}
    ps = ps if isinstance(ps, dict) else {}
    for kind, key in (("want", "goals"), ("fear", "fears")):
        for g in ps.get(key) or []:
            if isinstance(g, dict) and str(g.get("text") or "").strip():
                out[kind].append((str(g.get("id")) if g.get("id") else None, str(g["text"]).strip()))
            elif isinstance(g, str) and g.strip():
                out[kind].append((None, g.strip()))
    for w in ps.get("values") or []:
        if isinstance(w, str) and w.strip():
            out["value"].append((None, _value_gist(w)))
    ext = ((card.get("extensions") or {}).get("cof") or {}) if isinstance(card, dict) else {}
    for kind, key in (("want", "goals"), ("fear", "fears"), ("habit", "behavior")):
        for x in ext.get(key) or []:
            if not isinstance(x, str) or not x.strip():
                continue
            x = x.strip()
            if any(i == x or _norm(t) == _norm(x) for i, t in out[kind]):      # the id of a psyche.json entry, or its text again
                continue
            out[kind].append((None, x))
    for kind in out:                                                        # duplicates within one list, by text
        seen, uniq = set(), []
        for i, t in out[kind]:
            if _norm(t) not in seen:
                seen.add(_norm(t)); uniq.append((i, t))
        out[kind] = uniq
    return out


def migrate_psyche(src: Path) -> dict:
    """`cof migrate --psyche`: the 1.0 / 1.1 lists (psyche.json goals / fears / values, card extensions cof.goals /
    cof.fears / cof.behavior) become psyche nodes — `want` (strength 70), `fear` (70), `value` (one word → "Word."),
    `habit` — written under elements/psyche/<id>/psyche-node.json, declared in the manifest and listed by every preset
    that holds the personality variant they come from; the file declares cof 1.2. The lists stay (a 1.0 reader needs
    them; RFC 0004 § 3 quater). Across the personality variants of one character, entries sharing a psyche.json id, or
    sitting at the same position in lists of equal length written in different languages, are one node with a gist per
    language. A character whose psyche already holds nodes is left alone (the conversion is for a file with lists and no
    psyche; its unmatched entries are counted so the author can add them with `cof psyche add`). Idempotent: an entry
    whose text (in any language) a node of the same kind already carries is skipped.
    Returns {"written": [ids], "skipped": n, "untouched": {character: n unmatched entries}, "manifest": m}."""
    from .model import resolve_preset_slots, variant_owner
    mpath = src / "manifest.json"
    m = json.loads(mpath.read_text("utf-8"))
    E = m.setdefault("elements", {})
    P = m.get("presets") or {}
    ids = m.get("identities") or {}
    pers = ((E.get("personality") or {}).get("variants")) or {}
    existing = ((E.get("psyche") or {}).get("variants")) or {}
    # what the nodes already say, by kind: (identity, normalised text) for every language of every gist
    known: set[tuple[str, str | None, str]] = set()
    for vid, v in existing.items():
        rel = v.get("node")
        try:
            node = json.loads((src / rel).read_text("utf-8")) if rel else {}
        except (OSError, ValueError):
            node = {}
        for t in (node.get("gist") or {}).values():
            known.add((v.get("kind"), variant_owner(m, "psyche", vid), _norm(t)))
    # candidates per character: kind → list of {"lang": text, ...} items, merged by id / text / position
    per_char: dict[str | None, dict[str, list[dict]]] = {}
    sources: dict[str | None, dict[str, dict[int, set[str]]]] = {}   # character → kind → item index → personality variants it came from
    for pvid, pv in pers.items():
        if pv.get("derives_from"):
            continue
        lists = _lists_of(src, m, pvid, pv)
        owner = variant_owner(m, "personality", pvid)
        lang = pv.get("language") or (ids.get(owner or "") or {}).get("language") or (m.get("languages") or ["en"])[0]
        for kind, entries in lists.items():
            if not entries:
                continue
            items = per_char.setdefault(owner, {}).setdefault(kind, [])
            srcs = sources.setdefault(owner, {}).setdefault(kind, {})
            # an earlier variant whose list of this kind has the same length and no entry in this language: positions
            # align (a card written twice, once per language)
            aligned: dict[int, int] = {}
            for b in dict.fromkeys(it["_batch"] for it in items):
                bi = [k for k, it in enumerate(items) if it["_batch"] == b]
                if len(bi) == len(entries) and all(lang not in items[k] for k in bi):
                    aligned = {pos: k for pos, k in enumerate(bi)}
                    break
            for pos, (eid, text) in enumerate(entries):
                hit = next((k for k, it in enumerate(items) if (eid and it.get("_id") == eid)
                            or any(_norm(t) == _norm(text) for kk, t in it.items() if not kk.startswith("_"))), None)
                if hit is None:
                    hit = aligned.get(pos)
                if hit is None:
                    items.append({"_batch": pvid, "_id": eid, lang: text}); hit = len(items) - 1
                else:
                    items[hit].setdefault(lang, text)
                    if eid and not items[hit].get("_id"):
                        items[hit]["_id"] = eid
                srcs.setdefault(hit, set()).add(pvid)
    # write the nodes
    from .psyche import ID_PREFIX
    from .selfdesc import _next_id
    V = E.setdefault("psyche", {}).setdefault("variants", {})
    written: list[str] = []
    skipped = 0
    untouched: dict[str | None, int] = {}
    has_nodes = {variant_owner(m, "psyche", vid) for vid in existing}
    strength = {"want": 70, "fear": 70}                                 # § 3 quater: goals and fears at 70; values and habits left to the author (default 50)
    per_variant_nodes: dict[str, list[str]] = {}
    for owner, kinds in per_char.items():
        for kind, items in kinds.items():
            for k, it in enumerate(items):
                gist = {kk: t for kk, t in it.items() if not kk.startswith("_")}
                if any((kind, owner, _norm(t)) in known for t in gist.values()):
                    skipped += 1; continue
                if owner in has_nodes:                                  # a psyche exists: the author decomposed it by hand, the lists are not poured on top
                    untouched[owner] = untouched.get(owner, 0) + 1; continue
                vid = _next_id(V, ID_PREFIX[kind])
                node: dict = {"gist": gist}
                if kind in strength:
                    node["strength"] = strength[kind]
                node.update({"stability": "settled", "origin": "authored", "visibility": "canon", "disclosure": "open"})
                d = src / "elements" / "psyche" / vid
                d.mkdir(parents=True, exist_ok=True)
                (d / "psyche-node.json").write_text(json.dumps(node, ensure_ascii=False, indent=2) + "\n", "utf-8")
                first = next(iter(gist.values()))
                var: dict = {"kind": kind, "label": _label(first), "node": f"elements/psyche/{vid}/psyche-node.json"}
                if owner and (len(ids) > 1 or (ids and any(v.get("identity") for e in E.values() for v in (e.get("variants") or {}).values()))):
                    var["identity"] = owner
                if kind in strength:
                    var["strength"] = strength[kind]
                V[vid] = var
                for t in gist.values():
                    known.add((kind, owner, _norm(t)))
                written.append(vid)
                for pvid in sources[owner][kind].get(k, set()):
                    per_variant_nodes.setdefault(pvid, []).append(vid)
    if not V:
        E.pop("psyche", None)                                           # nothing to convert and no category before: none after
    # every preset that holds a converted personality variant lists the nodes it yielded
    for pid, p in P.items():
        held = resolve_preset_slots(m, pid)
        want_nodes = [n for pvid in (held.get("personality") or []) for n in per_variant_nodes.get(pvid, [])]
        have = held.get("psyche") or []
        missing = [n for n in want_nodes if n not in have]
        if missing:
            p.setdefault("slots", {})["psyche"] = list(have) + missing
    if written:
        try:
            if tuple(int(x) for x in str(m.get("cof", "1.0")).split(".")[:2]) < (1, 2):
                m["cof"] = "1.2"
        except ValueError:
            m["cof"] = "1.2"
        tags = m.setdefault("tags", {}); auto = tags.setdefault("auto", [])
        if "has-psyche" not in auto:
            auto.append("has-psyche")
        cov = m.setdefault("coverage", {})
        if "psyche" not in (cov.get("elements") or []):
            cov["elements"] = sorted(set(cov.get("elements") or []) | {"psyche"})
        from datetime import datetime, timezone
        m.setdefault("provenance", {})["modified"] = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    mpath.write_text(json.dumps(m, ensure_ascii=False, indent=2) + "\n", "utf-8")
    return {"written": written, "skipped": skipped, "untouched": untouched, "manifest": m}
