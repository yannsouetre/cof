"""Merge several character directories into one (multi-identity), extract a preset into a lighter directory."""
from __future__ import annotations

import json
import re
import shutil
from datetime import datetime, timezone
from pathlib import Path

from .container import copy_rel, safe_rel
from .convert import ulid_like
from .model import preset_alternatives, resolve_preset_slots

NOW = lambda: datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _ident_key(m: dict, ident: dict | None = None) -> tuple:
    """Same character = same name, nickname, fictional status and morphology class (a real and a fictional
    homonym, or two unrelated 'Marc' of different natures, stay distinct)."""
    i = ident or m
    return ((i.get("name") or "").strip().lower(), (i.get("nickname") or "").strip().lower(),
            i.get("fictional") is not False, ((i.get("morphology") or {}).get("class") or "human"))


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
                copy_rel(src, a["path"], dst, newp)
            if a.get("transcript") and (src / a["transcript"]).is_file():
                t = a["transcript"]
                if (dst / t).exists():
                    parts = t.split("/"); parts[-1] = f"{prefix}-{parts[-1]}"; t = "/".join(parts)
                copy_rel(src, a["transcript"], dst, t); a["transcript"] = t
            a["path"] = newp
        taken_assets[a.get("sha256") or new_id] = a
        aid_map[old_id] = new_id
    return aid_map


