#!/usr/bin/env python3
"""COF seed pipeline — character sheet (JSON) → reference images (Gemini API) → COF folder → `cof pack` → `cof validate`.

Runs on the author's own computer. Every character it produces waits for a human review (REVIEW.md) before anything
is published; this script never uploads, posts or shares anything.

Safety rules of the seed gallery (enforced here, not only in the prompts):
  - fictional, original characters only: no real person, no franchise, no "in the style of" a living artist;
  - adults (age >= 18) or non-human characters only; no intimate content (tags.content = ["none"]);
  - the API key is read from the GEMINI_API_KEY environment variable and never written anywhere.

Usage:
  python seed.py sheets/*.json --out out/            # generate, pack, validate
  python seed.py sheets/aiko.json --dry-run          # no API call: placeholder images (tests the whole chain)
  python seed.py sheets/aiko.json --prompts-only     # print the prompts and stop
Options: --model NAME (or COF_GEMINI_MODEL), --views head,body (default), --pause SECONDS between calls.
"""
from __future__ import annotations

import argparse
import base64
import datetime as dt
import io
import json
import os
import random
import re
import shutil
import subprocess
import sys
import time
from pathlib import Path

DEFAULT_MODEL = os.environ.get("COF_GEMINI_MODEL", "gemini-2.5-flash-image")   # check the current image model name in Google's docs
HUMAN_FORM = {"human", "humanoid", "anthropomorphic-animal"}
CLASSES = HUMAN_FORM | {"quadruped", "avian", "aquatic", "mechanical", "amorphous", "other"}
STYLES = {"photo-realistic", "cinematic", "3d-render", "anime", "manga", "comic", "cartoon", "pixel-art", "lego", "clay",
          "watercolor", "oil-painting", "ink-sketch", "lineart", "low-poly", "voxel", "chibi"}
IPTC_AI = "http://cv.iptc.org/newscodes/digitalsourcetype/trainedAlgorithmicMedia"

# (variant, file name, subject, angle, framing, prompt fragment)
VIEWS = {
    "head": [("f1", "head.front.jpg", "head", "front", "head", "head-and-shoulders portrait, facing the camera, neutral expression, eyes open"),
             ("f1", "head.left34.jpg", "head", "left34", "head", "head-and-shoulders portrait, three-quarter view turned to the left"),
             ("f1", "head.right.jpg", "head", "right", "head", "head-and-shoulders portrait, strict side profile facing right")],
    "body": [("b1", "body.front.jpg", "body", "front", "full", "full-body view from head to feet, standing, facing the camera, arms relaxed"),
             ("b1", "body.back.jpg", "body", "back", "full", "full-body view from head to feet, standing, seen from the back"),
             ("b1", "body.left34.jpg", "body", "left34", "full", "full-body view from head to feet, standing, three-quarter view turned to the left")],
}


class SheetError(ValueError):
    pass


# ---------- character sheet ----------

def load_sheet(path: Path) -> dict:
    s = json.loads(path.read_text("utf-8"))
    for k in ("name", "summary", "morphology", "style", "appearance", "card"):
        if not s.get(k):
            raise SheetError(f"{path.name}: missing '{k}'")
    if s.get("real_person") or s.get("fictional") is False:
        raise SheetError(f"{path.name}: the seed gallery holds fictional characters only")
    if s.get("franchise") or s.get("based_on"):
        raise SheetError(f"{path.name}: the seed gallery holds original characters only (no franchise, no 'based on')")
    cls = (s["morphology"] or {}).get("class")
    if cls not in CLASSES:
        raise SheetError(f"{path.name}: morphology.class must be one of {sorted(CLASSES)}")
    age = s.get("age")
    if cls in HUMAN_FORM:
        if not isinstance(age, (int, float)) or age < 18:
            raise SheetError(f"{path.name}: a human-shaped seed character needs an age of 18 or more")
    elif age is not None and (not isinstance(age, (int, float)) or age < 0):
        raise SheetError(f"{path.name}: invalid age")
    if s["style"] not in STYLES:
        raise SheetError(f"{path.name}: style must be one of {sorted(STYLES)}")
    for k in ("content",):
        if s.get(k) not in (None, ["none"]):
            raise SheetError(f"{path.name}: the seed gallery holds no flagged content")
    return s


