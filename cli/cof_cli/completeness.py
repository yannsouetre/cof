"""Completeness KPI — public rules (spec § 2.2). Pure function of the unpacked character directory + manifest.

Each layer is scored 0–100 from the presence (and representation level) of its blocks; the global score is a
weighted mean. Rules are intentionally simple and transparent; they measure *coverage*, not artistic quality.
"""
from __future__ import annotations

import json
from pathlib import Path

WEIGHTS = {
    "identity": 0.10, "personality": 0.20, "appearance": 0.20, "physique": 0.05,
    "voice": 0.15, "volume": 0.10, "motion": 0.05, "rights": 0.15,
}


def _exists(src: Path | None, rel) -> bool:
    return bool(src and rel and (src / rel).is_file())


def _load(src: Path | None, rel):
    try:
        return json.loads((src / rel).read_text("utf-8")) if _exists(src, rel) else None
    except Exception:
        return None


def _assets(m: dict, role: str) -> list[dict]:
    return [a for a in m.get("assets", []) if a.get("role") == role]


def compute(manifest: dict, src: Path | None = None) -> dict:
    m = manifest
    sec = m.get("sections", {}) or {}
    app = sec.get("appearance", {}) or {}
    vol = sec.get("volume", {}) or {}
    mot = sec.get("motion", {}) or {}
    layers: dict[str, int] = {}

    # identity
    s = 0
    s += 20 if m.get("name") else 0
    s += 20 if isinstance(m.get("age"), dict) and "value" in m["age"] else 0
    s += 20 if m.get("summary") else 0
    s += 10 if m.get("languages") else 0
    s += 10 if m.get("morphology") else 0
    tags = m.get("tags", {}) or {}
    s += 10 if tags.get("content") else 0
    s += 10 if isinstance(tags.get("ip"), dict) else 0
    layers["identity"] = s

    # personality
    s = 0
    card = _load(src, sec.get("character")) if src else None
    if sec.get("character"):
        s += 30
        d = (card or {}).get("data", {}) if card else {}
        s += 10 if d.get("description") else 0
        s += 10 if d.get("personality") else 0
        s += 5 if d.get("scenario") else 0
        s += 10 if d.get("first_mes") else 0
        s += 10 if d.get("mes_example") else 0
        if card is None and src is None:
            s += 25  # cannot inspect: assume a complete card
    s += 15 if sec.get("psyche") else 0
    s += 10 if (sec.get("story") or sec.get("lorebook") or ((card or {}).get("data", {}).get("character_book"))) else 0
    layers["personality"] = min(100, s)

    # appearance
    s = 0
    views = _assets(m, "view")
    if any(a.get("subject") == "head" and a.get("angle") == "front" for a in views):
        s += 25
    if len(views) >= 3:
        s += 15
    s += 10 if app.get("face") else 0
    s += 15 if app.get("face_vec") else 0
    s += 10 if app.get("body") or app.get("body_vec") else 0
    s += 5 if app.get("hair") else 0
    s += 10 if app.get("outfits") else 0
    s += 5 if _assets(m, "expression") else 0
    s += 5 if _assets(m, "reference") else 0
    layers["appearance"] = min(100, s)

    # physique
    s = 60 if sec.get("physique") else 0
    s += 40 if (sec.get("poses") or (src and (src / "physique" / "poses").is_dir() and any((src / "physique" / "poses").glob("*.pose.json")))) else 0
    layers["physique"] = min(100, s)

    # voice
    s = 0
    samples = _assets(m, "voice-sample")
    if samples and all(a.get("transcript") for a in samples):
        s += 40
    elif samples:
        s += 20
    s += 25 if sec.get("voice") else 0
    s += 20 if sec.get("voice_vec") else 0
    durations = sorted(a.get("duration_s", 0) for a in samples)
    if durations and durations[0] <= 12 and durations[-1] >= 25:
        s += 10
    s += 5 if _assets(m, "engine-artifact") else 0
    layers["voice"] = min(100, s)

    # volume
    s = 60 if (vol.get("avatar") or _assets(m, "avatar")) else 0
    s += 10 if any(a.get("rig") for a in _assets(m, "avatar")) else 0
    s += 15 if (vol.get("splat") or _assets(m, "splat")) else 0
    s += 15 if (vol.get("print") or _assets(m, "print")) else 0
    layers["volume"] = min(100, s)

    # motion
    clips = _assets(m, "motion-clip")
    s = 60 if clips else 0
    s += 25 if mot.get("visemes") else 0
    s += 15 if clips and all(a.get("rig") for a in clips) else 0
    layers["motion"] = min(100, s)

    # rights
    r = m.get("rights", {}) or {}
    s = 40 if r.get("permissions") else 0
    assets = m.get("assets", [])
    s += 15 if (not assets or all(a.get("license") for a in assets)) else 0
    needs_consent = (m.get("fictional") is False) or any(a.get("role") == "voice-consent" for a in assets)
    s += 20 if (r.get("consent") if needs_consent else True) else 0
    prov = m.get("provenance", {}) or {}
    s += 10 if prov.get("source") else 0
    s += 15 if (prov.get("c2pa") or prov.get("signatures")) else 0
    layers["rights"] = min(100, s)

    score = round(sum(layers[k] * w for k, w in WEIGHTS.items()))
    level = "A" if score >= 85 else "B" if score >= 60 else "C" if score >= 35 else "D"

    targets = []
    if layers["personality"] >= 50:
        targets += ["chat-text", "agent-persona"]
    if layers["personality"] >= 50 and layers["voice"] >= 40:
        targets.append("chat-voice")
    if layers["appearance"] >= 25:
        targets.append("image-video-gen")
    if layers["voice"] >= 40 and layers["appearance"] >= 40 and (app.get("face") or vol.get("avatar")):
        targets.append("video-realtime")
    if vol.get("avatar") or _assets(m, "avatar"):
        targets.append("game-3d")
    if vol.get("print") or _assets(m, "print"):
        targets.append("print-3d")
    if layers["rights"] >= 60:
        targets.append("archive")

    return {"score": score, "level": level, "layers": layers, "targets_ready": targets}
