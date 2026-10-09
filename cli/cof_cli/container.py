"""ZIP container: pack / unpack / read, with the COF rules (sentinel, paths, storage)."""
from __future__ import annotations

import hashlib
import json
import os
import re
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


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def check_path(rel: str) -> None:
    if not SAFE_PATH.match(rel):
        raise ContainerError(f"chemin non conforme (ASCII, sans '..', sans '/' initial) : {rel!r}")
    if rel in ("mimetype",):
        raise ContainerError("'mimetype' est réservé au packer")


def iter_source_files(src: Path):
    for root, dirs, files in os.walk(src):
        dirs.sort()
        for name in sorted(files):
            p = Path(root) / name
            if p.is_symlink():
                raise ContainerError(f"lien symbolique interdit : {p}")
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
                notes.append(f"asset externe sans copie locale : {rel}")
                continue
            msg = f"asset déclaré mais absent : {rel}"
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
        raise ContainerError("manifest.json introuvable à la racine du dossier")
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
        # 3) everything else, deterministic order
        for rel, p in iter_source_files(src):
            if rel == "manifest.json":
                continue
            check_path(rel)
            ct = zipfile.ZIP_STORED if p.suffix.lower() in STORED_EXT else zipfile.ZIP_DEFLATED
            z.write(p, rel, compress_type=ct)
    return dest


def read_manifest(cof: str | os.PathLike) -> dict:
    with zipfile.ZipFile(cof) as z:
        names = z.namelist()
        if not names or names[0] != "mimetype":
            raise ContainerError("la première entrée doit être 'mimetype'")
        info = z.getinfo("mimetype")
        if info.compress_type != zipfile.ZIP_STORED:
            raise ContainerError("'mimetype' doit être stocké sans compression")
        if z.read("mimetype").decode("ascii", "replace").strip() != MIMETYPE:
            raise ContainerError("contenu de 'mimetype' inattendu")
        if "manifest.json" not in names:
            raise ContainerError("manifest.json absent")
        return json.loads(z.read("manifest.json").decode("utf-8"))


def inspect(cof: str | os.PathLike) -> dict:
    """Structural checks on the archive itself (no schema): returns {'errors': [...], 'warnings': [...], 'entries': n}."""
    errors, warnings = [], []
    with zipfile.ZipFile(cof) as z:
        infos = z.infolist()
        names = [i.filename for i in infos]
        if not names or names[0] != "mimetype":
            errors.append("première entrée ≠ 'mimetype'")
        elif infos[0].compress_type != zipfile.ZIP_STORED:
            errors.append("'mimetype' compressé")
        if len(names) > 1 and names[1] != "manifest.json":
            warnings.append("manifest.json n'est pas la deuxième entrée (lecture partielle plus lente)")
        total_u = total_c = 0
        for i in infos:
            n = i.filename
            if n != "mimetype" and not SAFE_PATH.match(n):
                errors.append(f"chemin non conforme : {n}")
            if n.endswith("/"):
                warnings.append(f"entrée de répertoire inutile : {n}")
            if i.flag_bits & 0x1:
                errors.append(f"entrée chiffrée interdite : {n}")
            if i.compress_size and i.file_size / max(i.compress_size, 1) > MAX_RATIO:
                errors.append(f"taux de compression suspect (> {MAX_RATIO}:1) : {n}")
            total_u += i.file_size
            total_c += i.compress_size
            ext = Path(n).suffix.lower()
            if ext in STORED_EXT and i.compress_type != zipfile.ZIP_STORED:
                warnings.append(f"binaire haute entropie compressé (devrait être stocké) : {n}")
        if total_u > MAX_UNCOMPRESSED:
            errors.append("taille décompressée > 4 GiB")
    return {"errors": errors, "warnings": warnings, "entries": len(names), "uncompressed": total_u, "compressed": total_c}


def unpack(cof: str | os.PathLike, dest: str | os.PathLike) -> Path:
    dest = Path(dest)
    dest.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(cof) as z:
        for info in z.infolist():
            n = info.filename
            if n == "mimetype":
                continue
            if not SAFE_PATH.match(n):
                raise ContainerError(f"chemin non conforme : {n}")
            target = (dest / n).resolve()
            if not str(target).startswith(str(dest.resolve())):
                raise ContainerError(f"zip-slip détecté : {n}")
            target.parent.mkdir(parents=True, exist_ok=True)
            with z.open(info) as s, open(target, "wb") as d:
                d.write(s.read())
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
                    errs.append(f"asset déclaré absent de l'archive : {rel}")
                continue
            data = z.read(rel)
            if a.get("bytes") is not None and a["bytes"] != len(data):
                errs.append(f"taille différente : {rel} ({a['bytes']} déclaré, {len(data)} réel)")
            if a.get("sha256") and a["sha256"] != hashlib.sha256(data).hexdigest():
                errs.append(f"sha256 différent : {rel}")
    return errs
