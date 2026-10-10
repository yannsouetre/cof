"""Completeness KPI (spec § 2.5) — per preset, pure function of the manifest (+ files when available).

Layers 0–100 from presence and representation levels; derived assets never count.
"""
from __future__ import annotations

import json
from pathlib import Path

from .model import asset_index, default_preset_id, preset_ids, resolved

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
    layers: dict[str, int] = {}

    def imgs(v):
        return [A[i] for i in (v or {}).get("images", []) if i in A]

    # identity
    s = 20 * bool(m.get("name")) + 20 * (isinstance(m.get("age"), dict) and "value" in m["age"]) + 20 * bool(m.get("summary"))
    s += 10 * bool(m.get("languages")) + 10 * bool(m.get("morphology"))
    tags = m.get("tags", {}) or {}
    s += 10 * bool(tags.get("content")) + 10 * isinstance(tags.get("ip"), dict)
    layers["identity"] = min(100, s)

    # personality
    p = r.get("personality")
    s = 0
    if p and p.get("card"):
        s += 30
        card = _load(src, p["card"])
        d = (card or {}).get("data", {})
        if card is None and src is None:
            s += 25
        s += 10 * bool(d.get("description")) + 10 * bool(d.get("personality")) + 5 * bool(d.get("scenario")) + 10 * bool(d.get("first_mes")) + 10 * bool(d.get("mes_example"))
        s += 10 * bool(p.get("story") or p.get("lorebook") or d.get("character_book"))
    s += 15 * bool(p and p.get("psyche"))
    layers["personality"] = min(100, s)

    # appearance (face, hair, body, outfit, weights)
    f, h, b, o, w = r.get("face"), r.get("hair"), r.get("body"), r.get("outfit"), r.get("identity_weights")
    fi = imgs(f)
    s = 0
    s += 25 * any(a.get("subject") == "head" and a.get("angle") == "front" for a in fi)
    s += 10 * (len(fi) >= 2)
    s += 10 * bool(f and (f.get("params") or f.get("mesh")))
    s += 5 * bool(f and f.get("mesh"))
    s += 5 * bool(h)
    bi = imgs(b)
    s += 10 * bool(bi) + 5 * (len(bi) >= 2) + 5 * bool(b and b.get("params"))
    s += 10 * bool(o)
    s += 15 * bool(w and w.get("spec"))
    layers["appearance"] = min(100, s)

    # physique
    at = r.get("attitude")
    layers["physique"] = min(100, 60 * bool(at and at.get("spec")) + 40 * bool(at and at.get("poses")))

    # voice
    v = r.get("voice")
    samples = [A[i] for i in (v or {}).get("samples", []) if i in A]
    s = 0
    if samples:
        s += 40 if all(a.get("transcript") for a in samples) else 20
        d = sorted(a.get("duration_s", 0) for a in samples)
        s += 10 * (d[0] <= 12 and d[-1] >= 25)
    s += 25 * bool(v and v.get("profile")) + 20 * bool(v and v.get("vec")) + 5 * bool(v and v.get("engines"))
    layers["voice"] = min(100, s)

    # volume
    av = r.get("avatar")
    s = 60 * bool(av and av.get("path")) + 10 * bool(av and av.get("rig")) + 15 * bool(av and av.get("splat")) + 15 * bool(av and av.get("print"))
    layers["volume"] = min(100, s)

    # motion
    mo = r.get("motion")
    clips = [A[i] for i in (mo or {}).get("clips", []) if i in A]
    s = 60 * bool(clips) + 25 * bool(mo and mo.get("visemes")) + 15 * (bool(clips) and all(a.get("rig") for a in clips))
    layers["motion"] = min(100, s)

    # rights
    rg = m.get("rights", {}) or {}
    assets = m.get("assets", [])
    s = 40 * bool(rg.get("permissions")) + 15 * (not assets or all(a.get("license") for a in assets))
    needs_consent = (m.get("fictional") is False) or any(a.get("role") == "voice-consent" for a in assets)
    s += 20 * (bool(rg.get("consent")) if needs_consent else True)
    prov = m.get("provenance", {}) or {}
    s += 10 * bool(prov.get("source")) + 15 * bool(prov.get("c2pa") or prov.get("signatures"))
    layers["rights"] = min(100, s)

    score = round(sum(layers[k] * wgt for k, wgt in WEIGHTS.items()))
    level = "A" if score >= 85 else "B" if score >= 60 else "C" if score >= 35 else "D"
    targets = []
    if layers["personality"] >= 50:
        targets += ["chat-text", "agent-persona"]
    if layers["personality"] >= 50 and layers["voice"] >= 40:
        targets.append("chat-voice")
    if layers["appearance"] >= 25:
        targets.append("image-video-gen")
    if layers["voice"] >= 40 and layers["appearance"] >= 40 and (f and (f.get("mesh") or f.get("params")) or av):
        targets.append("video-realtime")
    if av and av.get("path"):
        targets.append("game-3d")
    if av and av.get("print"):
        targets.append("print-3d")
    if layers["rights"] >= 60:
        targets.append("archive")
    return {"score": score, "level": level, "layers": layers, "targets_ready": targets}


def compute(manifest: dict, src: Path | None = None) -> dict:
    """File-level KPI = default preset's; plus per-preset results and coverage."""
    pids = preset_ids(manifest)
    per = {pid: compute_preset(manifest, pid, src) for pid in pids}
    dp = default_preset_id(manifest)
    file_level = per[dp] if dp in per else compute_preset(manifest, None, src)
    elements = manifest.get("elements", {}) or {}
    coverage = {"elements": [e for e, v in elements.items() if (v or {}).get("variants")],
                "variants": sum(len((v or {}).get("variants", {})) for v in elements.values()),
                "presets": len(pids)}
    return {"file": file_level, "presets": per, "coverage": coverage}
