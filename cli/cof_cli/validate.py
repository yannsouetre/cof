"""Validation (v0.3): schema + structure + semantic rules + KPI recomputation (per preset)."""
from __future__ import annotations

import json
import re
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
from .model import garments, ADULT, implicit_resolved, AGELESS_KINDS, AGE_CATEGORIES, CATEGORIES, KINDS, MULTI_KINDS, _age_value, age_required, asset_index, default_preset_id, first, lowest_age, preset_age, preset_identity, preset_ids, region_conflicts, resolve_preset_slots, resolve_variant, resolved, single_kind_violations, by_kind, preset_alternatives, preset_primary_image, resolved_all, backstage
from .tokens import count as count_tokens, tokenizer_name

PROMPT_FIELDS = ("description", "personality", "scenario", "first_mes", "mes_example", "system_prompt", "post_history_instructions")
EXEC_EXT = {".js", ".lua", ".py", ".wasm", ".exe", ".sh", ".bat", ".ps1"}
PICKLE_EXT = {".pkl", ".pickle", ".ckpt", ".pt", ".pth"}          # never allowed: loading them runs arbitrary code
ENGINE_EXT = {".safetensors", ".npz", ".npy", ".json", ".onnx", ".index"}


def _is_pickle(path: Path) -> bool:
    """Pickle by extension, or by content for ambiguous .bin (raw glTF buffers are fine)."""
    suf = path.suffix.lower()
    if suf in PICKLE_EXT:
        return True
    if suf == ".bin":
        try:
            head = path.open("rb").read(4)
            if head[:1] == b"\x80":
                return True
            if head == b"PK\x03\x04":
                import zipfile as _z
                return any(n.endswith((".pkl", "data.pkl")) for n in _z.ZipFile(path).namelist())
        except Exception:
            return False
    return False


def _npy_has_objects(data: bytes) -> bool:
    """A .npy whose dtype is object needs pickle to load: refuse it."""
    if not data.startswith(b"\x93NUMPY"):
        return True
    major = data[6]
    hl = int.from_bytes(data[8:10], "little") if major == 1 else int.from_bytes(data[8:12], "little")
    header = data[10 if major == 1 else 12:(10 if major == 1 else 12) + hl].decode("latin1")
    return "'|O'" in header or "'O'" in header or "object" in header
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


_sub_validators: dict[str, Draft202012Validator] = {}
# which sub-file schema validates which variant field (by category / kind)
SUBFILE_SCHEMAS = {
    ("personality", None, "card"): "card", ("personality", None, "psyche"): "psyche",
    ("identity_weights", None, "spec"): "weights", ("voice", None, "profile"): "voice-profile",
    ("posture", "attitude", "spec"): "attitude", ("motion", "attitude", "spec"): "attitude",
    ("posture", None, "pose"): "pose", ("appearance", "hair", "code"): "hair", ("appearance", "body", "params"): "body",
    ("motion", None, "visemes"): "visemes",
}


def sub_validator(name: str) -> Draft202012Validator:
    if name not in _sub_validators:
        with resources.files("cof_cli").joinpath(f"schemas/{name}.schema.json").open("r", encoding="utf-8") as f:
            _sub_validators[name] = Draft202012Validator(json.load(f), format_checker=jsonschema.FormatChecker())
    return _sub_validators[name]


def validate_subfile(obj: dict, schema: str, rep: "Report", where: str) -> None:
    """Validate a sub-file (or inline object) against spec/schemas/<schema>.schema.json. Errors are errors: these files are ours."""
    for e in sorted(sub_validator(schema).iter_errors(obj), key=lambda e: list(e.path)):
        loc = "/".join(str(p) for p in e.path) or "(root)"
        rep.errors.append(f"{where} [{schema}.schema {loc}]: {_schema_msg(e)}")


def _schema_msg(e) -> str:
    """Readable jsonschema message; enum errors always list every allowed value (agents rely on it)."""
    if e.validator == "enum":
        return f"{e.instance!r} is not an allowed value — allowed values: {', '.join(map(str, e.validator_value))}"
    return e.message if len(e.message) <= 300 else e.message[:300] + "…"


def validate_manifest(manifest: dict, rep: Report) -> None:
    for e in sorted(manifest_validator().iter_errors(manifest), key=lambda e: list(e.path)):
        loc = "/".join(str(p) for p in e.path) or "(root)"
        rep.errors.append(f"manifest.json [{loc}]: {_schema_msg(e)}")


