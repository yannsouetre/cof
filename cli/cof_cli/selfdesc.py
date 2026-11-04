"""COF.md — the container describes itself to whoever opens it without the specification at hand (an agent, a script,
a person). Written at the root of every .cof by `cof pack` and by the builder; short, versioned, never normative:
the specification wins. Also: `cof memory add` and `cof psyche add`, the write paths the note describes."""
from __future__ import annotations

import hashlib
import json
import mimetypes
import re
import shutil
from datetime import datetime, timezone
from pathlib import Path

SELFDESC_PATH = "COF.md"
SELFDESC_VERSION = "1.2"


# the IPTC Digital Source Type of a file the user or host gives (the long form, a URI, as in the schema and the examples)
DIGITAL_CAPTURE = "http://cv.iptc.org/newscodes/digitalsourcetype/digitalCapture"
# fixed before mimetypes, whose answer depends on the Python version and, on Windows, on the registry (a .md could come
# out as application/octet-stream and lose its text status and its language)
_MEDIA_TYPES = {".md": "text/markdown", ".markdown": "text/markdown", ".txt": "text/plain", ".webp": "image/webp"}


def media_type(name: str) -> str:
    """The media type of a file name: the fixed table first, then mimetypes, else application/octet-stream."""
    return _MEDIA_TYPES.get(Path(name).suffix.lower()) or mimetypes.guess_type(name)[0] or "application/octet-stream"


