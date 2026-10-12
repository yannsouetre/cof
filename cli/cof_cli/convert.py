"""Converters: PNG character cards (chara / ccv3 tEXt chunks) ⇄ COF directory, SOUL.md / IDENTITY.md export."""
from __future__ import annotations

import base64
import json
import re
import struct
import zlib
from datetime import datetime, timezone
from pathlib import Path

PNG_SIG = b"\x89PNG\r\n\x1a\n"


# ---------- PNG chunk helpers ----------

def png_chunks(data: bytes):
    if not data.startswith(PNG_SIG):
        raise ValueError("not a PNG")
    pos = 8
    while pos + 8 <= len(data):
        length = struct.unpack(">I", data[pos:pos + 4])[0]
        ctype = data[pos + 4:pos + 8]
        body = data[pos + 8:pos + 8 + length]
        pos += 12 + length
        yield ctype, body
        if ctype == b"IEND":
            break


def png_build(chunks) -> bytes:
    out = bytearray(PNG_SIG)
    for ctype, body in chunks:
        out += struct.pack(">I", len(body)) + ctype + body + struct.pack(">I", zlib.crc32(ctype + body) & 0xFFFFFFFF)
    return bytes(out)


def read_card_from_png(data: bytes) -> dict:
    """Return the richest card found: ccv3 first, else chara (V2/V1)."""
    found = {}
    for ctype, body in png_chunks(data):
        if ctype == b"tEXt" and b"\x00" in body:
            key, _, val = body.partition(b"\x00")
            k = key.decode("latin-1")
            if k in ("chara", "ccv3"):
                try:
                    found[k] = json.loads(base64.b64decode(val).decode("utf-8"))
                except Exception:
                    pass
    if "ccv3" in found:
        return found["ccv3"]
    if "chara" in found:
        card = found["chara"]
        if "spec" not in card:  # V1 flat → wrap as V2
            card = {"spec": "chara_card_v2", "spec_version": "2.0", "data": card}
        return card
    raise ValueError("no character card ('chara'/'ccv3' chunks) in this PNG")


def write_card_to_png(png: bytes, card: dict) -> bytes:
    """Embed both 'ccv3' (V3) and 'chara' (V2 downgrade) chunks, replacing existing ones."""
    v3 = {**card, "spec": "chara_card_v3", "spec_version": "3.0"}
    v2 = {"spec": "chara_card_v2", "spec_version": "2.0", "data": {k: v for k, v in card.get("data", {}).items()
          if k not in ("assets", "nickname", "creator_notes_multilingual", "source", "group_only_greetings",
                       "creation_date", "modification_date")}}
    chunks = [(t, b) for t, b in png_chunks(png) if not (t == b"tEXt" and (b.startswith(b"chara\x00") or b.startswith(b"ccv3\x00")))]
    iend = chunks.pop()  # IEND
    for key, obj in (("chara", v2), ("ccv3", v3)):
        body = key.encode() + b"\x00" + base64.b64encode(json.dumps(obj, ensure_ascii=False).encode("utf-8"))
        chunks.append((b"tEXt", body))
    chunks.append(iend)
    return png_build(chunks)


# ---------- description text embedded in an image (no card) ----------

def write_text_to_png(png: bytes, text: str, keyword: str = "Description") -> bytes:
    """Embed a UTF-8 text as a PNG iTXt chunk (standard keyword 'Description'), replacing an existing one."""
    chunks = []
    for t, b in png_chunks(png):
        if t == b"iTXt" and b.split(b"\x00", 1)[0].decode("latin1") == keyword:
            continue
        chunks.append((t, b))
    iend = chunks.pop()
    body = keyword.encode("latin1") + b"\x00" + b"\x00\x00" + b"\x00" + b"\x00" + text.encode("utf-8")   # compression flag 0, method 0, no language, no translated keyword
    chunks.append((b"iTXt", body)); chunks.append(iend)
    return png_build(chunks)


