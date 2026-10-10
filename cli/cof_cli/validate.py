"""Validation (v0.3): schema + structure + semantic rules + KPI recomputation (per preset)."""
from __future__ import annotations

import json
import tempfile
from dataclasses import dataclass, field
from datetime import datetime, timezone
from importlib import resources
from pathlib import Path

import jsonschema
from jsonschema import Draft202012Validator

from . import SPEC_VERSION, __version__
from .completeness import compute as compute_completeness
from .container import ContainerError, inspect, read_manifest, unpack, verify_hashes
from .model import CATEGORIES, KINDS, MULTI_KINDS, asset_index, default_preset_id, first, lowest_age, preset_age, preset_identity, preset_ids, region_conflicts, resolve_preset_slots, resolve_variant, resolved, single_kind_violations, by_kind
from .tokens import count as count_tokens, tokenizer_name

PROMPT_FIELDS = ("description", "personality", "scenario", "first_mes", "mes_example", "system_prompt", "post_history_instructions")
EXEC_EXT = {".js", ".lua", ".py", ".wasm", ".exe", ".sh", ".bat", ".ps1", ".pkl", ".pickle", ".ckpt", ".pt", ".pth", ".bin"}
PATH_FIELDS = ("card", "psyche", "story", "lorebook", "params", "code", "spec", "profile", "vec", "visemes", "path", "skeleton")


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


_validator = None


def manifest_validator() -> Draft202012Validator:
    global _validator
    if _validator is None:
        with resources.files("cof_cli").joinpath("schemas/manifest.schema.json").open("r", encoding="utf-8") as f:
            _validator = Draft202012Validator(json.load(f), format_checker=jsonschema.FormatChecker())
    return _validator


def validate_manifest(manifest: dict, rep: Report) -> None:
    for e in sorted(manifest_validator().iter_errors(manifest), key=lambda e: list(e.path)):
        loc = "/".join(str(p) for p in e.path) or "(racine)"
        rep.errors.append(f"manifest.json [{loc}] : {e.message[:200]}")


def validate_card(card: dict, rep: Report, lang: str, where: str) -> dict:
    tokens = {}
    if card.get("spec") not in ("chara_card_v3", "chara_card_v2"):
        rep.errors.append(f"{where} : 'spec' doit être 'chara_card_v3' (ou 'chara_card_v2')")
    data = card.get("data")
    if not isinstance(data, dict):
        rep.errors.append(f"{where} : 'data' manquant")
        return tokens
    if not data.get("name"):
        rep.errors.append(f"{where} : data.name manquant")
    for f in PROMPT_FIELDS:
        v = data.get(f)
        if isinstance(v, str) and v:
            tokens[f] = count_tokens(v, lang)
    permanent = sum(tokens.get(k, 0) for k in ("description", "personality", "scenario"))
    tokens["permanent"] = permanent
    if permanent > 2500:
        rep.warnings.append(f"{where} : bloc permanent = {permanent} tokens (> 2 500)")
    book = data.get("character_book")
    if isinstance(book, dict):
        entries = book.get("entries", [])
        tokens["lore"] = sum(count_tokens(e.get("content", ""), lang) for e in entries if isinstance(e, dict))
        const = [e for e in entries if isinstance(e, dict) and e.get("constant")]
        if const:
            rep.warnings.append(f"{where} : {len(const)} entrée(s) 'constant' — à afficher à l'import")
    if data.get("post_history_instructions"):
        rep.warnings.append(f"{where} : post_history_instructions présent — à afficher à l'import (texte 'untrusted')")
    return tokens


def _dup_ratio(a: str, b: str) -> float:
    def sh(t):
        w = t.lower().split()
        return {" ".join(w[i:i + 4]) for i in range(max(0, len(w) - 3))}
    sa, sb = sh(a), sh(b)
    return len(sa & sb) / min(len(sa), len(sb)) if sa and sb else 0.0