def validate_card(card: dict, rep: Report, lang: str, where: str) -> dict:
    tokens = {}
    if card.get("spec") not in ("chara_card_v3", "chara_card_v2"):
        rep.errors.append(f"{where}: 'spec' must be 'chara_card_v3' (or 'chara_card_v2')")
    data = card.get("data")
    if not isinstance(data, dict):
        rep.errors.append(f"{where}: 'data' missing")
        return tokens
    if not data.get("name"):
        rep.errors.append(f"{where}: data.name missing")
    for f in PROMPT_FIELDS:
        v = data.get(f)
        if isinstance(v, str) and v:
            tokens[f] = count_tokens(v, lang)
    permanent = sum(tokens.get(k, 0) for k in ("description", "personality", "scenario"))
    tokens["permanent"] = permanent
    if permanent > 2500:
        rep.warnings.append(f"{where}: permanent block = {permanent} tokens (> 2,500)")
    book = data.get("character_book")
    if isinstance(book, dict):
        entries = book.get("entries", [])
        tokens["lore"] = sum(count_tokens(e.get("content", ""), lang) for e in entries if isinstance(e, dict))
        const = [e for e in entries if isinstance(e, dict) and e.get("constant")]
        if const:
            rep.warnings.append(f"{where}: {len(const)} 'constant' entry(ies) — show them on import")
    if data.get("post_history_instructions"):
        rep.warnings.append(f"{where}: post_history_instructions present — show it on import ('untrusted' text)")
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
        rep.errors.append("manifest.json not found")
        return {}
    try:
        manifest = json.loads(mpath.read_text("utf-8"))
    except Exception as e:
        rep.errors.append(f"manifest.json unreadable: {e}")
        return {}
    ver = str(manifest.get("cof", ""))
    if ver in ("0.2", "0.3", "0.4", "0.5"):
        rep.errors.append(f"manifest v{ver}: run `cof migrate` (format 1.x expected)")
        return manifest
    if re.fullmatch(r"1\.\d+", ver) and int(ver.split(".")[1]) > int(SPEC_VERSION.split(".")[1]):
        rep.warnings.append(f"manifest v{ver} is newer than this validator ({SPEC_VERSION}): unknown optional fields are preserved, not checked")
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
            rep.errors.append(f"unknown default_identity: {di}")
        else:
            for k in ("name", "fictional", "morphology"):
                if json.dumps(ids[di].get(k), sort_keys=True) != json.dumps(manifest.get(k), sort_keys=True):
                    rep.errors.append(f"the root must mirror the default identity ({k} differs)")
            for iid, ident in ids.items():
                if ident.get("fictional") is False and not ident.get("consent"):
                    rep.errors.append(f"identities.{iid}: real person without consent")

    # asset ids unique, files present
    seen = set()
    for a in manifest.get("assets", []):
        if a["id"] in seen:
            rep.errors.append(f"duplicate asset id: {a['id']}")
        seen.add(a["id"])
        if a.get("path") and not (src / a["path"]).is_file() and not a.get("uri"):
            rep.errors.append(f"missing asset: {a['path']}")
        if a.get("role") == "derived" and a.get("source") not in A:
            rep.errors.append(f"derived asset {a['id']}: unknown source {a.get('source')}")
        if a.get("role") == "voice-sample":
            t = a.get("transcript")
            if t and not (src / t).is_file():
                rep.errors.append(f"voice sample: transcript declared but missing: {t}")
            elif not t:
                rep.warnings.append(f"voice sample without transcript (optional; useful to text-aligned engines): {a.get('path')}")

    # variants: kind valid, referenced files and assets exist; derives_from resolvable
    for etype, e in elements.items():
        for vid, v in ((e or {}).get("variants", {}) or {}).items():
            where = f"elements.{etype}.{vid}"
            if v.get("derives_from") and v["derives_from"] not in e["variants"]:
                rep.errors.append(f"{where}: unknown derives_from {v['derives_from']}")
            rv = resolve_variant(manifest, etype, vid) or {}
            if etype in KINDS and rv.get("kind") not in KINDS[etype]:
                rep.errors.append(f"{where}: unknown kind '{rv.get('kind')}' for {etype} (expected: {', '.join(KINDS[etype])})")
            if etype == "appearance" and rv.get("kind") == "clothing" and not rv.get("garment"):
                rep.warnings.append(f"{where}: clothing without a 'garment' type (layering rules cannot apply)")
            if rv.get("accessory_use") and rv.get("kind") != "accessory":
                rep.warnings.append(f"{where}: accessory_use only applies to kind 'accessory' (ignored)")
            if rv.get("kind") == "accessory":
                use = rv.get("accessory_use") or "worn"
                acc_types = garments()["accessories"]["types"]
                if use == "worn" and rv.get("accessory") and rv["accessory"] not in acc_types:
                    rep.warnings.append(f"{where}: unknown accessory type '{rv['accessory']}' (garments-1.0: {', '.join(acc_types)}); for a vehicle or a companion set accessory_use to 'not-worn' or 'companion'")
                if use != "worn" and rv.get("accessory"):
                    rep.warnings.append(f"{where}: accessory type '{rv['accessory']}' ignored — accessory_use is '{use}' (only worn accessories have a body region)")
            if etype == "motion" and rv.get("kind") == "video":
                for aid in rv.get("videos") or []:
                    a = A.get(aid)
                    if a and a.get("bytes", 0) > 20_000_000 and not rv.get("max_bytes_ack"):
                        rep.warnings.append(f"{where}: video {aid} > 20 MB without `max_bytes_ack` (portability)")
            if "identity" in rv and ids and rv["identity"] not in ids:
                rep.errors.append(f"{where}: unknown identity {rv['identity']}")
            for fld in PATH_FIELDS:
                rel = rv.get(fld)
                if isinstance(rel, str) and not (src / rel).is_file():
                    rep.errors.append(f"{where}.{fld}: missing file {rel}")
                elif isinstance(rel, str) and rel.endswith(".json"):
                    schema = SUBFILE_SCHEMAS.get((etype, rv.get("kind"), fld)) or SUBFILE_SCHEMAS.get((etype, None, fld))
                    if schema:
                        try:
                            validate_subfile(json.loads((src / rel).read_text("utf-8")), schema, rep, f"{where}.{fld} ({rel})")
                        except Exception as ex:
                            rep.errors.append(f"{where}.{fld}: unreadable JSON ({ex})")
            if isinstance(rv.get("mesh"), dict) and not (src / rv["mesh"]["path"]).is_file():
                rep.errors.append(f"{where}.mesh: missing file {rv['mesh']['path']}")
            for lst in ("images", "derived", "samples", "clips", "videos", "files"):
                for aid in rv.get(lst, []) or []:
                    if aid not in A:
                        rep.errors.append(f"{where}.{lst}: unknown asset {aid}")
                    elif lst == "images" and A[aid].get("role") == "derived":
                        rep.errors.append(f"{where}.images: {aid} is a derived asset — list it in 'derived', not in 'images'")
            if etype == "identity_weights" and rv.get("spec"):
                w = json.loads((src / rv["spec"]).read_text("utf-8")) if (src / rv["spec"]).is_file() else {}
                if not (w.get("base_model") or {}).get("name"):
                    rep.errors.append(f"{where}: weights.json without base_model.name (a LoRA without its base model is unusable)")
                if w.get("file") and w["file"] not in A:
                    rep.errors.append(f"{where}: unknown weights asset {w['file']}")

    # presets: slots resolvable, extends known, identity known, kind/region rules
    pids = preset_ids(manifest)
    perms_all = (manifest.get("rights", {}) or {}).get("permissions", {}) or {}
    for pid in pids:
        p = manifest["presets"][pid]
        if p.get("extends") and p["extends"] not in manifest["presets"]:
            rep.errors.append(f"presets.{pid}: unknown extends {p['extends']}")
        if p.get("identity") and ids and p["identity"] not in ids:
            rep.errors.append(f"presets.{pid}: unknown identity {p['identity']}")
        for cat, vids in resolve_preset_slots(manifest, pid).items():
            for vid in vids:
                if cat not in elements or vid not in (elements[cat] or {}).get("variants", {}):
                    rep.errors.append(f"presets.{pid}.slots.{cat}: unknown variant {vid}")
                else:
                    rv = resolve_variant(manifest, cat, vid) or {}
                    pidn = p.get("identity") or manifest.get("default_identity")
                    if rv.get("identity") and pidn and rv["identity"] != pidn:
                        rep.errors.append(f"presets.{pid}: '{vid}' is reserved for identity {rv['identity']}")
        own_slots = p.get("slots") or {}
        for cat, vids in (p.get("alternatives") or {}).items():
            for vid in vids:
                if vid in (own_slots.get(cat) or []):
                    rep.warnings.append(f"presets.{pid}: '{vid}' is both applied (slots) and offered (alternatives) — kept as applied")
        for cat, vids in preset_alternatives(manifest, pid).items():
            for vid in vids:
                if cat not in elements or vid not in (elements[cat] or {}).get("variants", {}):
                    rep.errors.append(f"presets.{pid}.alternatives.{cat}: unknown variant {vid}")
                else:
                    rv = resolve_variant(manifest, cat, vid) or {}
                    pidn = p.get("identity") or manifest.get("default_identity")
                    if rv.get("identity") and pidn and rv["identity"] != pidn:
                        rep.errors.append(f"presets.{pid}: alternative '{vid}' is reserved for identity {rv['identity']}")
        rules = p.get("rules") or {}
        res = resolved(manifest, pid)
        if rules.get("single_per_kind", True):
            rep.errors += [f"presets.{pid}: {x}" for x in single_kind_violations(res)]
        if rules.get("exclusive_regions", True):
            rep.warnings += [f"presets.{pid}: {x}" for x in region_conflicts(res)]
        _primary_image_rules(manifest, pid, res, A, rep)
        _age_rules(manifest, pid, resolved_all(manifest, pid), perms_all, rep)   # applied ∪ offered
    if not pids:
        _age_rules(manifest, None, implicit_resolved(manifest), perms_all, rep)
    for etype, e in elements.items():
        V = (e or {}).get("variants", {}) or {}
        for vid, v in V.items():
            par = V.get(v.get("derives_from") or "")
            if par and par.get("kind") != v.get("kind"):
                rep.warnings.append(f"elements.{etype}.{vid} ({v.get('kind')}) derives from {v['derives_from']} ({par.get('kind')}): different kinds, inheritance mixes unrelated fields")
    ages_by_voice: dict[str, list] = {}
    for pid in pids:
        pa = preset_age(manifest, pid)
        for v in resolved(manifest, pid).get("voice", []):
            if pa is not None:
                ages_by_voice.setdefault(v["_id"], []).append((pa, pid))
    for vid, lst in ages_by_voice.items():
        lo, hi = min(lst), max(lst)
        if hi[0] - lo[0] > 15:
            rep.warnings.append(f"voice.{vid} shared by presets of very different ages ({lo[1]}: {lo[0]:g} years, {hi[1]}: {hi[0]:g} years) — provide one voice per age range")
    # intimate ⇒ tags.content must flag it (opt-in element, never hidden)
    has_intimate = any((v or {}).get("kind") == "intimate" for v in ((elements.get("appearance") or {}).get("variants", {}) or {}).values())
    content = set(((manifest.get("tags") or {}).get("content") or []))
    if has_intimate and not (content & {"nudity", "sexual"}):
        rep.errors.append("intimate variant present: tags.content must include 'nudity' or 'sexual'")
    if manifest.get("preset_groups") is not None:
        rep.warnings.append("preset_groups is deprecated (builder 0.8.0): use preset_tags — `cof migrate` converts it")
    seen_t = set()
    for tg in manifest.get("preset_tags") or []:
        tid = tg.get("id")
        if tid in seen_t:
            rep.errors.append(f"preset_tags: duplicate tag id '{tid}'")
        seen_t.add(tid)
        for pid in tg.get("presets") or []:
            if pid not in (manifest.get("presets") or {}):
                rep.errors.append(f"preset_tags.{tid}: unknown preset '{pid}'")
    by_tags: dict[frozenset, list[str]] = {}
    for pid in pids:
        ts = frozenset(tg.get("id") for tg in manifest.get("preset_tags") or [] if pid in (tg.get("presets") or []))
        if ts:
            by_tags.setdefault(ts, []).append(pid)
    for ts, same in by_tags.items():
        if len(same) > 1:
            rep.warnings.append(f"presets {', '.join(same)} carry the same tags ({', '.join(sorted(ts))}) — facet navigation cannot tell them apart; add a tag (e.g. facet 'look')")
    dp = default_preset_id(manifest)
    if pids and dp not in manifest["presets"]:
        rep.errors.append(f"unknown default_preset: {dp}")
    for cat, vid in backstage(manifest):
        rep.warnings.append(f"elements.{cat}.{vid} is backstage: referenced by no preset (kept, never applied nor offered) — offer it in a preset, or delete it if it is a leftover")

    # intimate variants: age mandatory and ≥ 18, wherever they are (even outside any preset)
    for vid, v in ((elements.get("appearance") or {}).get("variants", {}) or {}).items():
        rv = resolve_variant(manifest, "appearance", vid) or {}
        if rv.get("kind") == "intimate":
            x = _age_value(rv.get("age"))
            if x is None:
                rep.errors.append(f"appearance.{vid} (intimate): age required (≥ {ADULT})")
            elif x < ADULT:
                rep.errors.append(f"appearance.{vid} (intimate): age {x} < {ADULT} — forbidden")
    for cwhere, cobj in [("rights.consent", (manifest.get("rights", {}) or {}).get("consent")), *[(f"identities.{i}.consent", (x or {}).get("consent")) for i, x in ids.items()]]:
        if isinstance(cobj, dict):
            validate_subfile(cobj, "consent", rep, cwhere)
    if manifest.get("fictional") is False and not (manifest.get("rights", {}) or {}).get("consent"):
        rep.errors.append("non-fictional character without rights.consent")

    for vid, v in ((elements.get("personality") or {}).get("variants") or {}).items():
        if v.get("kind") == "description" and not (v.get("text") or "").strip():
            rep.warnings.append(f"personality.{vid} (description): empty `text` field — free text goes inline in `text`")
        if v.get("kind") == "card" and not v.get("card"):
            rep.errors.append(f"personality.{vid} (card): `card` path (card.json) missing")

    # voice engine artifacts: tied to an exact engine/model, safe formats only
    perms0 = (manifest.get("rights") or {}).get("permissions") or {}
    for vid, v in ((elements.get("voice") or {}).get("variants") or {}).items():
        prof_path = v.get("profile")
        try:
            prof = json.loads((src / prof_path).read_text("utf-8")) if prof_path and (src / prof_path).is_file() else {}
        except Exception:
            prof = {}
        for i, en in enumerate(prof.get("engines") or []):
            w = f"voice.{vid}.engines[{i}] ({en.get('engine')})"
            ids = list(en.get("files") or []) + ([en["artifact"]] if en.get("artifact") else [])
            if not ids and not en.get("voice_id"):
                rep.warnings.append(f"{w}: neither files nor voice_id — entry has no effect")
            if ids and not en.get("model"):
                rep.warnings.append(f"{w}: specify `model` (exact model, e.g. coqui/XTTS-v2) — a voice embedding is only readable by the model that produced it")
            for aid in ids:
                a = A.get(aid)
                if not a:
                    rep.errors.append(f"{w}: unknown asset '{aid}'")
                elif a.get("path") and Path(a["path"]).suffix.lower() not in ENGINE_EXT:
                    rep.warnings.append(f"{w}: unexpected format {Path(a['path']).suffix} — expected: {', '.join(sorted(ENGINE_EXT))}")
            if ids and perms0.get("allowVoiceCloning") is False:
                rep.warnings.append(f"{w}: voice embedding included while allowVoiceCloning = false — readers may only use it to voice THIS character")
    # Daz Studio content: references a content library by design; licence of store products
    for vid, v in ((elements.get("volume3d") or {}).get("variants") or {}).items():
        if v.get("kind") != "daz":
            continue
        w = f"volume3d.{vid} (daz)"
        if not v.get("daz_category"):
            rep.warnings.append(f"{w}: specify daz_category (characters, wearables, hair, environments, props, poses-animations)")
        if not v.get("requires"):
            rep.warnings.append(f"{w}: list in `requires` the Daz products the .duf files depend on (base figure, morphs, textures)")
        for aid in v.get("files") or []:
            a = A.get(aid) or {}
            ap = src / a.get("path", "") if a.get("path") else None
            if not ap or not ap.is_file():
                continue
            if ap.suffix.lower() == ".zip":
                try:
                    import zipfile as _z
                    names = _z.ZipFile(ap).namelist()
                    risky = [x for x in names if x.lower().endswith((".dsa", ".dse", ".exe", ".dll", ".bat", ".ps1", ".sh", ".py", ".js"))]
                    if risky:
                        rep.warnings.append(f"{w}: archive {ap.name} contains {len(risky)} script(s) or executable(s) (e.g. {risky[0]}) — Daz scripts (.dsa/.dse) run inside Daz Studio: only open trusted archives")
                except Exception:
                    rep.errors.append(f"{w}: unreadable archive {ap.name}")
            elif ap.suffix.lower() == ".rar":
                rep.warnings.append(f"{w}: RAR archive {ap.name} not inspected by the validator — prefer .zip, or only open trusted archives")
            if str(a.get("license", "")).startswith("LicenseRef-Daz") and perms0.get("allowRedistribution"):
                rep.warnings.append(f"{w}: {ap.name} is under a Daz licence (Store product) while allowRedistribution = true — such a .cof must not be shared")
        rep.warnings.append(f"{w}: Daz licence — the standard licence covers renders, not redistribution of Store 3D files (an Interactive License is required); only embed your own files (preset or pose .duf, morphs you made)")
    # assets by link (e.g. LoRA weights): allowed, flagged
    for a in manifest.get("assets", []) or []:
        if a.get("uri") and not a.get("path"):
            if a.get("sha256"):
                rep.warnings.append(f"asset {a.get('id')} by link ({a.get('uri')}): version pinned by sha256, but the link may disappear or change — embedding it in the .cof guarantees reproducibility")
            else:
                rep.warnings.append(f"asset {a.get('id')} by link without sha256: follows the latest version (not reproducible) and the link may disappear")
    # 3D must be self-contained: one file carrying meshes AND textures (GLB/VRM/USDZ/3MF/splats)
    for vid, v in ((elements.get("volume3d") or {}).get("variants") or {}).items():
        for rel in [v.get("path"), (v.get("mesh") or {}).get("path")]:
            if not rel:
                continue
            ext = rel.rsplit(".", 1)[-1].lower()
            where3 = f"volume3d.{vid} ({v.get('kind')})"
            if ext in ("obj", "gltf") and v.get("self_contained") is False:
                rep.warnings.append(f"{where3}: declared not self-contained (`self_contained: false`) — external materials / textures / data missing, accepted by the author's choice")
                continue
            if ext == "obj":
                rep.errors.append(f"{where3}: OBJ is not self-contained (separate MTL and textures) — convert to GLB (Blender, obj2gltf), or declare `self_contained: false` if an untextured mesh is enough (e.g. poses)")
            elif ext == "gltf":
                try:
                    g = json.loads((src / rel).read_text("utf-8"))
                    ext_uris = [x.get("uri") for k in ("buffers", "images") for x in g.get(k, []) if x.get("uri") and not str(x.get("uri")).startswith("data:")]
                except Exception:
                    ext_uris = ["?"]
                if ext_uris:
                    rep.errors.append(f"{where3}: glTF with external resources ({len(ext_uris)}) — convert to GLB (gltf-transform copy in.gltf out.glb), or declare `self_contained: false`")
            elif ext == "fbx":
                rep.warnings.append(f"{where3}: FBX may reference external textures and is proprietary — prefer GLB/VRM")
            elif v.get("kind") == "environment" and ext not in ("glb", "usdz", "spz", "ply", "splat", "gltf"):
                rep.warnings.append(f"{where3}: unexpected format for a 3D environment (.{ext}) — expected: GLB, USDZ, splats (SPZ/PLY/SPLAT)")

    # a coherence finding of severity `illegal` (e.g. sexualised content in a minor preset) invalidates the file
    for pid_, p_ in (manifest.get("presets") or {}).items():
        for iss in ((p_.get("coherence") or {}).get("issues") or []):
            if iss.get("severity") == "illegal":
                rep.errors.append(f"preset {pid_}: coherence finding of severity `illegal` — {iss.get('message', '')} (the file must not be published)")

    # per-preset checks: cards, psyche refs, duplicates, style coherence
    tokens_by_preset = {}
    for pid in (pids or [None]):
        r = resolved(manifest, pid)
        label = pid or "(implicit)"
        p = first(r, "personality")
        if p and p.get("card") and (src / p["card"]).is_file():
            try:
                card = json.loads((src / p["card"]).read_text("utf-8"))
                tokens_by_preset[label] = validate_card(card, rep, lang, f"{p['card']}")
            except Exception as e:
                rep.errors.append(f"{p['card']} unreadable: {e}")
        ids_ = set()
        if p and p.get("psyche") and (src / p["psyche"]).is_file():
            try:
                ps = json.loads((src / p["psyche"]).read_text("utf-8"))
                ids_ |= {t.get("id") for t in (ps.get("traits", {}).get("custom") or [])}
                for k in ("goals", "fears"):
                    ids_ |= {it.get("id") for it in ps.get(k, []) or []}
                ids_ |= {f"trait:big5.{d}" for d in (ps.get("traits", {}).get("big5") or {})}
            except Exception as e:
                rep.errors.append(f"{p['psyche']} unreadable: {e}")
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
                        rep.warnings.append(f"{rel}: unresolved references to psyche: {', '.join(missing)}")
                except Exception as e:
                    rep.errors.append(f"{rel} unreadable: {e}")
        pstyle = (manifest.get("presets", {}).get(pid, {}) if pid else {}).get("style")
        styles = set()
        for v in r.get("appearance", []):
            if v.get("style"):
                styles.add(v["style"])
            for aid in v.get("images", []) or []:
                if aid in A and A[aid].get("style"):
                    styles.add(A[aid]["style"])
        if pstyle and styles - {pstyle}:
            rep.warnings.append(f"preset {label}: declared style '{pstyle}' but variants/images in {sorted(styles - {pstyle})}")
        elif not pstyle and len(styles) > 1:
            rep.warnings.append(f"preset {label}: mixed visual styles {sorted(styles)} with no declared style")

    # executable / unsafe serialized content
    declared = (manifest.get("container") or {}).get("executableContent", "none")
    for pth in src.rglob("*"):
        if not pth.is_file():
            continue
        rel = pth.relative_to(src).as_posix()
        if _is_pickle(pth):
            rep.errors.append(f"pickle file refused: {rel} — loading it runs code; convert to .safetensors (or numeric .npz)")
        elif pth.suffix.lower() in EXEC_EXT and declared == "none":
            rep.errors.append(f"undeclared executable content: {rel} — declare container.executableContent: \"scripts\" or remove the file")
        elif pth.suffix.lower() == ".npy" and _npy_has_objects(pth.read_bytes()[:4096]):
            rep.errors.append(f"NumPy object array (requires pickle): {rel} — save a numeric array")
        elif pth.suffix.lower() == ".npz":
            import zipfile as _z
            try:
                with _z.ZipFile(pth) as z:
                    if any(_npy_has_objects(z.open(nm).read(4096)) for nm in z.namelist() if nm.endswith(".npy")):
                        rep.errors.append(f"NumPy archive with object arrays (requires pickle): {rel} — save numeric arrays")
            except Exception:
                rep.errors.append(f"unreadable NumPy archive: {rel}")

    _duplicate_images(src, manifest, rep)

    # KPIs
    comp = compute_completeness(manifest, src)
    if recompute:
        now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        manifest["completeness"] = {**comp["file"], "computed_by": f"cof-cli/{__version__}", "computed_at": now}
        manifest["coverage"] = comp["coverage"]
        for pid, c in comp["presets"].items():
            manifest["presets"][pid]["completeness"] = {**c, "computed_by": f"cof-cli/{__version__}", "computed_at": now}
        # thumbnail = thumbnail_source, else the default preset's primary_image, else head.front of its face, else first image of face / character-sheet / reference-set / body
        r = resolved(manifest, dp)
        cand = []
        for k in ("face", "character-sheet", "reference-set", "body"):
            for v in [x for x in r.get("appearance", []) if x.get("kind") == k]:
                cand += [A[i] for i in v.get("images", []) or [] if i in A and A[i].get("path")]
        best = next((a for a in cand if a.get("subject") == "head" and a.get("angle") == "front"), cand[0] if cand else None)
        pim = ((manifest.get("presets") or {}).get(dp or "") or {}).get("primary_image")
        if pim and A.get(pim, {}).get("path"):
            best = A[pim]                  # the default preset's primary image
        ts = A.get(manifest.get("thumbnail_source") or "")
        if ts and ts.get("path"):
            best = ts                      # the author's explicit choice wins
        if best:
            manifest["thumbnail"] = best["path"]
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
        rep.errors.append(f"unreadable archive: {e}")
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
        try:
            folder = unpack(cof, td)
        except ContainerError as e:
            rep.errors.append(str(e))
            return rep
        validate_dir(folder, rep, recompute=False)
    limit = {"lite": 20_000_000, "standard": 100_000_000}.get(manifest.get("size_class"))
    if limit and st["compressed"] > limit:
        rep.warnings.append(f"size_class '{manifest.get('size_class')}' exceeded: {st['compressed']/1e6:.1f} MB")
    if manifest.get("cof") != SPEC_VERSION:
        rep.warnings.append(f"format version {manifest.get('cof')} (tool: {SPEC_VERSION})")
    return rep


