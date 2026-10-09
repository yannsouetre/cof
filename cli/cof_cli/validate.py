"""Validation: schema + structural + semantic rules + completeness recomputation."""
from __future__ import annotations

import json
import tempfile
from dataclasses import dataclass, field
from importlib import resources
from pathlib import Path

import jsonschema
from jsonschema import Draft202012Validator

from . import SPEC_VERSION, __version__
from .completeness import compute as compute_completeness
from .container import ContainerError, inspect, read_manifest, unpack, verify_hashes
from .tokens import count as count_tokens, tokenizer_name

PROMPT_FIELDS = ("description", "personality", "scenario", "first_mes", "mes_example", "system_prompt", "post_history_instructions")


@dataclass
class Report:
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    info: dict = field(default_factory=dict)

    @property
    def ok(self) -> bool:
        return not self.errors

    def to_dict(self) -> dict:
        return {"ok": self.ok, "errors": self.errors, "warnings": self.warnings, "info": self.info}


def _schema() -> dict:
    with resources.files("cof_cli").joinpath("schemas/manifest.schema.json").open("r", encoding="utf-8") as f:
        return json.load(f)


_validator = None


def manifest_validator() -> Draft202012Validator:
    global _validator
    if _validator is None:
        _validator = Draft202012Validator(_schema(), format_checker=jsonschema.FormatChecker())
    return _validator


def validate_manifest(manifest: dict, rep: Report) -> None:
    for e in sorted(manifest_validator().iter_errors(manifest), key=lambda e: list(e.path)):
        loc = "/".join(str(p) for p in e.path) or "(racine)"
        rep.errors.append(f"manifest.json [{loc}] : {e.message}")


def validate_card(card: dict, rep: Report, lang: str) -> dict:
    """Basic Character Card V3 checks; returns token estimates per field."""
    tokens = {}
    if card.get("spec") not in ("chara_card_v3", "chara_card_v2"):
        rep.errors.append("character/card.json : 'spec' doit être 'chara_card_v3' (ou 'chara_card_v2')")
    data = card.get("data")
    if not isinstance(data, dict):
        rep.errors.append("character/card.json : 'data' manquant")
        return tokens
    if not data.get("name"):
        rep.errors.append("character/card.json : data.name manquant")
    for f in PROMPT_FIELDS:
        v = data.get(f)
        if isinstance(v, str) and v:
            tokens[f] = count_tokens(v, lang)
    permanent = sum(tokens.get(k, 0) for k in ("description", "personality", "scenario"))
    tokens["permanent"] = permanent
    if permanent > 2500:
        rep.warnings.append(f"bloc permanent de la carte = {permanent} tokens (> 2 500 : à justifier dans creator_notes)")
    book = data.get("character_book")
    if isinstance(book, dict):
        entries = book.get("entries", [])
        lore = sum(count_tokens(e.get("content", ""), lang) for e in entries if isinstance(e, dict))
        tokens["lore"] = lore
        const = [e for e in entries if isinstance(e, dict) and e.get("constant")]
        if const:
            rep.warnings.append(f"lorebook : {len(const)} entrée(s) 'constant' (toujours injectées) — à afficher à l'import")
        if lore > 32000:
            rep.warnings.append(f"lorebook = {lore} tokens (> 32 k)")
    if data.get("post_history_instructions"):
        rep.warnings.append("post_history_instructions présent — à afficher à l'import (texte 'untrusted')")
    return tokens


def _dup_ratio(a: str, b: str) -> float:
    """Cheap textual overlap ratio (word shingles)."""
    def sh(t):
        w = t.lower().split()
        return {" ".join(w[i:i + 4]) for i in range(max(0, len(w) - 3))}
    sa, sb = sh(a), sh(b)
    if not sa or not sb:
        return 0.0
    return len(sa & sb) / min(len(sa), len(sb))


