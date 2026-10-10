"""Manifest model helpers (v0.4): categories → variants (with `kind`), presets with multi-slots, identities, regions."""
from __future__ import annotations

import json
from importlib import resources

CATEGORIES = ["personality", "appearance", "identity_weights", "volume3d", "voice", "posture", "motion"]
KINDS = {
    "personality": ["card", "description"],
    "appearance": ["reference-set", "character-sheet", "face", "body", "hair", "clothing", "accessory", "intimate", "pilosity", "feature", "description"],
    "identity_weights": ["lora", "lycoris", "dora", "textual-inversion", "ip-adapter-embedding", "dreambooth", "other"],
    "volume3d": ["mesh", "face-mesh", "point-cloud", "print", "other"],
    "voice": ["samples", "described"],
    "posture": ["photo", "photos", "openpose", "silhouette", "attitude", "description"],
    "motion": ["clips", "video", "attitude", "description"],   # 'attitude' (signature de mouvement) est admis ici ET dans posture
}
# categories that are LIBRARIES in a preset: several variants of any kind, none mandatory at inference
LIBRARY_CATEGORIES = {"posture", "motion"}
# kinds that may appear several times in one preset (subject to region rules)
MULTI_KINDS = {"clothing", "accessory", "pilosity", "feature"}

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
    return {k: manifest.get(k) for k in ("name", "nickname", "age", "summary", "fictional", "morphology")}


# categories whose variants may carry their own `age` (a character declined at several ages of its life)
AGE_CATEGORIES = {"appearance", "volume3d", "identity_weights"}
AGELESS_KINDS = {"clothing", "accessory", "feature", "description"}


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
    """Lowest age declared anywhere (root, identities, presets' age_override, morphological variants). None = no age known."""
    ages = []
    for src in [manifest, *((manifest.get("identities") or {}).values())]:
        x = _age_value(src.get("age"))
        if x is not None:
            ages.append(x)
    for p in (manifest.get("presets", {}) or {}).values():
        x = _age_value(p.get("age_override"))
        if x is not None:
            ages.append(x)
    ages += variant_ages(manifest)
    return min(ages) if ages else None


def preset_age(manifest: dict, pid: str | None) -> float | None:
    """Age of a preset: lowest age of its resolved morphological variants, else age_override, else identity age, else None."""
    res = resolved(manifest, pid) if pid else {}
    va = [x for cat in AGE_CATEGORIES for v in res.get(cat, []) if v.get("kind") not in AGELESS_KINDS for x in [_age_value(v.get("age"))] if x is not None]
    if va:
        return min(va)
    p = (manifest.get("presets", {}) or {}).get(pid or "", {}) or {}
    x = _age_value(p.get("age_override"))
    if x is not None:
        return x
    return _age_value(preset_identity(manifest, pid).get("age"))


# ---------- region rules (clothing / accessories / pilosity / features / weights) ----------

def region_conflicts(res: dict[str, list[dict]]) -> list[str]:
    """Return human-readable conflicts for a resolved preset (empty = OK)."""
    g = garments()
    issues = []
    cloth = by_kind(res, "appearance", "clothing")
    full = [v for v in cloth if (v.get("garment") or "other") == "full-outfit"]
    if full and len(cloth) > 1:
        issues.append(f"tenue complète '{full[0]['_id']}' combinée avec d'autres vêtements")
    occupied: dict[tuple[str, str], str] = {}
    for v in cloth:
        t = g["types"].get(v.get("garment") or "other", {"regions": [], "layer": "outer", "stackable": True})
        if t.get("stackable") or t.get("exclusive"):
            continue
        for r in t["regions"]:
            key = (r, t["layer"])
            if key in occupied:
                issues.append(f"vêtements '{occupied[key]}' et '{v['_id']}' se recouvrent ({r}, couche {t['layer']})")
            occupied[key] = v["_id"]
    occ = {}
    for v in by_kind(res, "appearance", "accessory"):
        t = g["accessories"]["types"].get(v.get("accessory") or "other", {"region": "none", "stackable": True})
        if t.get("stackable") or t["region"] in ("none",):
            continue
        if t["region"] in occ:
            issues.append(f"accessoires '{occ[t['region']]}' et '{v['_id']}' sur la même région ({t['region']})")
        occ[t["region"]] = v["_id"]
    areas = {}
    for v in by_kind(res, "appearance", "pilosity"):
        a = v.get("area") or "face"
        if a in areas:
            issues.append(f"deux pilosités pour la zone '{a}' ('{areas[a]}', '{v['_id']}')")
        areas[a] = v["_id"]
    covered: dict[str, str] = {}
    for v in res.get("identity_weights", []):
        for c in v.get("covers") or []:
            if c in covered:
                issues.append(f"poids d'identité '{covered[c]}' et '{v['_id']}' couvrent tous deux '{c}'")
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
                out.append(f"{cat} : deux déclinaisons de type '{k}' ('{seen[k]}', '{v['_id']}')")
            seen[k] = v["_id"]
    return out
