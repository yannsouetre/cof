"""COF-Vector — face extractor (v0.1, proof of concept).

photo → MediaPipe Face Mesh (478 pts) → ordered contours → cubic Béziers in a normalised frame
(origin = mid-pupils, unit = inter-pupillary distance) → measures → procedural surface colours → face.vec.json + SVG.

Usage: python face_vec.py head.front.jpg out_dir/
Requires the legacy mediapipe wheel (bundled models), numpy, opencv, pillow.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import cv2
import numpy as np
from PIL import Image

import mediapipe as mp

FM = mp.solutions.face_mesh
C = mp.solutions.face_mesh_connections

# Monk Skin Tone scale (10 orbs, CC BY 4.0) — representative sRGB values
MONK = ["#f6ede4", "#f3e7db", "#f7ead0", "#eadaba", "#d7bd96", "#a07e56", "#825c43", "#604134", "#3a312a", "#292420"]

LEFT_IRIS, RIGHT_IRIS = range(468, 473), range(473, 478)   # 468/473 = iris centres


# ---------- contour ordering ----------

def chain(edges) -> list[list[int]]:
    """Turn an edge set into ordered polylines/loops (one per connected chain)."""
    adj: dict[int, list[int]] = {}
    for a, b in edges:
        adj.setdefault(a, []).append(b)
        adj.setdefault(b, []).append(a)
    seen, paths = set(), []
    # start from endpoints (degree 1) first, then any remaining (loops)
    starts = [n for n, nb in adj.items() if len(nb) == 1] + list(adj)
    for s in starts:
        if s in seen:
            continue
        path, cur, prev = [s], s, None
        seen.add(s)
        while True:
            nxt = [n for n in adj[cur] if n != prev and n not in seen]
            if not nxt:
                # close loop if possible
                if len(path) > 2 and s in adj[cur]:
                    path.append(s)
                break
            prev, cur = cur, nxt[0]
            seen.add(cur)
            path.append(cur)
        if len(path) > 2:
            paths.append(path)
    return paths


def catmull_to_bezier(pts: np.ndarray, closed: bool, step: int = 1) -> list[list[float]]:
    """Ordered points → cubic Bézier segments [x0,y0,c1x,c1y,c2x,c2y,x1,y1] (Catmull-Rom, tension 0.5)."""
    P = pts[::step] if step > 1 else pts
    if closed and np.allclose(P[0], P[-1]):
        P = P[:-1]
    n = len(P)
    segs = []
    rng = range(n) if closed else range(n - 1)
    for i in rng:
        p0 = P[(i - 1) % n] if closed else P[max(i - 1, 0)]
        p1, p2 = P[i], P[(i + 1) % n]
        p3 = P[(i + 2) % n] if closed else P[min(i + 2, n - 1)]
        c1 = p1 + (p2 - p0) / 6
        c2 = p2 - (p3 - p1) / 6
        segs.append([round(float(v), 3) for v in (*p1, *c1, *c2, *p2)])
    return segs


# ---------- extraction ----------

def landmarks(rgb: np.ndarray):
    with FM.FaceMesh(static_image_mode=True, max_num_faces=1, refine_landmarks=True, min_detection_confidence=0.4) as fm:
        r = fm.process(rgb)
    if not r.multi_face_landmarks:
        return None
    h, w = rgb.shape[:2]
    lm = r.multi_face_landmarks[0].landmark
    return np.array([[p.x * w, p.y * h, p.z * w] for p in lm])


def sample_hex(rgb: np.ndarray, x: float, y: float, r: int = 6) -> str:
    h, w = rgb.shape[:2]
    x0, x1 = max(0, int(x - r)), min(w, int(x + r)); y0, y1 = max(0, int(y - r)), min(h, int(y + r))
    patch = rgb[y0:y1, x0:x1].reshape(-1, 3)
    if len(patch) == 0:
        return "#000000"
    med = np.median(patch, axis=0).astype(int)
    return "#%02x%02x%02x" % tuple(int(v) for v in med)


def nearest_monk(hexcol: str) -> int:
    c = np.array([int(hexcol[i:i + 2], 16) for i in (1, 3, 5)], float)
    lab = cv2.cvtColor(np.uint8([[c]]), cv2.COLOR_RGB2LAB)[0, 0].astype(float)
    best, bd = 1, 1e9
    for i, m in enumerate(MONK, 1):
        mc = np.array([int(m[j:j + 2], 16) for j in (1, 3, 5)], float)
        ml = cv2.cvtColor(np.uint8([[mc]]), cv2.COLOR_RGB2LAB)[0, 0].astype(float)
        d = np.linalg.norm(lab - ml)
        if d < bd:
            best, bd = i, d
    return best


def extract(img_path: Path, lod: str = "standard") -> dict | None:
    img = Image.open(img_path).convert("RGB")
    rgb = np.array(img)
    L = landmarks(rgb)
    if L is None:
        return None
    pl, pr = L[468, :2], L[473, :2]            # iris centres (subject's left eye is on screen-right)
    ipd = float(np.linalg.norm(pl - pr))
    origin = (pl + pr) / 2
    roll = float(np.degrees(np.arctan2(pr[1] - pl[1], pr[0] - pl[0])))
    # normalise: translate, rotate (level the eyes), scale by IPD, flip y (up = +)
    th = np.radians(-roll)
    R = np.array([[np.cos(th), -np.sin(th)], [np.sin(th), np.cos(th)]])
    N = ((L[:, :2] - origin) @ R.T) / ipd
    N[:, 1] *= -1
    N = N * np.array([-1, 1]) if False else N   # screen-right = subject's left; keep screen coords (x → right)

    def contour(name, edges, closed, step=1):
        out = {}
        for k, path in enumerate(chain(edges)):
            pts = N[path]
            is_loop = closed and len(path) > 3 and path[0] == path[-1]
            key = name if k == 0 else f"{name}.{k + 1}"
            out[key] = {"closed": is_loop, "pts": catmull_to_bezier(pts, is_loop, step)}
        return out

    step = {"coarse": 3, "standard": 2, "fine": 1}[lod]
    contours = {}
    contours.update(contour("F.outline", C.FACEMESH_FACE_OVAL, True, step))
    lips = contour("F.lip", C.FACEMESH_LIPS, True, step)
    # name the lip loops by size: larger = outer
    if len(lips) >= 2:
        keys = sorted(lips, key=lambda k: -len(lips[k]["pts"]))
        contours["F.lip.outer"], contours["F.lip.inner"] = lips[keys[0]], lips[keys[1]]
    else:
        contours.update(lips)
    contours.update(contour("F.eye.R", C.FACEMESH_RIGHT_EYE, True, 1))     # subject's right eye (screen-left)
    contours.update(contour("F.eye.L", C.FACEMESH_LEFT_EYE, True, 1))
    contours.update(contour("F.brow.R", C.FACEMESH_RIGHT_EYEBROW, True, 1))
    contours.update(contour("F.brow.L", C.FACEMESH_LEFT_EYEBROW, True, 1))
    contours.update(contour("F.nose", C.FACEMESH_NOSE, False, step))
    for nm, idx in (("F.iris.R", 473), ("F.iris.L", 468)):
        ring = N[list(range(idx + 1, idx + 5))]
        r = float(np.mean(np.linalg.norm(ring - N[idx], axis=1)))
        contours[nm] = {"circle": [round(float(N[idx][0]), 3), round(float(N[idx][1]), 3), round(r, 3)]}

    # measures (IPD units)
    def d(a, b):
        return float(np.linalg.norm(N[a] - N[b]))
    oval = N[[i for e in C.FACEMESH_FACE_OVAL for i in e]]
    measures = {
        "face_width": round(float(oval[:, 0].max() - oval[:, 0].min()), 3),
        "face_height_mesh": round(d(10, 152), 3),                 # forehead-top mesh point to chin (hairline not in mesh)
        "eye_width": round((d(33, 133) + d(362, 263)) / 2, 3),
        "eye_height": round((d(159, 145) + d(386, 374)) / 2, 3),
        "inner_canthal": round(d(133, 362), 3),
        "canthal_tilt_deg": round(float(np.degrees(np.arctan2(N[33][1] - N[133][1], N[133][0] - N[33][0]))), 1),
        "nose_length": round(d(168, 2), 3),
        "nose_width": round(d(129, 358), 3),
        "mouth_width": round(d(61, 291), 3),
        "lip_upper_h": round(d(0, 13), 3),
        "lip_lower_h": round(d(14, 17), 3),
        "chin_height": round(d(17, 152), 3),
        "philtrum": round(d(2, 0), 3),
        "jaw_width": round(d(172, 397), 3),
        "forehead_mesh_h": round(d(10, 9), 3),
    }
    # surface colours (sampled on the original image)
    pix = lambda i: (L[i][0], L[i][1])
    skin = sample_hex(rgb, *pix(50), 10) if True else None
    skin2 = sample_hex(rgb, *pix(280), 10)
    forehead = sample_hex(rgb, *pix(151), 10)
    lips_hex = sample_hex(rgb, *pix(15), 4)
    iris_hex = sample_hex(rgb, *pix(468), 3)
    brow_hex = sample_hex(rgb, *pix(105), 3)
    hair_pt = (L[10][0], L[10][1] - 0.45 * ipd)
    hair_hex = sample_hex(rgb, *hair_pt, 8)
    def lab_dist(h1, h2):
        a = np.uint8([[[int(h1[i:i + 2], 16) for i in (1, 3, 5)]]]); b = np.uint8([[[int(h2[i:i + 2], 16) for i in (1, 3, 5)]]])
        return float(np.linalg.norm(cv2.cvtColor(a, cv2.COLOR_RGB2LAB)[0, 0].astype(float) - cv2.cvtColor(b, cv2.COLOR_RGB2LAB)[0, 0].astype(float)))
    bald = lab_dist(hair_hex, "#ffffff") < 25 or lab_dist(hair_hex, forehead) < 18
    surface = {
        "skin": {"hex": skin, "hex_alt": [skin2, forehead], "monk": nearest_monk(skin)},
        "eyes": {"iris_hex": iris_hex},
        "brows": {"hex": brow_hex},
        "lips": {"hex": lips_hex},
        "hair": {"hex": None if bald else hair_hex, "present_above_forehead": not bald},
    }
    yaw = float(np.degrees(np.arctan2(N[1][0] - (N[234][0] + N[454][0]) / 2, 1.0)))  # crude: nose tip offset vs cheek centre
    return {
        "cofvec": "0.1", "kind": "face", "lod": lod,
        "frame": {"unit": "ipd", "origin": "mid-pupils", "ipd_px": round(ipd, 1), "roll_deg_removed": round(roll, 2), "yaw_hint_deg": round(yaw * 30, 1)},
        "applies_to": ["humanoid"],
        "contours": contours,
        "landmarks": {k: [round(float(N[i][0]), 3), round(float(N[i][1]), 3)] for k, i in
                      {"pupil.R": 473, "pupil.L": 468, "nose.tip": 1, "nose.bridge": 168, "mouth.center": 13, "chin": 152, "forehead.mesh_top": 10}.items()},
        "measures": measures,
        "surface": surface,
        "provenance": {"extracted_from": img_path.name, "method": "mediapipe-face-mesh-478 + catmull-rom→bezier", "manual_edits": 0},
    }


# ---------- rendering ----------

def to_svg(vec: dict, flat: bool = False, size: int = 1024, span_ipd: float = 5.0) -> str:
    s = size / span_ipd
    cx, cy = size / 2, size * 0.42

    def T(x, y):
        return (cx + x * s, cy - y * s)

    def path_d(c):
        d = ""
        for seg in c["pts"]:
            x0, y0, c1x, c1y, c2x, c2y, x1, y1 = seg
            if not d:
                d += "M %.1f %.1f " % T(x0, y0)
            d += "C %.1f %.1f %.1f %.1f %.1f %.1f " % (*T(c1x, c1y), *T(c2x, c2y), *T(x1, y1))
        return d + ("Z" if c.get("closed") else "")

    out = [f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {size} {size}" width="{size}" height="{size}">',
           f'<rect width="{size}" height="{size}" fill="white"/>']
    surf = vec.get("surface", {})
    for name, c in vec["contours"].items():
        if "circle" in c:
            x, y, r = c["circle"]
            px, py = T(x, y)
            fill = surf.get("eyes", {}).get("iris_hex", "#333") if flat else "none"
            out.append(f'<circle cx="{px:.1f}" cy="{py:.1f}" r="{r * s:.1f}" fill="{fill}" stroke="#111" stroke-width="2"/>')
            continue
        fill = "none"
        if flat:
            if name == "F.outline":
                fill = surf.get("skin", {}).get("hex", "#ddd")
            elif name == "F.lip.outer":
                fill = surf.get("lips", {}).get("hex", "#b56")
            elif name.startswith("F.brow"):
                fill = surf.get("brows", {}).get("hex", "#321")
            elif name.startswith("F.eye"):
                fill = "#f4f2ee"
        out.append(f'<path d="{path_d(c)}" fill="{fill}" stroke="#111" stroke-width="{3 if name == "F.outline" else 2}" stroke-linejoin="round"/>')
    out.append("</svg>")
    return "\n".join(out)


def describe(vec: dict) -> str:
    m, su = vec["measures"], vec["surface"]
    # thresholds are rough priors in IPD units for adult human faces; they produce a readable gloss, not a diagnosis
    def grade(v, lo, hi, words):
        return words[0] if v < lo else words[2] if v > hi else words[1]
    parts = [
        grade(m["face_width"] / max(m["face_height_mesh"], 1e-6), 0.78, 0.9, ("long", "oval", "round")) + " face",
        grade(m["eye_width"], 0.42, 0.5, ("small", "medium", "large")) + " eyes, " + grade(m["inner_canthal"], 0.55, 0.68, ("close-set", "average-set", "wide-set")),
        ("upturned" if m["canthal_tilt_deg"] > 4 else "downturned" if m["canthal_tilt_deg"] < -4 else "level") + " eye tilt",
        grade(m["nose_width"], 0.52, 0.62, ("narrow", "medium", "wide")) + " nose, " + grade(m["nose_length"], 0.8, 0.95, ("short", "medium", "long")),
        grade(m["mouth_width"], 0.78, 0.92, ("narrow", "medium", "wide")) + " mouth",
        ("thin upper lip" if m["lip_upper_h"] < 0.08 else "full upper lip" if m["lip_upper_h"] > 0.13 else "medium upper lip"),
        ("full lower lip" if m["lip_lower_h"] > 0.17 else "thin lower lip" if m["lip_lower_h"] < 0.1 else "medium lower lip"),
        grade(m["chin_height"], 0.45, 0.6, ("short", "medium", "long")) + " chin",
        f"skin {su['skin']['hex']} (Monk {su['skin']['monk']}), iris {su['eyes']['iris_hex']}",
        (f"hair {su['hair']['hex']}" if su["hair"]["hex"] else "no hair above the forehead"),
    ]
    return "; ".join(parts) + "."


def run(img_path: Path, out: Path, lod: str = "standard") -> dict | None:
    vec = extract(img_path, lod)
    out.mkdir(parents=True, exist_ok=True)
    if vec is None:
        (out / "face.vec.error.txt").write_text("no face mesh detected", "utf-8")
        return None
    vec["renderings"] = {"lineart_svg": "face.vec.F.svg", "flat_svg": "face.vec.flat.svg", "sentence": describe(vec)}
    (out / "face.vec.json").write_text(json.dumps(vec, ensure_ascii=False, indent=1), "utf-8")
    (out / "face.vec.F.svg").write_text(to_svg(vec), "utf-8")
    (out / "face.vec.flat.svg").write_text(to_svg(vec, flat=True), "utf-8")
    # overlay for visual check
    img = Image.open(img_path).convert("RGB")
    rgb = np.array(img)
    L = landmarks(rgb)
    ov = rgb.copy()
    for edges in (C.FACEMESH_FACE_OVAL, C.FACEMESH_LIPS, C.FACEMESH_LEFT_EYE, C.FACEMESH_RIGHT_EYE, C.FACEMESH_LEFT_EYEBROW, C.FACEMESH_RIGHT_EYEBROW, C.FACEMESH_NOSE):
        for a, b in edges:
            cv2.line(ov, (int(L[a][0]), int(L[a][1])), (int(L[b][0]), int(L[b][1])), (255, 40, 40), 2)
    Image.fromarray(ov).save(out / "face.vec.overlay.jpg", quality=85)
    return vec


if __name__ == "__main__":
    v = run(Path(sys.argv[1]), Path(sys.argv[2]), sys.argv[3] if len(sys.argv) > 3 else "standard")
    print(json.dumps({"ok": v is not None, "bytes_json": len(json.dumps(v)) if v else 0,
                      "sentence": v["renderings"]["sentence"] if v else None}, ensure_ascii=False, indent=2))