def prompt_for(s: dict, view: str) -> str:
    cls = s["morphology"]["class"]
    who = s["appearance"].strip().rstrip(".")
    age = f", {int(s['age'])} years old" if cls in HUMAN_FORM else ""
    return (f"Character reference image. {who}{age}. {view}. Style: {s['style'].replace('-', ' ')}. "
            "Plain light-grey studio background, even soft lighting, no text, no logo, no watermark, no other person. "
            "Fully clothed, everyday outfit as described. An original character that does not resemble any real person, "
            "celebrity or existing franchise character. Keep exactly the same face, hair, body and outfit as the reference image if one is given.")


# ---------- image generation ----------

def gemini_client():
    key = os.environ.get("GEMINI_API_KEY")
    if not key:
        raise SystemExit("GEMINI_API_KEY is not set (put it in an environment variable, never in a file or a sheet)")
    try:
        from google import genai            # pip install google-genai
    except ImportError:
        raise SystemExit("missing package: pip install google-genai pillow")
    return genai.Client(api_key=key)


def generate(client, model: str, prompt: str, refs: list[bytes], pause: float, tries: int = 3) -> bytes:
    from google.genai import types
    parts = [types.Part.from_bytes(data=r, mime_type="image/jpeg") for r in refs] + [prompt]
    last = None
    for i in range(tries):
        try:
            resp = client.models.generate_content(model=model, contents=parts,
                                                  config=types.GenerateContentConfig(response_modalities=["IMAGE"]))
            for cand in resp.candidates or []:
                for part in (cand.content.parts if cand.content else []) or []:
                    data = getattr(part, "inline_data", None)
                    if data and data.data:
                        return data.data if isinstance(data.data, bytes) else base64.b64decode(data.data)
            last = "no image in the answer (refused or filtered?)"
        except Exception as ex:                         # quota, network, safety block…
            last = f"{ex.__class__.__name__}: {ex}"
        time.sleep(pause * (i + 1))
    raise RuntimeError(f"image generation failed after {tries} tries — {last}")