def _copy_variant_files(src: Path, dst: Path, v: dict, prefix: str):
    for fld in ("card", "psyche", "story", "lorebook", "params", "code", "spec", "profile", "vec", "visemes", "path", "skeleton", "memory"):
        rel = v.get(fld)
        if isinstance(rel, str) and (src / rel).is_file():
            newrel = rel
            if (dst / rel).exists():
                parts = rel.split("/"); parts[-1] = f"{prefix}-{parts[-1]}"; newrel = "/".join(parts)
            copy_rel(src, rel, dst, newrel); v[fld] = newrel
    if isinstance(v.get("mesh"), dict) and (src / v["mesh"]["path"]).is_file():
        copy_rel(src, v["mesh"]["path"], dst)


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
        src_ids = m.get("identities") or {m.get("default_identity") or _slug(m.get("name")): {k: m.get(k) for k in ("name", "nickname", "summary", "fictional", "morphology") if m.get(k) is not None}}
        id_map = {}
        src_default = m.get("default_identity") or next(iter(src_ids))
        for iid, ident in src_ids.items():
            key = _ident_key(m, ident)
            if key in ids_by_key:
                id_map[iid] = ids_by_key[key]
            else:
                new_iid = iid if iid not in out["identities"] else f"{prefix}-{iid}"
                ident = json.loads(json.dumps(ident))
                # each character keeps ITS rights: the source file's rights travel with its characters
                if not ident.get("rights") and m.get("rights") and json.dumps(m["rights"].get("permissions"), sort_keys=True) != json.dumps((base.get("rights") or {}).get("permissions"), sort_keys=True):
                    ident["rights"] = {"permissions": m["rights"]["permissions"]}
                if iid == src_default and not ident.get("consent") and (m.get("rights") or {}).get("consent"):
                    ident["consent"] = m["rights"]["consent"]
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
                for lst in ("images", "derived", "samples", "clips", "videos", "media", "files"):
                    if nv.get(lst):
                        nv[lst] = [aid_map.get(x, x) for x in nv[lst]]
                if not v.get("derives_from"):          # every element names its character (inherited by derived ones)
                    nv["identity"] = id_map.get(v.get("identity") or src_default, v.get("identity") or src_default)
                elif nv.get("identity"):
                    nv["identity"] = id_map.get(nv["identity"], nv["identity"])
                _copy_variant_files(src, dst, nv, prefix)
                out["elements"].setdefault(cat, {"variants": {}})["variants"][new_vid] = nv
        ref_map = {f"{c}/{v0}": f"{c}/{v1}" for (c, v0), v1 in vid_map.items() if v0 != v1}   # qualified refs of this file's renamed variants
        for cat, e in out["elements"].items():   # fix derives_from after renames
            for vid, v in e["variants"].items():
                if v.get("derives_from") and (cat, v["derives_from"]) in vid_map:
                    v["derives_from"] = vid_map[(cat, v["derives_from"])]
        for (cat, vid0), vid1 in vid_map.items():        # memory nodes of this file: media_from, links, where, who follow the renames (RFC 0002 § 3)
            if cat != "memories":
                continue
            v = out["elements"]["memories"]["variants"][vid1]
            if v.get("media_from") in ref_map:
                v["media_from"] = ref_map[v["media_from"]]
            rel = v.get("memory")
            if ref_map and isinstance(rel, str) and (dst / rel).is_file():
                node = json.loads((dst / rel).read_text("utf-8"))
                for ln in node.get("links") or []:
                    if isinstance(ln, dict) and ln.get("to") in ref_map:
                        ln["to"] = ref_map[ln["to"]]
                w = node.get("where")
                if isinstance(w, dict) and w.get("environment") in ref_map:
                    w["environment"] = ref_map[w["environment"]]
                for who in node.get("who") or []:
                    if isinstance(who, dict) and who.get("identity") not in (None, "self") and who["identity"] in id_map:
                        who["identity"] = id_map[who["identity"]]
                (dst / rel).write_text(json.dumps(node, ensure_ascii=False, indent=2) + "\n", "utf-8")
        pid_map = {}
        for pid, p in (m.get("presets") or {}).items():
            np_ = json.loads(json.dumps(p))
            new_pid = pid if pid not in out["presets"] else f"{prefix}-{pid}"
            pid_map[pid] = new_pid
            np_["slots"] = {cat: [vid_map.get((cat, x), x) for x in vids] for cat, vids in (p.get("slots") or {}).items()}
            if p.get("alternatives"):
                np_["alternatives"] = {cat: [vid_map.get((cat, x), x) for x in vids] for cat, vids in p["alternatives"].items()}
            if p.get("primary_image"):
                np_["primary_image"] = aid_map.get(p["primary_image"], p["primary_image"])
            np_["identity"] = id_map.get(p.get("identity") or m.get("default_identity") or next(iter(src_ids)))
            if pid == m.get("default_preset"):
                for oi in {id_map.get(src_default)}:
                    out["identities"][oi].setdefault("default_preset", new_pid)
            for iid0, ident0 in (m.get("identities") or {}).items():
                if ident0.get("default_preset") == pid:
                    out["identities"][id_map[iid0]]["default_preset"] = new_pid
            if np_.get("extends") and np_["extends"] in (m.get("presets") or {}) and np_["extends"] != pid:
                np_["extends"] = np_["extends"] if np_["extends"] in out["presets"] else f"{prefix}-{np_['extends']}"
            out["presets"][new_pid] = np_
            if n == 0 and pid == m.get("default_preset"):
                out["default_preset"] = new_pid
        for tg in m.get("preset_tags") or []:            # tags follow their presets; same id + same label ⇒ same tag
            tl = out.setdefault("preset_tags", [])
            pres = [pid_map.get(x, x) for x in tg.get("presets") or []]
            same = next((x for x in tl if x["id"] == tg["id"] and x.get("label") == tg.get("label")), None)
            if same:
                same["presets"] = list(dict.fromkeys(same["presets"] + pres))
            else:
                tid = tg["id"] if all(x["id"] != tg["id"] for x in tl) else f"{prefix}-{tg['id']}"
                tl.append({**tg, "id": tid, "presets": pres})
    out["assets"] = list({a["id"]: a for a in taken_assets.values()}.values())
    out["id"] = ulid_like()
    di = out["identities"][out["default_identity"]]
    for k in ("name", "nickname", "summary", "fictional", "morphology"):
        if di.get(k) is not None:
            out[k] = di[k]
    out.setdefault("provenance", {})["modified"] = NOW()
    out["provenance"]["source"] = sorted({s for src in sources for s in (json.loads((src / "manifest.json").read_text("utf-8")).get("provenance", {}).get("source") or [])} | {f"cof:{json.loads((src / 'manifest.json').read_text('utf-8')).get('id')}" for src in sources})
    out["provenance"]["generator"] = "cof-cli merge"
    out.pop("completeness", None); out.pop("coverage", None); out.pop("thumbnail", None)
    _relocate_files(dst, out)
    (dst / "manifest.json").write_text(json.dumps(out, ensure_ascii=False, indent=2) + "\n", "utf-8")
    return out