def _exif_texts(ex: bytes) -> dict:
    out = {}
    if len(ex) < 8:
        return out
    le = ex[:2] == b"II"; fmt = "<" if le else ">"
    u16 = lambda o: struct.unpack(fmt + "H", ex[o:o + 2])[0]; u32 = lambda o: struct.unpack(fmt + "I", ex[o:o + 4])[0]
    SZ = {1: 1, 2: 1, 3: 2, 4: 4, 5: 8, 7: 1, 9: 4, 10: 8}

    def ifd(off, depth=0):
        if depth > 3 or off + 2 > len(ex):
            return
        for k in range(u16(off)):
            e = off + 2 + 12 * k
            if e + 12 > len(ex):
                break
            tag, typ, cnt = u16(e), u16(e + 2), u32(e + 4); sz = SZ.get(typ, 1) * cnt
            vo = e + 8 if sz <= 4 else u32(e + 8); val = ex[vo:vo + sz]
            if tag == 0x8769:
                ifd(u32(e + 8), depth + 1)
            elif tag == 0x010E:
                out["ImageDescription"] = val.rstrip(b"\x00").decode("utf-8", "replace")
            elif tag == 0x9286:
                h = val[:8]
                out["UserComment"] = (val[8:].decode("utf-16-le" if le else "utf-16-be", "replace") if h.startswith(b"UNICODE") else (val[8:] if h.startswith((b"ASCII", b"JIS")) else val).decode("utf-8", "replace")).rstrip("\x00")
            elif tag == 0x9C9C:
                out["XPComment"] = val.decode("utf-16-le", "replace").rstrip("\x00")
    try:
        ifd(u32(4))
    except Exception:
        pass
    return out


def _xmp_description(xml: str) -> str:
    m = re.search(r"<dc:description>[\s\S]*?<rdf:li[^>]*>([\s\S]*?)</rdf:li>", xml) or re.search(r'dc:description="([^"]*)"', xml)
    return (m.group(1) if m else "").replace("&lt;", "<").replace("&gt;", ">").replace("&amp;", "&").replace("&quot;", '"').strip()


def read_text_from_image(data: bytes) -> dict | None:
    """Longest descriptive text found in a PNG (iTXt/tEXt/zTXt Description|Comment, XMP, EXIF incl. 'Raw profile type') or JPEG (EXIF, XMP, COM)."""
    cands = []
    push = lambda source, text: cands.append({"source": source, "text": text.strip()}) if text and len(text.strip()) >= 20 else None
    if data.startswith(PNG_SIG):
        for t, b in png_chunks(data):
            try:
                if t == b"tEXt":
                    k, v = b.split(b"\x00", 1); key = k.decode("latin1")
                    if key.lower() in ("description", "comment", "cof:description"):
                        push("PNG tEXt " + key, v.decode("latin1"))
                    elif key == "XML:com.adobe.xmp":
                        push("PNG XMP", _xmp_description(v.decode("utf-8", "replace")))
                elif t == b"iTXt":
                    k, rest = b.split(b"\x00", 1); key = k.decode("latin1"); cf = rest[0]; rest = rest[2:]
                    _lang, rest = rest.split(b"\x00", 1); _tk, txt = rest.split(b"\x00", 1)
                    if cf:
                        txt = zlib.decompress(txt)
                    if key.lower() in ("description", "comment", "cof:description"):
                        push("PNG iTXt " + key, txt.decode("utf-8", "replace"))
                    elif key == "XML:com.adobe.xmp":
                        push("PNG XMP", _xmp_description(txt.decode("utf-8", "replace")))
                elif t == b"zTXt":
                    k, rest = b.split(b"\x00", 1); key = k.decode("latin1"); txt = zlib.decompress(rest[1:]).decode("latin1")
                    if key.lower() in ("description", "comment"):
                        push("PNG zTXt " + key, txt)
                    elif re.match(r"Raw profile type (APP1|exif)$", key, re.I):
                        hexs = "".join(txt.split("\n")[3:]).replace(" ", ""); ex = bytes.fromhex(hexs)
                        for kk, vv in _exif_texts(ex[6:] if ex.startswith(b"Exif") else ex).items():
                            push("EXIF " + kk, vv)
                    elif re.match(r"Raw profile type xmp$", key, re.I):
                        push("PNG XMP", _xmp_description(bytes.fromhex("".join(txt.split("\n")[3:]).replace(" ", "")).decode("utf-8", "replace")))
                elif t == b"eXIf":
                    for kk, vv in _exif_texts(b).items():
                        push("EXIF " + kk, vv)
            except Exception:
                continue
    elif data[:2] == b"\xff\xd8":
        p = 2
        while p + 4 < len(data) and data[p] == 0xFF:
            marker = data[p + 1]
            if marker in (0xDA, 0xD9):
                break
            ln = struct.unpack(">H", data[p + 2:p + 4])[0]; seg = data[p + 4:p + 2 + ln]
            if marker == 0xE1:
                if seg.startswith(b"Exif\x00\x00"):
                    for kk, vv in _exif_texts(seg[6:]).items():
                        push("EXIF " + kk, vv)
                elif seg.startswith(b"http://ns.adobe.com/xap/1.0/"):
                    push("JPEG XMP", _xmp_description(seg[29:].decode("utf-8", "replace")))
            elif marker == 0xFE:
                push("JPEG COM", seg.decode("utf-8", "replace"))
            p += 2 + ln
    cands.sort(key=lambda c: -len(c["text"]))
    return cands[0] if cands else None


