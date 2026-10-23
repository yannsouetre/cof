"""Shared image generation for the seed pipelines (gallery characters, memories).

- the API key is read from GEMINI_API_KEY and never written anywhere;
- the model name is a parameter (--model, or COF_GEMINI_MODEL): image model names change often, check Google's docs;
- `generate()` uses the Interactions API of the google-genai SDK (Nano Banana 2.x / Pro) and falls back to the older
  `models.generate_content` call for SDKs or models that do not expose it;
- `placeholder()` draws a dry-run image so the whole chain can be tested without any API call.
"""
from __future__ import annotations

import base64
import io
import os
import random
import time

DEFAULT_MODEL = os.environ.get("COF_GEMINI_MODEL", "gemini-nano-banana-2.1")   # check the current image model name in Google's docs
IPTC_AI = "http://cv.iptc.org/newscodes/digitalsourcetype/trainedAlgorithmicMedia"


def gemini_client():
    key = os.environ.get("GEMINI_API_KEY")
    if not key:
        raise SystemExit("GEMINI_API_KEY is not set (put it in an environment variable, never in a file or a sheet)")
    try:
        from google import genai            # pip install -U google-genai
    except ImportError:
        raise SystemExit("missing package: pip install -U google-genai pillow")
    return genai.Client(api_key=key)


def _b64(data) -> bytes:
    return data if isinstance(data, bytes) else base64.b64decode(data)


def _via_interactions(client, model: str, prompt: str, refs: list[bytes], aspect: str | None, size: str | None):
    """google-genai ≥ Interactions API: input = text + image blocks; response_format = aspect ratio / size."""
    blocks = [{"type": "image", "data": base64.b64encode(r).decode("ascii"), "mime_type": "image/jpeg"} for r in refs]
    blocks.append({"type": "text", "text": prompt})
    kwargs = {}
    fmt = {k: v for k, v in (("aspect_ratio", aspect), ("image_size", size)) if v}
    if fmt:
        kwargs["response_format"] = fmt
    inter = client.interactions.create(model=model, input=blocks, **kwargs)
    img = getattr(inter, "output_image", None)
    if img is not None and getattr(img, "data", None):
        return _b64(img.data)
    for step in getattr(inter, "steps", None) or []:
        if getattr(step, "type", "") == "model_output":
            for cb in getattr(step, "content", None) or []:
                if getattr(cb, "type", "") == "image" and getattr(cb, "data", None):
                    return _b64(cb.data)
    return None


def _via_generate_content(client, model: str, prompt: str, refs: list[bytes]):
    """Older call (google-genai before the Interactions API, or models that only answer there)."""
    from google.genai import types
    parts = [types.Part.from_bytes(data=r, mime_type="image/jpeg") for r in refs] + [prompt]
    resp = client.models.generate_content(model=model, contents=parts,
                                          config=types.GenerateContentConfig(response_modalities=["IMAGE"]))
    for cand in resp.candidates or []:
        for part in (cand.content.parts if cand.content else []) or []:
            data = getattr(part, "inline_data", None)
            if data and data.data:
                return _b64(data.data)
    return None


def generate(client, model: str, prompt: str, refs: list[bytes], pause: float = 2.0, tries: int = 3,
             aspect: str | None = None, size: str | None = "1K") -> bytes:
    """One image. `refs` are JPEG bytes sent before the prompt (likeness references). Raises after `tries` failures."""
    last = None
    for i in range(tries):
        try:
            out = None
            if hasattr(client, "interactions"):
                try:
                    out = _via_interactions(client, model, prompt, refs, aspect, size)
                except (AttributeError, TypeError) as ex:     # SDK without the Interactions API, or an older signature
                    last = f"interactions API unavailable ({ex.__class__.__name__}); falling back"
                    out = None
            if out is None:
                out = _via_generate_content(client, model, prompt + (f" Aspect ratio {aspect}." if aspect else ""), refs)
            if out:
                return out
            last = "no image in the answer (refused or filtered?)"
        except Exception as ex:                         # quota, network, safety block…
            last = f"{ex.__class__.__name__}: {ex}"
        time.sleep(pause * (i + 1))
    raise RuntimeError(f"image generation failed after {tries} tries — {last}")


def placeholder(text: str, tall: bool = False, size: tuple[int, int] | None = None) -> bytes:
    from PIL import Image, ImageDraw
    w, h = size or ((512, 1024) if tall else (512, 512))
    rnd = random.Random(text)
    im = Image.new("RGB", (w, h), tuple(rnd.randint(20, 235) for _ in range(3)))
    dr = ImageDraw.Draw(im)
    for y in range(0, h, 24):
        dr.line([(0, y), (w, y + rnd.randint(-20, 20))], fill=tuple(rnd.randint(90, 200) for _ in range(3)))
    dr.text((16, h // 2), "DRY RUN — " + text[:40], fill=(255, 255, 255))
    buf = io.BytesIO(); im.save(buf, "JPEG", quality=85); return buf.getvalue()


def to_jpeg(data: bytes, max_side: int | None = None) -> tuple[bytes, int, int]:
    from PIL import Image
    with Image.open(io.BytesIO(data)) as im:
        im = im.convert("RGB")
        if max_side and max(im.size) > max_side:
            im.thumbnail((max_side, max_side))
        buf = io.BytesIO(); im.save(buf, "JPEG", quality=90)
        return buf.getvalue(), im.width, im.height