def _relocate_files(dst: Path, out: dict) -> None:
    """After a merge, move each file used by a single element into that element's own folder
    (elements/<category>/<variant>/), dropping the collision prefix — a renamed variant keeps its files together."""
    import re
    from .model import variant_asset_ids
    users: dict[str, list[tuple[str, str]]] = {}
    for cat, e in (out.get("elements") or {}).items():
        for vid, v in (e.get("variants") or {}).items():
            for aid in variant_asset_ids(v):
                users.setdefault(aid, []).append((cat, vid))
    for a in out.get("assets") or []:
        u = users.get(a["id"]) or []
        if len(u) != 1 or not a.get("path", "").startswith("elements/"):
            continue
        cat, vid = u[0]
        parts = a["path"].split("/")
        if len(parts) < 4 or parts[1] != cat or parts[2] == vid:
            continue
        for fld in ("path", "transcript"):
            old = a.get(fld)
            if not old or not (dst / old).is_file():
                continue
            base = re.sub(r"^m\d+-", "", old.split("/")[-1])
            new = "/".join(["elements", cat, vid, *old.split("/")[3:-1], base])
            k = 2
            while (dst / new).exists():
                stem, dot, ext = base.rpartition(".")
                new = "/".join(["elements", cat, vid, *old.split("/")[3:-1], f"{stem}.{k}.{ext}" if dot else f"{base}.{k}"]); k += 1
            (dst / new).parent.mkdir(parents=True, exist_ok=True)
            shutil.move(str(dst / old), str(dst / new))
            a[fld] = new


def extract_preset(src: Path, dst: Path, pid: str) -> dict:
    """Keep only what preset `pid` references (variants, their parents, assets, identity)."""
    return extract_presets(src, dst, [pid])


def extract_identity(src: Path, dst: Path, iid: str, notes: list[str] | None = None) -> dict:
    """Export one character: all its presets, its elements, their files, its rights. Memory media that show
    another real person stay behind (their consent does not travel — RFC 0002 § 4.5); `notes` receives one line each."""
    from .model import preset_owner
    m = json.loads((src / "manifest.json").read_text("utf-8"))
    if iid not in (m.get("identities") or {}) and iid != m.get("default_identity"):
        raise ValueError(f"unknown character: {iid}")
    pids = [p for p in (m.get("presets") or {}) if preset_owner(m, p) == iid]
    if not pids:
        raise ValueError(f"character {iid} has no preset")
    dp = ((m.get("identities") or {}).get(iid) or {}).get("default_preset")
    if dp in pids:
        pids.remove(dp); pids.insert(0, dp)
    out = extract_presets(src, dst, pids, cast_cleanup=False)
    out["default_preset"] = pids[0]
    from .cast import drop_foreign_relations
    for line in drop_foreign_relations(out):                      # RFC 0003 § 6: a relation to a character that leaves the file
        (notes if notes is not None else []).append(f"{line}: relation dropped (the other character is not in this file)")
    (dst / "manifest.json").write_text(json.dumps(out, ensure_ascii=False, indent=2) + "\n", "utf-8")
    for vid in strip_foreign_real_media(dst, {iid}, m.get("identities") or {}):
        (notes if notes is not None else []).append(f"memories.{vid}: media showing another real person left behind (gist kept)")
    for line in relabel_departed_identities(dst, json.loads((dst / "manifest.json").read_text("utf-8")), m.get("identities") or {}):
        (notes if notes is not None else []).append(line)
    return json.loads((dst / "manifest.json").read_text("utf-8"))


def relabel_departed_identities(dst: Path, m: dict, identities: dict) -> list[str]:
    """After an extract of one character: a `who` entry that named another character of the source file becomes a
    plain person — its name as label, its age kept, `real: true` when that character was a real person (the
    consent record did not travel; the file stays honest about who is shown). Returns one line per rewrite."""
    kept = set(m.get("identities") or {})
    out = []
    for vid, v in _memory_variants(m).items():
        rel = v.get("memory")
        if not rel or not (dst / rel).is_file():
            continue
        try:
            node = json.loads((dst / rel).read_text("utf-8"))
        except Exception:
            continue
        changed = False
        for w in node.get("who") or []:
            i = w.get("identity")
            if i and i != "self" and i not in kept:
                src = identities.get(i) or {}
                w.pop("identity")
                w.setdefault("label", {(src.get("language") or "en"): src.get("name") or i})
                if src.get("fictional") is False:
                    w["real"] = True
                changed = True
                out.append(f"memories.{vid}: who: {i} is not in this file any more — kept as a person named {src.get('name') or i}")
        if changed:
            (dst / rel).write_text(json.dumps(node, ensure_ascii=False, indent=2) + "\n", "utf-8")
    return out


