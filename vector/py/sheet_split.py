"""Character-sheet splitter — detects panels in a multi-view sheet, strips titles, crops to content,
classifies each panel (subject: body/head; angle: front/left/right/back) and writes canonical COF views.

Usage:  python sheet_split.py sheet.jpg out_dir/ [--name lea]
Output: out_dir/views/<subject>.<angle>.jpg + out_dir/sheet.regions.json (frames over the original sheet)

Heuristics only (no network): white background assumed, vertical separators optional.
Requires: numpy, pillow, opencv, mediapipe (legacy solutions: face_detection, face_mesh, pose).
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import cv2
import numpy as np
from PIL import Image

try:
    import mediapipe as mp
    _FD = mp.solutions.face_detection
    _FM = mp.solutions.face_mesh
    _POSE = mp.solutions.pose
except Exception:  # pragma: no cover
    mp = None

WHITE = 235  # background threshold (0-255 gray)


# ---------- 1. panel detection ----------

def find_panels(gray: np.ndarray) -> list[tuple[int, int]]:
    """Return list of (x0, x1) panel spans. Uses dark vertical separator lines, else whitespace gaps."""
    h, w = gray.shape
    dark_frac = (gray < 160).mean(axis=0)           # per column
    sep = np.where(dark_frac > 0.9)[0]              # near-full-height lines
    cuts = []
    if len(sep):
        groups = np.split(sep, np.where(np.diff(sep) > 3)[0] + 1)
        # a separator is THIN (≤ 8 px) — a dark garment column is wide
        cuts = [int(g.mean()) for g in groups if len(g) <= 8 and 0.02 * w < g.mean() < 0.98 * w]
    if not cuts:
        # whitespace gaps: columns with almost no non-white pixels (ignore top title band)
        body = gray[int(0.12 * h):, :]
        content = (body < WHITE).mean(axis=0) > 0.005
        gaps = np.where(~content)[0]
        groups = np.split(gaps, np.where(np.diff(gaps) > 1)[0] + 1)
        for g in groups:
            if len(g) > 0.01 * w and 0.05 * w < g.mean() < 0.95 * w:
                cuts.append(int(g.mean()))
    bounds = [0] + sorted(cuts) + [w]
    panels = [(bounds[i] + 10, bounds[i + 1] - 10) for i in range(len(bounds) - 1)]
    return [p for p in panels if p[1] - p[0] > 0.05 * w]


def strip_title(gray_panel: np.ndarray) -> int:
    """Return y where the content starts (below a text title band), or 0."""
    h, w = gray_panel.shape
    core = gray_panel[:, int(0.05 * w): int(0.95 * w)]          # ignore edge remnants
    rows = (core < 160).mean(axis=1)
    top = rows[: int(0.15 * h)]
    inked = np.where(top > 0.002)[0]
    if len(inked) == 0:
        return 0
    # title = first ink cluster; find the first fully blank row after it
    end = inked[0]
    for y in range(inked[0], int(0.15 * h)):
        if rows[y] > 0.002:
            end = y
        elif y - end > 6:
            break
    # title must be a short band (< 6 % of height) followed by blank rows; otherwise it is the figure itself
    if end - inked[0] > 0.06 * h:
        return 0
    return min(int(end + 8), int(0.15 * h))


def content_bbox(gray: np.ndarray, y0: int) -> tuple[int, int, int, int] | None:
    m = gray[y0:, :] < WHITE
    m = cv2.morphologyEx(m.astype(np.uint8), cv2.MORPH_OPEN, np.ones((3, 3), np.uint8)).astype(bool)  # drop 1-2 px remnants
    ys, xs = np.where(m)
    if len(xs) == 0:
        return None
    return int(xs.min()), int(y0 + ys.min()), int(xs.max()), int(y0 + ys.max())


# ---------- 2. classification ----------

def detect_face(rgb: np.ndarray):
    if mp is None:
        return None
    with _FD.FaceDetection(model_selection=1, min_detection_confidence=0.4) as fd:
        r = fd.process(rgb)
    if not r.detections:
        return None
    d = max(r.detections, key=lambda d: d.location_data.relative_bounding_box.height)
    bb = d.location_data.relative_bounding_box
    kp = d.location_data.relative_keypoints  # 0 right eye, 1 left eye, 2 nose tip, 3 mouth, 4 right ear, 5 left ear
    return {"x": bb.xmin, "y": bb.ymin, "w": bb.width, "h": bb.height, "score": d.score[0],
            "kp": [(k.x, k.y) for k in kp]}


def yaw_from_keypoints(kp) -> float:
    """Rough yaw in degrees from face-detector keypoints. 0 = frontal; + = subject's LEFT side visible
    (nose points screen-right); − = right side visible."""
    re_, le, nose, mouth, rear, lear = kp
    eye_w = abs(le[0] - re_[0]) + 1e-6
    ear_w = abs(lear[0] - rear[0]) + 1e-6
    ears_cx = (lear[0] + rear[0]) / 2
    off = (nose[0] - ears_cx) / max(ear_w, eye_w)
    yaw = float(np.clip(off * 120, -90, 90))
    if eye_w / ear_w < 0.35 or ear_w < 0.02:  # eyes/ears collapsed → near-profile
        yaw = 85.0 if nose[0] > ears_cx else -85.0
    return yaw


def run_pose(rgb: np.ndarray):
    if mp is None:
        return None
    with _POSE.Pose(static_image_mode=True, model_complexity=1, min_detection_confidence=0.4) as pose:
        r = pose.process(rgb)
    return r.pose_landmarks.landmark if r.pose_landmarks else None


def pose_yaw(lm) -> float | None:
    nose, le, re_ = lm[0], lm[7], lm[8]
    if nose.visibility < 0.5:
        return None
    ears_cx = (le.x + re_.x) / 2
    ear_gap = abs(le.x - re_.x)
    sh_gap = abs(lm[11].x - lm[12].x) + 1e-6
    if ear_gap / sh_gap > 0.3 and abs(nose.x - ears_cx) / sh_gap < 0.12:
        return 0.0
    return 85.0 if nose.x > ears_cx else -85.0


def silhouette(crop_rgb: np.ndarray) -> np.ndarray:
    """Foreground mask by flood-filling the (near-white) background from the borders — robust to white garments."""
    g = cv2.cvtColor(crop_rgb, cv2.COLOR_RGB2GRAY)
    h, w = g.shape
    pad = cv2.copyMakeBorder(g, 1, 1, 1, 1, cv2.BORDER_CONSTANT, value=255)
    ff = np.zeros((h + 4, w + 4), np.uint8)
    for seed in [(0, 0), (w + 1, 0), (0, h + 1), (w + 1, h + 1)]:
        cv2.floodFill(pad, ff, seed, 0, loDiff=22, upDiff=22, flags=4 | cv2.FLOODFILL_MASK_ONLY | cv2.FLOODFILL_FIXED_RANGE | (1 << 8))
    bg = ff[2:-2, 2:-2]
    mask = (bg == 0).astype(np.uint8)
    mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, np.ones((5, 5), np.uint8))
    return mask


def symmetry_score(mask: np.ndarray) -> float:
    """IoU between the silhouette and its horizontal mirror, after centring on the column centroid."""
    cols = mask.sum(axis=0)
    if cols.sum() == 0:
        return 0.0
    cx = int((cols * np.arange(len(cols))).sum() / cols.sum())
    half = min(cx, mask.shape[1] - cx - 1)
    a = mask[:, cx - half: cx + half + 1]
    b = a[:, ::-1]
    inter, union = np.logical_and(a, b).sum(), np.logical_or(a, b).sum()
    return float(inter / max(union, 1))


def protrusion_direction(mask: np.ndarray, subject: str) -> float:
    """For a faceless profile: the FACE side has the more irregular outline (brow, nose, lips, chin) than the
    back of the skull. + → nose points screen-right (subject's left profile)."""
    h = mask.shape[0]
    head = mask[: max(3, int(0.16 * h))] if subject == "body" else mask[: int(0.75 * h)]
    rows = [np.where(r)[0] for r in head]
    rows = [r for r in rows if len(r)]
    if len(rows) < 10:
        return 0.0
    lefts = np.array([r.min() for r in rows], float); rights = np.array([r.max() for r in rows], float)
    # irregularity = total variation of the outline (sum of |second difference|)
    tv = lambda a: np.abs(np.diff(a, n=2)).sum()
    return 85.0 if tv(rights) > tv(lefts) else -85.0


def classify(panel_rgb: np.ndarray, bbox, order_prior: str | None = None) -> dict:
    x0, y0, x1, y1 = bbox
    crop = panel_rgb[y0:y1, x0:x1]
    ch, cw = crop.shape[:2]
    cut_bottom = y1 >= panel_rgb.shape[0] - 4   # figure runs off the panel edge → cropped closeup
    face = detect_face(crop)
    lm = run_pose(crop)
    mask = silhouette(crop)
    sym = symmetry_score(mask)
    conf = 0.9

    # subject: legs visible → body ; figure cut by the bottom edge over most of the width → closeup (head/bust)
    legs = bool(lm) and max(lm[25].visibility, lm[26].visibility, lm[27].visibility, lm[28].visibility) > 0.5
    bottom_contact = float(mask[-max(2, int(0.02 * ch)):, :].mean())
    top_contact = float(mask[: max(2, int(0.02 * ch)), :].mean())
    if legs:
        subject = "body"
    elif face and face["h"] > 0.30:
        subject = "head"
    elif cut_bottom and bottom_contact > 0.55:
        subject = "head"; conf = 0.7
    elif lm and (lm[11].visibility > 0.5 or lm[12].visibility > 0.5):
        subject = "head"
    else:
        subject = "body"; conf = 0.5

    # yaw
    yaw = None
    if lm:
        yaw = pose_yaw(lm)
    if yaw is None and face:
        yaw = yaw_from_keypoints(face["kp"])
    if yaw is None:
        if sym > 0.80:
            yaw = 0.0 if face else 180.0
            conf = min(conf, 0.7 if face else 0.6)
        else:
            yaw = protrusion_direction(mask, subject); conf = min(conf, 0.5)
    elif not face and sym > 0.85:
        yaw = 180.0; conf = min(conf, 0.6)     # symmetric silhouette, no face → back view

    if yaw == 180.0:
        angle = "back"
    elif abs(yaw) < 25:
        angle = "front"
    elif abs(yaw) < 65:
        angle = "left34" if yaw > 0 else "right34"
    else:
        angle = "left" if yaw > 0 else "right"
    return {"face": face is not None, "pose": lm is not None, "subject": subject, "angle": angle,
            "yaw": round(float(yaw), 1), "symmetry": round(sym, 3), "confidence": conf, "aspect": round(cw / ch, 3),
            "top_cut": top_contact > 0.1, "framing": "closeup" if (subject == "head" and top_contact > 0.1) else ("head" if subject == "head" else "full")}


# ---------- 3. canonical crops ----------

def canonical_crop(img: Image.Image, bbox, subject: str, clip=None) -> Image.Image:
    """Pad to a canonical aspect on white: head → 1:1, body → 1:2. Margin 6 %, never crossing `clip`
    (the panel span, so that neighbouring panels and titles never leak in)."""
    x0, y0, x1, y1 = bbox
    if clip:
        cx0, cy0, cx1, cy1 = clip
        x0, y0, x1, y1 = max(x0, cx0), max(y0, cy0), min(x1, cx1), min(y1, cy1)
    crop = img.crop((x0, y0, x1, y1))
    w, h = crop.size
    m = int(0.06 * max(w, h))
    target = 1.0 if subject == "head" else 0.5
    cw, ch = w + 2 * m, h + 2 * m
    if cw / ch < target:
        cw = int(ch * target)
    else:
        ch = int(cw / target)
    canvas = Image.new("RGB", (cw, ch), (255, 255, 255))
    canvas.paste(crop, ((cw - w) // 2, (ch - h) // 2))
    size = (1024, 1024) if subject == "head" else (1024, 2048)
    return canvas.resize(size, Image.LANCZOS)


def split_sheet(path: Path, out: Path, name: str = "character") -> dict:
    img = Image.open(path).convert("RGB")
    rgb = np.array(img)
    gray = cv2.cvtColor(rgb, cv2.COLOR_RGB2GRAY)
    H, W = gray.shape
    panels = find_panels(gray)
    (out / "views").mkdir(parents=True, exist_ok=True)
    regions, used = [], {}
    infos = []
    for i, (px0, px1) in enumerate(panels):
        g = gray[:, px0:px1]
        y0 = strip_title(g)
        bb = content_bbox(g, y0)
        infos.append((px0, px1, y0, bb, classify(rgb[:, px0:px1], bb) if bb else None))
    # layout prior: a 5-panel sheet whose panels are all low-confidence gets the common order as a proposal
    PRIOR = [("body", "front"), ("body", "left"), ("body", "back"), ("head", "front"), ("head", "left")]
    if len(infos) == 5 and all(i[4] and i[4]["confidence"] <= 0.7 for i in infos):
        for k, (px0, px1, y0, bb, info) in enumerate(infos):
            if info["confidence"] < 0.7:
                info["subject"], info["angle"] = PRIOR[k]
                info["prior_applied"] = True
    for i, (px0, px1, y0, bb, info) in enumerate(infos):
        if not bb:
            continue
        bx0, by0, bx1, by1 = bb
        bbox_abs = (px0 + bx0, by0, px0 + bx1, by1)
        key = f"{info['subject']}.{info['angle']}" + (".closeup" if info.get("framing") == "closeup" else "")
        # avoid collisions: second head.front becomes head.front.2 etc.
        n = used.get(key, 0) + 1
        used[key] = n
        fname = f"{key}{'' if n == 1 else '.' + str(n)}.jpg"
        canonical_crop(img, bbox_abs, info["subject"], clip=(px0, y0, px1, H)).save(out / "views" / fname, quality=92)
        regions.append({"panel": i, "file": f"views/{fname}", "subject": info["subject"], "angle": info["angle"], "framing": info.get("framing"),
                        "prior_applied": info.get("prior_applied", False),
                        "yaw_est": info["yaw"], "face_detected": info["face"], "pose_detected": info["pose"],
                        "symmetry": info["symmetry"], "confidence": info["confidence"],
                        "box": [round(bbox_abs[0] / W, 4), round(bbox_abs[1] / H, 4), round(bbox_abs[2] / W, 4), round(bbox_abs[3] / H, 4)]})
    # canonical head.front (full head, 1:1) derived from body.front when the closeup is cut at the top
    have_head_front = any(r["subject"] == "head" and r["angle"] == "front" and r["framing"] == "head" for r in regions)
    bf = next((r for r in regions if r["subject"] == "body" and r["angle"] == "front"), None)
    if bf and not have_head_front:
        x0, y0, x1, y1 = [int(v * (W if k % 2 == 0 else H)) for k, v in enumerate(bf["box"])]
        crop = rgb[y0:y1, x0:x1]
        face = detect_face(crop)
        if face:
            fh, fw = crop.shape[:2]
            cx, cy = (face["x"] + face["w"] / 2) * fw, (face["y"] + face["h"] / 2) * fh
            half = face["h"] * fh * 1.25            # box ≈ 2.5 × face height → hair to chin with margin
            hb = (int(max(0, x0 + cx - half)), int(max(0, y0 + cy - half * 1.05)), int(min(W, x0 + cx + half)), int(min(H, y0 + cy + half * 0.95)))
            canonical_crop(img, hb, "head", clip=(x0, y0, x1, y1)).save(out / "views" / "head.front.jpg", quality=92)
            regions.append({"panel": bf["panel"], "file": "views/head.front.jpg", "subject": "head", "angle": "front", "framing": "head",
                            "derived_from": bf["file"], "confidence": 0.8,
                            "box": [round(hb[0] / W, 4), round(hb[1] / H, 4), round(hb[2] / W, 4), round(hb[3] / H, 4)]})
    meta = {"source": path.name, "width": W, "height": H, "panels": len(panels), "regions": regions}
    (out / "sheet.regions.json").write_text(json.dumps(meta, indent=2), "utf-8")
    return meta


if __name__ == "__main__":
    src, dst = Path(sys.argv[1]), Path(sys.argv[2])
    nm = sys.argv[sys.argv.index("--name") + 1] if "--name" in sys.argv else "character"
    print(json.dumps(split_sheet(src, dst, nm), indent=2))