# ---------- card → COF directory ----------

def _slug(s: str) -> str:
    s = re.sub(r"[^A-Za-z0-9._-]+", "-", s).strip("-")
    return s or "character"


def ulid_like() -> str:
    """26-char Crockford base32 ULID (time + randomness)."""
    import os, time
    alphabet = "0123456789ABCDEFGHJKMNPQRSTVWXYZ"
    t = int(time.time() * 1000)
    out = ""
    for _ in range(10):
        out = alphabet[t & 31] + out
        t >>= 5
    rnd = int.from_bytes(os.urandom(10), "big")
    tail = ""
    for _ in range(16):
        tail = alphabet[rnd & 31] + tail
        rnd >>= 5
    return out + tail


def default_permissions() -> dict:
    return {"avatarPermission": "onlyAuthor", "commercialUsage": "personalNonProfit", "modification": "prohibited",
            "allowRedistribution": False, "creditNotation": "required",
            "allowExcessivelyViolentUsage": False, "allowSexualUsage": False, "allowPoliticalOrReligiousUsage": False,
            "allowAntisocialOrHateUsage": False, "allowVoiceCloning": False, "allowTraining": "none",
            "allowImpersonationOfRealPerson": False, "aiDisclosure": True}


def card_to_cof_dir(card: dict, dest: Path, *, png: bytes | None = None, age: int | None = None,
                    fictional: bool = True, language: str = "en") -> Path:
    """Character Card (V2/V3) → v0.3 directory: elements.personality.p1 (+ face.f1 from the PNG) + preset 'default'."""
    data = card.get("data", {})
    dest.mkdir(parents=True, exist_ok=True)
    pdir = dest / "elements" / "personality" / "p1"
    pdir.mkdir(parents=True, exist_ok=True)
    now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    v3 = {**card, "spec": "chara_card_v3", "spec_version": "3.0"}
    v3.setdefault("data", {}).setdefault("extensions", {})
    (pdir / "card.json").write_text(json.dumps(v3, ensure_ascii=False, indent=2) + "\n", "utf-8")

    elements = {"personality": {"variants": {"p1": {"kind": "card", "label": data.get("name") or "Personality", "language": language, "card": "elements/personality/p1/card.json"}}}}
    slots = {"personality": ["p1"]}
    assets = []
    if png:
        fdir = dest / "elements" / "appearance" / "f1"
        fdir.mkdir(parents=True, exist_ok=True)
        (fdir / "head.front.png").write_bytes(png)
        assets.append({"id": "a-face-f1-front", "path": "elements/appearance/f1/head.front.png", "role": "view", "subject": "head", "angle": "front",
                       "framing": "head", "mediaType": "image/png", "bytes": 0, "sha256": "0" * 64, "license": "LicenseRef-Unknown"})
        fv = {"kind": "face", "label": "Face (card thumbnail)", "images": ["a-face-f1-front"]}
        if age is not None:
            fv["age"] = {"value": age, "unit": "years", "basis": "declared"}      # v0.5: age is carried by the representation
        elements["appearance"] = {"variants": {"f1": fv}}
        slots["appearance"] = ["f1"]

    manual = [re.sub(r"[^a-z0-9-]", "-", t.lower()).strip("-") for t in (data.get("tags") or []) if isinstance(t, str)]
    manifest = {
        "cof": "1.0", "id": ulid_like(),
        "name": data.get("name") or "Unnamed", "nickname": data.get("nickname") or "",
        "languages": [language], "summary": (data.get("description") or "")[:300], "fictional": fictional,
        "morphology": {"class": "human", "species": "human"},
        "tags": {"auto": ["humanoid", "imported-ccv3"], "manual": [t for t in manual if t][:30], "content": ["none"],
                 "ip": {"original": True, "franchise": None, "based_on": None}},
        "elements": elements,
        "presets": {"default": {"label": "Default", "slots": slots, **({"age_override": {"value": age, "unit": "years", "basis": "declared"}} if age is not None else {})}},
        "default_preset": "default",
        "priorities": {"visual": ["identity_weights", "images", "avatar", "descriptive"], "voice": ["samples", "described"]},
        "mapping_vocabularies": {}, "assets": assets,
        "size_class": "lite", "container": {"aligned": 0, "executableContent": "none"},
        "rights": {"permissions": default_permissions(), "consent": None},
        "provenance": {"created": now, "modified": now, "generator": "cof-cli", "source": list(data.get("source") or []), "c2pa": None, "signatures": []},
        "metadata": {"@context": {"dc": "http://purl.org/dc/elements/1.1/"}, "dc:creator": [data.get("creator") or ""]},
        "extensions": {},
    }
    (dest / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", "utf-8")
    return dest


# ---------- COF directory → SOUL.md / IDENTITY.md ----------

def export_soul(src: Path, preset: str | None = None) -> tuple[str, str]:
    from .model import asset_index, default_preset_id, first, resolved
    manifest = json.loads((src / "manifest.json").read_text("utf-8"))
    r = resolved(manifest, preset or default_preset_id(manifest))
    p = first(r, "personality") or {}
    data = json.loads((src / p["card"]).read_text("utf-8")).get("data", {}) if p.get("card") else {}
    psyche = json.loads((src / p["psyche"]).read_text("utf-8")) if p.get("psyche") and (src / p["psyche"]).is_file() else {}
    A = asset_index(manifest)

    lines = [f"# SOUL.md — {manifest.get('name')}", ""]
    if data.get("personality"):
        lines += ["## Voice & stance", data["personality"].strip(), ""]
    beh = (data.get("extensions", {}).get("cof", {}) or {}).get("behavior")
    if beh:
        lines += ["## Habits", *[f"- {b}" for b in beh], ""]
    if psyche.get("values"):
        lines += ["## Values", *[f"- {v}" for v in psyche["values"]], ""]
    if psyche.get("goals"):
        lines += ["## Goals", *[f"- {g.get('text')}" for g in psyche["goals"]], ""]
    if psyche.get("fears"):
        lines += ["## Fears", *[f"- {f.get('text')}" for f in psyche["fears"]], ""]
    if data.get("system_prompt"):
        lines += ["## Boundaries", data["system_prompt"].strip(), ""]
    perms = manifest.get("rights", {}).get("permissions", {})
    if perms.get("aiDisclosure", True):
        lines += ["## Disclosure", "I am a synthetic character. I say so when asked.", ""]
    soul = "\n".join(lines)[:20000]

    avatar = manifest.get("thumbnail") or next((A[i]["path"] for i in (first(r, "appearance", "face") or {}).get("images", []) if i in A and A[i].get("subject") == "head"), "")
    identity = "\n".join([
        f"- Name: {manifest.get('name')}",
        f"- Creature: {manifest.get('morphology', {}).get('species', 'human')}",
        f"- Vibe: {(manifest.get('summary') or '').strip()}",
        f"- Emoji: {manifest.get('extensions', {}).get('emoji', '🙂')}",
        f"- Avatar: {avatar}",
        "",
    ])
    return soul, identity