# ---- memories (RFC 0002 § 5.7, § 5.8, § 4.5) ---------------------------------------------------------------------

def _memory_variants(m: dict) -> dict:
    return ((m.get("elements") or {}).get("memories") or {}).get("variants") or {}


def _prune_assets(dst: Path, m: dict, freed: set[str]) -> None:
    """Remove the assets in `freed` that no variant uses any more (file and manifest entry); fix primary images."""
    from .model import variant_asset_ids
    still = {aid for e in (m.get("elements") or {}).values() for v in (e.get("variants") or {}).values() for aid in variant_asset_ids(v)}
    gone = freed - still
    for a in list(m.get("assets") or []):
        if a["id"] in gone or a.get("source") in gone:
            if a.get("path") and (dst / a["path"]).is_file():
                (dst / a["path"]).unlink()
            m["assets"].remove(a)
    for p in (m.get("presets") or {}).values():
        if p.get("primary_image") in gone:
            p.pop("primary_image")


def _unlist_variant(m: dict, cat: str, vid: str) -> None:
    for p in (m.get("presets") or {}).values():
        for key in ("slots", "alternatives"):
            if (p.get(key) or {}).get(cat):
                p[key][cat] = [x for x in p[key][cat] if x != vid]
                if not p[key][cat]:
                    del p[key][cat]


def drop_dangling_memory_links(dst: Path, m: dict) -> list[str]:
    """Links whose target node is no longer in the file are removed from the node files (an extract of one character
    loses the `same-event` links to the others'). Returns "vid → target" for each dropped link."""
    E = m.get("elements") or {}
    dropped = []
    for vid, v in _memory_variants(m).items():
        rel = v.get("memory")
        if not rel or not (dst / rel).is_file():
            continue
        try:
            node = json.loads((dst / rel).read_text("utf-8"))
        except Exception:
            continue
        keep = []
        for ln in node.get("links") or []:
            cat, _, tgt = str(ln.get("to", "")).partition("/")
            if tgt in (((E.get(cat) or {}).get("variants") or {})):
                keep.append(ln)
            else:
                dropped.append(f"{vid} → {ln.get('to')}")
        if len(keep) != len(node.get("links") or []):
            if keep:
                node["links"] = keep
            else:
                node.pop("links", None)
            (dst / rel).write_text(json.dumps(node, ensure_ascii=False, indent=2) + "\n", "utf-8")
    return dropped


def _memory_media_off(dst: Path, m: dict, vid: str) -> set[str]:
    """Take the media off one memory node (the gist stays): variant `media` / `media_from` / `nudity`, node `explicit`.
    Nodes that borrowed these media through `media_from` lose them too. Returns the freed asset ids."""
    V = _memory_variants(m)
    v = V.get(vid) or {}
    freed = set(v.pop("media", None) or [])
    v.pop("media_from", None); v.pop("nudity", None)
    rel = v.get("memory")
    if rel and (dst / rel).is_file():
        try:
            node = json.loads((dst / rel).read_text("utf-8"))
            if node.pop("explicit", None) is not None:
                (dst / rel).write_text(json.dumps(node, ensure_ascii=False, indent=2) + "\n", "utf-8")
        except Exception:
            pass
    for ovid, ov in V.items():
        if str(ov.get("media_from") or "").partition("/")[2] == vid:
            freed |= _memory_media_off(dst, m, ovid)
    return freed


def strip_explicit_memory_media(dst: Path) -> list[str]:
    """All-audiences purge of the memories (RFC 0002 § 5.8): explicit nodes keep their gist and lose their media."""
    m = json.loads((dst / "manifest.json").read_text("utf-8"))
    V = _memory_variants(m)
    hit = [vid for vid, v in V.items() if v.get("nudity") is True]
    if not hit:
        return []
    freed = set()
    for vid in hit:
        freed |= _memory_media_off(dst, m, vid)
    _prune_assets(dst, m, freed)
    (dst / "manifest.json").write_text(json.dumps(m, ensure_ascii=False, indent=2) + "\n", "utf-8")
    return hit


