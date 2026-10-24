#!/usr/bin/env python3
"""COF memories pipeline - a memories sheet (JSON) -> one to three images per memory (Gemini API) -> `elements/memories/` in an
existing `.cof` (or COF folder) -> `cof pack` -> `cof validate` -> REVIEW.md.  RFC 0002, format 1.1.

Runs on the author's own computer; never uploads, posts or shares anything. The API key is read from GEMINI_API_KEY
and never written anywhere.

Usage:
  python memories.py sheets/clara.memories.json --prompts-only            # 1. read the prompts
  python memories.py sheets/clara.memories.json --dry-run --out out        # 2. whole chain, placeholder images, no API call
  python memories.py sheets/clara.memories.json --out out                  # 3. for real
Options: --model NAME (or COF_GEMINI_MODEL), --pause SECONDS, --size 1K|2K, --keep (keep the unpacked folder).

The sheet:
  { "source": "path/to/character.cof" | "path/to/folder",      the file or folder to extend (never modified in place)
    "identity": "id1",                                            optional: the character (default: the file's default identity)
    "language": "fr",                                             optional: primary language written on the identity
    "reference": "a-head-front",                                  optional: asset id (or path) of the likeness reference
    "presets": { "default": ["m1", "m3"], "fr-12": ["m1"] },      which presets list which memories (default: every preset lists all)
    "memories": [ { "id": "m1", "kind": "moment", "label": "…",
                    "node": { …memory.json content: gist (required), when, where, who, felt_then, felt_now, fidelity, … },
                    "images": [ { "prompt": "…", "shows_character": false, "shows_person": false, "aspect": "3:2", "style": "photo-realistic",
                                  "refs": ["path.jpg"],                 optional extra reference images (relative to the sheet)
                                  "base": "path.jpg",                   optional: an existing image to EDIT (sent first; the prompt says what changes)
                                  "keep": "path.jpg" } ],               optional: reuse this already-reviewed image, no API call
                    "age": 29 } ] }                               the character's age when shown (required if shows_character)
  (`image: {…}` is accepted as a one-element `images`.)  For the example, one image for a fleeting memory, up to three in general.

Safety rules enforced before any API call: no `explicit` memory in a seed sheet; a memory whose image shows the character
needs an age ≥ 18 (the gallery never depicts minors); `who[].real` is refused (no real person in the seed gallery).
"""
from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import os
import shutil
import subprocess
import sys
import tempfile
import time
import zipfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from gen import DEFAULT_API, DEFAULT_MODEL, IPTC_AI, gemini_client, generate, placeholder, to_jpeg  # noqa: E402

ASPECT_PX = {"3:2": (1536, 1024), "4:3": (1365, 1024), "1:1": (1024, 1024), "16:9": (1820, 1024), "2:3": (1024, 1536)}


class SheetError(ValueError):
    pass


def load_sheet(path: Path) -> dict:
    s = json.loads(path.read_text("utf-8"))
    for k in ("source", "memories"):
        if k not in s:
            raise SheetError(f"{path}: missing '{k}'")
    seen = set()
    for mem in s["memories"]:
        for k in ("id", "kind", "label", "node"):
            if k not in mem:
                raise SheetError(f"{path}: memory without '{k}'")
        if mem["id"] in seen:
            raise SheetError(f"{path}: duplicate memory id {mem['id']}")
        seen.add(mem["id"])
        if mem["kind"] not in ("moment", "period"):
            raise SheetError(f"{path}: {mem['id']}: kind must be moment or period")
        node = mem["node"]
        if not isinstance(node.get("gist"), dict) or not node["gist"]:
            raise SheetError(f"{path}: {mem['id']}: node.gist is required (a map language -> text)")
        if node.get("explicit"):
            raise SheetError(f"{path}: {mem['id']}: no explicit memory in a seed sheet")
        if any(w.get("real") for w in node.get("who") or []):
            raise SheetError(f"{path}: {mem['id']}: no real person in a seed sheet")
        imgs = mem.get("images")
        if imgs is None:
            imgs = [mem["image"]] if mem.get("image") else []
        if not isinstance(imgs, list) or len(imgs) > 3:
            raise SheetError(f"{path}: {mem['id']}: images is a list of at most 3 entries (1 for a fleeting memory, 3 in general)")
        mem["images"] = imgs
        for n, img in enumerate(imgs, 1):
            if not img.get("prompt") and not img.get("keep"):
                raise SheetError(f"{path}: {mem['id']}#{n}: image.prompt is required (unless keep)")
            if img.get("shows_character"):
                if mem.get("age") is None or mem["age"] < 18:
                    raise SheetError(f"{path}: {mem['id']}: an image showing the character needs age ≥ 18 (the gallery never depicts minors)")
            if img.get("aspect", "3:2") not in ASPECT_PX:
                raise SheetError(f"{path}: {mem['id']}#{n}: aspect must be one of {', '.join(ASPECT_PX)}")
            for k in ("base", "keep", *(img.get("refs") or [])):
                rel = img.get(k) if k in ("base", "keep") else k
                if rel and not (path.parent / rel).is_file():
                    raise SheetError(f"{path}: {mem['id']}#{n}: file not found: {rel}")
    return s


