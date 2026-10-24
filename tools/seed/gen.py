"""Shared image generation for the seed pipelines (gallery characters, memories).

- the API key is read from GEMINI_API_KEY and never written anywhere;
- the model name is a parameter (--model, or COF_GEMINI_MODEL): image model names change often, check Google's docs;
- `generate()` uses the Interactions API of the google-genai SDK (Nano Banana 2.x / Pro) and falls back to the older
  `models.generate_content` call for SDKs or models that do not expose it;
- `placeholder()` draws a dry-run image so the whole chain can be tested without any API call.
"""
from __future__ import annotations

import base64
import concurrent.futures
import io
import os
import random
import time

DEFAULT_MODEL = os.environ.get("COF_GEMINI_MODEL", "gemini-2.5-flash-image")   # the proven generate_content image model; newer names via --model
DEFAULT_API = os.environ.get("COF_GEMINI_API", "generate")                        # generate (models.generate_content) | interactions
CALL_TIMEOUT_S = 240                                                               # hard watchdog per API call: a stuck call never blocks the run
IPTC_AI = "http://cv.iptc.org/newscodes/digitalsourcetype/trainedAlgorithmicMedia"


def gemini_client():
    key = os.environ.get("GEMINI_API_KEY")
    if not key:
        raise SystemExit("GEMINI_API_KEY is not set (put it in an environment variable, never in a file or a sheet)")
    try:
        from google import genai            # pip install -U google-genai
    except ImportError:
        raise SystemExit("missing package: pip install -U google-genai pillow")
    # a hard HTTP timeout: a stuck connection must fail and retry, never hang the whole run
    return genai.Client(api_key=key, http_options={"timeout": 180_000})


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


def _via_generate_content(client, model: str, prompt: str, refs: list[bytes], aspect: str | None = None):
    """models.generate_content with IMAGE output (the long-standing image path); aspect ratio through image_config when the SDK has it."""
    from google.genai import types
    parts = [types.Part.from_bytes(data=r, mime_type="image/jpeg") for r in refs] + [prompt]
    cfg = None
    if aspect:
        try:
            cfg = types.GenerateContentConfig(response_modalities=["IMAGE"], image_config=types.ImageConfig(aspect_ratio=aspect))
        except Exception:
            cfg = None
    if cfg is None:
        cfg = types.GenerateContentConfig(response_modalities=["IMAGE"])
    resp = client.models.generate_content(model=model, contents=parts, config=cfg)
    texts = []
    for cand in resp.candidates or []:
        for part in (cand.content.parts if cand.content else []) or []:
            data = getattr(part, "inline_data", None)
            if data and data.data:
                return _b64(data.data)
            if getattr(part, "text", None):
                texts.append(part.text.strip())
        fr = getattr(cand, "finish_reason", None)
        if fr:
            texts.append(f"finish_reason={fr}")
    pf = getattr(resp, "prompt_feedback", None)
    if pf and getattr(pf, "block_reason", None):
        texts.append(f"block_reason={pf.block_reason}")
    raise NoImage(" | ".join(t[:200] for t in texts) or "empty answer")


class NoImage(Exception):
    """The model answered without an image: the text or the finish reason it gave, for the log."""


_pool = concurrent.futures.ThreadPoolExecutor(max_workers=2)


def _call(fn, *args):
    """Run an SDK call under a hard timeout; a call that never returns is abandoned (its thread is left behind)."""
    fut = _pool.submit(fn, *args)
    return fut.result(timeout=CALL_TIMEOUT_S)


def generate(client, model: str, prompt: str, refs: list[bytes], pause: float = 2.0, tries: int = 3,
             aspect: str | None = None, size: str | None = "1K", log=None, api: str | None = None) -> bytes:
    """One image. `refs` are JPEG bytes sent before the prompt (likeness references). Raises after `tries` failures.
    `log(msg)` receives one line per attempt, so a stalled run can be diagnosed from the log.
    `api`: "generate" (models.generate_content, default) or "interactions" (the Interactions API)."""
    last = None
    say = log or (lambda m: None)
    api = api or DEFAULT_API
    for i in range(tries):
        say(f"      attempt {i + 1}/{tries} ({model}, {api}, {len(refs)} reference(s), {aspect or 'default'} {size or ''})")
        try:
            if api == "interactions" and hasattr(client, "interactions"):
                out = _call(_via_interactions, client, model, prompt, refs, aspect, size)
            else:
                out = _call(_via_generate_content, client, model, prompt, refs, aspect)
            if out:
                say(f"      ok ({len(out)} bytes)")
                return out
            last = "no image in the answer (refused or filtered?)"
        except NoImage as ex:
            last = f"no image — the model said: {ex}"
        except concurrent.futures.TimeoutError:
            last = f"no answer after {CALL_TIMEOUT_S} s (call abandoned)"
        except Exception as ex:                         # quota, network, safety block…
            last = f"{ex.__class__.__name__}: {str(ex)[:300]}"
        say(f"      failed: {last}")
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
