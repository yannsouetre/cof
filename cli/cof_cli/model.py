"""Manifest model helpers (v0.5): categories → variants (with `kind`), presets with multi-slots, identities, regions."""
from __future__ import annotations

import json
from importlib import resources

CATEGORIES = ["personality", "appearance", "identity_weights", "volume3d", "voice", "posture", "motion", "files"]
KINDS = {
    "personality": ["card", "description"],
    "appearance": ["reference-set", "character-sheet", "face", "body", "hair", "clothing", "accessory", "intimate", "pilosity", "feature", "environment", "description"],
    "identity_weights": ["lora", "lycoris", "dora", "textual-inversion", "ip-adapter-embedding", "dreambooth", "other"],
    "volume3d": ["mesh", "face-mesh", "point-cloud", "print", "other", "environment", "daz"],
    "voice": ["samples", "described", "embedding"],
    "posture": ["photo", "photos", "openpose", "silhouette", "attitude", "description"],
    "motion": ["clips", "video", "attitude", "description"],   # 'attitude' (movement signature) is allowed here AND in posture
    "files": ["skill", "memory", "document", "other"],          # free files: agent skills, memories, documents — library
}
# categories that are LIBRARIES in a preset: several variants of any kind, none mandatory at inference
LIBRARY_CATEGORIES = {"posture", "motion", "files"}
# kinds that may appear several times in one preset (subject to region rules)
MULTI_KINDS = {"clothing", "accessory", "pilosity", "feature", "environment"}

_garments = None


def garments() -> dict:
    global _garments
    if _garments is None:
        try:
            with resources.files("cof_cli").joinpath("schemas/garments-1.0.json").open("r", encoding="utf-8") as f:
                _garments = json.load(f)
        except Exception:
            _garments = {"types": {}, "accessories": {"types": {}}}
    return _garments


def asset_index(manifest: dict) -> dict[str, dict]:
    return {a["id"]: a for a in manifest.get("assets", []) if "id" in a}


def variants_of(manifest: dict, cat: str) -> dict:
    return ((manifest.get("elements", {}) or {}).get(cat, {}) or {}).get("variants", {}) or {}


def resolve_variant(manifest: dict, cat: str, vid: str, _seen=None) -> dict | None:
    v = variants_of(manifest, cat).get(vid)
    if v is None:
        return None
    _seen = _seen or set()
    if vid in _seen:
        return dict(v)
    _seen.add(vid)
    parent = resolve_variant(manifest, cat, v["derives_from"], _seen) if v.get("derives_from") else None
    merged = dict(parent or {})
    merged.update({k: val for k, val in v.items() if k != "derives_from"})
    merged["_id"] = vid
    return merged


def resolve_preset_slots(manifest: dict, pid: str, _seen=None) -> dict[str, list[str]]:
    presets = manifest.get("presets", {}) or {}
    p = presets.get(pid)
    if p is None:
        return {}
    _seen = _seen or set()
    if pid in _seen:
        return {k: list(v) for k, v in (p.get("slots") or {}).items()}
    _seen.add(pid)
    base = resolve_preset_slots(manifest, p["extends"], _seen) if p.get("extends") else {}
    for k, v in (p.get("slots") or {}).items():
        base[k] = list(v)          # a child replaces the whole category list
    return base


def resolve_preset_alternatives(manifest: dict, pid: str, _seen=None) -> dict[str, list[str]]:
    """Elements OFFERED (not applied) by a preset, as declared; same inheritance rule as slots (see preset_alternatives)."""
    presets = manifest.get("presets", {}) or {}
    p = presets.get(pid)
    if p is None:
        return {}
    _seen = _seen or set()
    if pid in _seen:
        return {k: list(v) for k, v in (p.get("alternatives") or {}).items()}
    _seen.add(pid)
    base = resolve_preset_alternatives(manifest, p["extends"], _seen) if p.get("extends") else {}
    for k, v in (p.get("alternatives") or {}).items():
        base[k] = list(v)
    return base


def preset_alternatives(manifest: dict, pid: str) -> dict[str, list[str]]:
    """Offered elements minus those already applied."""
    slots = resolve_preset_slots(manifest, pid)
    alt = resolve_preset_alternatives(manifest, pid)
    return {k: [x for x in v if x not in slots.get(k, [])] for k, v in alt.items() if [x for x in v if x not in slots.get(k, [])]}


def preset_primary_image(manifest: dict, pid: str | None) -> str | None:
    """Asset id of the preset's primary image: explicit (inherited through extends) or the first image
    of the first face / reference-set / character-sheet / body applied by the preset."""
    presets = manifest.get("presets", {}) or {}
    seen = set()
    q = pid
    while q and q in presets and q not in seen:
        seen.add(q)
        if presets[q].get("primary_image"):
            return presets[q]["primary_image"]
        q = presets[q].get("extends")
    A = asset_index(manifest)
    r = resolved(manifest, pid) if pid else implicit_resolved(manifest)
    for k in ("face", "reference-set", "character-sheet", "body"):
        for v in [x for x in r.get("appearance", []) if x.get("kind") == k]:
            for i in v.get("images", []) or []:
                if i in A and str(A[i].get("mediaType", "")).startswith("image/"):
                    return i
    return None


