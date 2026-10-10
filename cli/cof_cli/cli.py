"""`cof` command line."""
from __future__ import annotations

import argparse
import json
import sys
import tempfile
from pathlib import Path

from . import __version__
from .completeness import compute as compute_completeness
from .container import ContainerError, pack, read_manifest, unpack
from .convert import card_to_cof_dir, export_soul, read_card_from_png, write_card_to_png
from .migrate import migrate_dir
from .model import asset_index, default_preset_id, resolved
from .validate import Report, validate_cof, validate_dir


def _print_report(rep: Report, as_json: bool) -> int:
    if as_json:
        print(json.dumps(rep.to_dict(), ensure_ascii=False, indent=2))
    else:
        for e in rep.errors:
            print(f"ERREUR  {e}")
        for w in rep.warnings:
            print(f"AVERT.  {w}")
        c = rep.info.get("completeness")
        if c:
            print(f"complétude : {c['score']}/100 (niveau {c['level']}) — " + ", ".join(f"{k} {v}" for k, v in c["layers"].items()))
            print("prêt pour  : " + (", ".join(c["targets_ready"]) or "—"))
        cov = rep.info.get("coverage")
        if cov:
            print(f"couverture : {', '.join(cov['elements']) or '—'} ({cov['variants']} déclinaison(s), {cov['presets']} preset(s))")
        if rep.info.get("presets") and len(rep.info["presets"]) > 1:
            print("presets    : " + ", ".join(f"{k} {v}" for k, v in rep.info["presets"].items()))
        t = rep.info.get("tokens")
        if t and "permanent" in t:
            print(f"tokens     : permanent {t['permanent']}" + (f", lore {t['lore']}" if "lore" in t else "") + f" ({t['tokenizer']})")
        print("OK" if rep.ok else f"NON CONFORME ({len(rep.errors)} erreur(s))")
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
    rep = Report()
    manifest = validate_dir(src, rep, recompute=True)
    if rep.errors and not a.force:
        _print_report(rep, a.json)
        print("Dossier non conforme : corrigez ou utilisez --force.", file=sys.stderr)
        return 1
    if manifest:
        (src / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", "utf-8")
    out = Path(a.out) if a.out else src.with_suffix(".cof")
    try:
        pack(src, out)
    except ContainerError as e:
        print(f"ERREUR  {e}", file=sys.stderr)
        return 1
    print(f"écrit : {out} ({out.stat().st_size/1e6:.2f} Mo)")
    return 0


def cmd_unpack(a):
    out = Path(a.out) if a.out else Path(a.cof).with_suffix("")
    unpack(a.cof, out)
    print(f"extrait dans : {out}")
    return 0


def cmd_info(a):
    m = read_manifest(a.cof)
    c = m.get("completeness") or compute_completeness(m)
    print(json.dumps({"name": m.get("name"), "id": m.get("id"), "cof": m.get("cof"), "age": m.get("age"),
                      "fictional": m.get("fictional"), "size_class": m.get("size_class"), "thumbnail": m.get("thumbnail"),
                      "completeness": c["file"] if isinstance(c, dict) and "file" in c else c, "coverage": m.get("coverage"),
                      "presets": {k: {"label": v.get("label"), "slots": v.get("slots"), "score": (v.get("completeness") or {}).get("score")} for k, v in (m.get("presets") or {}).items()},
                      "default_preset": m.get("default_preset"), "tags": m.get("tags"), "assets": len(m.get("assets", []))},
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
        print("source attendue : .png (carte) ou .json (carte)", file=sys.stderr)
        return 1
    dest = Path(a.out) if a.out else Path(src.stem)
    card_to_cof_dir(card, dest, png=png if a.keep_png else None, age=a.age, fictional=not a.real, language=a.lang)
    rep = Report()
    validate_dir(dest, rep, recompute=True)
    print(f"dossier COF créé : {dest}")
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
        card_path = (r.get("personality") or {}).get("card")
        if fmt in ("png", "card") and not card_path:
            print("ce preset n'a pas de déclinaison de personnalité (card.json)", file=sys.stderr)
            return 1
        if fmt == "png":
            card = json.loads((d / card_path).read_text("utf-8"))
            head = next((A[i]["path"] for i in (r.get("face") or {}).get("images", []) if i in A and A[i].get("subject") == "head" and A[i].get("angle") == "front"), None)
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
        elif fmt == "card":
            card = json.loads((d / card_path).read_text("utf-8"))
            out = out or Path(f"{manifest['name']}.card.json")
            out.write_text(json.dumps(card, ensure_ascii=False, indent=2), "utf-8")
        else:
            print(f"format non géré : {fmt}", file=sys.stderr)
            return 1
    print(f"exporté : {out}")
    return 0


def cmd_migrate(a):
    m = migrate_dir(Path(a.dir))
    rep = Report()
    validate_dir(Path(a.dir), rep, recompute=True)
    Path(a.dir, "manifest.json").write_text(json.dumps(m | {k: v for k, v in json.loads(Path(a.dir, "manifest.json").read_text("utf-8")).items()}, ensure_ascii=False, indent=2) + "\n", "utf-8")
    print(f"migré en v0.3 : {a.dir}")
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
    ap = argparse.ArgumentParser(prog="cof", description="COF — Character Open File tooling")
    ap.add_argument("--version", action="version", version=f"cof-cli {__version__}")
    sub = ap.add_subparsers(dest="cmd", required=True)

    s = sub.add_parser("validate", help="valide un .cof ou un dossier de personnage"); s.add_argument("path"); s.add_argument("--json", action="store_true"); s.set_defaults(fn=cmd_validate)
    s = sub.add_parser("pack", help="dossier → .cof (recalcule hashes et complétude)"); s.add_argument("dir"); s.add_argument("-o", "--out"); s.add_argument("--force", action="store_true"); s.add_argument("--json", action="store_true"); s.set_defaults(fn=cmd_pack)
    s = sub.add_parser("unpack", help=".cof → dossier"); s.add_argument("cof"); s.add_argument("-o", "--out"); s.set_defaults(fn=cmd_unpack)
    s = sub.add_parser("info", help="résumé d'un .cof"); s.add_argument("cof"); s.set_defaults(fn=cmd_info)
    s = sub.add_parser("tokens", help="estimation des tokens par bloc"); s.add_argument("path"); s.set_defaults(fn=cmd_tokens)
    s = sub.add_parser("import", help="carte PNG/JSON (CCv2/V3) → dossier COF"); s.add_argument("src"); s.add_argument("-o", "--out"); s.add_argument("--age", type=int); s.add_argument("--real", action="store_true", help="personnage basé sur une personne réelle (consentement requis)"); s.add_argument("--lang", default="en"); s.add_argument("--keep-png", action="store_true", help="garde le PNG comme vue head.front"); s.add_argument("--json", action="store_true"); s.set_defaults(fn=cmd_import)
    s = sub.add_parser("export", help="dossier/.cof → png | soul | card (depuis le preset par défaut ou --preset)"); s.add_argument("src"); s.add_argument("--format", choices=["png", "soul", "card"], required=True); s.add_argument("-o", "--out"); s.add_argument("--preset"); s.set_defaults(fn=cmd_export)
    s = sub.add_parser("migrate", help="dossier v0.2 → v0.3 (elements / presets)"); s.add_argument("dir"); s.add_argument("--json", action="store_true"); s.set_defaults(fn=cmd_migrate)

    a = ap.parse_args(argv)
    try:
        return a.fn(a)
    except (ContainerError, ValueError) as e:
        print(f"ERREUR  {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