def self_description(manifest: dict) -> str:
    """The note for this file: what it is, how to read it, the rules, how to add a lived memory."""
    name = manifest.get("name") or "character"
    ids = manifest.get("identities") or {}
    cast = ", ".join(f"`{k}` ({(v or {}).get('name') or k})" for k, v in ids.items()) or f"`{manifest.get('default_identity') or 'id1'}`"
    presets = ", ".join(f"`{k}`" for k in (manifest.get("presets") or {}).keys())
    cats = ", ".join(f"`{c}`" for c in (manifest.get("elements") or {}).keys())
    has_mem = "memories" in (manifest.get("elements") or {})
    has_psy = "psyche" in (manifest.get("elements") or {})
    perms = (manifest.get("rights") or {}).get("permissions") or {}
    lines = [
        f"# COF.md — how to read this file ({name})",
        "",
        f"This is a **Character Open File** (COF {manifest.get('cof', '1.0')}, a ZIP with `manifest.json` at its root; MIME `application/vnd.cof.character+zip`).",
        "It carries one or more AI characters: their personality, looks, voice, body, past and rights, in one portable container.",
        f"Specification, schemas and tools: https://github.com/yannsouetre/cof — `pip install cof-cli` gives `cof validate`, `cof info`, `cof export`, `cof extract`, `cof memory add`, `cof psyche add`.",
        "This note is a courtesy for readers without the specification; **the specification and `manifest.json` win** whenever they differ.",
        "",
        "## Reading",
        f"- `manifest.json` is the index. Characters: {cast}. Presets (a consistent way to present a character — age, style, language): {presets or 'none'}; `default_preset` says which to use when nobody chooses.",
        f"- Elements by category ({cats or 'none'}): each category has `variants`; a preset's `slots` lists the variants it applies, `alternatives` the ones it offers; `extends` inherits from another preset.",
        "- Every file of the container is declared in `assets` (path, `mediaType`, `sha256`, `license`, `role`); a variant names its files by asset id. Sub-files (`card.json`, `psyche.json`, `profile.json`, `memory.json`, `psyche-node.json`) are JSON next to their variant under `elements/<category>/<variant>/`.",
        "- Short texts that are per language are maps keyed by BCP 47 (`{\"fr\": …, \"en\": …}`); pick the preset's personality language, else the identity's `language`, else the first entry.",
        "- `cof export --format agent --preset <id>` turns a preset into `SOUL.md` + `IDENTITY.md` + `MEMORY.md` for a text agent; the ComfyUI nodes read the file directly.",
        "",
        "## Rules you must honour",
        "- **Rights**: `rights.permissions` (and a character's own `identities.<id>.rights`) say what may be done — " + (", ".join(f"`{k}`: {json.dumps(v)}" for k, v in sorted(perms.items())) if perms else "see the manifest") + ". `aiDisclosure` true means: say you are synthetic when asked.",
        "- **Ages**: a preset's age is the lowest age of what it applies (`age`, `age_override`). A preset under 18 shows nothing nude or intimate, ever; `allowSexualUsage` is an opt-in that a host must ask for explicitly, never a default.",
        "- **Real persons** (`fictional: false`) come with a consent record; their likeness, voice and memories never travel to another character or another file.",
        "- **Content flags** (`tags.content`) list what the file holds (`nudity`, `violence`…); `none` means nothing flagged.",
    ]
    try:
        v12 = tuple(int(x) for x in str(manifest.get("cof", "1.0")).split(".")[:2]) >= (1, 2)
    except ValueError:
        v12 = False
    if has_mem:
        lines += [
            "- **Memories** (`elements/memories`, COF 1.1 / RFC 0002): nodes `moment` or `period`, each with a `memory.json` (gist per language, when, where, who, " + ("what — the objects, an accessory element and/or a name (1.2, RFC 0005) —, " if v12 else "") + "feelings, `fidelity`, links). `disclosure: secret` is never told; `guarded` only when it matters; `visibility: personal` nodes are one user's data and never leave this file without their consent; `explicit` nodes show no media to anyone but an adult preset with the opt-in. Readers order by age, else date, else links.",
        ]
    if has_psy:
        lines += [
            "- **Psyche** (`elements/psyche`, COF 1.2 / RFC 0004): what the character is inside and why, as a graph of short nodes — `value`, `belief` (a lie it tells itself is `false_but_held`), `want`, `need`, `fear`, `wound`, `stance` (toward a character, a node, the user or a label), `taste`, `habit`, `contradiction` (owns a tension between two nodes), `rule` (a boundary kept whatever the pressure) — each in `psyche-node.json` (gist per language, `strength` 0–100, `stability` core / settled / shifting / fragile, `since` and `until` (when it appeared, when it was let go), `aware` (yes / partly / no: whether the character knows this about itself — a `no` node is acted on, never stated), `valence` on a stance or a taste (−100 hostile / hates … +100 warm / loves; the affinity toward the user is a stance `about: user`), links `because` / `about` / `supports` / `conflicts` to memories and nodes, and the people, places and objects it is tied to — `who`, `where`, `what`, RFC 0005: a character of the file, an environment, an accessory, or a name). A node may be illustrated: `media` on its variant lists images only (an asset of another type is an error), the first replaces the kind's icon, the others are references, at most 3 (RFC 0004 § 3 decies); an image that shows the character makes the variant carry `age`, as a memory's media do. Presets pick nodes in `slots.psyche`. `disclosure: secret` nodes are context, never quoted; `personal` nodes are one user's data. **Declared risk**: a node's `risk` is `inappropriate` (unsuitable for some audiences) or `dangerous` (would make the character harmful if it acted on it), mirrored at file level by `tags.content` `psyche-inappropriate` / `psyche-dangerous` — a host that gives the character tools or data access MUST NOT load `dangerous` nodes (`cof export --format agent` leaves them out unless `--keep-dangerous`; `cof extract --no-risk` drops both levels); a fiction host may load everything and should say so. `cof export --format agent` renders the nodes as the « Who she is » section of `SOUL.md`.",
        ]
    lines += [
        "",
        "## Writing back what the character lives (hosts and agents)",
        "The canon is read-only for tools. What happens at use time is added as **new memory nodes** with `origin: \"lived\"`, and `visibility: \"personal\"` when it concerns one user:",
        "1. Create `elements/memories/<id>/memory.json` — `{\"gist\": {\"<lang>\": \"one paragraph\"}, \"when\": {\"date\": \"YYYY-MM-DD\"}, \"origin\": \"lived\", \"visibility\": \"personal\", \"disclosure\": \"open\", \"fidelity\": \"clear\", \"nature\": [\"experienced\"]}` (ids `ev<n>` for moments, `ep<n>` for periods; never reuse an id).",
        "2. Declare it in `manifest.json` › `elements.memories.variants.<id>`: `{\"kind\": \"moment\", \"label\": \"…\", \"memory\": \"elements/memories/<id>/memory.json\", \"identity\": \"<character>\"}`, and list the id in the `slots.memories` of the presets that may recall it. Media go under the same folder, declared in `assets` with role `memory-media` and their `sha256`; say who is in them — `who: [{\"identity\": \"self\", \"shown\": true}]` with the character's `age` on the variant, `{\"label\": {…}, \"shown\": true, \"real\": true}` for the user — a validator warns on image media with nobody declared shown.",
        "3. Set `cof` to `\"1.1\"` if it says `\"1.0\"`, then run `cof validate` — or let the tool do all of it: `cof memory add <file.cof> --identity <id> --gist fr=\"…\" --date 2026-10-25 --personal` (add `--self-shown --age 29` when the character is in the media, `--who \"Sam|shown|34|real\"` for someone else).",
        "Do not rewrite existing nodes; a changed feeling is a new `lived` node linked `about` the old one. Never add a memory that shows a real person who is not a consenting identity of this file.",
        "What the character came to think or want at use time is a **lived psyche node** (COF 1.2): `cof psyche add <file.cof> --kind stance --gist fr=\"…\" --about user --strength 60 --stability shifting --link because=memories/ev3 --since-date 2026-10-25` writes `elements/psyche/<id>/psyche-node.json` with `origin: \"lived\"`, `visibility: \"personal\"` (add `--canon` for a node that belongs to the character for everyone) and a first `revisions` entry, declares it and lists it in the presets. A `core` node is never changed at use time; a `settled` one only through a lived node that declares it; `shifting` with evidence, the previous value kept in `revisions`; `fragile` within one conversation. A stance's warmth toward the user is `--valence N` (−100 … +100); `--aware partly|no` marks what the character only half knows or does not know about itself; `--until-age` / `--until-date` close a node the character no longer holds.",
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


def axis_entry(spec: str, lang: str, ref_key: str, words: tuple[str, ...] = (), opt: str = "") -> dict:
    """One person, place or object entry from the command line (RFC 0005 § 2.1), the `--who` syntax of `memory add`:
    parts separated by `|` — `<ref_key>=<reference>` (identity=martien, environment=appearance/e1, item=appearance/x1),
    the allowed `words` (shown, real) as flags, anything else the free name. "le carnet", "item=appearance/x1|shown",
    "ma guitare|item=appearance/x1"."""
    e: dict = {}
    for x in (p.strip() for p in str(spec).split("|")):
        if not x:
            continue
        if x.startswith(ref_key + "="):
            e[ref_key] = x[len(ref_key) + 1:].strip()
        elif x.lower() in words:
            e[x.lower()] = True
        elif "label" not in e:
            e["label"] = {lang: x}
        else:
            raise ValueError(f"{opt} {spec!r}: two names ({x!r}); use {ref_key}=<ref> for the reference" + (f", or the words {', '.join(words)}" if words else ""))
    if not (e.get(ref_key) or e.get("label")):
        raise ValueError(f"{opt} {spec!r}: give a name or {ref_key}=<ref>")
    return {k: e[k] for k in (ref_key, "label", *words) if k in e}


def memory_add(src: Path, *, identity: str | None, kind: str, gists: dict[str, str], label: str | None = None, age: float | None = None,
               date: str | None = None, approx: bool = False, where: str | None = None, who: list[str] | None = None, tags: list[str] | None = None,
               personal: bool = False, origin: str = "lived", disclosure: str = "open", fidelity: str = "clear", salience: int | None = None,
               media: list[Path] | None = None, presets: list[str] | None = None, lang: str | None = None, self_shown: bool = False,
               what: list[str] | None = None) -> str:
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
    W = []
    if self_shown:
        if age is None:
            raise ValueError("--self-shown needs --age: a media showing the character carries the character's age (RFC 0002 § 5)")
        W.append({"identity": "self", "shown": True})
    for w in who or []:                                    # "label|shown|34|real" — the builder's 'Other people' line
        parts = [x.strip() for x in str(w).split("|")]
        e: dict = {"label": {lang: parts[0]}}
        for x in parts[1:]:
            if x.lower() == "shown":
                e["shown"] = True
            elif x.lower() == "real":
                e["real"] = True
            elif re.fullmatch(r"\d+(\.\d+)?", x):
                e["age"] = {"value": float(x) if "." in x else int(x), "unit": "years"}
            elif x:
                raise ValueError(f"--who {w!r}: unknown word {x!r} (use shown, real or an age)")
        W.append(e)
    if W:
        node["who"] = W
    O = [axis_entry(x, lang, "item", ("shown",), "--what") for x in what or []]    # objects (1.2, RFC 0005 § 2.2)
    if O:
        node["what"] = O
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
    if self_shown:
        var["age"] = {"value": age, "unit": "years"}
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
        mt = media_type(f.name)
        asset = {"id": aid, "path": f"elements/memories/{vid}/{f.name}", "role": "memory-media", "mediaType": mt, "bytes": len(data),
                 "sha256": hashlib.sha256(data).hexdigest(), "license": "LicenseRef-Personal", "digitalSourceType": DIGITAL_CAPTURE}
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
    if O and str(m.get("cof")) == "1.1":                         # objects are a 1.2 field: the lowest minor that defines what the file uses
        m["cof"] = "1.2"
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


# ---- cof psyche add (RFC 0004) ------------------------------------------------------------------------------------

def psyche_add(src: Path, *, identity: str | None, kind: str, gists: dict[str, str], label: str | None = None, strength: int | None = None,
               stability: str | None = None, since_age: float | None = None, since_date: str | None = None, approx: bool = False,
               links: list[str] | None = None, about: str | None = None, lie: bool = False, tags: list[str] | None = None, risk: str = "none",
               origin: str = "lived", personal: bool = True, disclosure: str = "open", presets: list[str] | None = None,
               who: list[str] | None = None, where: list[str] | None = None, what: list[str] | None = None,
               aware: str | None = None, valence: int | None = None, until_age: float | None = None, until_date: str | None = None,
               images: list[Path] | None = None, self_shown: bool = False, image_age: float | None = None) -> str:
    """Append one psyche node to an unpacked character folder — the host's write path (RFC 0004 § 3 bis, § 3 ter):
    `origin: lived` and `visibility: personal` by default like a memory lived with one user, a first `revisions` entry on a
    lived node, the node listed by the character's presets, `tags.content` following `risk`. Returns the new node id."""
    from .psyche import ID_PREFIX, KINDS, STABILITIES, RISK_TAGS
    mpath = src / "manifest.json"
    m = json.loads(mpath.read_text("utf-8"))
    if not gists:
        raise ValueError("a gist is required (--gist lang=text)")
    if kind not in KINDS:
        raise ValueError(f"kind must be one of {', '.join(KINDS)}")
    if stability is not None and stability not in STABILITIES:
        raise ValueError(f"stability must be one of {', '.join(STABILITIES)}")
    if strength is not None and not (0 <= int(strength) <= 100):
        raise ValueError("--strength is an integer between 0 and 100")
    if lie and kind != "belief":
        raise ValueError("--lie (false_but_held) is for a belief only")
    if about is not None and kind != "stance":
        raise ValueError("--about is for a stance only; other kinds say what they bear on with --link about=<ref>")
    if risk not in RISK_TAGS and risk != "none":
        raise ValueError("risk must be none, inappropriate or dangerous")
    if aware is not None and aware not in ("yes", "partly", "no"):                    # § 3 nonies
        raise ValueError("--aware is yes, partly or no")
    if valence is not None and kind not in ("stance", "taste"):
        raise ValueError(f"--valence is for a stance or a taste only (which way the feeling leans); a {kind} weighs through --strength")
    if valence is not None and not (-100 <= int(valence) <= 100):
        raise ValueError("--valence is an integer between -100 and 100")
    ids = m.get("identities") or {}
    iid = identity or m.get("default_identity") or (next(iter(ids)) if ids else None)
    if ids and iid not in ids:
        raise ValueError(f"unknown character {iid!r}; known: {', '.join(ids)}")
    E = m.setdefault("elements", {})
    V = E.setdefault("psyche", {}).setdefault("variants", {})
    vid = _next_id(V, ID_PREFIX[kind])
    lang = next(iter(gists))
    node: dict = {"gist": dict(gists)}
    if strength is not None:
        node["strength"] = int(strength)
    if stability:
        node["stability"] = stability
    if risk != "none":
        node["risk"] = risk
    for key, age_, date_ in (("since", since_age, since_date), ("until", until_age, until_date)):
        pt: dict = {}
        if age_ is not None:
            pt["age"] = {"value": age_, "unit": "years"}
        if date_:
            pt["date"] = date_
        if approx and pt:
            pt["approx"] = True
        if pt:
            node[key] = pt
    if aware is not None and aware != "yes":                            # the default is not written
        node["aware"] = aware
    if valence is not None:
        node["valence"] = int(valence)
    if lie:
        node["false_but_held"] = True
    if about is not None:                                              # user | identity=<id> | node=<category>/<id> | label=<text> | <text>
        a = str(about).strip()
        if a.lower() == "user":
            node["about"] = {"user": True}
        elif a.startswith("identity="):
            node["about"] = {"identity": a[len("identity="):].strip()}
        elif a.startswith("node="):
            node["about"] = {"node": a[len("node="):].strip()}
        else:
            node["about"] = {"label": {lang: a[len("label="):].strip() if a.startswith("label=") else a}}
    L = []
    for ln in links or []:                                             # "because=memories/ev3", "supports=psyche/val1"
        ty, _, to = str(ln).partition("=")
        ty, to = ty.strip(), to.strip()
        if ty not in ("because", "about", "supports", "conflicts") or "/" not in to:
            raise ValueError(f"--link {ln!r}: expected TYPE=<category>/<id> with TYPE because, about, supports or conflicts")
        if to.startswith("identities/"):
            raise ValueError(f"--link {ln!r}: links target memories and psyche nodes — a person goes in --who identity={to.partition('/')[2]} (RFC 0005)")
        L.append({"to": to, "type": ty})
    if self_shown and image_age is None:
        raise ValueError("--self-shown needs --age: an image showing the character carries the character's age (RFC 0004 § 3 decies)")
    if image_age is not None and not (0 <= image_age <= 200):
        raise ValueError("--age is a number of years between 0 and 200")
    for key, specs, ref_key, words in (("who", who, "identity", ("real", "shown")), ("where", where, "environment", ()), ("what", what, "item", ())):
        E_ = []
        for x in specs or []:                                           # people, places, objects (RFC 0005 § 2.3); a person's image age: a bare number, "Léo|shown|34"
            parts = [q.strip() for q in str(x).split("|")]
            num = [q for q in parts if re.fullmatch(r"\d+(\.\d+)?", q)] if key == "who" else []
            e_ = axis_entry("|".join(q for q in parts if q not in num), lang, ref_key, words, f"--{key}")
            if num:
                e_["age"] = {"value": float(num[0]) if "." in num[0] else int(num[0]), "unit": "years"}
            E_.append(e_)
        if self_shown:
            if key == "who":
                E_.insert(0, {"identity": "self", "shown": True})
        if E_:
            node[key] = E_
    if L:
        node["links"] = L
    node["origin"] = origin
    node["visibility"] = "personal" if personal else "canon"
    node["disclosure"] = disclosure
    if tags:
        import unicodedata
        slug = lambda t: re.sub(r"[^a-z0-9:-]+", "-", unicodedata.normalize("NFKD", t).encode("ascii", "ignore").decode().lower()).strip("-")
        node["tags"] = [x for x in (slug(t) for t in tags) if x]
    now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    if origin == "lived":                                              # the first revision records what was written, by whom
        rev = {"date": now, "gist": dict(gists), "by": "cof-cli psyche add"}
        if strength is not None:
            rev["strength"] = int(strength)
        if stability:
            rev["stability"] = stability
        if valence is not None:
            rev["valence"] = int(valence)
        if "aware" in node:
            rev["aware"] = node["aware"]
        node["revisions"] = [rev]
    d = src / "elements" / "psyche" / vid
    d.mkdir(parents=True, exist_ok=True)
    (d / "psyche-node.json").write_text(json.dumps(node, ensure_ascii=False, indent=2) + "\n", "utf-8")
    var: dict = {"kind": kind, "label": label or next(iter(gists.values()))[:60], "node": f"elements/psyche/{vid}/psyche-node.json"}
    if iid and (len(ids) > 1 or (ids and any(v.get("identity") for e in E.values() for v in (e.get("variants") or {}).values()))):
        var["identity"] = iid
    if strength is not None:
        var["strength"] = int(strength)
    media_ids = []
    for f in images or []:                                             # the illustrations of the node (§ 3 decies): images only, the first is the picture
        f = Path(f)
        if not f.is_file():
            raise ValueError(f"image not found: {f}")
        mt = media_type(f.name)
        if not mt.startswith("image/"):
            raise ValueError(f"--image {f.name}: {mt} is not an image — a psyche node is illustrated by images only (a sound, a video or a text belongs to a memory)")
        dest = d / f.name
        shutil.copy(f, dest)
        data = dest.read_bytes()
        aid = f"a-psy-{vid}-{re.sub(r'[^a-z0-9]+', '-', f.stem.lower()).strip('-') or 'image'}"
        m.setdefault("assets", []).append({"id": aid, "path": f"elements/psyche/{vid}/{f.name}", "role": "psyche-media", "mediaType": mt, "bytes": len(data),
                                           "sha256": hashlib.sha256(data).hexdigest(), "license": "LicenseRef-Personal", "digitalSourceType": DIGITAL_CAPTURE})
        media_ids.append(aid)
    if media_ids:
        var["media"] = media_ids
        if image_age is not None:
            var["age"] = {"value": image_age, "unit": "years"}
    elif self_shown or image_age is not None:
        raise ValueError("--self-shown / --age go with --image: they describe what an image shows")
    V[vid] = var
    P = m.get("presets") or {}
    targets = presets or [p for p, q in P.items() if (q.get("identity") or m.get("default_identity") or iid) == iid]
    if not targets and P:
        targets = [m.get("default_preset") or next(iter(P))]
    for pid in targets:
        if pid not in P:
            raise ValueError(f"unknown preset {pid!r}")
        sl = P[pid].setdefault("slots", {})
        if "psyche" not in sl:                                        # inherited through extends: copy the effective list before adding
            from .model import resolve_preset_slots
            sl["psyche"] = list(resolve_preset_slots(m, pid).get("psyche") or [])
        if vid not in sl["psyche"]:
            sl["psyche"].append(vid)
    try:
        if tuple(int(x) for x in str(m.get("cof", "1.0")).split(".")[:2]) < (1, 2):
            m["cof"] = "1.2"
    except ValueError:
        m["cof"] = "1.2"
    cov = m.setdefault("coverage", {})
    if "psyche" not in (cov.get("elements") or []):
        cov["elements"] = sorted(set(cov.get("elements") or []) | {"psyche"})
    tags_ = m.setdefault("tags", {})
    auto = tags_.setdefault("auto", [])
    if "has-psyche" not in auto:
        auto.append("has-psyche")
    if risk != "none":                                                 # § 3 septies: the file-level tag follows the node
        content = [t for t in (tags_.get("content") or []) if t != "none"]
        if RISK_TAGS[risk] not in content:
            content.append(RISK_TAGS[risk])
        tags_["content"] = content
    m.setdefault("provenance", {})["modified"] = now
    mpath.write_text(json.dumps(m, ensure_ascii=False, indent=2) + "\n", "utf-8")
    return vid