def backstage(manifest: dict) -> list[tuple[str, str]]:
    """Variants referenced by no preset — neither applied, offered, nor parent (derives_from) of one that is.
    They are kept, never applied nor offered; an explorer MAY show them. Empty when the file has no preset."""
    P = manifest.get("presets") or {}
    if not P:
        return []
    used: set[tuple[str, str]] = set()
    for pid in P:
        for src in (resolve_preset_slots(manifest, pid), resolve_preset_alternatives(manifest, pid)):
            for cat, vids in src.items():
                for vid in vids:
                    cur, seen = vid, set()
                    while cur and cur not in seen:
                        seen.add(cur)
                        used.add((cat, cur))
                        cur = (variants_of(manifest, cat).get(cur) or {}).get("derives_from")
    return [(cat, vid) for cat, e in (manifest.get("elements") or {}).items()
            for vid in ((e or {}).get("variants") or {}) if (cat, vid) not in used]


def facet_switch(manifest: dict, pid: str, tag_id: str) -> list[str]:
    """Facet navigation: the presets carrying `tag_id` whose tags in every OTHER facet equal those of `pid`
    (e.g. from en-12, tag 'fr' → fr-12). Tags without a facet count as their own facet."""
    T = {t.get("id"): t for t in manifest.get("preset_tags") or []}
    if tag_id not in T:
        return []
    fac = lambda tid: T[tid].get("facet") or f"__{tid}"
    target_facet = fac(tag_id)
    tags_of = lambda p: {tid for tid, t in T.items() if p in (t.get("presets") or [])}
    others = lambda p: {x for x in tags_of(p) if fac(x) != target_facet}
    ref = others(pid)
    return [q for q in (manifest.get("presets") or {}) if q in (T[tag_id].get("presets") or []) and others(q) == ref]


def implicit_preset(manifest: dict) -> dict[str, list[str]]:
    slots = {}
    for cat, e in (manifest.get("elements", {}) or {}).items():
        vs = list((e or {}).get("variants", {}).keys())
        if vs:
            slots[cat] = [vs[0]]
    return slots


def preset_ids(manifest: dict) -> list[str]:
    return list((manifest.get("presets", {}) or {}).keys())


def default_preset_id(manifest: dict) -> str | None:
    return manifest.get("default_preset") or (preset_ids(manifest)[0] if preset_ids(manifest) else None)


def resolved(manifest: dict, pid: str | None = None) -> dict[str, list[dict]]:
    """category → list of resolved variants for a preset (or the implicit one)."""
    slots = resolve_preset_slots(manifest, pid) if pid else implicit_preset(manifest)
    out: dict[str, list[dict]] = {}
    for cat, vids in slots.items():
        lst = []
        for vid in vids:
            v = resolve_variant(manifest, cat, vid)
            if v is not None:
                lst.append(v)
        if lst:
            out[cat] = lst
    return out


def resolved_all(manifest: dict, pid: str | None = None) -> dict[str, list[dict]]:
    """Applied ∪ offered variants of a preset (age and minor rules apply to this union)."""
    out = {k: list(v) for k, v in (resolved(manifest, pid) if pid else implicit_resolved(manifest)).items()}
    if not pid:
        return out
    for cat, vids in preset_alternatives(manifest, pid).items():
        have = {v["_id"] for v in out.get(cat, [])}
        for vid in vids:
            v = resolve_variant(manifest, cat, vid)
            if v is not None and vid not in have:
                out.setdefault(cat, []).append(v)
    return out


def by_kind(res: dict[str, list[dict]], cat: str, kind: str) -> list[dict]:
    return [v for v in res.get(cat, []) if v.get("kind") == kind]


def first(res: dict[str, list[dict]], cat: str, kind: str | None = None) -> dict | None:
    lst = res.get(cat, [])
    if kind:
        lst = [v for v in lst if v.get("kind") == kind]
    return lst[0] if lst else None


def preset_identity(manifest: dict, pid: str | None) -> dict:
    """Identity record for a preset: identities[preset.identity] or the root copy."""
    p = (manifest.get("presets", {}) or {}).get(pid or "", {}) or {}
    iid = p.get("identity") or manifest.get("default_identity")
    ids = manifest.get("identities") or {}
    if iid and iid in ids:
        return ids[iid]
    return {k: manifest.get(k) for k in ("name", "nickname", "summary", "fictional", "morphology")}


# Age is a property of the REPRESENTATION, never of the identity (v0.5).
AGE_CATEGORIES = {"appearance", "volume3d", "identity_weights"}       # variants that MAY carry `age`
AGELESS_KINDS = {"clothing", "accessory", "feature", "description", "environment"}    # variants that never do
AGE_REQUIRED_KINDS = {"face", "body", "character-sheet", "reference-set"}   # MUST carry `age` for human-form morphologies
HUMAN_FORM = {"human", "humanoid", "anthropomorphic-animal"}
ADULT = 18


