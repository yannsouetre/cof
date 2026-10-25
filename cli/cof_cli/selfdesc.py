"""COF.md — the container describes itself to whoever opens it without the specification at hand (an agent, a script,
a person). Written at the root of every .cof by `cof pack` and by the builder; short, versioned, never normative:
the specification wins. Also: `cof memory add`, the write path the note describes."""
from __future__ import annotations

import hashlib
import json
import mimetypes
import re
import shutil
from datetime import datetime, timezone
from pathlib import Path

SELFDESC_PATH = "COF.md"
SELFDESC_VERSION = "1.1"


def self_description(manifest: dict) -> str:
    """The note for this file: what it is, how to read it, the rules, how to add a lived memory."""
    name = manifest.get("name") or "character"
    ids = manifest.get("identities") or {}
    cast = ", ".join(f"`{k}` ({(v or {}).get('name') or k})" for k, v in ids.items()) or f"`{manifest.get('default_identity') or 'id1'}`"
    presets = ", ".join(f"`{k}`" for k in (manifest.get("presets") or {}).keys())
    cats = ", ".join(f"`{c}`" for c in (manifest.get("elements") or {}).keys())
    has_mem = "memories" in (manifest.get("elements") or {})
    perms = (manifest.get("rights") or {}).get("permissions") or {}
    lines = [
        f"# COF.md — how to read this file ({name})",
        "",
        f"This is a **Character Open File** (COF {manifest.get('cof', '1.0')}, a ZIP with `manifest.json` at its root; MIME `application/vnd.cof.character+zip`).",
        "It carries one or more AI characters: their personality, looks, voice, body, past and rights, in one portable container.",
        f"Specification, schemas and tools: https://github.com/yannsouetre/cof — `pip install cof-cli` gives `cof validate`, `cof info`, `cof export`, `cof extract`, `cof memory add`.",
        "This note is a courtesy for readers without the specification; **the specification and `manifest.json` win** whenever they differ.",
        "",
        "## Reading",
        f"- `manifest.json` is the index. Characters: {cast}. Presets (a consistent way to present a character — age, style, language): {presets or 'none'}; `default_preset` says which to use when nobody chooses.",
        f"- Elements by category ({cats or 'none'}): each category has `variants`; a preset's `slots` lists the variants it applies, `alternatives` the ones it offers; `extends` inherits from another preset.",
        "- Every file of the container is declared in `assets` (path, `mediaType`, `sha256`, `license`, `role`); a variant names its files by asset id. Sub-files (`card.json`, `psyche.json`, `profile.json`, `memory.json`) are JSON next to their variant under `elements/<category>/<variant>/`.",
        "- Short texts that are per language are maps keyed by BCP 47 (`{\"fr\": …, \"en\": …}`); pick the preset's personality language, else the identity's `language`, else the first entry.",
        "- `cof export --format agent --preset <id>` turns a preset into `SOUL.md` + `IDENTITY.md` + `MEMORY.md` for a text agent; the ComfyUI nodes read the file directly.",
        "",
        "## Rules you must honour",
        "- **Rights**: `rights.permissions` (and a character's own `identities.<id>.rights`) say what may be done — " + (", ".join(f"`{k}`: {json.dumps(v)}" for k, v in sorted(perms.items())) if perms else "see the manifest") + ". `aiDisclosure` true means: say you are synthetic when asked.",
        "- **Ages**: a preset's age is the lowest age of what it applies (`age`, `age_override`). A preset under 18 shows nothing nude or intimate, ever; `allowSexualUsage` is an opt-in that a host must ask for explicitly, never a default.",
        "- **Real persons** (`fictional: false`) come with a consent record; their likeness, voice and memories never travel to another character or another file.",
        "- **Content flags** (`tags.content`) list what the file holds (`nudity`, `violence`…); `none` means nothing flagged.",
    ]
    if has_mem:
        lines += [
            "- **Memories** (`elements/memories`, COF 1.1 / RFC 0002): nodes `moment` or `period`, each with a `memory.json` (gist per language, when, where, who, feelings, `fidelity`, links). `disclosure: secret` is never told; `guarded` only when it matters; `visibility: personal` nodes are one user's data and never leave this file without their consent; `explicit` nodes show no media to anyone but an adult preset with the opt-in. Readers order by age, else date, else links.",
        ]
    lines += [
        "",
        "## Writing back what the character lives (hosts and agents)",
        "The canon is read-only for tools. What happens at use time is added as **new memory nodes** with `origin: \"lived\"`, and `visibility: \"personal\"` when it concerns one user:",
        "1. Create `elements/memories/<id>/memory.json` — `{\"gist\": {\"<lang>\": \"one paragraph\"}, \"when\": {\"date\": \"YYYY-MM-DD\"}, \"origin\": \"lived\", \"visibility\": \"personal\", \"disclosure\": \"open\", \"fidelity\": \"clear\", \"nature\": [\"experienced\"]}` (ids `ev<n>` for moments, `ep<n>` for periods; never reuse an id).",
        "2. Declare it in `manifest.json` › `elements.memories.variants.<id>`: `{\"kind\": \"moment\", \"label\": \"…\", \"memory\": \"elements/memories/<id>/memory.json\", \"identity\": \"<character>\"}`, and list the id in the `slots.memories` of the presets that may recall it. Media go under the same folder, declared in `assets` with role `memory-media` and their `sha256`.",
        "3. Set `cof` to `\"1.1\"` if it says `\"1.0\"`, then run `cof validate` — or let the tool do all of it: `cof memory add <file.cof> --identity <id> --gist fr=\"…\" --date 2026-10-25 --personal`.",
        "Do not rewrite existing nodes; a changed feeling is a new `lived` node linked `about` the old one. Never add a memory that shows a real person who is not a consenting identity of this file.",
        "",
        f"_Written by cof-cli for COF {SELFDESC_VERSION}; regenerate with `cof pack`. Not part of the character._",
    ]
    return "\n".join(lines) + "\n"