def prompt_for(mem: dict, img: dict, style: str | None) -> str:
    st = (img.get("style") or style or "photo-realistic").replace("-", " ")
    if img.get("base"):                                   # an edit: the first image is the one to change
        base = (f"Edit the first image, a photograph. {img['prompt']} Keep everything else exactly as it is: same framing, "
                f"same poses, same lighting, same background, same people. Style: {st}. "
                "No text, no watermark, no logo, no recognizable real person, celebrity, brand or franchise character.")
        return base
    base = (f"A memory, seen as a photograph the character keeps. {img['prompt']} Style: {st}. "
            "Original scene, no text, no watermark, no logo, no recognizable real person, celebrity, brand or franchise character.")
    if img.get("shows_character"):
        base += (" The person shown is the character in the first reference image: keep exactly the same face and hair, adult, fully clothed, "
                 f"aged about {mem['age']}.")
    elif img.get("shows_person"):                        # someone else (never the character, never a child)
        base += " Every person shown is clearly an adult; no child anywhere in the image."
    else:
        base += " No person's face is visible, no child anywhere in the image."
    return base


# ---------- source handling ----------

def open_source(src: Path, work: Path) -> Path:
    d = work / "src"
    if src.is_dir():
        shutil.copytree(src, d)
    else:
        with zipfile.ZipFile(src) as z:
            z.extractall(d)
    if not (d / "manifest.json").is_file():
        raise SheetError(f"{src}: no manifest.json")
    return d


def default_identity(m: dict) -> str | None:
    return m.get("default_identity") or (next(iter(m.get("identities") or {}), None))


def find_reference(m: dict, d: Path, ref: str | None, pid: str) -> bytes | None:
    """JPEG bytes of the likeness reference: an asset id, a path, or the preset's primary / first face image."""
    assets = {a["id"]: a for a in m.get("assets", [])}
    cand = None
    if ref:
        cand = assets.get(ref, {}).get("path") or ref
    else:
        p = (m.get("presets") or {}).get(pid) or {}
        aid = p.get("primary_image")
        if not aid:
            for vid in (p.get("slots") or {}).get("appearance", []):
                v = ((m["elements"].get("appearance") or {}).get("variants") or {}).get(vid) or {}
                if v.get("kind") == "face" and v.get("images"):
                    aid = v["images"][0]; break
        cand = assets.get(aid, {}).get("path") if aid else None
    if not cand or not (d / cand).is_file():
        return None
    jpg, _, _ = to_jpeg((d / cand).read_bytes(), 1024)
    return jpg


# ---------- writing ----------

