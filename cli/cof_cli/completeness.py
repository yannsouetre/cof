"""Completeness KPI (v0.4) — per preset, from categories/kinds. Derived assets never count."""
from __future__ import annotations

import json
from pathlib import Path

from .model import asset_index, by_kind, default_preset_id, first, preset_identity, preset_ids, resolved

WEIGHTS = {"identity": 0.10, "personality": 0.20, "appearance": 0.20, "physique": 0.05,
           "voice": 0.15, "volume": 0.10, "motion": 0.05, "rights": 0.15}


def _load(src: Path | None, rel):
    try:
        return json.loads((src / rel).read_text("utf-8")) if src and rel and (src / rel).is_file() else None
    except Exception:
        return None


def compute_preset(manifest: dict, pid: str | None, src: Path | None = None) -> dict:
    m = manifest
    r = resolved(m, pid)
    A = asset_index(m)
    ident = preset_identity(m, pid)
    L: dict[str, int] = {}
    imgs = lambda v: [A[i] for i in (v or {}).get("images", []) if i in A]

    s = 20 * bool(ident.get("name")) + 20 * (isinstance(ident.get("age"), dict) and "value" in ident["age"]) + 20 * bool(ident.get("summary"))
    s += 10 * bool(m.get("languages")) + 10 * bool(ident.get("morphology"))
    tags = m.get("tags", {}) or {}
    s += 10 * bool(tags.get("content")) + 10 * isinstance(tags.get("ip"), dict)
    L["identity"] = min(100, s)

    p = first(r, "personality")
    s = 0
    if p and p.get("kind") == "card" and p.get("card"):
        s += 30
        card = _load(src, p["card"]); d = (card or {}).get("data", {})
        if card is None and src is None:
            s += 25
        s += 10 * bool(d.get("description")) + 10 * bool(d.get("personality")) + 5 * bool(d.get("scenario")) + 10 * bool(d.get("first_mes")) + 10 * bool(d.get("mes_example"))
        s += 10 * bool(p.get("story") or p.get("lorebook") or d.get("character_book"))
    elif p and p.get("kind") == "description":
        s += 35
    s += 15 * bool(p and p.get("psyche"))
    L["personality"] = min(100, s)

    f = first(r, "appearance", "face"); fi = imgs(f)
    s = 25 * any(a.get("subject") == "head" and a.get("angle") == "front" for a in fi) + 10 * (len(fi) >= 2)
    s += 10 * bool(f and (f.get("params") or f.get("mesh")))
    s += 5 * bool(first(r, "volume3d", "face-mesh"))
    s += 5 * bool(first(r, "appearance", "hair"))
    b = first(r, "appearance", "body"); bi = imgs(b)
    s += 10 * bool(bi) + 5 * (len(bi) >= 2) + 5 * bool(b and b.get("params"))
    s += 10 * bool(by_kind(r, "appearance", "clothing"))
    cs = first(r, "appearance", "character-sheet") or first(r, "appearance", "reference-set")
    if not fi and cs and imgs(cs):
        s += 20                       # a sheet / reference set gives a usable look even without split views
    s += 15 * bool(r.get("identity_weights"))
    L["appearance"] = min(100, s)

    po = r.get("posture", [])
    s = 60 * bool(po) + 40 * any(v.get("kind") in ("openpose", "attitude", "photo", "photos") for v in po)
    L["physique"] = min(100, s)

    v = first(r, "voice"); samples = [A[i] for i in (v or {}).get("samples", []) if i in A]
    s = 0
    if samples:
        s += 40 if all(a.get("transcript") for a in samples) else 20
        d = sorted(a.get("duration_s", 0) for a in samples)
        s += 10 * (d[0] <= 12 and d[-1] >= 25)
    s += 25 * bool(v and (v.get("profile") or v.get("kind") == "described")) + 20 * bool(v and v.get("vec")) + 5 * bool(v and v.get("engines"))
    L["voice"] = min(100, s)

    mesh = first(r, "volume3d", "mesh")
    s = 60 * bool(mesh and mesh.get("path")) + 10 * bool(mesh and mesh.get("rig")) + 15 * bool(first(r, "volume3d", "point-cloud")) + 15 * bool(first(r, "volume3d", "print"))
    L["volume"] = min(100, s)

    mo = r.get("motion", [])
    clips = [A[i] for v in mo for i in (v.get("clips") or []) if i in A]
    vids = [A[i] for v in mo for i in (v.get("videos") or []) if i in A]
    s = 60 * bool(clips or vids) + 25 * any(v.get("visemes") for v in mo) + 15 * (bool(clips) and all(a.get("rig") for a in clips))
    s += 30 * any(v.get("kind") == "attitude" for v in mo)   # signature de mouvement (attitude.json) admise ici
    L["motion"] = min(100, s)

    rg = m.get("rights", {}) or {}
    assets = m.get("assets", [])
    s = 40 * bool(rg.get("permissions")) + 15 * (not assets or all(a.get("license") for a in assets))
    needs_consent = (ident.get("fictional") is False) or any(a.get("role") == "voice-consent" for a in assets)
    s += 20 * (bool(rg.get("consent") or ident.get("consent")) if needs_consent else True)
    prov = m.get("provenance", {}) or {}
    s += 10 * bool(prov.get("source")) + 15 * bool(prov.get("c2pa") or prov.get("signatures"))
    L["rights"] = min(100, s)

    score = round(sum(L[k] * w for k, w in WEIGHTS.items()))
    level = "A" if score >= 85 else "B" if score >= 60 else "C" if score >= 35 else "D"
    t = []
    if L["personality"] >= 50:
        t += ["chat-text", "agent-persona"]
    if L["personality"] >= 50 and L["voice"] >= 40:
        t.append("chat-voice")
    if L["appearance"] >= 25:
        t.append("image-video-gen")
    if L["voice"] >= 40 and L["appearance"] >= 40 and (f and (f.get("mesh") or f.get("params")) or mesh):
        t.append("video-realtime")
    if mesh and mesh.get("path"):
        t.append("game-3d")
    if first(r, "volume3d", "print"):
        t.append("print-3d")
    if L["rights"] >= 60:
        t.append("archive")
    return {"score": score, "level": level, "layers": L, "targets_ready": t}


def compute(manifest: dict, src: Path | None = None) -> dict:
    pids = preset_ids(manifest)
    per = {pid: compute_preset(manifest, pid, src) for pid in pids}
    dp = default_preset_id(manifest)
    file_level = per[dp] if dp in per else compute_preset(manifest, None, src)
    elements = manifest.get("elements", {}) or {}
    coverage = {"elements": [e for e, v in elements.items() if (v or {}).get("variants")],
                "variants": sum(len((v or {}).get("variants", {})) for v in elements.values()),
                "presets": len(pids), "identities": len(manifest.get("identities") or {}) or 1}
    return {"file": file_level, "presets": per, "coverage": coverage}