def strip_foreign_real_media(dst: Path, kept_identities: set[str], identities: dict | None = None) -> list[str]:
    """Extraction guard (RFC 0002 § 4.5): media showing a real person who is not among `kept_identities` are dropped.
    `identities` is the source file's table (the extract no longer holds the other characters)."""
    from .memories import load_nodes, shows_other_real_person
    m = json.loads((dst / "manifest.json").read_text("utf-8"))
    nodes = load_nodes(dst, m)
    hit = [vid for vid, node in nodes.items()
           if (_memory_variants(m).get(vid) or {}).get("media") or (_memory_variants(m).get(vid) or {}).get("media_from")
           if shows_other_real_person(m, vid, node, kept_identities, identities)]
    if not hit:
        return []
    freed = set()
    for vid in hit:
        freed |= _memory_media_off(dst, m, vid)
    _prune_assets(dst, m, freed)
    (dst / "manifest.json").write_text(json.dumps(m, ensure_ascii=False, indent=2) + "\n", "utf-8")
    return hit


def drop_personal_memories(dst: Path) -> list[str]:
    """RFC 0002 § 5.7: `visibility: personal` nodes are a user's data — removed with their files, unlisted from presets."""
    from .memories import load_nodes
    from .model import variant_asset_ids
    m = json.loads((dst / "manifest.json").read_text("utf-8"))
    V = _memory_variants(m)
    nodes = load_nodes(dst, m)
    hit = [vid for vid, node in nodes.items() if node.get("visibility") == "personal"]
    if not hit:
        return []
    freed = set()
    for vid in hit:
        for ovid, ov in V.items():          # a node that borrowed the media of a personal node loses them: the files leave with the personal node (RFC 0002 § 5.7)
            if ovid not in hit and str(ov.get("media_from") or "").partition("/")[2] == vid:
                ov.pop("media_from")
        v = V.pop(vid)
        freed |= variant_asset_ids(v)
        _unlist_variant(m, "memories", vid)
        folder = dst / "elements" / "memories" / vid
        if folder.is_dir():
            shutil.rmtree(folder)
    if not V:
        m["elements"].pop("memories", None)
        md = dst / "elements/memories"
        if md.is_dir() and not any(md.iterdir()):
            md.rmdir()
    drop_dangling_memory_links(dst, m)
    _prune_assets(dst, m, freed)
    (dst / "manifest.json").write_text(json.dumps(m, ensure_ascii=False, indent=2) + "\n", "utf-8")
    return hit


def extract_tag(src: Path, dst: Path, tids: list[str]) -> dict:
    """Keep the presets carrying ALL the given tags (intersection), and what they reference."""
    m = json.loads((src / "manifest.json").read_text("utf-8"))
    T = {t.get("id"): t for t in m.get("preset_tags") or []}
    for tid in tids:
        if tid not in T:
            raise ValueError(f"unknown tag: {tid}")
    pids = [p for p in (m.get("presets") or {}) if all(p in (T[t].get("presets") or []) for t in tids)]
    if not pids:
        raise ValueError("no preset carries " + " + ".join(tids))
    return extract_presets(src, dst, pids, tags=tids)


