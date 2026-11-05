"""`cof` command line."""
from __future__ import annotations

import argparse
import json
import zipfile
import shutil
import math
import re
import sys
import tempfile
from pathlib import Path

from . import __version__
from .completeness import compute as compute_completeness
from .container import make_thumbnail, refresh_asset_index, ContainerError, pack, read_manifest, unpack
from .convert import card_to_cof_dir, export_soul, read_card_from_png, write_card_to_png
from .migrate import migrate_any
from .ops import extract_preset, merge_dirs, extract_tag
from .model import asset_index, default_preset_id, first, preset_age, resolved
from .validate import Report, validate_cof, validate_dir


def _print_report(rep: Report, as_json: bool) -> int:
    if as_json:
        print(json.dumps(rep.to_dict(), ensure_ascii=False, indent=2))
    else:
        for e in rep.errors:
            print(f"ERROR  {e}")
        for w in rep.warnings:
            print(f"WARN   {w}")
        for n in rep.info.get("notes") or []:
            print(f"INFO   {n}")
        c = rep.info.get("completeness")
        if c:
            print(f"completeness: {c['score']}/100 (level {c['level']}) — " + ", ".join(f"{k} {v}" for k, v in c["layers"].items()))
            print("ready for:    " + (", ".join(c["targets_ready"]) or "—"))
        cov = rep.info.get("coverage")
        if cov:
            print(f"coverage:     {', '.join(cov['elements']) or '—'} ({cov['variants']} variant(s), {cov['presets']} preset(s))")
        if rep.info.get("presets") and len(rep.info["presets"]) > 1:
            print("presets:      " + ", ".join(f"{k} {v}" for k, v in rep.info["presets"].items()))
        t = rep.info.get("tokens")
        if t and "permanent" in t:
            print(f"tokens:       permanent {t['permanent']}" + (f", lore {t['lore']}" if "lore" in t else "") + f" ({t['tokenizer']})")
        print("OK" if rep.ok else f"NOT CONFORMANT ({len(rep.errors)} error(s))")
    return 0 if rep.ok else 1


def cmd_validate(a):
    p = Path(a.path)
    if p.is_dir():
        rep = Report()
        validate_dir(p, rep, recompute=False)
    else:
        rep = validate_cof(p)
    return _print_report(rep, a.json)