def validate_dir(src: Path, rep: Report, *, recompute: bool = True) -> dict:
    """Validate an unpacked character directory. Returns the (possibly updated) manifest."""
    mpath = src / "manifest.json"
    if not mpath.is_file():
        rep.errors.append("manifest.json introuvable")
        return {}
    try:
        manifest = json.loads(mpath.read_text("utf-8"))
    except Exception as e:
        rep.errors.append(f"manifest.json illisible : {e}")
        return {}
    validate_manifest(manifest, rep)
    if rep.errors:
        return manifest

    lang = (manifest.get("languages") or ["en"])[0]
    sec = manifest.get("sections", {}) or {}

    # sections must exist on disk
    def walk(obj, prefix="sections"):
        if isinstance(obj, str):
            if not (src / obj).is_file():
                rep.errors.append(f"{prefix} → fichier absent : {obj}")
        elif isinstance(obj, dict):
            for k, v in obj.items():
                walk(v, f"{prefix}.{k}")
        elif isinstance(obj, list):
            for v in obj:
                walk(v, prefix)
    walk(sec)

    # card
    tokens = {}
    if sec.get("character") and (src / sec["character"]).is_file():
        try:
            card = json.loads((src / sec["character"]).read_text("utf-8"))
            tokens = validate_card(card, rep, lang)
            if card.get("data", {}).get("name") and card["data"]["name"] != manifest.get("name"):
                rep.warnings.append("le nom de la carte diffère de manifest.name")
        except Exception as e:
            rep.errors.append(f"character/card.json illisible : {e}")

    # age coherence
    age = (manifest.get("age") or {}).get("value")
    body = sec.get("appearance", {}).get("body") if isinstance(sec.get("appearance"), dict) else None
    if body and (src / body).is_file():
        try:
            b = json.loads((src / body).read_text("utf-8"))
            if b.get("age_years") is not None and age is not None and abs(b["age_years"] - age) > 0.5:
                rep.errors.append(f"âge incohérent : manifest {age} ≠ body.json {b['age_years']}")
            if age is not None and age < 18 and b.get("intimate"):
                rep.errors.append("body.intimate interdit pour un personnage mineur")
        except Exception as e:
            rep.errors.append(f"body.json illisible : {e}")

    # psyche cross-references
    psyche = sec.get("psyche")
    ids = set()
    if psyche and (src / psyche).is_file():
        try:
            p = json.loads((src / psyche).read_text("utf-8"))
            for t in (p.get("traits", {}).get("custom") or []):
                ids.add(t.get("id"))
            for k in ("goals", "fears"):
                for it in p.get(k, []) or []:
                    ids.add(it.get("id"))
            for dim in (p.get("traits", {}).get("big5") or {}):
                ids.add(f"trait:big5.{dim}")
        except Exception as e:
            rep.errors.append(f"psyche.json illisible : {e}")
    for rel in [sec.get("physique"), sec.get("voice")]:
        if rel and (src / rel).is_file():
            try:
                obj = json.loads((src / rel).read_text("utf-8"))
                refs = set(obj.get("expresses", []) or [])
                for g in obj.get("gestures", []) or []:
                    refs |= set(g.get("expresses", []) or [])
                refs |= set((obj.get("speech_style") or {}).get("expresses", []) or [])
                missing = [r for r in refs if r not in ids]
                if missing:
                    rep.warnings.append(f"{rel} : renvois non résolus vers psyche.json : {', '.join(missing)}")
            except Exception as e:
                rep.errors.append(f"{rel} illisible : {e}")

    # textual duplication between personality and attitude/voice sentences
    try:
        card_text = ""
        if sec.get("character"):
            d = json.loads((src / sec["character"]).read_text("utf-8")).get("data", {})
            card_text = " ".join(str(d.get(k, "")) for k in ("description", "personality"))
        for rel in [sec.get("physique"), sec.get("voice")]:
            if rel and card_text:
                obj = json.loads((src / rel).read_text("utf-8"))
                sent = (obj.get("renderings") or {}).get("sentence", "")
                if sent and _dup_ratio(card_text, sent) > 0.8:
                    rep.warnings.append(f"{rel} : texte dupliqué à > 80 % avec la carte (règle « une vérité, des projections »)")
    except Exception:
        pass

    # voice samples need transcripts, consent if real person
    for a in manifest.get("assets", []):
        if a.get("role") == "voice-sample":
            t = a.get("transcript")
            if not t or not (src / t).is_file():
                rep.errors.append(f"échantillon de voix sans transcription lisible : {a.get('path')}")
    if manifest.get("fictional") is False and not (manifest.get("rights", {}) or {}).get("consent"):
        rep.errors.append("personnage non fictif sans rights.consent")

    # executable content
    exec_ext = {".js", ".lua", ".py", ".wasm", ".exe", ".sh", ".bat", ".ps1"}
    declared = (manifest.get("container") or {}).get("executableContent", "none")
    for p in src.rglob("*"):
        if p.is_file() and p.suffix.lower() in exec_ext and declared == "none":
            rep.errors.append(f"contenu exécutable non déclaré : {p.relative_to(src).as_posix()}")

    # completeness
    comp = compute_completeness(manifest, src)
    declared_c = manifest.get("completeness")
    if declared_c and declared_c.get("score") != comp["score"]:
        rep.warnings.append(f"completeness déclarée {declared_c.get('score')} ≠ calculée {comp['score']}")
    if recompute:
        from datetime import datetime, timezone
        manifest["completeness"] = {**comp, "computed_by": f"cof-cli/{__version__}",
                                    "computed_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")}
    rep.info["completeness"] = comp
    rep.info["tokens"] = {**tokens, "tokenizer": tokenizer_name()}
    return manifest


def validate_cof(cof: Path) -> Report:
    rep = Report()
    try:
        st = inspect(cof)
    except Exception as e:
        rep.errors.append(f"archive illisible : {e}")
        return rep
    rep.errors += st["errors"]
    rep.warnings += st["warnings"]
    rep.info["entries"] = st["entries"]
    rep.info["bytes"] = st["compressed"]
    try:
        manifest = read_manifest(cof)
    except ContainerError as e:
        rep.errors.append(str(e))
        return rep
    rep.errors += verify_hashes(cof, manifest)
    with tempfile.TemporaryDirectory() as td:
        d = unpack(cof, td)
        validate_dir(d, rep, recompute=False)
    size = st["compressed"]
    cls = manifest.get("size_class")
    limit = {"lite": 20_000_000, "standard": 100_000_000}.get(cls)
    if limit and size > limit:
        rep.warnings.append(f"size_class '{cls}' dépassée : {size/1e6:.1f} Mo")
    if manifest.get("cof") != SPEC_VERSION:
        rep.warnings.append(f"version de format {manifest.get('cof')} (outil : {SPEC_VERSION})")
    return rep
