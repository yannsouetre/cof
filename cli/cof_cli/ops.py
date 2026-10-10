"""Merge several character directories into one (multi-identity), extract a preset into a lighter directory."""
from __future__ import annotations

import json
import re
import shutil
from datetime import datetime, timezone
from pathlib import Path

from .convert import ulid_like
from .model import resolve_preset_slots

NOW = lambda: datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _ident_key(m: dict, ident: dict | None = None) -> tuple[str, str]:
    i = ident or m
    return ((i.get("name") or "").strip().lower(), (i.get("nickname") or "").strip().lower())


def _slug(s: str) -> str:
    import unicodedata
    s = unicodedata.normalize("NFKD", s or "x").encode("ascii", "ignore").decode()
    return re.sub(r"[^a-z0-9-]+", "-", s.lower()).strip("-")[:40] or "x"


def _copy_tree_assets(src: Path, dst: Path, m: dict, prefix: str, taken_assets: dict[str, dict]) -> dict:
    """Copy files of `m` from src to dst, renaming paths under a prefix to avoid collisions; returns id remap."""
    aid_map = {}
    for a in m.get("assets", []):
        old_id = a["id"]
        dup = taken_assets.get(a.get("sha256"))
        if dup and a.get("sha256", "0" * 64) != "0" * 64:
            aid_map[old_id] = dup["id"]            # same bytes already present → reuse
            continue
        new_id = old_id if old_id not in {x["id"] for x in taken_assets.values()} else f"{prefix}-{old_id}"
        a = dict(a); a["id"] = new_id
        if a.get("path"):
            newp = a["path"]
            if (dst / newp).exists():
                parts = newp.split("/"); parts[-1] = f"{prefix}-{parts[-1]}"; newp = "/".join(parts)
            if (src / a["path"]).is_file():
                (dst / newp).parent.mkdir(parents=True, exist_ok=True); shutil.copy(src / a["path"], dst / newp)
            if a.get("transcript") and (src / a["transcript"]).is_file():
                t = a["transcript"]
                if (dst / t).exists():
                    parts = t.split("/"); parts[-1] = f"{prefix}-{parts[-1]}"; t = "/".join(parts)
                (dst / t).parent.mkdir(parents=True, exist_ok=True); shutil.copy(src / a["transcript"], dst / t); a["transcript"] = t
            a["path"] = newp
        taken_assets[a.get("sha256") or new_id] = a
        aid_map[old_id] = new_id
    return aid_map


def _copy_variant_files(src: Path, dst: Path, v: dict, prefix: str):
    for fld in ("card", "psyche", "story", "lorebook", "params", "code", "spec", "profile", "vec", "visemes", "path", "skeleton"):
        rel = v.get(fld)
        if isinstance(rel, str) and (src / rel).is_file():
            newrel = rel
            if (dst / rel).exists():
                parts = rel.split("/"); parts[-1] = f"{prefix}-{parts[-1]}"; newrel = "/".join(parts)
            (dst / newrel).parent.mkdir(parents=True, exist_ok=True); shutil.copy(src / rel, dst / newrel); v[fld] = newrel
    if isinstance(v.get("mesh"), dict) and (src / v["mesh"]["path"]).is_file():
        rel = v["mesh"]["path"]; (dst / rel).parent.mkdir(parents=True, exist_ok=True); shutil.copy(src / rel, dst / rel)