def placeholder(text: str, tall: bool) -> bytes:
    from PIL import Image, ImageDraw
    w, h = (512, 1024) if tall else (512, 512)
    rnd = random.Random(text)
    im = Image.new("RGB", (w, h), tuple(rnd.randint(20, 235) for _ in range(3)))
    dr = ImageDraw.Draw(im)
    for y in range(0, h, 24):
        dr.line([(0, y), (w, y + rnd.randint(-20, 20))], fill=tuple(rnd.randint(90, 200) for _ in range(3)))
    dr.text((16, h // 2), "DRY RUN — " + text[:40], fill=(255, 255, 255))
    buf = io.BytesIO(); im.save(buf, "JPEG", quality=85); return buf.getvalue()


def to_jpeg(data: bytes) -> tuple[bytes, int, int]:
    from PIL import Image
    with Image.open(io.BytesIO(data)) as im:
        im = im.convert("RGB")
        buf = io.BytesIO(); im.save(buf, "JPEG", quality=90)
        return buf.getvalue(), im.width, im.height


# ---------- COF folder ----------

def ulid() -> str:
    alphabet = "0123456789ABCDEFGHJKMNPQRSTVWXYZ"
    t = int(time.time() * 1000)
    head = "".join(alphabet[(t >> (5 * i)) & 31] for i in reversed(range(10)))
    return head + "".join(random.choice(alphabet) for _ in range(16))


def slug(name: str) -> str:
    s = re.sub(r"[^a-z0-9]+", "-", name.lower().encode("ascii", "ignore").decode()).strip("-")
    return s or "character"


def build_folder(s: dict, images: dict, out: Path, model: str, dry: bool) -> Path:
    d = out / slug(s["name"])
    if d.exists():
        shutil.rmtree(d)
    (d / "elements/personality/p1").mkdir(parents=True)
    now = dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    lang = s.get("language", "en")
    cls = s["morphology"]["class"]
    lic = s.get("license", "CC-BY-4.0")
    c = s["card"]
    card = {"spec": "chara_card_v3", "spec_version": "3.0", "data": {
        "name": s["name"], "nickname": s.get("nickname", ""), "description": c.get("description", s["summary"]),
        "personality": c.get("personality", ""), "scenario": c.get("scenario", ""), "first_mes": c.get("first_mes", ""),
        "mes_example": c.get("mes_example", ""), "creator_notes": "COF seed gallery — original fictional character. Images generated with "
        + ("placeholders (dry run)" if dry else f"Google Gemini ({model})") + "; reviewed by a human before publication.",
        "system_prompt": "", "post_history_instructions": "", "alternate_greetings": c.get("alternate_greetings", []),
        "tags": s.get("tags", []), "creator": s.get("creator", "Yann Souetre"), "character_version": "1.0.0",
        "extensions": {}, "source": [], "group_only_greetings": [], "creation_date": int(time.time()), "modification_date": int(time.time())}}
    (d / "elements/personality/p1/card.json").write_text(json.dumps(card, ensure_ascii=False, indent=2) + "\n", "utf-8")
    assets, variants = [], {}
    age = {"value": s["age"], "unit": "years", "basis": "canonical"} if s.get("age") is not None else None
    for (vid, fname, subject, angle, framing, _), (data, w, h) in images.items():
        rel = f"elements/appearance/{vid}/{fname}"
        (d / rel).parent.mkdir(parents=True, exist_ok=True)
        (d / rel).write_bytes(data)
        aid = f"a-{vid}-{fname.rsplit('.', 1)[0].replace('.', '-')}"
        assets.append({"id": aid, "path": rel, "role": "view", "mediaType": "image/jpeg", "license": lic,
                       "subject": subject, "angle": angle, "framing": framing, "width": w, "height": h, "style": s["style"],
                       "digitalSourceType": IPTC_AI, "generator": "placeholder (dry run)" if dry else f"Google Gemini ({model})"})
        v = variants.setdefault(vid, {"kind": "face" if vid == "f1" else "body", "label": "Face" if vid == "f1" else "Body",
                                      "style": s["style"], "images": []})
        v["images"].append(aid)
        if age:
            v["age"] = age
    slots = {"personality": ["p1"], "appearance": sorted(variants)}
    m = {"cof": "1.0", "id": ulid(), "name": s["name"], "languages": [lang], "summary": s["summary"], "fictional": True,
         "morphology": {k: v for k, v in s["morphology"].items() if v}, "default_identity": slug(s["name"]),
         "tags": {"manual": s.get("tags", []), "content": ["none"], "ip": {"original": True, "franchise": None, "based_on": None}},
         "elements": {"personality": {"variants": {"p1": {"kind": "card", "label": s["name"], "language": lang, "card": "elements/personality/p1/card.json"}}},
                      "appearance": {"variants": variants}},
         "presets": {"default": {"label": s.get("preset_label", "Default"), "style": s["style"], "slots": slots,
                                 **({"primary_image": next(a["id"] for a in assets if a["subject"] == "body" and a["angle"] == "front")}
                                    if any(a["subject"] == "body" and a["angle"] == "front" for a in assets) else {})}},
         "default_preset": "default",
         "container": {"executableContent": "none"},
         "rights": {"permissions": {"avatarPermission": "everyone", "commercialUsage": "personalNonProfit", "modification": "allowModification",
                                    "allowRedistribution": True, "creditNotation": "required", "allowExcessivelyViolentUsage": False,
                                    "allowSexualUsage": False, "allowPoliticalOrReligiousUsage": False, "allowAntisocialOrHateUsage": False,
                                    "allowVoiceCloning": False, "allowTraining": "none", "allowImpersonationOfRealPerson": False,
                                    "aiDisclosure": True},
                    "consent": None},
         "provenance": {"created": now, "modified": now, "generator": "cof-seed/1.0", "source": [], "c2pa": None, "signatures": []},
         "assets": assets}
    if "species" in s["morphology"] and not s["morphology"]["species"]:
        m["morphology"].pop("species")
    m.pop("default_identity")                         # single character: no identities block needed
    (d / "manifest.json").write_text(json.dumps(m, ensure_ascii=False, indent=2) + "\n", "utf-8")
    return d


def review_file(s: dict, d: Path, cof: Path, report: str, prompts: dict) -> None:
    lines = [f"# Review — {s['name']}", "", "Status: **waiting for human review** — do not publish before every box is ticked.", "",
             "- [ ] Every image shows the same character (face, hair, body, outfit).",
             "- [ ] The character looks like the declared age" + (f" ({s['age']})" if s.get("age") is not None else "") + " and is clearly an adult (or non-human).",
             "- [ ] No resemblance to a real person, a celebrity or a franchise character (reverse image search on the front views).",
             "- [ ] Fully clothed, nothing suggestive, no text or watermark in the images.",
             "- [ ] The card text matches the images and contains no real person or third party.",
             "- [ ] The image API terms allow publishing these images under the declared licence.", "",
             f"File: `{cof.name}`", "", "## cof validate", "```", report.strip(), "```", "", "## Prompts used"]
    lines += [f"- `{k}`: {v}" for k, v in prompts.items()]
    (d.parent / f"{d.name}.REVIEW.md").write_text("\n".join(lines) + "\n", "utf-8")


def cof_cmd() -> list[str]:
    exe = shutil.which("cof")
    return [exe] if exe else [sys.executable, "-c", "import sys; from cof_cli.cli import main; sys.exit(main())"]


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("sheets", nargs="+", type=Path)
    ap.add_argument("--out", type=Path, default=Path("out"))
    ap.add_argument("--model", default=DEFAULT_MODEL)
    ap.add_argument("--views", default="head,body", help="comma list among: head, body")
    ap.add_argument("--pause", type=float, default=4.0, help="seconds between API calls")
    ap.add_argument("--dry-run", action="store_true", help="placeholder images, no API call")
    ap.add_argument("--prompts-only", action="store_true")
    a = ap.parse_args(argv)
    views = [v for k in a.views.split(",") for v in VIEWS[k.strip()]]
    client = None if (a.dry_run or a.prompts_only) else gemini_client()
    a.out.mkdir(parents=True, exist_ok=True)
    failures = 0
    for path in a.sheets:
        try:
            s = load_sheet(path)
        except SheetError as ex:
            print(f"SKIP {ex}"); failures += 1; continue
        prompts = {f"{v[0]}/{v[1]}": prompt_for(s, v[5]) for v in views}
        if a.prompts_only:
            print(f"== {s['name']}"); [print(f"{k}: {p}") for k, p in prompts.items()]; continue
        print(f"== {s['name']} ({len(views)} images, {'dry run' if a.dry_run else a.model})")
        images, ref = {}, []
        try:
            for v in views:
                p = prompts[f"{v[0]}/{v[1]}"]
                raw = placeholder(f"{s['name']} {v[1]}", v[4] == "full") if a.dry_run else generate(client, a.model, p, ref[:1], a.pause)
                jpg, w, h = to_jpeg(raw)
                images[v] = (jpg, w, h)
                if not ref:
                    ref.append(jpg)                   # the first view anchors the identity of every following one
                print(f"   ok {v[0]}/{v[1]} {w}x{h}")
                if not a.dry_run:
                    time.sleep(a.pause)
        except RuntimeError as ex:
            print(f"FAIL {s['name']}: {ex}"); failures += 1; continue
        d = build_folder(s, images, a.out, a.model, a.dry_run)
        cof = a.out / f"{d.name}.cof"
        r1 = subprocess.run(cof_cmd() + ["pack", str(d), "-o", str(cof)], capture_output=True, text=True)
        r2 = subprocess.run(cof_cmd() + ["validate", str(cof)], capture_output=True, text=True) if r1.returncode == 0 else r1
        report = (r2.stdout + r2.stderr)
        review_file(s, d, cof, report, prompts)
        ok = r2.returncode == 0 and report.strip().endswith("OK")
        print(f"   {'VALID' if ok else 'INVALID'} → {cof}  (review: {d.name}.REVIEW.md)")
        failures += 0 if ok else 1
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
