"""`cof` command line."""
from __future__ import annotations

import argparse
import json
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
    card_to_cof_dir(card, dest, png=png if a.keep_png else None, age=a.age, fictional=not a.real, language=a.lang)
    rep = Report()
    validate_dir(dest, rep, recompute=True)
    print(f"COF folder created: {dest}")
    return _print_report(rep, a.json)


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
        if fmt == "png":
            card = json.loads((d / card_path).read_text("utf-8"))
            head = next((A[i]["path"] for i in (first(r, "appearance", "face") or {}).get("images", []) if i in A and A[i].get("subject") == "head" and A[i].get("angle") == "front"), None)
            if head and head.lower().endswith(".png"):
                png = (d / head).read_bytes()
            else:
                png = _placeholder_png(d / head if head else None)
            out = out or Path(f"{manifest['name']}.png")
            out.write_bytes(write_card_to_png(png, card))
        elif fmt == "soul":
            soul, identity = export_soul(d, pid)
            out = out or Path(".")
            out.mkdir(parents=True, exist_ok=True)
            (out / "SOUL.md").write_text(soul, "utf-8")
            (out / "IDENTITY.md").write_text(identity, "utf-8")
        elif fmt == "agent":
            from .convert import export_agent
            out = out or Path(f"{manifest['name']}-agent")
            done = export_agent(d, out, pid, keep_personal=getattr(a, "keep_personal", False))
            print(f"skills: {', '.join(done['skills']) or '—'} · memory files: {len(done['memories'])} · memories (nodes): {done.get('memory_nodes', 0)} · documents: {len(done['documents'])}")
            if done.get("personal_dropped"):
                print(f"personal memories not exported: {done['personal_dropped']} (--keep-personal exports them)")
        elif fmt == "card":
            card = json.loads((d / card_path).read_text("utf-8"))
            out = out or Path(f"{manifest['name']}.card.json")
            out.write_text(json.dumps(card, ensure_ascii=False, indent=2), "utf-8")
        else:
            print(f"unsupported format: {fmt}", file=sys.stderr)
            return 1
    print(f"exported: {out}")
    return 0


def cmd_merge(a):
    dirs = []
    for src in a.sources:
        p = Path(src)
        if p.is_file():
            td = Path(tempfile.mkdtemp()); unpack(p, td); dirs.append(td)
        else:
            dirs.append(p)
    merge_dirs(dirs, Path(a.out))
    rep = Report(); validate_dir(Path(a.out), rep, recompute=True)
    Path(a.out, "manifest.json").write_text(json.dumps(json.loads(Path(a.out, "manifest.json").read_text("utf-8")) | {}, ensure_ascii=False, indent=2) + "\n", "utf-8")
    print(f"merged into: {a.out}")
    return _print_report(rep, a.json)


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
        if not getattr(a, "keep_personal", False):           # RFC 0002 § 5.7: personal memories never travel unasked
            from .ops import drop_personal_memories
            dropped = drop_personal_memories(Path(a.out))
            if dropped:
                print(f"personal memories dropped: {', '.join(dropped)} (--keep-personal keeps them)")
        if getattr(a, "no_intimate", False):
            from .ops import strip_intimate
            gone = strip_intimate(Path(a.out))
            print(f"--all-audiences: removed {', '.join(gone) or 'nothing'}; allowSexualUsage set to false — review tags.content")
    rep = Report(); validate_dir(Path(a.out), rep, recompute=True)
    what = 'tags ' + '+'.join(a.tag) if a.tag else ('character ' + a.identity if getattr(a, "identity", None) else 'preset ' + a.preset)
    print(f"{what} extracted to: {a.out}")
    return _print_report(rep, a.json)


def cmd_migrate(a):
    m = migrate_any(Path(a.dir))
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
    s = sub.add_parser("unpack", help=".cof → folder"); s.add_argument("cof"); s.add_argument("-o", "--out"); s.set_defaults(fn=cmd_unpack)
    s = sub.add_parser("info", help="summary of a .cof"); s.add_argument("cof"); s.set_defaults(fn=cmd_info)
    s = sub.add_parser("tokens", help="token estimate per block"); s.add_argument("path"); s.set_defaults(fn=cmd_tokens)
    s = sub.add_parser("embed-text", help="write a text (.md/.txt) into a PNG as iTXt 'Description' — readable by the builder (personality + appearance)"); s.add_argument("png"); s.add_argument("text"); s.add_argument("-o", "--out"); s.set_defaults(fn=cmd_embed_text)
    s = sub.add_parser("read-text", help="show the descriptive text embedded in an image (PNG/JPEG: iTXt, XMP, EXIF)"); s.add_argument("image"); s.set_defaults(fn=cmd_read_text)
    s = sub.add_parser("import", help="PNG/JSON card (CCv2/V3) → COF folder"); s.add_argument("src"); s.add_argument("-o", "--out"); s.add_argument("--age", type=int); s.add_argument("--real", action="store_true", help="character based on a real person (consent required)"); s.add_argument("--lang", default="en"); s.add_argument("--keep-png", action="store_true", help="keep the PNG as the head.front view"); s.add_argument("--json", action="store_true"); s.set_defaults(fn=cmd_import)
    s = sub.add_parser("export", help="folder/.cof → png | soul | card | agent (workspace: SOUL.md, IDENTITY.md, skills/, memories) — from the default preset or --preset"); s.add_argument("src"); s.add_argument("--format", choices=["png", "soul", "card", "agent"], required=True); s.add_argument("-o", "--out"); s.add_argument("--preset"); s.add_argument("--keep-personal", action="store_true", help="agent: also export `visibility: personal` memories (dropped by default)"); s.set_defaults(fn=cmd_export)
    s = sub.add_parser("migrate", help="folder v0.2 … v0.5 → v1.0"); s.add_argument("dir"); s.add_argument("--json", action="store_true"); s.set_defaults(fn=cmd_migrate)
    s = sub.add_parser("merge", help="merge several .cof files/folders (same name, nickname, fictional status and morphology class ⇒ same identity, otherwise multiple identities)"); s.add_argument("sources", nargs="+"); s.add_argument("-o", "--out", required=True); s.add_argument("--json", action="store_true"); s.set_defaults(fn=cmd_merge)
    s = sub.add_parser("extract", help="extract a preset, a character (--identity), or the presets carrying one or more tags (intersection), into a lighter COF folder"); s.add_argument("src"); g = s.add_mutually_exclusive_group(required=True); g.add_argument("--preset"); g.add_argument("--identity", help="one character: all its presets, elements, files and rights"); g.add_argument("--tag", action="append", help="repeatable: --tag english --tag age-12"); s.add_argument("-o", "--out", required=True); s.add_argument("--json", action="store_true"); s.add_argument("--all-audiences", "--no-intimate", dest="no_intimate", action="store_true", help="all-audiences slice: drop intimate / nude variants and the media of explicit memories (gist kept), allowSexualUsage = false"); s.add_argument("--keep-personal", action="store_true", help="keep `visibility: personal` memories (a user's data; dropped by default)"); s.set_defaults(fn=cmd_extract)

    a = ap.parse_args(argv)
    try:
        return a.fn(a)
    except (ContainerError, ValueError) as e:
        print(f"ERROR  {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