def _age_value(a) -> float | None:
    return a["value"] if isinstance(a, dict) and isinstance(a.get("value"), (int, float)) else None


def variant_ages(manifest: dict) -> list[float]:
    out = []
    for cat in AGE_CATEGORIES:
        for v in variants_of(manifest, cat).values():
            if v.get("kind") in AGELESS_KINDS:
                continue
            x = _age_value(v.get("age"))
            if x is not None:
                out.append(x)
    return out


def lowest_age(manifest: dict) -> float | None:
    """Lowest age declared anywhere (presets' age_override, morphological variants). None = no age known."""
    ages = []
    for p in (manifest.get("presets", {}) or {}).values():
        x = _age_value(p.get("age_override"))
        if x is not None:
            ages.append(x)
    ages += variant_ages(manifest)
    return min(ages) if ages else None


def preset_age(manifest: dict, pid: str | None) -> float | None:
    """Age of a preset = min(ages of its applied AND offered morphological variants, age_override). None = no age known (e.g. text only)."""
    res = resolved_all(manifest, pid)
    va = [x for cat in AGE_CATEGORIES for v in res.get(cat, []) if v.get("kind") not in AGELESS_KINDS for x in [_age_value(v.get("age"))] if x is not None]
    p = (manifest.get("presets", {}) or {}).get(pid or "", {}) or {}
    x = _age_value(p.get("age_override"))
    if x is not None:
        va.append(x)
    return min(va) if va else None


def implicit_resolved(manifest: dict) -> dict[str, list[dict]]:
    out = {}
    for cat, vids in implicit_preset(manifest).items():
        lst = [v for v in (resolve_variant(manifest, cat, vid) for vid in vids) if v]
        if lst:
            out[cat] = lst
    return out


def age_required(manifest: dict, pid: str | None, v: dict) -> bool:
    """Does this (resolved) variant have to carry an age? intimate: always; face/body/sheet/reference: for human-form morphologies."""
    if v.get("kind") == "intimate":
        return True
    if v.get("kind") == "daz":                      # Daz Studio content: only a character carries an age
        if v.get("daz_category") != "characters":
            return False
    elif v.get("kind") not in AGE_REQUIRED_KINDS:
        return False
    cls = ((preset_identity(manifest, pid) or {}).get("morphology") or {}).get("class") or "human"
    return cls in HUMAN_FORM


# ---------- region rules (clothing / accessories / pilosity / features / weights) ----------

def region_conflicts(res: dict[str, list[dict]]) -> list[str]:
    """Return human-readable conflicts for a resolved preset (empty = OK)."""
    g = garments()
    issues = []
    cloth = by_kind(res, "appearance", "clothing")
    full = [v for v in cloth if (v.get("garment") or "other") == "full-outfit"]
    if full and len(cloth) > 1:
        issues.append(f"full outfit '{full[0]['_id']}' combined with other clothing")
    occupied: dict[tuple[str, str], str] = {}
    for v in cloth:
        t = g["types"].get(v.get("garment") or "other", {"regions": [], "layer": "outer", "stackable": True})
        if t.get("stackable") or t.get("exclusive"):
            continue
        for r in t["regions"]:
            key = (r, t["layer"])
            if key in occupied:
                issues.append(f"clothing '{occupied[key]}' and '{v['_id']}' overlap ({r}, layer {t['layer']})")
            occupied[key] = v["_id"]
    occ = {}
    for v in by_kind(res, "appearance", "accessory"):
        if (v.get("accessory_use") or "worn") != "worn":
            continue                                   # not worn, companion, other: no body region
        t = g["accessories"]["types"].get(v.get("accessory") or "other", {"region": "none", "stackable": True})
        if t.get("stackable") or t["region"] in ("none",):
            continue
        if t["region"] in occ:
            issues.append(f"accessories '{occ[t['region']]}' and '{v['_id']}' on the same region ({t['region']})")
        occ[t["region"]] = v["_id"]
    areas = {}
    for v in by_kind(res, "appearance", "pilosity"):
        a = v.get("area") or "face"
        if a in areas:
            issues.append(f"two pilosity variants for area '{a}' ('{areas[a]}', '{v['_id']}')")
        areas[a] = v["_id"]
    covered: dict[str, str] = {}
    for v in res.get("identity_weights", []):
        for c in v.get("covers") or []:
            if c in covered:
                issues.append(f"identity weights '{covered[c]}' and '{v['_id']}' both cover '{c}'")
            covered[c] = v["_id"]
    return issues


def single_kind_violations(res: dict[str, list[dict]]) -> list[str]:
    out = []
    for cat, lst in res.items():
        if cat in LIBRARY_CATEGORIES:
            continue
        seen = {}
        for v in lst:
            k = v.get("kind")
            if k in MULTI_KINDS:
                continue
            if k in seen:
                out.append(f"{cat}: two variants of kind '{k}' ('{seen[k]}', '{v['_id']}')")
            seen[k] = v["_id"]
    return out