def _image_sig(path: Path):
    """24×24 grayscale thumbnail + aspect ratio + pixel size (None if Pillow is missing or the image is unreadable)."""
    try:
        from PIL import Image
        with Image.open(path) as im:
            size = im.size
            im.draft("L", (96, 96))
            px = list(im.convert("L").resize((24, 24)).tobytes())
        return px, size[0] / size[1] if size[1] else 0, size
    except Exception:
        return None


def _duplicate_images(src: Path, manifest: dict, rep: "Report") -> None:
    """Warn when the same picture is embedded twice (e.g. a reduced copy AND the original): same aspect ratio,
    near-identical pixels (mean difference ≤ 2/255 on a 24×24 thumbnail). Front/back views of a silhouette differ far more."""
    seen = []
    for a in manifest.get("assets") or []:
        if not str(a.get("mediaType", "")).startswith("image/") or a.get("role") == "derived" or not a.get("path"):
            continue
        f = src / a["path"]
        if not f.is_file():
            continue
        sig = _image_sig(f)
        if not sig:
            continue
        for b, sb in seen:
            if abs(sig[1] - sb[1]) <= 0.01 * max(sb[1], 1e-6) and sum(abs(x - y) for x, y in zip(sig[0], sb[0])) / len(sig[0]) <= 2:
                small, big = (a, b) if sig[2][0] * sig[2][1] <= sb[2][0] * sb[2][1] else (b, a)
                rep.warnings.append(f"assets {small['id']} and {big['id']} are the same image{' at two resolutions' if sig[2] != sb[2] else ''} ({small['path']}, {big['path']}) — keep one (the lighter one is usually enough)")
                break
        else:
            seen.append((a, sig))