def add_memories(d: Path, m: dict, s: dict, images: dict[str, list[tuple[bytes, int, int, str]]], model: str, dry: bool) -> dict:
    """`images[vid]` = [(jpeg, w, h, generator), …] in sheet order; earlier memory assets of the same node are replaced."""
    iid = s.get("identity") or default_identity(m)
    multi = bool(m.get("identities"))
    if multi and iid not in m["identities"]:
        raise SheetError(f"unknown identity {iid} (available: {', '.join(m['identities'])})")
    if s.get("language") and multi:
        m["identities"][iid]["language"] = s["language"]
    m["cof"] = "1.1"
    lic = s.get("license", "CC-BY-4.0")
    mem_el = m["elements"].setdefault("memories", {"variants": {}})
    for mem in s["memories"]:
        vid = mem["id"]
        rel_dir = f"elements/memories/{vid}"
        (d / rel_dir).mkdir(parents=True, exist_ok=True)
        node = json.loads(json.dumps(mem["node"]))
        (d / rel_dir / "memory.json").write_text(json.dumps(node, ensure_ascii=False, indent=2) + "\n", "utf-8")
        v = {"kind": mem["kind"], "label": mem["label"], "memory": f"{rel_dir}/memory.json"}
        if multi:
            v["identity"] = iid
        # earlier media of this node (a previous run, a single `<vid>.jpg`) are replaced
        m["assets"] = [a for a in m.get("assets", []) if not (a.get("id") == f"a-mem-{vid}" or a.get("id", "").startswith(f"a-mem-{vid}-"))]
        for old in (d / rel_dir).glob("*.jpg"):
            old.unlink()
        if images.get(vid):
            v["media"] = []
            for n, (data, w, h, generator) in enumerate(images[vid], 1):
                fname = f"{vid}-{n}.jpg" if len(images[vid]) > 1 else f"{vid}.jpg"
                (d / rel_dir / fname).write_bytes(data)
                aid = f"a-mem-{vid}-{n}" if len(images[vid]) > 1 else f"a-mem-{vid}"
                img = mem["images"][n - 1]
                m["assets"].append({"id": aid, "path": f"{rel_dir}/{fname}", "role": "memory-media", "mediaType": "image/jpeg",
                                    "bytes": len(data), "sha256": hashlib.sha256(data).hexdigest(), "license": lic,
                                    "width": w, "height": h, "style": img.get("style") or s.get("style") or "photo-realistic",
                                    "digitalSourceType": IPTC_AI, "generator": generator})
                v["media"].append(aid)
            if any(img.get("shows_character") for img in mem["images"]):
                v["age"] = {"value": mem["age"], "unit": "years", "basis": "canonical"}
                who = node.setdefault("who", [])
                if not any(w.get("identity") == "self" for w in who):
                    who.insert(0, {"identity": "self", "shown": True})
                else:
                    for w in who:
                        if w.get("identity") == "self":
                            w["shown"] = True
                (d / rel_dir / "memory.json").write_text(json.dumps(node, ensure_ascii=False, indent=2) + "\n", "utf-8")
        mem_el["variants"][vid] = v
    # presets: which memories each preset lists (default: every preset of this character lists all)
    all_ids = [mem["id"] for mem in s["memories"]]
    plan = s.get("presets")
    for pid, p in (m.get("presets") or {}).items():
        owner = p.get("identity") or default_identity(m)
        if multi and owner != iid:
            continue
        if plan is None:
            if p.get("extends") and (plan is None):
                continue                                   # inherited from the parent preset
            p.setdefault("slots", {})["memories"] = all_ids
        elif pid in plan:
            p.setdefault("slots", {})["memories"] = list(plan[pid])
    now = dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    m.setdefault("provenance", {})["modified"] = now
    for k in ("completeness", "coverage"):
        m.pop(k, None)
    return m


def review_file(s: dict, out: Path, cof: Path, report: str, prompts: dict) -> None:
    lines = [f"# Review - memories of {s.get('name') or cof.stem}", "", "Status: **waiting for human review** - do not publish before every box is ticked.", "",
             "- [ ] No image shows a child or a person who could look under 18 (the childhood memory shows a place or an object, never the character as a child).",
             "- [ ] Images that show the character show the same person as the file's face views, at the declared age, fully clothed.",
             "- [ ] No real person, celebrity, brand, franchise character or third-party work in any image (reverse image search).",
             "- [ ] No text, watermark or logo in the images.",
             "- [ ] Each gist matches its image; `when` / `where` / `who` are consistent with the character's story and presets.",
             "- [ ] The image API terms (paid tier) allow publishing these images under the declared licence.", "",
             f"File: `{cof.name}`", "", "## cof validate", "```", report.strip(), "```", "", "## Prompts used"]
    lines += [f"- `{k}`: {v}" for k, v in prompts.items()]
    (out / f"{cof.stem}.memories.REVIEW.md").write_text("\n".join(lines) + "\n", "utf-8")


def cof_cmd() -> list[str]:
    """The cof-cli of the interpreter running this script, if installed (never an older `cof` found on PATH)."""
    import importlib.util
    if importlib.util.find_spec("cof_cli"):
        return [sys.executable, "-c", "import sys; from cof_cli.cli import main; sys.exit(main())"]
    exe = shutil.which("cof")
    return [exe] if exe else [sys.executable, "-m", "cof_cli.cli"]


def say(msg: str) -> None:
    print(msg, flush=True)