def extract_presets(src: Path, dst: Path, pids: list[str], tags: list[str] | None = None, cast_cleanup: bool = True) -> dict:
    """Keep what the presets reference. On a cast file, the characters no preset keeps leave the file: their relations are
    dropped and the `who` entries that named them become plain persons (as `extract --identity` does; `cast_cleanup=False`
    lets that caller do it itself and report it)."""
    m = json.loads((src / "manifest.json").read_text("utf-8"))
    for pid in pids:
        if pid not in (m.get("presets") or {}):
            raise ValueError(f"unknown preset: {pid}")
    dst.mkdir(parents=True, exist_ok=True)
    sel = set(pids)
    keep_v: set[tuple[str, str]] = set()
    out_presets = {}
    for pid in pids:
        p = json.loads(json.dumps(m["presets"][pid]))
        slots = resolve_preset_slots(m, pid)
        alts = preset_alternatives(m, pid)
        if p.get("extends") in sel:          # parent kept: keep inheritance as is
            own = p.get("slots") or {}
        else:                                 # parent dropped: flatten (slots, alternatives, primary image)
            own = slots; p.pop("extends", None)
            if alts:
                p["alternatives"] = alts
            q, seen = pid, set()               # an explicit primary image inherited from a dropped parent is copied
            while q in (m.get("presets") or {}) and q not in seen and not p.get("primary_image"):
                seen.add(q)
                p["primary_image"] = m["presets"][q].get("primary_image")
                q = m["presets"][q].get("extends")
            if not p.get("primary_image"):
                p.pop("primary_image", None)
        p["slots"] = own
        out_presets[pid] = p
        for cat, vids in [*slots.items(), *alts.items()]:
            for vid in vids:
                cur = vid
                while cur and (cat, cur) not in keep_v:
                    keep_v.add((cat, cur))
                    cur = (m["elements"].get(cat, {}).get("variants", {}).get(cur) or {}).get("derives_from")
    # what the kept memories point at outside their category (RFC 0002 § 3): the place of a memory (`where.environment`)
    # and the elements its links name (a garment, an accessory, a place) travel with the memory, whether or not the preset lists them
    for cat, vid in sorted(keep_v):
        if cat != "memories":
            continue
        rel = (m["elements"]["memories"]["variants"].get(vid) or {}).get("memory")
        try:
            node = json.loads((src / rel).read_text("utf-8")) if rel else {}
        except (OSError, ValueError):
            node = {}
        refs = [str((node.get("where") or {}).get("environment") or "")] + [str(l.get("to") or "") for l in node.get("links") or []]
        for ref in refs:
            rcat, _, rvid = ref.partition("/")
            if not rvid or rcat == "memories" or rvid not in (m["elements"].get(rcat, {}).get("variants") or {}):
                continue
            cur = rvid
            while cur and (rcat, cur) not in keep_v:
                keep_v.add((rcat, cur))
                cur = (m["elements"][rcat]["variants"].get(cur) or {}).get("derives_from")
    out = json.loads(json.dumps(m))
    out["elements"] = {}
    keep_assets: set[str] = set()
    for cat, vid in sorted(keep_v):
        v = json.loads(json.dumps(m["elements"][cat]["variants"][vid]))
        if cat == "memories" and v.get("media_from"):
            # shared media (RFC 0002 § 4.5): when the node the media come from leaves the file, the list is copied here
            from .memories import effective_media
            tgt = str(v["media_from"]).partition("/")[2]
            if ("memories", tgt) not in keep_v:
                med = effective_media(m, vid)
                v.pop("media_from")
                if med:
                    v["media"] = med
        out["elements"].setdefault(cat, {"variants": {}})["variants"][vid] = v
        for lst in ("images", "derived", "samples", "clips", "videos", "files", "media"):
            keep_assets |= set(v.get(lst) or [])
        if isinstance(v.get("mesh"), dict):
            keep_assets |= set(v["mesh"].get("textures") or [])
        if cat == "identity_weights" and v.get("spec") and (src / v["spec"]).is_file():
            w = json.loads((src / v["spec"]).read_text("utf-8"))
            if w.get("file"):
                keep_assets.add(w["file"])
        _copy_variant_files(src, dst, v, "x")
    out["presets"] = out_presets
    out["default_preset"] = m.get("default_preset") if m.get("default_preset") in sel else pids[0]
    kept = []                                   # tags are kept, restricted to the exported presets
    for tg in m.get("preset_tags") or []:
        pres = [p for p in tg.get("presets") or [] if p in sel]
        if pres:
            kept.append({**tg, "presets": pres})
    if kept:
        out["preset_tags"] = kept
    else:
        out.pop("preset_tags", None)
    idents = {out_presets[p].get("identity") or m.get("default_identity") for p in pids}
    if m.get("identities"):
        out["identities"] = {i: m["identities"][i] for i in idents if i in m["identities"]}
        dp_ident = out_presets[out["default_preset"]].get("identity") or m.get("default_identity")
        if dp_ident in out["identities"]:
            out["default_identity"] = dp_ident
            for k in ("name", "nickname", "summary", "fictional", "morphology"):
                if m["identities"][dp_ident].get(k) is not None:
                    out[k] = m["identities"][dp_ident][k]
        if len(out["identities"]) == 1:                  # one character left: its rights become the file's
            only = next(iter(out["identities"].values()))
            if only.get("rights"):
                out["rights"] = {**(out.get("rights") or {}), **only["rights"]}
            if only.get("consent"):
                out.setdefault("rights", {})["consent"] = only["consent"]
        for iid, ident in out["identities"].items():
            if ident.get("default_preset") and ident["default_preset"] not in sel:
                ident.pop("default_preset")
    out["assets"] = []
    for a in m.get("assets", []):
        if a["id"] in keep_assets or a.get("source") in keep_assets:
            out["assets"].append(a)
            for fld in ("path", "transcript"):
                if a.get(fld) and (src / a[fld]).is_file():
                    copy_rel(src, a[fld], dst)
    for d in ("rights",):
        if (src / d).is_dir():
            shutil.copytree(src / d, dst / d, dirs_exist_ok=True)
    out["id"] = ulid_like()
    tag = ("#tags=" + "+".join(tags)) if tags else f"#preset={pids[0]}"
    out.setdefault("provenance", {})["source"] = list(dict.fromkeys((m.get("provenance", {}).get("source") or []) + [f"cof:{m.get('id')}{tag}"]))
    out["provenance"]["modified"] = NOW(); out["provenance"]["generator"] = "cof-cli extract"
    for k in ("completeness", "coverage", "thumbnail"):
        out.pop(k, None)
    (dst / "manifest.json").write_text(json.dumps(out, ensure_ascii=False, indent=2) + "\n", "utf-8")
    drop_dangling_memory_links(dst, out)
    if cast_cleanup and m.get("identities") and set(out.get("identities") or {}) < set(m["identities"]):
        from .cast import drop_foreign_relations
        drop_foreign_relations(out)
        (dst / "manifest.json").write_text(json.dumps(out, ensure_ascii=False, indent=2) + "\n", "utf-8")
        relabel_departed_identities(dst, out, m["identities"])
        out = json.loads((dst / "manifest.json").read_text("utf-8"))
    return out