def validate_dir(src: Path, rep: Report, *, recompute: bool = True) -> dict:
    mpath = src / "manifest.json"
    if not mpath.is_file():
        rep.errors.append("manifest.json introuvable")
        return {}
    try:
        manifest = json.loads(mpath.read_text("utf-8"))
    except Exception as e:
        rep.errors.append(f"manifest.json illisible : {e}")
        return {}
    if str(manifest.get("cof", "")) in ("0.2", "0.3"):
        rep.errors.append(f"manifest v{manifest.get('cof')} : lancer `cof migrate` (structure v0.4 attendue)")
        return manifest
    validate_manifest(manifest, rep)
    if rep.errors:
        return manifest

    lang = (manifest.get("languages") or ["en"])[0]
    A = asset_index(manifest)
    elements = manifest.get("elements", {}) or {}

    # identities: root must mirror the default identity
    ids = manifest.get("identities") or {}
    if ids:
        di = manifest.get("default_identity")
        if di not in ids:
            rep.errors.append(f"default_identity inconnu : {di}")
        else:
            for k in ("name", "age", "fictional", "morphology"):
                if json.dumps(ids[di].get(k), sort_keys=True) != json.dumps(manifest.get(k), sort_keys=True):
                    rep.errors.append(f"la racine doit refléter l'identité par défaut ({k} diffère)")
            for iid, ident in ids.items():
                if ident.get("fictional") is False and not ident.get("consent"):
                    rep.errors.append(f"identities.{iid} : personne réelle sans consentement")

    # asset ids unique, files present
    seen = set()
    for a in manifest.get("assets", []):
        if a["id"] in seen:
            rep.errors.append(f"asset id dupliqué : {a['id']}")
        seen.add(a["id"])
        if a.get("path") and not (src / a["path"]).is_file() and not a.get("uri"):
            rep.errors.append(f"asset absent : {a['path']}")
        if a.get("role") == "derived" and a.get("source") not in A:
            rep.errors.append(f"dérivé {a['id']} : source inconnue {a.get('source')}")
        if a.get("role") == "voice-sample":
            t = a.get("transcript")
            if t and not (src / t).is_file():
                rep.errors.append(f"échantillon de voix : transcription déclarée mais absente : {t}")
            elif not t:
                rep.warnings.append(f"échantillon de voix sans transcription (facultative ; utile aux moteurs à alignement texte) : {a.get('path')}")

    # variants: kind valid, referenced files and assets exist; derives_from resolvable
    for etype, e in elements.items():
        for vid, v in ((e or {}).get("variants", {}) or {}).items():
            where = f"elements.{etype}.{vid}"
            if v.get("derives_from") and v["derives_from"] not in e["variants"]:
                rep.errors.append(f"{where} : derives_from inconnu {v['derives_from']}")
            rv = resolve_variant(manifest, etype, vid) or {}
            if etype in KINDS and rv.get("kind") not in KINDS[etype]:
                rep.errors.append(f"{where} : kind '{rv.get('kind')}' inconnu pour {etype} (attendu : {', '.join(KINDS[etype])})")
            if etype == "appearance" and rv.get("kind") == "clothing" and not rv.get("garment"):
                rep.warnings.append(f"{where} : vêtement sans type 'garment' (règles de cumul inapplicables)")
            if etype == "motion" and rv.get("kind") == "video":
                for aid in rv.get("videos") or []:
                    a = A.get(aid)
                    if a and a.get("bytes", 0) > 20_000_000 and not rv.get("max_bytes_ack"):
                        rep.warnings.append(f"{where} : vidéo {aid} > 20 Mo sans accusé (transportabilité)")
            if "identity" in rv and ids and rv["identity"] not in ids:
                rep.errors.append(f"{where} : identité inconnue {rv['identity']}")
            for fld in PATH_FIELDS:
                rel = rv.get(fld)
                if isinstance(rel, str) and not (src / rel).is_file():
                    rep.errors.append(f"{where}.{fld} : fichier absent {rel}")
            if isinstance(rv.get("mesh"), dict) and not (src / rv["mesh"]["path"]).is_file():
                rep.errors.append(f"{where}.mesh : fichier absent {rv['mesh']['path']}")
            for lst in ("images", "derived", "samples", "clips", "videos"):
                for aid in rv.get(lst, []) or []:
                    if aid not in A:
                        rep.errors.append(f"{where}.{lst} : asset inconnu {aid}")
                    elif lst == "images" and A[aid].get("role") == "derived":
                        rep.errors.append(f"{where}.images : {aid} est un dérivé — il doit être listé dans 'derived', pas dans 'images'")
            if etype == "identity_weights" and rv.get("spec"):
                w = json.loads((src / rv["spec"]).read_text("utf-8")) if (src / rv["spec"]).is_file() else {}
                if not (w.get("base_model") or {}).get("name"):
                    rep.errors.append(f"{where} : weights.json sans base_model.name (un LoRA sans modèle de base est inutilisable)")
                if w.get("file") and w["file"] not in A:
                    rep.errors.append(f"{where} : asset de poids inconnu {w['file']}")

    # presets: slots resolvable, extends known, identity known, kind/region rules
    pids = preset_ids(manifest)
    for pid in pids:
        p = manifest["presets"][pid]
        if p.get("extends") and p["extends"] not in manifest["presets"]:
            rep.errors.append(f"presets.{pid} : extends inconnu {p['extends']}")
        if p.get("identity") and ids and p["identity"] not in ids:
            rep.errors.append(f"presets.{pid} : identité inconnue {p['identity']}")
        for cat, vids in resolve_preset_slots(manifest, pid).items():
            for vid in vids:
                if cat not in elements or vid not in (elements[cat] or {}).get("variants", {}):
                    rep.errors.append(f"presets.{pid}.slots.{cat} : déclinaison inconnue {vid}")
                else:
                    rv = resolve_variant(manifest, cat, vid) or {}
                    pidn = p.get("identity") or manifest.get("default_identity")
                    if rv.get("identity") and pidn and rv["identity"] != pidn:
                        rep.errors.append(f"presets.{pid} : '{vid}' est réservée à l'identité {rv['identity']}")
        rules = p.get("rules") or {}
        res = resolved(manifest, pid)
        if rules.get("single_per_kind", True):
            rep.errors += [f"presets.{pid} : {x}" for x in single_kind_violations(res)]
        if rules.get("exclusive_regions", True):
            rep.warnings += [f"presets.{pid} : {x}" for x in region_conflicts(res)]
        # per-preset age: intimate forbidden, estimated body forbidden
        pa = preset_age(manifest, pid)
        if pa is not None and pa < 18:
            if by_kind(res, "appearance", "intimate"):
                rep.errors.append(f"presets.{pid} : élément intime interdit (âge du preset {pa})")
            for b in by_kind(res, "appearance", "body"):
                if b.get("estimated"):
                    rep.errors.append(f"presets.{pid} : morphologie estimée interdite (âge {pa})")
    # intimate ⇒ tags.content must flag it (opt-in element, never hidden)
    has_intimate = any((v or {}).get("kind") == "intimate" for v in ((elements.get("appearance") or {}).get("variants", {}) or {}).values())
    content = set(((manifest.get("tags") or {}).get("content") or []))
    if has_intimate and not (content & {"nudity", "sexual"}):
        rep.errors.append("déclinaison intime présente : tags.content doit contenir 'nudity' ou 'sexual'")
    dp = default_preset_id(manifest)
    if pids and dp not in manifest["presets"]:
        rep.errors.append(f"default_preset inconnu : {dp}")
    used = set()
    for pid in pids:
        for cat, vids in resolve_preset_slots(manifest, pid).items():
            for vid in vids:
                used.add((cat, vid))
    if pids:
        for cat, e in elements.items():
            for vid in (e or {}).get("variants", {}):
                if (cat, vid) not in used:
                    rep.warnings.append(f"elements.{cat}.{vid} n'est référencée par aucun preset")

    # age rules on the lowest age (age is optional everywhere; no age at all ⇒ no sensitive usage)
    la = lowest_age(manifest)
    perms = (manifest.get("rights", {}) or {}).get("permissions", {} ) or {}
    if la is None:
        if perms.get("allowSexualUsage"):
            rep.errors.append("allowSexualUsage refusé : aucun âge déclaré (identité, preset ou déclinaison) — déclarez-en un")
        if has_intimate:
            rep.errors.append("déclinaison intime refusée : aucun âge déclaré — déclarez-en un")
    if la is not None and la < 18:
        if perms.get("allowSexualUsage"):
            rep.errors.append("allowSexualUsage interdit : âge le plus bas < 18")
        for vid, v in ((elements.get("appearance") or {}).get("variants", {}) or {}).items():
            rv = resolve_variant(manifest, "appearance", vid) or {}
            if rv.get("kind") == "intimate" and not ids:
                rep.errors.append(f"appearance.{vid} : élément intime interdit (âge le plus bas < 18)")
    # per-preset permission overrides: never more permissive than the preset's own age allows
    for pid in pids:
        p = manifest["presets"][pid]
        ov = p.get("permissions_override") or {}
        if not ov:
            continue
        page = preset_age(manifest, pid)
        eff = {**perms, **ov}
        if page is not None and page < 18 and eff.get("allowSexualUsage"):
            rep.errors.append(f"presets.{pid}.permissions_override : allowSexualUsage interdit (âge du preset {page})")
    if manifest.get("fictional") is False and not (manifest.get("rights", {}) or {}).get("consent"):
        rep.errors.append("personnage non fictif sans rights.consent")

    # per-preset checks: cards, psyche refs, duplicates, style coherence
    tokens_by_preset = {}
    for pid in (pids or [None]):
        r = resolved(manifest, pid)
        label = pid or "(implicite)"
        p = first(r, "personality")
        if p and p.get("card") and (src / p["card"]).is_file():
            try:
                card = json.loads((src / p["card"]).read_text("utf-8"))
                tokens_by_preset[label] = validate_card(card, rep, lang, f"{p['card']}")
            except Exception as e:
                rep.errors.append(f"{p['card']} illisible : {e}")
        ids_ = set()
        if p and p.get("psyche") and (src / p["psyche"]).is_file():
            try:
                ps = json.loads((src / p["psyche"]).read_text("utf-8"))
                ids_ |= {t.get("id") for t in (ps.get("traits", {}).get("custom") or [])}
                for k in ("goals", "fears"):
                    ids_ |= {it.get("id") for it in ps.get(k, []) or []}
                ids_ |= {f"trait:big5.{d}" for d in (ps.get("traits", {}).get("big5") or {})}
            except Exception as e:
                rep.errors.append(f"{p['psyche']} illisible : {e}")
        for v in r.get("posture", []) + r.get("voice", []):
            rel = v.get("spec") or v.get("profile")
            if rel and (src / rel).is_file():
                try:
                    obj = json.loads((src / rel).read_text("utf-8"))
                    refs = set(obj.get("expresses", []) or [])
                    for g in obj.get("gestures", []) or []:
                        refs |= set(g.get("expresses", []) or [])
                    refs |= set((obj.get("speech_style") or {}).get("expresses", []) or [])
                    missing = [x for x in refs if x not in ids_]
                    if missing and ids_:
                        rep.warnings.append(f"{rel} : renvois non résolus vers psyche : {', '.join(missing)}")
                except Exception as e:
                    rep.errors.append(f"{rel} illisible : {e}")
        pstyle = (manifest.get("presets", {}).get(pid, {}) if pid else {}).get("style")
        styles = set()
        for v in r.get("appearance", []):
            if v.get("style"):
                styles.add(v["style"])
            for aid in v.get("images", []) or []:
                if aid in A and A[aid].get("style"):
                    styles.add(A[aid]["style"])
        if pstyle and styles - {pstyle}:
            rep.warnings.append(f"preset {label} : style déclaré '{pstyle}' mais déclinaisons/images en {sorted(styles - {pstyle})}")
        elif not pstyle and len(styles) > 1:
            rep.warnings.append(f"preset {label} : styles visuels mélangés {sorted(styles)} sans style déclaré")

    # executable / unsafe serialized content
    declared = (manifest.get("container") or {}).get("executableContent", "none")
    for pth in src.rglob("*"):
        if pth.is_file() and pth.suffix.lower() in EXEC_EXT and declared == "none":
            rep.errors.append(f"contenu exécutable ou sérialisé non sûr : {pth.relative_to(src).as_posix()} (poids → safetensors)")

    # KPIs
    comp = compute_completeness(manifest, src)
    if recompute:
        now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        manifest["completeness"] = {**comp["file"], "computed_by": f"cof-cli/{__version__}", "computed_at": now}
        manifest["coverage"] = comp["coverage"]
        for pid, c in comp["presets"].items():
            manifest["presets"][pid]["completeness"] = {**c, "computed_by": f"cof-cli/{__version__}", "computed_at": now}
        # thumbnail = head.front of the default preset's face
        r = resolved(manifest, dp)
        fv = first(r, "appearance", "face")
        for aid in (fv or {}).get("images", []) or []:
            a = A.get(aid)
            if a and a.get("subject") == "head" and a.get("angle") == "front" and a.get("path"):
                manifest["thumbnail"] = a["path"]
                break
        # languages = union of personality / voice sample languages
        langs = set(manifest.get("languages") or [])
        for v in (elements.get("personality") or {}).get("variants", {}).values():
            if v.get("language"):
                langs.add(v["language"])
        for a in manifest.get("assets", []):
            if a.get("role") == "voice-sample" and a.get("language"):
                langs.add(a["language"])
        if langs:
            manifest["languages"] = sorted(langs)
    rep.info["completeness"] = comp["file"]
    rep.info["presets"] = {k: v["score"] for k, v in comp["presets"].items()}
    rep.info["coverage"] = comp["coverage"]
    rep.info["tokens"] = {**(tokens_by_preset.get(dp) or next(iter(tokens_by_preset.values()), {})), "tokenizer": tokenizer_name()}
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
        validate_dir(unpack(cof, td), rep, recompute=False)
    limit = {"lite": 20_000_000, "standard": 100_000_000}.get(manifest.get("size_class"))
    if limit and st["compressed"] > limit:
        rep.warnings.append(f"size_class '{manifest.get('size_class')}' dépassée : {st['compressed']/1e6:.1f} Mo")
    if manifest.get("cof") != SPEC_VERSION:
        rep.warnings.append(f"version de format {manifest.get('cof')} (outil : {SPEC_VERSION})")
    return rep