HEAD_ONLY = {"closeup", "head", "bust"}      # asset framings that cannot show an outfit


def _primary_image_rules(manifest: dict, pid: str, res: dict, A: dict, rep: "Report") -> None:
    """primary_image must be an image of a variant the preset APPLIES; warn when it cannot show an outfit."""
    p = manifest["presets"][pid]
    pim = p.get("primary_image")
    if pim:
        if pim not in A:
            rep.errors.append(f"presets.{pid}.primary_image: unknown asset {pim}")
            return
        if not str(A[pim].get("mediaType", "")).startswith("image/"):
            rep.errors.append(f"presets.{pid}.primary_image: {pim} is not an image")
            return
        applied = {i for lst in res.values() for v in lst for i in (v.get("images") or [])}
        if pim not in applied:
            rep.errors.append(f"presets.{pid}.primary_image: {pim} is not an image of a variant applied by this preset (slots)")
            return
    aid = preset_primary_image(manifest, pid)
    if not aid or aid not in A:
        return
    a = A[aid]
    head_only = a.get("framing") in HEAD_ONLY or (a.get("subject") == "head" and a.get("framing") != "full")
    if head_only and not by_kind(res, "appearance", "clothing"):
        rep.warnings.append(f"presets.{pid}: the primary image ({aid}) shows only the head and the preset applies no clothing — the default outfit is undefined (set primary_image to a body image or apply clothing)")


