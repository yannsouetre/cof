"""ZIP container: pack / unpack / read, with the COF rules (sentinel, paths, storage)."""
from __future__ import annotations

import hashlib
import json
import os
import re
import shutil
import zipfile
from pathlib import Path

from . import MIMETYPE

SAFE_PATH = re.compile(r"^(?!/)(?!.*\.\.)[A-Za-z0-9._/-]+$")

# High-entropy media that gains nothing from deflate → stored (ZIP_STORED)
STORED_EXT = {
    ".jpg", ".jpeg", ".webp", ".avif", ".png", ".gif",
    ".opus", ".ogg", ".mp3", ".flac", ".m4a",
    ".mp4", ".webm", ".mkv",
    ".glb", ".vrm", ".spz", ".ply", ".3mf", ".safetensors", ".onnx", ".pt", ".npz", ".zip",
}

MAX_RATIO = 100          # anti zip-bomb: uncompressed / compressed
MAX_UNCOMPRESSED = 4 * 1024 ** 3  # 4 GiB default ceiling


class ContainerError(Exception):
    pass


THUMBNAIL_PATH = "Thumbnails/thumbnail.png"   # reserved: ≤ 256 px PNG for file managers (ODF convention)


def make_thumbnail(src: Path, manifest: dict, size: int = 256) -> str | None:
    """Derive Thumbnails/thumbnail.png from manifest['thumbnail'] (an image asset). Returns the path or None."""
    rel = manifest.get("thumbnail")
    if not rel or rel == THUMBNAIL_PATH or not (src / rel).is_file():
        return None
    try:
        from PIL import Image
    except ImportError:
        return None
    try:
        im = Image.open(src / rel)
        im.thumbnail((size, size))
        if im.mode not in ("RGB", "RGBA"):
            im = im.convert("RGBA")
        out = src / THUMBNAIL_PATH
        out.parent.mkdir(parents=True, exist_ok=True)
        im.save(out, "PNG", optimize=True)
    except Exception:
        return None
    srca = next((a for a in manifest.get("assets", []) if a.get("path") == rel), {})
    manifest["assets"] = [a for a in manifest.get("assets", []) if a.get("path") != THUMBNAIL_PATH]
    manifest["assets"].append({"id": "thumbnail", "path": THUMBNAIL_PATH, "role": "derived", "method": "thumbnail",
                               "source": srca.get("id"), "mediaType": "image/png", "bytes": out.stat().st_size,
                               "sha256": sha256_file(out), "license": srca.get("license", "LicenseRef-Unknown")})
    if not manifest["assets"][-1]["source"]:
        manifest["assets"][-1].pop("source")
    manifest["thumbnail"] = THUMBNAIL_PATH
    return THUMBNAIL_PATH


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def check_path(rel: str) -> None:
    if not SAFE_PATH.match(rel):
        raise ContainerError(f"non-conformant path (ASCII, no '..', no leading '/'): {rel!r}")
    if rel in ("mimetype",):
        raise ContainerError("'mimetype' is reserved for the packer")


def iter_source_files(src: Path):
    for root, dirs, files in os.walk(src):
        dirs.sort()
        for name in sorted(files):
            p = Path(root) / name
            if p.is_symlink():
                raise ContainerError(f"symbolic link forbidden: {p}")
            rel = p.relative_to(src).as_posix()
            if rel == "mimetype":
                continue
            yield rel, p


def refresh_asset_index(src: Path, manifest: dict, strict: bool = True) -> list[str]:
    """Fill bytes/sha256 for every asset entry that points to a packed path. Returns notes."""
    notes = []
    for a in manifest.get("assets", []):
        rel = a.get("path")
        if not rel:
            continue
        p = src / rel
        if not p.is_file():
            if a.get("uri"):
                notes.append(f"external asset without local copy: {rel}")
                continue
            msg = f"asset declared but missing: {rel}"
            if strict:
                raise ContainerError(msg)
            notes.append(msg)
            continue
        a["bytes"] = p.stat().st_size
        a["sha256"] = sha256_file(p)
    return notes


def pack(src: str | os.PathLike, dest: str | os.PathLike, *, refresh: bool = True, aligned: int = 0) -> Path:
    src, dest = Path(src), Path(dest)
    mpath = src / "manifest.json"
    if not mpath.is_file():
        raise ContainerError("manifest.json not found at the root of the folder")
    manifest = json.loads(mpath.read_text("utf-8"))
    if refresh:
        refresh_asset_index(src, manifest)
        mpath.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", "utf-8")

    with zipfile.ZipFile(dest, "w", allowZip64=True) as z:
        # 1) sentinel, stored, first
        zi = zipfile.ZipInfo("mimetype", date_time=(1980, 1, 1, 0, 0, 0))
        zi.compress_type = zipfile.ZIP_STORED
        z.writestr(zi, MIMETYPE)
        # 2) manifest second
        z.write(mpath, "manifest.json", compress_type=zipfile.ZIP_DEFLATED)
        # 3) OS thumbnail third (reserved path, stored) so file-manager thumbnailers find it at once
        tp = src / THUMBNAIL_PATH
        if tp.is_file():
            z.write(tp, THUMBNAIL_PATH, compress_type=zipfile.ZIP_STORED)
        # 4) everything else, deterministic order
        for rel, p in iter_source_files(src):
            if rel in ("manifest.json", THUMBNAIL_PATH):
                continue
            check_path(rel)
            ct = zipfile.ZIP_STORED if p.suffix.lower() in STORED_EXT else zipfile.ZIP_DEFLATED
            z.write(p, rel, compress_type=ct)
    return dest