def main(argv=None) -> int:
    for stream in (sys.stdout, sys.stderr):           # Windows consoles default to cp1252: never crash on a non-ASCII character
        try:
            stream.reconfigure(encoding="utf-8", errors="replace")
        except Exception:
            pass
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("sheet", type=Path)
    ap.add_argument("--out", type=Path, default=Path("out"))
    ap.add_argument("--model", default=DEFAULT_MODEL)
    ap.add_argument("--pause", type=float, default=4.0, help="seconds between API calls")
    ap.add_argument("--size", default="1K", help="image size requested from the API (1K, 2K; interactions API only)")
    ap.add_argument("--api", default=DEFAULT_API, choices=["generate", "interactions"], help="generate_content (default) or the Interactions API")
    ap.add_argument("--dry-run", action="store_true", help="placeholder images, no API call")
    ap.add_argument("--prompts-only", action="store_true")
    ap.add_argument("--keep", action="store_true", help="keep the unpacked folder next to the .cof")
    a = ap.parse_args(argv)
    try:
        s = load_sheet(a.sheet)
    except SheetError as ex:
        print(f"SHEET ERROR {ex}"); return 1
    style = s.get("style")
    prompts = {f"{mem['id']}#{n}": prompt_for(mem, img, style) for mem in s["memories"] for n, img in enumerate(mem["images"], 1) if not img.get("keep")}
    sheet_dir = a.sheet.resolve().parent
    if a.prompts_only:
        for k, p in prompts.items():
            print(f"{k}: {p}\n")
        return 0
    src = (a.sheet.parent / s["source"]).resolve() if not Path(s["source"]).is_absolute() else Path(s["source"])
    if not src.exists():
        print(f"source not found: {src}"); return 1
    client = None if a.dry_run else gemini_client()
    a.out.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory() as td:
        work = Path(td)
        d = open_source(src, work)
        m = json.loads((d / "manifest.json").read_text("utf-8"))
        pid = m.get("default_preset") or next(iter(m.get("presets") or {}), "default")
        ref = find_reference(m, d, s.get("reference"), pid)
        if any(img.get("shows_character") and not img.get("base") and not img.get("keep") for mem in s["memories"] for img in mem["images"]) and ref is None:
            print("no likeness reference found (set 'reference' to an asset id of a face view)"); return 1
        images: dict[str, list] = {}
        keep_dir = a.out / "images"; keep_dir.mkdir(exist_ok=True)
        say(f"== memories of {src.name} ({len(prompts)} images to generate, {'dry run' if a.dry_run else a.model})")
        for mem in s["memories"]:
            for n, img in enumerate(mem["images"], 1):
                key = f"{mem['id']}#{n}"
                aspect = img.get("aspect", "3:2")
                if img.get("keep"):                                   # an image already generated and reviewed: reused as is
                    data = (sheet_dir / img["keep"]).read_bytes()
                    jpg, w, h = to_jpeg(data, None)
                    images.setdefault(mem["id"], []).append((jpg, w, h, f"kept from {img['keep']}"))
                    say(f"   keep {key} {w}x{h} ({img['keep']})"); continue
                refs = []
                if img.get("base"):
                    refs.append(to_jpeg((sheet_dir / img["base"]).read_bytes(), 1536)[0])
                elif img.get("shows_character") and ref:
                    refs.append(ref)
                for r in img.get("refs") or []:
                    refs.append(to_jpeg((sheet_dir / r).read_bytes(), 1024)[0])
                try:
                    raw = (placeholder(mem["label"], size=ASPECT_PX[aspect]) if a.dry_run
                           else generate(client, a.model, prompts[key], refs, a.pause, aspect=aspect, size=a.size, log=say, api=a.api))
                except RuntimeError as ex:
                    say(f"FAIL {key}: {ex}"); return 1
                jpg, w, h = to_jpeg(raw, 1024 if aspect in ("1:1", "2:3") else 1536)
                images.setdefault(mem["id"], []).append((jpg, w, h, "placeholder (dry run)" if a.dry_run else f"Google Gemini ({a.model})"))
                if not a.dry_run:
                    (keep_dir / f"{mem['id']}-{n}.jpg").write_bytes(jpg)       # each image is saved as soon as it exists
                say(f"   ok {key} {w}x{h}")
                if not a.dry_run:
                    time.sleep(a.pause)
        try:
            m = add_memories(d, m, s, images, a.model, a.dry_run)
        except SheetError as ex:
            print(f"SHEET ERROR {ex}"); return 1
        (d / "manifest.json").write_text(json.dumps(m, ensure_ascii=False, indent=2) + "\n", "utf-8")
        cof = a.out / (src.stem.replace(".cof", "") + "-memories.cof")
        r1 = subprocess.run(cof_cmd() + ["pack", str(d), "-o", str(cof), "--force"], capture_output=True, text=True)
        r2 = subprocess.run(cof_cmd() + ["validate", str(cof)], capture_output=True, text=True) if r1.returncode == 0 else r1
        report = r2.stdout + r2.stderr
        review_file(s, a.out, cof, report, prompts)
        if a.keep:
            keep = a.out / cof.stem
            if keep.exists():
                shutil.rmtree(keep)
            shutil.copytree(d, keep)
        ok = r2.returncode == 0 and report.strip().endswith("OK")
        say(f"   {'VALID' if ok else 'INVALID'} -> {cof}  (review: {cof.stem}.memories.REVIEW.md)")
        if not ok:
            say(report)
        sys.stdout.flush(); sys.stderr.flush()
        os._exit(0 if ok else 1)                       # never wait for an abandoned API call thread


if __name__ == "__main__":
    sys.exit(main())