def merge_dirs(sources: list[Path], dst: Path) -> dict:
    """Merge character directories. Same (name, nickname) ⇒ same identity; else additional identities."""
    dst.mkdir(parents=True, exist_ok=True)
    base = json.loads((sources[0] / "manifest.json").read_text("utf-8"))
    out = json.loads(json.dumps(base))
    out["elements"], out["presets"], out["assets"] = {}, {}, []
    out["identities"] = {}
    taken_assets: dict[str, dict] = {}
    ids_by_key: dict[tuple[str, str], str] = {}
    for n, src in enumerate(sources):
        m = json.loads((src / "manifest.json").read_text("utf-8"))
        prefix = f"m{n}"
        # identities of this file
        src_ids = m.get("identities") or {m.get("default_identity") or _slug(m.get("name")): {k: m.get(k) for k in ("name", "nickname", "age", "summary", "fictional", "morphology") if m.get(k) is not None}}
        id_map = {}
        for iid, ident in src_ids.items():
            key = _ident_key(m, ident)
            if key in ids_by_key:
                id_map[iid] = ids_by_key[key]
            else:
                new_iid = iid if iid not in out["identities"] else f"{prefix}-{iid}"
                out["identities"][new_iid] = ident; ids_by_key[key] = new_iid; id_map[iid] = new_iid
        if n == 0:
            out["default_identity"] = id_map.get(m.get("default_identity") or next(iter(src_ids)))
        aid_map = _copy_tree_assets(src, dst, m, prefix, taken_assets)
        for a in taken_assets.values():          # remap cross-asset references of this file's assets
            for fld in ("source", "derived_from"):
                if a.get(fld) in aid_map:
                    a[fld] = aid_map[a[fld]]
        vid_map = {}
        for cat, e in (m.get("elements") or {}).items():
            for vid, v in (e.get("variants") or {}).items():
                nv = json.loads(json.dumps(v))
                new_vid = vid if vid not in out["elements"].get(cat, {"variants": {}})["variants"] else f"{prefix}-{vid}"
                vid_map[(cat, vid)] = new_vid
                for lst in ("images", "derived", "samples", "clips", "videos"):
                    if nv.get(lst):
                        nv[lst] = [aid_map.get(x, x) for x in nv[lst]]
                if nv.get("identity"):
                    nv["identity"] = id_map.get(nv["identity"], nv["identity"])
                _copy_variant_files(src, dst, nv, prefix)
                out["elements"].setdefault(cat, {"variants": {}})["variants"][new_vid] = nv
        for cat, e in out["elements"].items():   # fix derives_from after renames
            for vid, v in e["variants"].items():
                if v.get("derives_from") and (cat, v["derives_from"]) in vid_map:
                    v["derives_from"] = vid_map[(cat, v["derives_from"])]
        for pid, p in (m.get("presets") or {}).items():
            np_ = json.loads(json.dumps(p))
            new_pid = pid if pid not in out["presets"] else f"{prefix}-{pid}"
            np_["slots"] = {cat: [vid_map.get((cat, x), x) for x in vids] for cat, vids in (p.get("slots") or {}).items()}
            np_["identity"] = id_map.get(p.get("identity") or m.get("default_identity") or next(iter(src_ids)))
            if np_.get("extends") and np_["extends"] in (m.get("presets") or {}) and np_["extends"] != pid:
                np_["extends"] = np_["extends"] if np_["extends"] in out["presets"] else f"{prefix}-{np_['extends']}"
            out["presets"][new_pid] = np_
            if n == 0 and pid == m.get("default_preset"):
                out["default_preset"] = new_pid
        for a in list(taken_assets.values()):
            pass
    out["assets"] = list({a["id"]: a for a in taken_assets.values()}.values())
    out["id"] = ulid_like()
    di = out["identities"][out["default_identity"]]
    for k in ("name", "nickname", "age", "summary", "fictional", "morphology"):
        if di.get(k) is not None:
            out[k] = di[k]
    out.setdefault("provenance", {})["modified"] = NOW()
    out["provenance"]["source"] = sorted({s for src in sources for s in (json.loads((src / "manifest.json").read_text("utf-8")).get("provenance", {}).get("source") or [])} | {f"cof:{json.loads((src / 'manifest.json').read_text('utf-8')).get('id')}" for src in sources})
    out["provenance"]["generator"] = "cof-cli merge"
    out.pop("completeness", None); out.pop("coverage", None); out.pop("thumbnail", None)
    (dst / "manifest.json").write_text(json.dumps(out, ensure_ascii=False, indent=2) + "\n", "utf-8")
    return out


def extract_preset(src: Path, dst: Path, pid: str) -> dict:
    """Keep only what preset `pid` references (variants, their parents, assets, identity)."""
    m = json.loads((src / "manifest.json").read_text("utf-8"))
    if pid not in (m.get("presets") or {}):
        raise ValueError(f"preset inconnu : {pid}")
    dst.mkdir(parents=True, exist_ok=True)
    slots = resolve_preset_slots(m, pid)
    keep_v: set[tuple[str, str]] = set()
    for cat, vids in slots.items():
        for vid in vids:
            cur = vid
            while cur and (cat, cur) not in keep_v:
                keep_v.add((cat, cur))
                cur = (m["elements"].get(cat, {}).get("variants", {}).get(cur) or {}).get("derives_from")
    out = json.loads(json.dumps(m))
    out["elements"] = {}
    keep_assets: set[str] = set()
    for cat, vid in keep_v:
        v = m["elements"][cat]["variants"][vid]
        out["elements"].setdefault(cat, {"variants": {}})["variants"][vid] = v
        for lst in ("images", "derived", "samples", "clips", "videos"):
            keep_assets |= set(v.get(lst) or [])
        if isinstance(v.get("mesh"), dict):
            keep_assets |= set(v["mesh"].get("textures") or [])
        if cat == "identity_weights" and v.get("spec") and (src / v["spec"]).is_file():
            w = json.loads((src / v["spec"]).read_text("utf-8"))
            if w.get("file"):
                keep_assets.add(w["file"])
        _copy_variant_files(src, dst, v, "x")
    p = m["presets"][pid]
    out["presets"] = {pid: {**json.loads(json.dumps(p)), "slots": slots}}
    out["presets"][pid].pop("extends", None)
    out["default_preset"] = pid
    ident = p.get("identity") or m.get("default_identity")
    if m.get("identities") and ident in m["identities"]:
        out["identities"] = {ident: m["identities"][ident]}; out["default_identity"] = ident
        for k in ("name", "nickname", "age", "summary", "fictional", "morphology"):
            if m["identities"][ident].get(k) is not None:
                out[k] = m["identities"][ident][k]
    out["assets"] = []
    for a in m.get("assets", []):
        if a["id"] in keep_assets or a.get("source") in keep_assets:
            out["assets"].append(a)
            for fld in ("path", "transcript"):
                if a.get(fld) and (src / a[fld]).is_file():
                    (dst / a[fld]).parent.mkdir(parents=True, exist_ok=True); shutil.copy(src / a[fld], dst / a[fld])
    for d in ("rights",):
        if (src / d).is_dir():
            shutil.copytree(src / d, dst / d, dirs_exist_ok=True)
    out["id"] = ulid_like()
    out.setdefault("provenance", {})["source"] = list(dict.fromkeys((m.get("provenance", {}).get("source") or []) + [f"cof:{m.get('id')}#preset={pid}"]))
    out["provenance"]["modified"] = NOW(); out["provenance"]["generator"] = "cof-cli extract"
    for k in ("completeness", "coverage", "thumbnail"):
        out.pop(k, None)
    (dst / "manifest.json").write_text(json.dumps(out, ensure_ascii=False, indent=2) + "\n", "utf-8")
    return out