def read_manifest(cof: str | os.PathLike) -> dict:
    with zipfile.ZipFile(cof) as z:
        names = z.namelist()
        if not names or names[0] != "mimetype":
            raise ContainerError("the first entry must be 'mimetype'")
        info = z.getinfo("mimetype")
        if info.compress_type != zipfile.ZIP_STORED:
            raise ContainerError("'mimetype' must be stored uncompressed")
        if z.read("mimetype").decode("ascii", "replace").strip() != MIMETYPE:
            raise ContainerError("unexpected 'mimetype' content")
        if "manifest.json" not in names:
            raise ContainerError("manifest.json missing")
        return json.loads(z.read("manifest.json").decode("utf-8"))


def safe_rel(rel) -> str:
    """A relative path read from a manifest, about to touch the filesystem: the container grammar (SPEC § 1 — no leading
    '/', no '..'), whatever the archive or folder it came from said."""
    if not isinstance(rel, str) or not SAFE_PATH.match(rel):
        raise ContainerError(f"non-conformant path in manifest: {rel!r}")
    return rel


def copy_rel(src: Path, rel: str, dst: Path, newrel: str | None = None) -> Path:
    """Copies src/rel to dst/newrel (default: same path), both paths checked by safe_rel."""
    safe_rel(rel); newrel = safe_rel(newrel or rel)
    (dst / newrel).parent.mkdir(parents=True, exist_ok=True)
    shutil.copy(src / rel, dst / newrel)
    return dst / newrel


def inspect(cof: str | os.PathLike) -> dict:
    """Structural checks on the archive itself (no schema): returns {'errors': [...], 'warnings': [...], 'entries': n}."""
    errors, warnings = [], []
    with zipfile.ZipFile(cof) as z:
        infos = z.infolist()
        names = [i.filename for i in infos]
        if not names or names[0] != "mimetype":
            errors.append("first entry ≠ 'mimetype'")
        elif infos[0].compress_type != zipfile.ZIP_STORED:
            errors.append("'mimetype' compressed")
        if len(names) > 1 and names[1] != "manifest.json":
            warnings.append("manifest.json is not the second entry (slower partial reads)")
        total_u = total_c = 0
        seen: set[str] = set()
        for i in infos:
            n = i.filename
            if n in seen:                                   # a second entry of the same name: readers disagree on which one wins
                errors.append(f"duplicate entry: {n}")
            seen.add(n)
            if n != "mimetype" and not SAFE_PATH.match(n):
                errors.append(f"non-conformant path: {n}")
            if n.endswith("/"):
                warnings.append(f"unnecessary directory entry: {n}")
            if i.flag_bits & 0x1:
                errors.append(f"encrypted entry forbidden: {n}")
            if i.compress_size and i.file_size / max(i.compress_size, 1) > MAX_RATIO:
                errors.append(f"suspicious compression ratio (> {MAX_RATIO}:1): {n}")
            total_u += i.file_size
            total_c += i.compress_size
            ext = Path(n).suffix.lower()
            if ext in STORED_EXT and i.compress_type != zipfile.ZIP_STORED:
                warnings.append(f"high-entropy binary compressed (should be stored): {n}")
        if total_u > MAX_UNCOMPRESSED:
            errors.append("uncompressed size > 4 GiB")
    return {"errors": errors, "warnings": warnings, "entries": len(names), "uncompressed": total_u, "compressed": total_c}


def unpack(cof: str | os.PathLike, dest: str | os.PathLike) -> Path:
    dest = Path(dest)
    dest.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(cof) as z:
        for info in z.infolist():
            n = info.filename
            if n == "mimetype" or n.endswith("/"):           # directory entries (zip -r) carry nothing
                continue
            if not SAFE_PATH.match(n):
                raise ContainerError(f"non-conformant path: {n}")
            target = (dest / n).resolve()
            if not str(target).startswith(str(dest.resolve())):
                raise ContainerError(f"zip-slip detected: {n}")
            target.parent.mkdir(parents=True, exist_ok=True)
            with z.open(info) as s, open(target, "wb") as d:
                shutil.copyfileobj(s, d, 1 << 20)
    return dest


def verify_hashes(cof: str | os.PathLike, manifest: dict) -> list[str]:
    """Return list of error strings for assets whose sha256/bytes do not match the archive."""
    errs = []
    with zipfile.ZipFile(cof) as z:
        names = set(z.namelist())
        for a in manifest.get("assets", []):
            rel = a.get("path")
            if not rel:
                continue
            if rel not in names:
                if not a.get("uri"):
                    errs.append(f"declared asset missing from archive: {rel}")
                continue
            h, n = hashlib.sha256(), 0
            with z.open(rel) as s:                          # streamed: a declared asset is never held whole in memory
                for chunk in iter(lambda: s.read(1 << 20), b""):
                    h.update(chunk); n += len(chunk)
            if a.get("bytes") is not None and a["bytes"] != n:
                errs.append(f"size mismatch: {rel} ({a['bytes']} declared, {n} actual)")
            if a.get("sha256") and a["sha256"] != h.hexdigest():
                errs.append(f"sha256 mismatch: {rel}")
    return errs