def _age_rules(manifest: dict, pid: str | None, res: dict, perms_all: dict, rep: "Report") -> None:
    """v0.5: age lives on the representation. Required on face/body/sheet/reference (human form) and intimate;
    a preset with any element < 18 admits no intimate, no estimated body, no effective allowSexualUsage."""
    label = f"presets.{pid}" if pid else "implicit preset"
    p = (manifest.get("presets", {}) or {}).get(pid or "", {}) or {}
    pa = preset_age(manifest, pid)
    for cat in AGE_CATEGORIES:
        for v in res.get(cat, []):
            if v.get("kind") in AGELESS_KINDS:
                continue
            if age_required(manifest, pid, v) and _age_value(v.get("age")) is None:
                rep.errors.append(f"{label}: {cat}.{v['_id']} ({v['kind']}) must declare an age (basis 'apparent' if the canonical age is unknown)")
    eff_perms = {**perms_all, **(p.get("permissions_override") or {})}
    if pa is not None and pa < ADULT:
        if by_kind(res, "appearance", "intimate"):
            rep.errors.append(f"{label}: intimate variant combined with an element under {ADULT} (preset age {pa}) — forbidden")
        for b in by_kind(res, "appearance", "body"):
            if b.get("estimated"):
                rep.errors.append(f"{label}: estimated morphology forbidden (age {pa})")
        if eff_perms.get("allowSexualUsage"):
            rep.errors.append(f"{label}: effective allowSexualUsage forbidden (preset age {pa}) — set it to false at file level or in permissions_override")