def write_self_description(src: Path, manifest: dict) -> Path:
    p = src / SELFDESC_PATH
    p.write_text(self_description(manifest), "utf-8")
    return p


# ---- cof memory add --------------------------------------------------------------------------------------------

def _next_id(variants: dict, prefix: str) -> str:
    n = 0
    for k in variants:
        m = re.fullmatch(prefix + r"(\d+)", k)
        if m:
            n = max(n, int(m.group(1)))
    return f"{prefix}{n + 1}"


def memory_add(src: Path, *, identity: str | None, kind: str, gists: dict[str, str], label: str | None = None, age: float | None = None,
               date: str | None = None, approx: bool = False, where: str | None = None, who: list[str] | None = None, tags: list[str] | None = None,
               personal: bool = False, origin: str = "lived", disclosure: str = "open", fidelity: str = "clear", salience: int | None = None,
               media: list[Path] | None = None, presets: list[str] | None = None, lang: str | None = None) -> str:
    """Append one lived memory to an unpacked character folder (RFC 0002 § 3, § 5.7); returns the new node id."""
    mpath = src / "manifest.json"
    m = json.loads(mpath.read_text("utf-8"))
    if not gists:
        raise ValueError("a gist is required (--gist lang=text)")
    if kind not in ("moment", "period"):
        raise ValueError("kind must be moment or period")
    ids = m.get("identities") or {}
    iid = identity or m.get("default_identity") or (next(iter(ids)) if ids else None)
    if ids and iid not in ids:
        raise ValueError(f"unknown character {iid!r}; known: {', '.join(ids)}")
    E = m.setdefault("elements", {})
    V = E.setdefault("memories", {}).setdefault("variants", {})
    vid = _next_id(V, "ev" if kind == "moment" else "ep")
    lang = lang or next(iter(gists))
    node: dict = {"gist": dict(gists), "nature": ["experienced"]}
    when: dict = {}
    pt: dict = {}
    if age is not None:
        pt["age"] = {"value": age, "unit": "years"}
    if date:
        pt["date"] = date
    if approx:
        pt["approx"] = True
    if kind == "period":
        if pt:
            when["from"] = pt
    else:
        when = pt
    if when:
        node["when"] = when
    if where:
        node["where"] = {"label": {lang: where}}
    if who:
        node["who"] = [{"label": {lang: w}} for w in who]
    if salience is not None:
        node["salience"] = int(salience)
    node["fidelity"] = fidelity
    node["origin"] = origin
    node["visibility"] = "personal" if personal else "canon"
    node["disclosure"] = disclosure
    if tags:
        import unicodedata
        slug = lambda t: re.sub(r"[^a-z0-9:-]+", "-", unicodedata.normalize("NFKD", t).encode("ascii", "ignore").decode().lower()).strip("-")
        node["tags"] = [x for x in (slug(t) for t in tags) if x]
    d = src / "elements" / "memories" / vid
    d.mkdir(parents=True, exist_ok=True)
    (d / "memory.json").write_text(json.dumps(node, ensure_ascii=False, indent=2) + "\n", "utf-8")
    var: dict = {"kind": kind, "label": label or next(iter(gists.values()))[:60], "memory": f"elements/memories/{vid}/memory.json"}
    if len(ids) > 1 or (ids and any(v.get("identity") for e in E.values() for v in (e.get("variants") or {}).values())):
        var["identity"] = iid
    media_ids = []
    for f in media or []:
        f = Path(f)
        if not f.is_file():
            raise ValueError(f"media not found: {f}")
        dest = d / f.name
        shutil.copy(f, dest)
        data = dest.read_bytes()
        aid = f"a-mem-{vid}-{re.sub(r'[^a-z0-9]+', '-', f.stem.lower()).strip('-') or 'media'}"
        mt = mimetypes.guess_type(f.name)[0] or "application/octet-stream"
        asset = {"id": aid, "path": f"elements/memories/{vid}/{f.name}", "role": "memory-media", "mediaType": mt, "bytes": len(data),
                 "sha256": hashlib.sha256(data).hexdigest(), "license": "LicenseRef-Personal", "digitalSourceType": "digitalCapture"}
        if mt.startswith("text/"):
            asset["language"] = lang
        m.setdefault("assets", []).append(asset)
        media_ids.append(aid)
    if media_ids:
        var["media"] = media_ids
    V[vid] = var
    P = m.get("presets") or {}
    targets = presets or [p for p, q in P.items() if (q.get("identity") or m.get("default_identity") or iid) == iid]
    if not targets and P:
        targets = [m.get("default_preset") or next(iter(P))]
    for pid in targets:
        if pid not in P:
            raise ValueError(f"unknown preset {pid!r}")
        sl = P[pid].setdefault("slots", {})
        if "memories" not in sl:                                  # inherited through extends: copy the effective list before adding
            from .model import resolve_preset_slots
            sl["memories"] = list(resolve_preset_slots(m, pid).get("memories") or [])
        if vid not in sl["memories"]:
            sl["memories"].append(vid)
    if str(m.get("cof", "1.0")) == "1.0":
        m["cof"] = "1.1"
    cov = m.setdefault("coverage", {})
    if "memories" not in (cov.get("elements") or []):
        cov["elements"] = sorted(set(cov.get("elements") or []) | {"memories"})
    tags_ = m.setdefault("tags", {})
    auto = tags_.setdefault("auto", [])
    if "has-memories" not in auto:
        auto.append("has-memories")
    m.setdefault("provenance", {})["modified"] = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    mpath.write_text(json.dumps(m, ensure_ascii=False, indent=2) + "\n", "utf-8")
    return vid
