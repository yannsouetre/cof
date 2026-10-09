"""COF-Vector v0.2 — line/edge representations of a view (the ControlNet family), model-free.

A view (photo) → three edge maps, each stored as a compact 1-bit/8-bit PNG and, optionally, vectorised to SVG:
  canny     : hard geometric edges (OpenCV Canny, auto thresholds)          → ControlNet canny
  lineart   : "lineart_standard" (Gaussian difference, white bg/black line) → ControlNet lineart
  softedge  : XDoG soft edges with stroke-width variation                   → stand-in for HED/PiDiNet
Usage: python edges.py view.jpg out_dir/ [--size 1024] [--svg]
"""
from __future__ import annotations

import io
import json
import sys
from pathlib import Path

import cv2
import numpy as np
from PIL import Image


def canny(gray: np.ndarray, sigma: float = 0.33) -> np.ndarray:
    v = np.median(gray)
    lo, hi = int(max(0, (1 - sigma) * v)), int(min(255, (1 + sigma) * v))
    e = cv2.Canny(cv2.GaussianBlur(gray, (3, 3), 0), lo, hi)
    return 255 - e  # white background, black lines


def lineart_standard(gray: np.ndarray, sigma: float = 6.0, intensity_threshold: int = 8) -> np.ndarray:
    """Port of controlnet_aux 'lineart_standard': difference between the image and its Gaussian blur."""
    x = gray.astype(np.float32)
    g = cv2.GaussianBlur(x, (0, 0), sigma)
    intensity = np.clip(g - x, 0, 255)
    intensity /= max(16, float(np.max(intensity)))
    intensity = np.clip(intensity * 255, 0, 255)
    intensity[intensity < intensity_threshold] = 0
    return (255 - intensity).astype(np.uint8)


def xdog(gray: np.ndarray, sigma: float = 1.0, k: float = 1.6, p: float = 25.0, eps: float = 0.985, phi: float = 60.0) -> np.ndarray:
    """eXtended Difference of Gaussians (Winnemöller 2012): dark variable-width strokes on white."""
    x = gray.astype(np.float32) / 255.0
    g1 = cv2.GaussianBlur(x, (0, 0), sigma)
    g2 = cv2.GaussianBlur(x, (0, 0), sigma * k)
    d = (1 + p) * g1 - p * g2
    out = np.where(d >= eps, 1.0, 1.0 + np.tanh(phi * (d - eps)))
    return (np.clip(out, 0, 1) * 255).astype(np.uint8)


def softedge(gray: np.ndarray) -> np.ndarray:
    """HED/PiDiNet stand-in without a neural model: smoothed gradient magnitude with soft falloff."""
    x = cv2.GaussianBlur(gray, (0, 0), 1.2).astype(np.float32)
    gx = cv2.Sobel(x, cv2.CV_32F, 1, 0, ksize=3); gy = cv2.Sobel(x, cv2.CV_32F, 0, 1, ksize=3)
    mag = np.sqrt(gx * gx + gy * gy)
    mag = mag / max(1e-6, np.percentile(mag, 99.5))
    mag = np.clip(mag, 0, 1) ** 0.6
    mag = cv2.GaussianBlur(mag, (0, 0), 1.5)
    return (255 - np.clip(mag, 0, 1) * 255).astype(np.uint8)


def to_1bit_png(img: np.ndarray) -> bytes:
    pil = Image.fromarray(img).convert("1")   # 1 bit/pixel, PNG deflate → very compact
    buf = io.BytesIO(); pil.save(buf, "PNG", optimize=True)
    return buf.getvalue()


def to_4bit_png(img: np.ndarray) -> bytes:
    """16 grey levels, 4 bits/pixel — enough for soft edges, ~4× smaller than 8-bit."""
    q = (img.astype(np.uint16) * 15 // 255).astype(np.uint8)
    pil = Image.fromarray(q, "L").convert("P")
    pil.putpalette(sum(([v, v, v] for v in [int(i * 255 / 15) for i in range(16)]), []) + [0, 0, 0] * 240)
    buf = io.BytesIO(); pil.save(buf, "PNG", optimize=True, bits=4)
    return buf.getvalue()


def vectorize(img: np.ndarray, turdsize: int = 4, alphamax: float = 1.0) -> str:
    """Black-line raster → SVG paths (potrace). Returns SVG text."""
    import potrace
    bm = potrace.Bitmap(img < 128)               # True = black
    path = bm.trace(turdsize=turdsize, alphamax=alphamax, opticurve=1, opttolerance=0.3)
    h, w = img.shape
    parts = []
    for curve in path:
        P = lambda pt: (float(pt.x), float(pt.y))
        d = "M %.1f %.1f " % P(curve.start_point)
        for seg in curve:
            if seg.is_corner:
                d += "L %.1f %.1f L %.1f %.1f " % (*P(seg.c), *P(seg.end_point))
            else:
                d += "C %.1f %.1f %.1f %.1f %.1f %.1f " % (*P(seg.c1), *P(seg.c2), *P(seg.end_point))
        parts.append(d + "Z")
    return (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {w} {h}" width="{w}" height="{h}">'
            f'<rect width="{w}" height="{h}" fill="white"/><path d="{" ".join(parts)}" fill="black" fill-rule="evenodd"/></svg>')


def run(src: Path, out: Path, size: int = 1024, want_svg: bool = True) -> dict:
    out.mkdir(parents=True, exist_ok=True)
    img = Image.open(src).convert("RGB")
    if max(img.size) != size:
        img = img.resize((size, int(size * img.height / img.width))) if img.width >= img.height else img.resize((int(size * img.width / img.height), size))
    gray = cv2.cvtColor(np.array(img), cv2.COLOR_RGB2GRAY)
    stem = src.stem
    la = lineart_standard(gray)
    la_bin = np.where(la < 200, 0, 255).astype(np.uint8)          # lineart stored as 1-bit lines
    maps = {"canny": canny(gray), "lineart": la_bin, "softedge": softedge(gray)}
    report = {}
    for name, m in maps.items():
        if name == "softedge" and size > 512:          # soft maps carry tone, not geometry: half resolution is enough
            m = cv2.resize(m, (m.shape[1] // 2, m.shape[0] // 2), interpolation=cv2.INTER_AREA)
        data = to_1bit_png(m) if name in ("canny", "lineart") else to_4bit_png(m)
        p = out / f"{stem}.{name}.png"
        p.write_bytes(data)
        report[name] = {"png": p.name, "bytes": len(data), "width": int(m.shape[1]), "height": int(m.shape[0]), "bits": 1 if name in ("canny", "lineart") else 4}
        if want_svg and name in ("canny", "lineart"):
            svg = vectorize(m)
            sp = out / f"{stem}.{name}.svg"
            sp.write_text(svg, "utf-8")
            report[name]["svg"] = sp.name
            report[name]["svg_bytes"] = len(svg.encode())
    return report


if __name__ == "__main__":
    a = sys.argv
    size = int(a[a.index("--size") + 1]) if "--size" in a else 1024
    print(json.dumps(run(Path(a[1]), Path(a[2]), size, "--svg" in a or True), indent=2))