def cmd_pack(a):
    src = Path(a.dir)
    # hashes first: missing sha256/bytes are schema errors that would otherwise skip the recompute of
    # completeness / coverage / languages and leave stale figures in the packed manifest
    mpath = src / "manifest.json"
    try:
        m0 = json.loads(mpath.read_text("utf-8"))
        refresh_asset_index(src, m0, strict=False)
        mpath.write_text(json.dumps(m0, ensure_ascii=False, indent=2) + "\n", "utf-8")
    except Exception:
        pass
    rep = Report()
    manifest = validate_dir(src, rep, recompute=True)
    if rep.errors and not a.force:
        _print_report(rep, a.json)
        print("Folder not conformant: fix it or use --force.", file=sys.stderr)
        return 1
    if manifest:
        make_thumbnail(src, manifest)
        from datetime import datetime, timezone
        manifest.setdefault("provenance", {})["modified"] = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        (src / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", "utf-8")
    if manifest and not getattr(a, "no_readme", False):
        from .selfdesc import write_self_description
        write_self_description(src, manifest)                     # COF.md: the container describes itself (never normative)
    out = Path(a.out) if a.out else src.with_suffix(".cof")
    try:
        pack(src, out)
    except ContainerError as e:
        print(f"ERROR  {e}", file=sys.stderr)
        return 1
    print(f"written: {out} ({out.stat().st_size/1e6:.2f} MB)")
    return 0


def cmd_unpack(a):
    out = Path(a.out) if a.out else Path(a.cof).with_suffix("")
    unpack(a.cof, out)
    print(f"extracted to: {out}")
    return 0


def cmd_info(a):
    m = read_manifest(a.cof)
    c = m.get("completeness") or compute_completeness(m)
    print(json.dumps({"name": m.get("name"), "id": m.get("id"), "cof": m.get("cof"), "age": {p: preset_age(m, p) for p in (m.get("presets") or {})},
                      "fictional": m.get("fictional"), "size_class": m.get("size_class"), "thumbnail": m.get("thumbnail"),
                      "completeness": c["file"] if isinstance(c, dict) and "file" in c else c, "coverage": m.get("coverage"),
                      "presets": {k: {kk: vv for kk, vv in {"label": v.get("label"), "identity": v.get("identity"), "extends": v.get("extends"), "slots": v.get("slots"),
                                          "alternatives": v.get("alternatives"), "primary_image": v.get("primary_image"),
                                          "tags": [t.get("id") for t in m.get("preset_tags") or [] if k in (t.get("presets") or [])],
                                          "score": (v.get("completeness") or {}).get("score")}.items() if vv} for k, v in (m.get("presets") or {}).items()},
                      "default_preset": m.get("default_preset"),
                      "variants": {cat: {vid: " · ".join(str(x) for x in (v.get("kind"), v.get("label"), v.get("language"), v.get("identity")) if x)
                                         for vid, v in (e.get("variants") or {}).items()} for cat, e in (m.get("elements") or {}).items()},
                      "preset_tags": [{"id": t.get("id"), "facet": t.get("facet"), "presets": t.get("presets")} for t in m.get("preset_tags") or []],
                      "characters": list((m.get("identities") or {}).keys()) or None,
                      "tags": m.get("tags"), "assets": len(m.get("assets", []))},
                     ensure_ascii=False, indent=2))
    return 0


def cmd_tokens(a):
    p = Path(a.path)
    rep = Report()
    if p.is_dir():
        validate_dir(p, rep, recompute=False)
    else:
        with tempfile.TemporaryDirectory() as td:
            validate_dir(unpack(p, td), rep, recompute=False)
    print(json.dumps(rep.info.get("tokens", {}), ensure_ascii=False, indent=2))
    return 0


def cmd_embed_text(a):
    from .convert import write_text_to_png
    png = Path(a.png).read_bytes(); text = Path(a.text).read_text("utf-8")
    out = Path(a.out) if a.out else Path(a.png).with_name(Path(a.png).stem + ".cof.png")
    out.write_bytes(write_text_to_png(png, text)); print(f"{out} — {len(text)} characters in iTXt Description")


def cmd_read_text(a):
    from .convert import read_text_from_image
    r = read_text_from_image(Path(a.image).read_bytes())
    if not r:
        print("no embedded descriptive text"); return 1
    print(f"[{r['source']}] {len(r['text'])} characters\n"); print(r["text"])


def cmd_import(a):
    src = Path(a.src)
    if src.suffix.lower() == ".png":
        png = src.read_bytes()
        card = read_card_from_png(png)
    elif src.suffix.lower() == ".json":
        card = json.loads(src.read_text("utf-8"))
        png = None
        if "spec" not in card:
            card = {"spec": "chara_card_v2", "spec_version": "2.0", "data": card}
    else:
        print("expected source: .png (card) or .json (card)", file=sys.stderr)
        return 1
    dest = Path(a.out) if a.out else Path(src.stem)
    removed = []
    card_to_cof_dir(card, dest, png=png if a.keep_png else None, age=a.age, fictional=not a.real, language=a.lang, removed=removed)
    rep = Report()
    validate_dir(dest, rep, recompute=True)
    if removed:
        rep.warnings.insert(0, "embedded chat / avatar not imported: a user's personal data, not part of the character (data.extensions." + ", data.extensions.".join(removed) + ")")
    print(f"COF folder created: {dest}")
    return _print_report(rep, a.json)


def _fname(manifest: dict) -> str:
    """A default output name from the character's name: a plain file name, never a path."""
    return re.sub(r"[^A-Za-z0-9._-]+", "-", str(manifest.get("name") or "character")).strip("-.") or "character"


def cmd_export(a):
    src = Path(a.src)
    with tempfile.TemporaryDirectory() as td:
        d = src if src.is_dir() else unpack(src, td)
        manifest = json.loads((d / "manifest.json").read_text("utf-8"))
        fmt = a.format
        out = Path(a.out) if a.out else None
        pid = a.preset or default_preset_id(manifest)
        r = resolved(manifest, pid)
        A = asset_index(manifest)
        card_path = (first(r, "personality") or {}).get("card")
        if fmt in ("png", "card") and not card_path:
            print("this preset has no personality variant (card.json)", file=sys.stderr)
            return 1
        if fmt in ("png", "card"):
            from .convert import strip_card_payloads
            card = json.loads((d / card_path).read_text("utf-8"))
            gone = strip_card_payloads(card)               # an old card may still carry a user's chat: it never leaves with an export (hunt H1-12)
            if gone:
                print("WARN   not exported: a user's personal data in the card (data.extensions." + ", data.extensions.".join(gone) + ")")
        if fmt == "png":
            head = next((A[i]["path"] for i in (first(r, "appearance", "face") or {}).get("images", []) if i in A and A[i].get("subject") == "head" and A[i].get("angle") == "front"), None)
            if head and head.lower().endswith(".png"):
                png = (d / head).read_bytes()
            else:
                png = _placeholder_png(d / head if head else None)
            out = out or Path(f"{_fname(manifest)}.png")
            out.write_bytes(write_card_to_png(png, card))
        elif fmt == "soul":
            soul, identity = export_soul(d, pid)
            out = out or Path(".")
            out.mkdir(parents=True, exist_ok=True)
            (out / "SOUL.md").write_text(soul, "utf-8")
            (out / "IDENTITY.md").write_text(identity, "utf-8")
        elif fmt == "agent":
            from .convert import export_agent
            out = out or Path(f"{_fname(manifest)}-agent")
            done = export_agent(d, out, pid, keep_personal=getattr(a, "keep_personal", False), keep_dangerous=getattr(a, "keep_dangerous", False))
            print(f"skills: {', '.join(done['skills']) or '—'} · memory files: {len(done['memories'])} · memories (nodes): {done.get('memory_nodes', 0)} · psyche (nodes): {done.get('psyche_nodes', 0)} · documents: {len(done['documents'])}")
            if done.get("personal_dropped") or done.get("psyche_personal_dropped"):
                print(f"personal memories not exported: {done.get('personal_dropped', 0)}, personal psyche nodes: {done.get('psyche_personal_dropped', 0)} (--keep-personal exports them)")
            if done.get("dangerous_dropped"):
                print(f"dangerous psyche nodes not exported: {done['dangerous_dropped']} (an agent acts — --keep-dangerous exports them)")
        elif fmt == "card":
            out = out or Path(f"{_fname(manifest)}.card.json")
            out.write_text(json.dumps(card, ensure_ascii=False, indent=2), "utf-8")
        else:
            print(f"unsupported format: {fmt}", file=sys.stderr)
            return 1
    print(f"exported: {out}")
    return 0


def cmd_merge(a):
    dirs = []
    with tempfile.TemporaryDirectory(prefix="cof-merge-") as td:
        for i, src in enumerate(a.sources):
            p = Path(src)
            if p.is_file():
                d = Path(td) / str(i); unpack(p, d); dirs.append(d)
            else:
                dirs.append(p)
        merge_dirs(dirs, Path(a.out))
    rep = Report(); validate_dir(Path(a.out), rep, recompute=True)
    Path(a.out, "manifest.json").write_text(json.dumps(json.loads(Path(a.out, "manifest.json").read_text("utf-8")) | {}, ensure_ascii=False, indent=2) + "\n", "utf-8")
    print(f"merged into: {a.out}")
    return _print_report(rep, a.json)


def _gists(a) -> dict | None:
    gists = {}
    for g in a.gist:
        if "=" not in g:
            print("ERROR  --gist expects LANG=TEXT (e.g. fr=\"…\")", file=sys.stderr); return None
        k, v = g.split("=", 1); gists[k.strip()] = v.strip()
    return gists


def _add_node(a, what: str, add):
    """The shared write path of `memory add` and `psyche add`: a copy is edited, validated, and only then written back
    (a .cof is repacked, a folder is overwritten); `add(work)` returns the new node id."""
    from .selfdesc import write_self_description
    src = Path(a.src)
    if not src.exists():
        print(f"ERROR  {src}: no such file or folder", file=sys.stderr); return 2
    is_file = src.is_file()
    tmp = tempfile.TemporaryDirectory(prefix="cof-add-")              # a folder is edited through a copy: nothing lands in it unless the result validates
    work = Path(tmp.name) / "x"
    try:
        if is_file:
            unpack(src, work)
        else:
            shutil.copytree(src, work)
        vid = add(work)
        rep = Report()
        manifest = validate_dir(work, rep, recompute=True)
        if rep.errors:
            _print_report(rep, False); print(f"{what} not added: the file would not validate.", file=sys.stderr); return 1
        if manifest:
            (work / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", "utf-8")
            write_self_description(work, manifest)
        if is_file:
            out = Path(a.out) if a.out else src
            pack(work, out)
            print(f"added {vid} → {out}")
        else:
            shutil.copytree(work, src, dirs_exist_ok=True)
            print(f"added {vid} in {src}")
        for w in rep.warnings:
            print(f"WARN   {w}")
        return 0
    except (ValueError, ContainerError) as e:
        print(f"ERROR  {e}", file=sys.stderr); return 2
    finally:
        tmp.cleanup()


def cmd_memory_add(a):
    from .selfdesc import memory_add
    gists = _gists(a)
    if gists is None:
        return 2
    if a.age is not None and not (math.isfinite(a.age) and 0 <= a.age <= 200):
        print("ERROR  --age must be a number of years between 0 and 200", file=sys.stderr); return 2
    return _add_node(a, "Memory", lambda work: memory_add(
        work, identity=a.identity, kind=a.kind, gists=gists, label=a.label, age=a.age, date=a.date, approx=a.approx, where=a.where,
        who=a.who, tags=a.tag, personal=a.personal, origin=a.origin, disclosure=a.disclosure, fidelity=a.fidelity, salience=a.salience,
        media=[Path(x) for x in (a.media or [])], presets=a.preset, self_shown=a.self_shown, what=a.what))


def cmd_psyche_add(a):
    from .selfdesc import psyche_add
    gists = _gists(a)
    if gists is None:
        return 2
    for opt, val in (("--since-age", a.since_age), ("--until-age", a.until_age)):
        if val is not None and not (math.isfinite(val) and 0 <= val <= 200):
            print(f"ERROR  {opt} must be a number of years between 0 and 200", file=sys.stderr); return 2
    return _add_node(a, "Psyche node", lambda work: psyche_add(
        work, identity=a.identity, kind=a.kind, gists=gists, label=a.label, strength=a.strength, stability=a.stability, since_age=a.since_age,
        since_date=a.since_date, approx=a.approx, links=a.link, about=a.about, lie=a.lie, tags=a.tag, risk=a.risk, origin=a.origin,
        personal=not a.canon, disclosure=a.disclosure, presets=a.preset, who=a.who, where=a.where, what=a.what,
        aware=a.aware, valence=a.valence, until_age=a.until_age, until_date=a.until_date,
        images=[Path(x) for x in (a.image or [])], self_shown=a.self_shown, image_age=a.age))


def cmd_psyche_propose(a):
    """personality → psyche as a proposal (docs/psyche-propose.md): the bundle, a proposal from the gateway / a file /
    the rules / the zodiac table, validated against the contract, printed as a table; written only with --apply --accept."""
    from . import propose as P
    src = Path(a.src)
    if not src.exists():
        print(f"ERROR  {src}: no such file or folder", file=sys.stderr); return 2
    if a.apply and not a.accept:
        print("ERROR  --apply writes nothing without --accept <id,id> or --accept all", file=sys.stderr); return 2
    langs = [x.strip() for x in (a.lang or "").split(",") if x.strip()] or None
    with tempfile.TemporaryDirectory(prefix="cof-propose-") as td:
        d = src if src.is_dir() else unpack(src, td)
        manifest = json.loads((d / "manifest.json").read_text("utf-8"))
        bundle = P.build_bundle(d, manifest, a.preset, a.identity, langs, keep_personal=getattr(a, "keep_personal", False))
        n_personal = bundle.pop("personal_left_out", 0)
        if n_personal:
            print(f"personal memories / psyche nodes left out of the bundle: {n_personal} (--keep-personal sends them)")
        iid = bundle["character"]["id"]
        if a.bundle_out:
            Path(a.bundle_out).write_text(json.dumps({"system": P.SYSTEM_PROMPT, "prompt": P.PROMPT, "bundle": bundle}, ensure_ascii=False, indent=2) + "\n", "utf-8")
            print(f"bundle and prompt written: {a.bundle_out} (give them to any model; save its answer and come back with --from-file)")
        parts = []
        if a.from_file:
            parts.append(P.parse_answer(json.loads(Path(a.from_file).read_text("utf-8"))))
        if a.rules:
            parts.append(P.rules_proposal(d, manifest, iid, bundle["languages"]))
        if a.zodiac:
            parts.append(P.zodiac_proposal(a.zodiac, bundle["languages"]))
        if a.mbti:
            parts.append(P.mbti_proposal(a.mbti, bundle["languages"]))
        if a.enneagram:
            parts.append(P.enneagram_proposal(a.enneagram, bundle["languages"]))
        if a.big_five:
            from . import profiles as PR
            if a.big_five == "annex":                           # a bare --big-five reads the preset's psyche.json › traits annex
                sc = PR.annex_scores(d, manifest, bundle.get("preset"))
                if not sc:
                    print("ERROR  --big-five without scores reads the personality's psyche.json › traits › big5 annex, and this file has none", file=sys.stderr); return 2
                parts.append(P.big_five_proposal(sc, bundle["languages"], where="from the file's psyche.json annex, 0–1 mapped to 0–100"))
            else:
                parts.append(P.big_five_proposal(PR.parse_big_five(a.big_five), bundle["languages"]))
        if a.provider:
            if a.provider != "openai-compatible":
                print(f"ERROR  unknown provider {a.provider!r} (openai-compatible)", file=sys.stderr); return 2
            if not a.base_url or not a.model:
                print("ERROR  --provider needs --base-url and --model (the key comes from the environment: COF_AI_KEY)", file=sys.stderr); return 2
            print(f"asking {a.model} at {a.base_url}…", file=sys.stderr)
            try:
                parts.append(P.call_gateway(a.base_url, a.model, bundle, P.key_from_env()))
            except Exception as e:                              # a network or a parse failure: nothing to review
                print(f"ERROR  the gateway did not answer with a proposal: {e}", file=sys.stderr); return 1
        if not parts:
            if a.bundle_out:
                return 0
            print("ERROR  no proposal: give --from-file <proposal.json>, --rules, --zodiac <sign>, --mbti <type>, --enneagram <n>, --big-five [O=80,…], or --provider openai-compatible --base-url … --model … (or --bundle-out to take the bundle to a model yourself)", file=sys.stderr); return 2
        proposal = P.normalize(P.merge(*[P.normalize(p) for p in parts]))
        errors, notes = P.validate(proposal, bundle)
        if errors:
            for e in errors:
                print(f"ERROR  {e}")
            print(f"proposal refused: {len(errors)} contract error(s) (docs/psyche-propose.md).", file=sys.stderr)
            return 1
        print(P.table(proposal, bundle, notes, a.accept if a.apply else None))
        if a.out:
            Path(a.out).write_text(json.dumps(proposal, ensure_ascii=False, indent=2) + "\n", "utf-8")
            print(f"proposal written: {a.out}")
        if not a.apply:
            return 0
    class _A:                                                   # the shared atomic write path: a copy edited, validated, then written back
        pass
    aa = _A(); aa.src = a.src; aa.out = a.out_cof
    def add(work):
        written, wnotes = P.apply(work, proposal, a.accept, iid, bundle)
        for n in wnotes:
            print(f"NOTE   {n}")
        return ", ".join(written)
    return _add_node(aa, "Psyche nodes", add)


def cmd_psyche_text(a):
    """The inverse: nodes → the « Who she is » text (SOUL.md's section, RFC 0004 § 3 quinquies), printed or appended to
    the card's personality field (never replacing it)."""
    from .psyche import load_nodes, soul_section
    src = Path(a.src)
    if not src.exists():
        print(f"ERROR  {src}: no such file or folder", file=sys.stderr); return 2
    with tempfile.TemporaryDirectory(prefix="cof-text-") as td:
        d = src if src.is_dir() else unpack(src, td)
        manifest = json.loads((d / "manifest.json").read_text("utf-8"))
        pid = a.preset or default_preset_id(manifest)
        from .memories import load_nodes as load_memories
        text, stats = soul_section(manifest, load_nodes(d, manifest), pid, keep_personal=a.keep_personal, keep_dangerous=a.keep_dangerous, memory_nodes=load_memories(d, manifest))
    if not text:
        print("no psyche node to render for this preset", file=sys.stderr); return 1
    if a.out:
        Path(a.out).write_text(text, "utf-8"); print(f"written: {a.out} ({stats['rendered']} node(s))")
    elif not a.into_card:
        print(text, end="")
    if not a.into_card:
        return 0
    class _A:
        pass
    aa = _A(); aa.src = a.src; aa.out = a.out_cof
    def add(work):
        from .model import first, resolved
        m = json.loads((work / "manifest.json").read_text("utf-8"))
        p = first(resolved(m, pid), "personality") or {}
        if not p.get("card"):
            raise ValueError("--into-card needs a preset whose personality is a card (card.json)")
        cp = work / p["card"]; card = json.loads(cp.read_text("utf-8"))
        data = card.setdefault("data", {})
        data["personality"] = (str(data.get("personality") or "").rstrip() + "\n\n" + text.strip()).strip() + "\n"
        cp.write_text(json.dumps(card, ensure_ascii=False, indent=2) + "\n", "utf-8")
        return f"the « Who she is » text to {p['card']} › personality"
    return _add_node(aa, "Psyche text", add)


def _refresh_auto_tags(dst: Path) -> None:
    """tags.auto recomputed on the written folder: an extraction and its purges may have removed what a tag said
    (`has-memories` after the personal memories left, `has-psyche`, an age bucket of a preset not kept…)."""
    from .validate import auto_tags
    mp = dst / "manifest.json"
    m = json.loads(mp.read_text("utf-8"))
    auto = auto_tags(m)
    if (m.get("tags") or {}).get("auto") != auto:
        m.setdefault("tags", {})["auto"] = auto
        mp.write_text(json.dumps(m, ensure_ascii=False, indent=2) + "\n", "utf-8")


def cmd_extract(a):
    src = Path(a.src)
    with tempfile.TemporaryDirectory() as td:
        d = src if src.is_dir() else unpack(src, td)
        notes: list[str] = []
        if a.tag:
            extract_tag(d, Path(a.out), a.tag)
        elif getattr(a, "identity", None):
            from .ops import extract_identity
            extract_identity(d, Path(a.out), a.identity, notes)
        else:
            extract_preset(d, Path(a.out), a.preset)
        for n in notes:
            print(f"WARN   {n}")
        from .ops import strip_card_payloads_dir
        for n in strip_card_payloads_dir(Path(a.out)):
            print(f"WARN   {n}")
        if not getattr(a, "keep_personal", False):           # RFC 0002 § 5.7: personal memories never travel unasked; RFC 0004 § 3 ter: personal psyche nodes likewise
            from .ops import drop_personal_memories
            from .psyche import drop_personal_nodes
            dropped = drop_personal_memories(Path(a.out))
            if dropped:
                print(f"personal memories dropped: {', '.join(dropped)} (--keep-personal keeps them)")
            dropped = drop_personal_nodes(Path(a.out))
            if dropped:
                print(f"personal psyche nodes dropped: {', '.join(dropped)} (--keep-personal keeps them)")
        if getattr(a, "no_intimate", False):
            from .ops import strip_intimate
            gone = strip_intimate(Path(a.out))
            print(f"--all-audiences: removed {', '.join(gone) or 'nothing'}; allowSexualUsage set to false — review tags.content")
        if getattr(a, "no_risk", False):                      # RFC 0004 § 3 septies: the risk purge, separate from the all-audiences one
            from .psyche import strip_risk
            gone = strip_risk(Path(a.out))
            print(f"--no-risk: psyche nodes removed: {', '.join(gone) or 'none'} (inappropriate and dangerous, with the contradictions that lost a side); tags.content updated")
    _refresh_auto_tags(Path(a.out))
    rep = Report(); validate_dir(Path(a.out), rep, recompute=True)
    what = 'tags ' + '+'.join(a.tag) if a.tag else ('character ' + a.identity if getattr(a, "identity", None) else 'preset ' + a.preset)
    print(f"{what} extracted to: {a.out}")
    return _print_report(rep, a.json)


def cmd_migrate(a):
    m = migrate_any(Path(a.dir))
    if getattr(a, "psyche", False):                           # RFC 0004 § 3 quater: the 1.0 lists become nodes, the lists stay
        from .migrate import migrate_psyche
        r = migrate_psyche(Path(a.dir)); m = r["manifest"]
        print(f"psyche: {len(r['written'])} node(s) written" + (f" ({', '.join(r['written'])})" if r["written"] else "") + (f", {r['skipped']} already present" if r["skipped"] else ""))
        for who, n in r["untouched"].items():
            print(f"psyche of {who or 'the character'} already has nodes: {n} list entr{'y' if n == 1 else 'ies'} with no node of the same text left as they are (add them with `cof psyche add` if they belong)")
    rep = Report()
    validate_dir(Path(a.dir), rep, recompute=True)
    Path(a.dir, "manifest.json").write_text(json.dumps(m | {k: v for k, v in json.loads(Path(a.dir, "manifest.json").read_text("utf-8")).items()}, ensure_ascii=False, indent=2) + "\n", "utf-8")
    print(f"migrated to v{m.get('cof')}: {a.dir}")
    return _print_report(rep, a.json)


def _placeholder_png(image_path: Path | None) -> bytes:
    """1024² PNG: converted from the given image if Pillow is available, else a flat grey PNG."""
    try:
        from PIL import Image
        import io
        if image_path and image_path.is_file():
            im = Image.open(image_path).convert("RGB")
        else:
            im = Image.new("RGB", (1024, 1024), (64, 64, 72))
        im = im.resize((1024, 1024))
        buf = io.BytesIO()
        im.save(buf, "PNG")
        return buf.getvalue()
    except Exception:
        import zlib, struct
        from .convert import png_build
        w = h = 64
        raw = b"".join(b"\x00" + bytes([64, 64, 72]) * w for _ in range(h))
        ihdr = struct.pack(">IIBBBBB", w, h, 8, 2, 0, 0, 0)
        return png_build([(b"IHDR", ihdr), (b"IDAT", zlib.compress(raw)), (b"IEND", b"")])


def main(argv=None) -> int:
    for stream in (sys.stdout, sys.stderr):      # Windows consoles default to cp1252: never crash on « — ✔ é »
        try:
            stream.reconfigure(encoding="utf-8", errors="replace")
        except Exception:
            pass
    ap = argparse.ArgumentParser(prog="cof", description="COF — Character Open File tooling")
    ap.add_argument("--version", action="version", version=f"cof-cli {__version__}")
    sub = ap.add_subparsers(dest="cmd", required=True)

    s = sub.add_parser("validate", help="validate a .cof or a character folder"); s.add_argument("path"); s.add_argument("--json", action="store_true"); s.set_defaults(fn=cmd_validate)
    s = sub.add_parser("pack", help="folder → .cof (recomputes hashes and completeness)"); s.add_argument("dir"); s.add_argument("-o", "--out"); s.add_argument("--force", action="store_true"); s.add_argument("--json", action="store_true"); s.set_defaults(fn=cmd_pack)
    s = sub.add_parser("memory", help="memories: `memory add` appends a lived memory to a .cof or a folder (RFC 0002, the write path of COF.md)")
    ms = s.add_subparsers(dest="mcmd", required=True)
    ma = ms.add_parser("add", help="append one memory node"); ma.add_argument("src", help=".cof file or character folder")
    ma.add_argument("--identity", help="character id (default: the file's default character)"); ma.add_argument("--kind", choices=["moment", "period"], default="moment")
    ma.add_argument("--gist", action="append", required=True, metavar="LANG=TEXT", help="the memory in one paragraph; repeat per language")
    ma.add_argument("--label"); ma.add_argument("--age", type=float); ma.add_argument("--date", help="YYYY, YYYY-MM or YYYY-MM-DD"); ma.add_argument("--approx", action="store_true")
    ma.add_argument("--where"); ma.add_argument("--who", action="append", metavar="LABEL[|shown][|AGE][|real]", help="a person: label, then optional words 'shown' (appears in a media), their age, 'real' (a real person who is not a character of the file); repeat");
    ma.add_argument("--what", action="append", metavar="LABEL[|item=REF][|shown]", help="an object (1.2, RFC 0005): its name and/or item=<category>/<id> (an accessory of the character, e.g. item=appearance/x1), 'shown' if it appears in a media; repeat")
    ma.add_argument("--self-shown", action="store_true", help="the character appears in the media (requires --age: the minor rules read it)"); ma.add_argument("--tag", action="append")
    ma.add_argument("--personal", action="store_true", help="visibility: personal (one user's data) instead of canon"); ma.add_argument("--origin", choices=["lived", "authored"], default="lived")
    ma.add_argument("--disclosure", choices=["open", "guarded", "secret"], default="open"); ma.add_argument("--fidelity", choices=["vivid", "clear", "faded", "fragment"], default="clear"); ma.add_argument("--salience", type=int)
    ma.add_argument("--media", action="append", help="image / audio / video / short text file; repeat"); ma.add_argument("--preset", action="append", help="preset(s) that may recall it (default: the character's presets)")
    ma.add_argument("-o", "--out", help="output .cof (default: in place)"); ma.set_defaults(fn=cmd_memory_add)
    s = sub.add_parser("psyche", help="psyche (RFC 0004): `psyche add` appends a lived node (the write path of COF.md); `psyche propose` turns a personality into candidate nodes to review; `psyche text` renders the nodes as text")
    ps_ = s.add_subparsers(dest="pcmd", required=True)
    pa = ps_.add_parser("add", help="append one psyche node"); pa.add_argument("src", help=".cof file or character folder")
    pa.add_argument("--identity", help="character id (default: the file's default character)")
    pa.add_argument("--kind", choices=["value", "belief", "want", "need", "fear", "wound", "stance", "taste", "habit", "contradiction", "rule"], required=True)
    pa.add_argument("--gist", action="append", required=True, metavar="LANG=TEXT", help="the node in one or two sentences; repeat per language")
    pa.add_argument("--label"); pa.add_argument("--strength", type=int, help="0–100 (default 50)"); pa.add_argument("--stability", choices=["core", "settled", "shifting", "fragile"], help="default settled")
    pa.add_argument("--since-age", type=float, help="age (years) when it appeared"); pa.add_argument("--since-date", help="YYYY, YYYY-MM or YYYY-MM-DD")
    pa.add_argument("--until-age", "--until", dest="until_age", type=float, metavar="AGE", help="age (years) when the character stopped holding it (RFC 0004 § 3 nonies)"); pa.add_argument("--until-date", help="YYYY, YYYY-MM or YYYY-MM-DD")
    pa.add_argument("--approx", action="store_true", help="the ages and dates given (since, until) are approximate")
    pa.add_argument("--aware", choices=["yes", "partly", "no"], help="whether the character knows this about itself (default yes; no = acted on, never stated)")
    pa.add_argument("--valence", type=int, metavar="N", help="stance or taste only: -100 (hostile / hates) … +100 (warm / loves) — not the strength")
    pa.add_argument("--link", action="append", metavar="TYPE=REF", help="because=memories/ev3, about=psyche/bel1, supports=psyche/val1, conflicts=psyche/bel3 (memories and psyche nodes; a person goes in --who); repeat")
    pa.add_argument("--who", action="append", metavar="LABEL[|identity=ID][|real][|shown][|AGE]", help="a person the node is tied to (RFC 0005): a name and/or identity=<cast id>, 'real' for a real person who is not a character of the file, 'shown' (and their age) when an --image shows them; repeat")
    pa.add_argument("--where", action="append", metavar="LABEL[|environment=REF]", help="a place the node is tied to: a name and/or environment=<category>/<id> (an environment of the character); repeat")
    pa.add_argument("--what", action="append", metavar="LABEL[|item=REF]", help="an object the node is tied to: a name and/or item=<category>/<id> (an accessory of the character); repeat")
    pa.add_argument("--image", action="append", metavar="FILE", help="an illustration of the node (RFC 0004 § 3 decies): an image file, repeat; the first replaces the kind's icon, more than 3 make it a memory")
    pa.add_argument("--self-shown", action="store_true", help="an image shows the character (requires --age: the minor rules read it)"); pa.add_argument("--age", type=float, help="the character's age in the image (with --self-shown); it enters the preset's lowest age")
    pa.add_argument("--about", metavar="SUBJECT", help="stance only: user | identity=<id> | node=<category>/<id> | a free label")
    pa.add_argument("--lie", action="store_true", help="belief only: false_but_held (the character holds it, the author says it is false)")
    pa.add_argument("--tag", action="append"); pa.add_argument("--risk", choices=["none", "inappropriate", "dangerous"], default="none", help="declared risk (tags.content follows)")
    pa.add_argument("--origin", choices=["lived", "authored"], default="lived"); pa.add_argument("--canon", action="store_true", help="visibility: canon (default personal: one user's data, as a lived memory)")
    pa.add_argument("--personal", action="store_true", help="visibility: personal (the default; kept for symmetry with memory add)")
    pa.add_argument("--disclosure", choices=["open", "guarded", "secret"], default="open"); pa.add_argument("--preset", action="append", help="preset(s) that hold it (default: the character's presets)")
    pa.add_argument("-o", "--out", help="output .cof (default: in place)"); pa.set_defaults(fn=cmd_psyche_add)
    pp = ps_.add_parser("propose", help="personality → psyche: candidate nodes from a model, the 1.0 lists, a zodiac sign, a Myers-Briggs type, an Enneagram type or Big Five scores, reviewed in a table, written only for the ids you accept (docs/psyche-propose.md)")
    pp.add_argument("--keep-personal", action="store_true", help="also put `visibility: personal` memories and psyche nodes (a user's data) in the bundle sent to a model (left out by default)")
    pp.add_argument("src", help=".cof file or character folder"); pp.add_argument("--preset", help="the preset whose personality and language are read (default: the character's)"); pp.add_argument("--identity", help="character id in a cast (default: the file's default character)")
    pp.add_argument("--lang", help="languages a gist must come in, comma-separated (default: the preset's, then the file's)")
    pp.add_argument("--provider", choices=["openai-compatible"], help="ask a model through an OpenAI-compatible gateway (key from the environment: COF_AI_KEY, never an argument)")
    pp.add_argument("--base-url", help="the gateway's base URL (https://api.openai.com/v1, http://localhost:11434/v1…)"); pp.add_argument("--model", help="the model name")
    pp.add_argument("--from-file", help="a proposal JSON produced elsewhere (a model's answer, the builder's export, a file saved with --out)")
    pp.add_argument("--rules", action="store_true", help="the rule-based conversion of the 1.0 lists (goals, fears, values, behaviours), as a proposal")
    pp.add_argument("--zodiac", metavar="SIGN", help="a handful of value / taste / habit candidates typical of a sun sign (aries … pisces, or the French names), to review")
    pp.add_argument("--mbti", metavar="TYPE", help="a Myers-Briggs four-letter type (INFJ, ESTP…): value / taste / habit / need candidates, to review (used descriptively, no affiliation)")
    pp.add_argument("--enneagram", metavar="N", help="an Enneagram type 1–9, optionally with a wing (4w5; only the main type is used): its basic fear and desire, a value and a habit, to review")
    pp.add_argument("--big-five", nargs="?", const="annex", metavar="O=80,C=35,E=20,A=70,N=60", help="Big Five scores 0–100 (70 or more proposes the high pole, 30 or less the low pole, in between nothing); without a value, the personality's psyche.json › traits annex (0–1) is read")
    pp.add_argument("--bundle-out", help="write the bundle and the prompt to this JSON file, to take to any model by hand")
    pp.add_argument("--out", help="save the validated proposal to this JSON file (reviewable later with --from-file)")
    pp.add_argument("--apply", action="store_true", help="write the accepted candidates (requires --accept)"); pp.add_argument("--accept", metavar="ID,ID|all", help="the candidate ids to write (nothing is written otherwise)")
    pp.add_argument("--out-cof", help="output .cof when applying (default: in place)"); pp.set_defaults(fn=cmd_psyche_propose)
    pt = ps_.add_parser("text", help="psyche → text: the « Who she is » section rendered from the preset's nodes (the inverse of propose); --into-card appends it to the card's personality field")
    pt.add_argument("src"); pt.add_argument("--preset"); pt.add_argument("--keep-personal", action="store_true"); pt.add_argument("--keep-dangerous", action="store_true")
    pt.add_argument("--out", help="write the markdown here instead of printing it"); pt.add_argument("--into-card", action="store_true", help="append the text to the personality field of the preset's card (never replaces it)")
    pt.add_argument("--out-cof", help="output .cof with --into-card (default: in place)"); pt.set_defaults(fn=cmd_psyche_text)
    s = sub.add_parser("unpack", help=".cof → folder"); s.add_argument("cof"); s.add_argument("-o", "--out"); s.set_defaults(fn=cmd_unpack)
    s = sub.add_parser("info", help="summary of a .cof"); s.add_argument("cof"); s.set_defaults(fn=cmd_info)
    s = sub.add_parser("tokens", help="token estimate per block"); s.add_argument("path"); s.set_defaults(fn=cmd_tokens)
    s = sub.add_parser("embed-text", help="write a text (.md/.txt) into a PNG as iTXt 'Description' — readable by the builder (personality + appearance)"); s.add_argument("png"); s.add_argument("text"); s.add_argument("-o", "--out"); s.set_defaults(fn=cmd_embed_text)
    s = sub.add_parser("read-text", help="show the descriptive text embedded in an image (PNG/JPEG: iTXt, XMP, EXIF)"); s.add_argument("image"); s.set_defaults(fn=cmd_read_text)
    s = sub.add_parser("import", help="PNG/JSON card (CCv2/V3) → COF folder"); s.add_argument("src"); s.add_argument("-o", "--out"); s.add_argument("--age", type=int); s.add_argument("--real", action="store_true", help="character based on a real person (consent required)"); s.add_argument("--lang", default="en"); s.add_argument("--keep-png", action="store_true", help="keep the PNG as the head.front view"); s.add_argument("--json", action="store_true"); s.set_defaults(fn=cmd_import)
    s = sub.add_parser("export", help="folder/.cof → png | soul | card | agent (workspace: SOUL.md, IDENTITY.md, skills/, memories) — from the default preset or --preset"); s.add_argument("src"); s.add_argument("--format", choices=["png", "soul", "card", "agent"], required=True); s.add_argument("-o", "--out"); s.add_argument("--preset"); s.add_argument("--keep-personal", action="store_true", help="agent: also export `visibility: personal` memories and psyche nodes (dropped by default)"); s.add_argument("--keep-dangerous", action="store_true", help="agent: also render psyche nodes of risk `dangerous` (dropped by default: an agent acts — RFC 0004 § 3 septies)"); s.set_defaults(fn=cmd_export)
    s = sub.add_parser("migrate", help="folder v0.2 … v0.5 → v1.0; --psyche converts the 1.0 lists (goals, fears, values, behaviours) into psyche nodes (1.2)"); s.add_argument("dir"); s.add_argument("--psyche", action="store_true", help="write psyche nodes from psyche.json goals / fears / values and the card's cof.goals / cof.fears / cof.behavior (the lists stay); idempotent"); s.add_argument("--json", action="store_true"); s.set_defaults(fn=cmd_migrate)
    s = sub.add_parser("merge", help="merge several .cof files/folders (same name, nickname, fictional status and morphology class ⇒ same identity, otherwise multiple identities)"); s.add_argument("sources", nargs="+"); s.add_argument("-o", "--out", required=True); s.add_argument("--json", action="store_true"); s.set_defaults(fn=cmd_merge)
    s = sub.add_parser("extract", help="extract a preset, a character (--identity), or the presets carrying one or more tags (intersection), into a lighter COF folder"); s.add_argument("src"); g = s.add_mutually_exclusive_group(required=True); g.add_argument("--preset"); g.add_argument("--identity", help="one character: all its presets, elements, files and rights"); g.add_argument("--tag", action="append", help="repeatable: --tag english --tag age-12"); s.add_argument("-o", "--out", required=True); s.add_argument("--json", action="store_true"); s.add_argument("--all-audiences", "--no-intimate", dest="no_intimate", action="store_true", help="all-audiences slice: drop intimate / nude variants and the media of explicit memories (gist kept), allowSexualUsage = false"); s.add_argument("--keep-personal", action="store_true", help="keep `visibility: personal` memories and psyche nodes (a user's data; dropped by default)"); s.add_argument("--no-risk", action="store_true", help="risk purge (RFC 0004 § 3 septies): drop psyche nodes of risk `inappropriate` and `dangerous` (and the contradictions that lose a side); separate from --all-audiences"); s.set_defaults(fn=cmd_extract)

    a = ap.parse_args(argv)
    try:
        return a.fn(a)
    except (ContainerError, ValueError) as e:                    # ValueError covers JSONDecodeError
        print(f"ERROR  {e}", file=sys.stderr)
        return 1
    except zipfile.BadZipFile as e:
        print(f"ERROR  not a .cof archive: {e}", file=sys.stderr)
        return 1
    except OSError as e:
        print(f"ERROR  {e.strerror or e}: {e.filename or ''}".rstrip(": "), file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