def strip_intimate(dst: Path) -> list[str]:
    """Safe-for-work slice: remove every `intimate` variant (and the files only it used), drop it from presets,
    and set allowSexualUsage to false everywhere (root, characters, presets). Returns the removed variant ids."""
    from .model import variant_asset_ids
    mem_hit = strip_explicit_memory_media(dst)                  # memories: the gist stays, the media go (RFC 0002 § 5.8)
    m = json.loads((dst / "manifest.json").read_text("utf-8"))
    V = ((m.get("elements") or {}).get("appearance") or {}).get("variants") or {}
    gone = [vid for vid, v in V.items() if v.get("kind") == "intimate" or v.get("nudity") is True]
    extra_freed, extra_gone = set(), [f"memories.{x} (media only)" for x in mem_hit]
    for cat, e in (m.get("elements") or {}).items():          # nude variants of other categories (posture photos…)
        if cat in ("appearance", "memories"):
            continue
        for vid in [k for k, v in ((e or {}).get("variants") or {}).items() if (v or {}).get("nudity") is True]:
            extra_freed |= variant_asset_ids(e["variants"].pop(vid)); extra_gone.append(f"{cat}.{vid}")
            for p in (m.get("presets") or {}).values():
                for key in ("slots", "alternatives"):
                    if (p.get(key) or {}).get(cat):
                        p[key][cat] = [x for x in p[key][cat] if x != vid]
    freed = set(extra_freed)
    for vid in gone:
        freed |= variant_asset_ids(V.pop(vid))
    still = {aid for e in (m.get("elements") or {}).values() for v in (e.get("variants") or {}).values() for aid in variant_asset_ids(v)}
    for a in list(m.get("assets") or []):
        if a["id"] in freed - still or a.get("source") in freed - still:
            if a.get("path") and (dst / a["path"]).is_file():
                (dst / a["path"]).unlink()
            m["assets"].remove(a)
    for p in (m.get("presets") or {}).values():
        for key in ("slots", "alternatives"):
            if (p.get(key) or {}).get("appearance"):
                p[key]["appearance"] = [x for x in p[key]["appearance"] if x not in gone]
        if (p.get("permissions_override") or {}).get("allowSexualUsage"):
            p["permissions_override"]["allowSexualUsage"] = False
        if p.get("primary_image") and p["primary_image"] in freed - still:
            p.pop("primary_image")
    for r in [m.get("rights") or {}] + [(i or {}).get("rights") or {} for i in (m.get("identities") or {}).values()]:
        if "permissions" in r:
            r["permissions"]["allowSexualUsage"] = False
    tc = (m.get("tags") or {}).get("content")
    if (gone or extra_gone) and isinstance(tc, list) and "nudity" in tc:     # images gone; `sexual` stays when set (texts may still be concerned)
        tc.remove("nudity")
        if not tc:
            tc.append("none")
    (dst / "manifest.json").write_text(json.dumps(m, ensure_ascii=False, indent=2) + "\n", "utf-8")
    return gone + extra_gone
