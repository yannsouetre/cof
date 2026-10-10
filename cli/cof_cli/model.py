"""Manifest model helpers (v0.3): element/variant/preset resolution, asset index."""
from __future__ import annotations

ELEMENT_TYPES = ["personality", "face", "hair", "facial_hair", "body", "body_hair", "intimate", "outfit",
                 "accessories", "identity_weights", "voice", "attitude", "avatar", "motion"]


def asset_index(manifest: dict) -> dict[str, dict]:
    return {a["id"]: a for a in manifest.get("assets", []) if "id" in a}


def resolve_variant(manifest: dict, etype: str, vid: str, _seen=None) -> dict | None:
    """Return the variant with `derives_from` inheritance applied (child fields win)."""
    variants = (manifest.get("elements", {}).get(etype, {}) or {}).get("variants", {}) or {}
    v = variants.get(vid)
    if v is None:
        return None
    _seen = _seen or set()
    if vid in _seen:
        return dict(v)
    _seen.add(vid)
    parent = resolve_variant(manifest, etype, v["derives_from"], _seen) if v.get("derives_from") else None
    merged = dict(parent or {})
    merged.update({k: val for k, val in v.items() if k != "derives_from"})
    merged["_id"] = vid
    return merged


def resolve_preset_slots(manifest: dict, pid: str, _seen=None) -> dict[str, str]:
    presets = manifest.get("presets", {}) or {}
    p = presets.get(pid)
    if p is None:
        return {}
    _seen = _seen or set()
    if pid in _seen:
        return dict(p.get("slots", {}))
    _seen.add(pid)
    base = resolve_preset_slots(manifest, p["extends"], _seen) if p.get("extends") else {}
    base.update(p.get("slots", {}) or {})
    return base


def implicit_preset(manifest: dict) -> dict[str, str]:
    """No presets declared → first variant of each element."""
    slots = {}
    for etype, e in (manifest.get("elements", {}) or {}).items():
        vs = list((e or {}).get("variants", {}).keys())
        if vs:
            slots[etype] = vs[0]
    return slots


def preset_ids(manifest: dict) -> list[str]:
    return list((manifest.get("presets", {}) or {}).keys())


def default_preset_id(manifest: dict) -> str | None:
    return manifest.get("default_preset") or (preset_ids(manifest)[0] if preset_ids(manifest) else None)


def resolved(manifest: dict, pid: str | None = None) -> dict[str, dict]:
    """slot → resolved variant for a preset (or the implicit one)."""
    slots = resolve_preset_slots(manifest, pid) if pid else implicit_preset(manifest)
    out = {}
    for etype, vid in slots.items():
        v = resolve_variant(manifest, etype, vid)
        if v is not None:
            out[etype] = v
    return out


def lowest_age(manifest: dict) -> float | None:
    ages = []
    a = manifest.get("age", {})
    if isinstance(a, dict) and isinstance(a.get("value"), (int, float)):
        ages.append(a["value"])
    for p in (manifest.get("presets", {}) or {}).values():
        ao = p.get("age_override")
        if isinstance(ao, dict) and isinstance(ao.get("value"), (int, float)):
            ages.append(ao["value"])
    return min(ages) if ages else None
