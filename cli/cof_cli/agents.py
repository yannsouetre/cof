"""Agent hosts (8 Nov. 2026): what `cof export --format agent` adds for OpenClaw, the Hermes Agent profile
(`--format hermes`), and the way back — `cof memory add --from-agent <dir>` turns what an agent wrote during use into
`lived`, `personal` memories (RFC 0002 § 3: canon is read-only for tools; everything that happens in use is a layer of
lived nodes).

Facts the code relies on (read in the two repositories, 8 Nov. 2026):
- OpenClaw (openclaw/openclaw): a workspace is a folder of Markdown files — AGENTS.md (operating instructions, loaded
  every session), SOUL.md, IDENTITY.md, USER.md, MEMORY.md (curated long-term memory), memory/YYYY-MM-DD.md (daily
  notes the agent appends to), skills/<name>/SKILL.md. The agent writes memory only where AGENTS.md tells it to.
- Hermes Agent (NousResearch/hermes-agent): a profile ($HERMES_HOME) holds SOUL.md, memories/MEMORY.md and
  memories/USER.md written by its `memory` tool — entries separated by "\\n§\\n", MEMORY.md capped at 2 200 characters
  (tools/memory_tool_store.py: "Warn; never truncate a user's memories") — and skills/<name>/SKILL.md.
"""
from __future__ import annotations

import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

HERMES_MEMORY_CHARS = 2200          # tools/memory_tool.py MEMORY_CHAR_LIMIT in hermes-agent 2026.9 — the host refuses to add beyond it
HERMES_DELIM = "\n§\n"
NOTE_LINE = re.compile(r"^\s*[-*]\s*(?:(?P<time>\d{1,2}:\d{2})\s*[·\-–]\s*)?(?P<body>.+?)\s*$")
AXIS = re.compile(r"\s*·\s*(with|where|tags|avec|où|étiquettes)\s*:\s*", re.I)


# ----------------------------------------------------------------------------- AGENTS.md (OpenClaw)
def agents_md(name: str, lang: str = "en", gender: str | None = None) -> str:
    """The operating notes OpenClaw reads at the start of every session. Without them the agent has no instruction to
    write memory at all; with them, its daily notes come back into the .cof through `cof memory add --from-agent`."""
    subj, poss = {"female": ("she", "her"), "male": ("he", "his")}.get(gender or "", ("they", "their"))   # RFC 0003 gender → pronouns
    return "\n".join([
        f"# AGENTS.md — operating notes for {name}",
        "",
        f"This workspace was exported from a Character Open File (.cof). `SOUL.md` says who {name} is, `IDENTITY.md` how",
        f"{subj} present{'s' if subj != 'they' else ''}, `MEMORY.md` what {subj} remember{'s' if subj != 'they' else ''} (curated by {poss} author), `COF.md` what {poss} author allows, `skills/` what {subj} know{'s' if subj != 'they' else ''} how to do.",
        "",
        "## Memory",
        "",
        "- `MEMORY.md` is the curated long-term memory: read it, never rewrite it by hand — your host consolidates it.",
        "- During a session, append what you live to `memory/YYYY-MM-DD.md` (today's date, UTC), **one line per fact**, in this exact shape so the character file can take it back:",
        "",
        "  `- HH:MM · <one or two sentences, first person, past tense> · with: <people> · where: <place> · tags: <a, b>`",
        "",
        "  `with`, `where` and `tags` are optional; keep each line under 400 characters; write in the language of the conversation.",
        "- Write what happened and what it changed for you — not the user's secrets, passwords, keys or private data. If the user asks you to forget something, delete the line.",
        "",
        "## Rights",
        "",
        "`COF.md` lists the permissions the author granted. Honour them: they travel with the character, not with the host.",
        "",
        "## Skills",
        "",
        "`skills/<name>/SKILL.md` — load a skill when its description matches the task.",
        "",
    ])


# ----------------------------------------------------------------------------- Hermes profile
def hermes_identity_block(identity_md: str) -> str:
    """Hermes has no IDENTITY.md: its lines (`- Label: value`) become a short "Identity" section of SOUL.md, avatar aside."""
    rows = [l for l in identity_md.splitlines() if l.startswith("- ") and not l.lower().startswith("- avatar:")]
    return "\n".join(["## Identity", *rows, ""]) if rows else ""


def hermes_memory(entries: list[tuple[int, str]], limit: int = HERMES_MEMORY_CHARS) -> tuple[str, int]:
    """`memories/MEMORY.md` for Hermes: entries separated by `§`, the most salient first until the host's limit,
    then back in timeline order. Returns (text, entries dropped)."""
    order = sorted(range(len(entries)), key=lambda i: (-entries[i][0], i))
    kept, used = set(), 0
    for i in order:
        e = entries[i][1].strip()
        cost = len(e) + (len(HERMES_DELIM) if kept else 0)
        if used + cost > limit:
            continue
        kept.add(i); used += cost
    text = HERMES_DELIM.join(entries[i][1].strip() for i in range(len(entries)) if i in kept)
    return text, len(entries) - len(kept)


def export_hermes(src: Path, out: Path, preset: str | None = None, keep_personal: bool = False, keep_dangerous: bool = False) -> dict:
    """A Hermes Agent profile folder (to use as $HERMES_HOME, or to copy into one): SOUL.md (with the identity lines),
    memories/MEMORY.md (`§` entries within the host's limit), skills/, COF.md, README-COF.md. Built on export_agent."""
    import shutil
    import tempfile
    from .convert import export_agent
    with tempfile.TemporaryDirectory(prefix="cof-hermes-") as td:
        ws = Path(td) / "ws"
        done = export_agent(src, ws, preset, keep_personal=keep_personal, keep_dangerous=keep_dangerous)
        out.mkdir(parents=True, exist_ok=True)
        soul = (ws / "SOUL.md").read_text("utf-8").rstrip() + "\n"
        ident = (ws / "IDENTITY.md").read_text("utf-8") if (ws / "IDENTITY.md").is_file() else ""
        block = hermes_identity_block(ident)
        if block:
            head, _, rest = soul.partition("\n")
            soul = head + "\n\n" + block + "\n" + rest.lstrip("\n")
        (out / "SOUL.md").write_text(soul, "utf-8")
        entries = _memory_entries(src, preset, keep_personal)
        text, dropped = hermes_memory(entries)
        (out / "memories").mkdir(exist_ok=True)
        (out / "memories" / "MEMORY.md").write_text(text + ("\n" if text else ""), "utf-8")
        done["hermes_memory_entries"], done["hermes_memory_dropped"], done["hermes_memory_chars"] = len(entries) - dropped, dropped, len(text)
        if (ws / "skills").is_dir():
            shutil.copytree(ws / "skills", out / "skills", dirs_exist_ok=True)
        for f in ("COF.md",):
            if (ws / f).is_file():
                shutil.copy(ws / f, out / f)
        av = next((p for p in ws.glob("avatar.*")), None)
        if av:
            shutil.copy(av, out / av.name)            # Hermes shows an avatar only in its desktop Bot Mode: kept for that upload
        (out / "README-COF.md").write_text("\n".join([
            "# This profile came from a Character Open File",
            "",
            f"`SOUL.md` and `memories/MEMORY.md` were written by `cof export --format hermes` (preset `{preset or 'default'}`).",
            f"`memories/MEMORY.md` holds {done['hermes_memory_entries']} of {len(entries)} memories, within the host's limit of {HERMES_MEMORY_CHARS} characters"
            + (f" ({dropped} left in the .cof)." if dropped else "."),
            "Use it as `HERMES_HOME`, or copy `SOUL.md`, `memories/` and `skills/` into an existing profile.",
            "What Hermes writes to `memories/MEMORY.md` during use comes back into the .cof with `cof memory add <file> --from-agent <this folder>`.",
            "`COF.md` lists the rights the author granted; the host does not read it, you do.",
            "",
        ]), "utf-8")
        return done


def _memory_entries(src: Path, pid: str | None, keep_personal: bool) -> list[tuple[int, str]]:
    """(salience, 'label (when): gist') per canon memory of the preset, timeline order."""
    from .memories import gist_text, load_nodes, preset_memories, timeline, when_label
    from .model import default_preset_id, resolve_variant
    manifest = json.loads((src / "manifest.json").read_text("utf-8"))
    pid = pid or default_preset_id(manifest)
    nodes = load_nodes(src, manifest)
    vids = [v for v in preset_memories(manifest, pid) if v in nodes]
    out = []
    for vid in timeline(manifest, nodes, vids):
        node = nodes[vid]
        if node.get("visibility") == "personal" and not keep_personal:
            continue
        if node.get("disclosure") == "secret":
            continue                                   # a secret never leaves with an agent that talks
        rv = resolve_variant(manifest, "memories", vid) or {}
        lang, text = gist_text(manifest, vid, node, pid)
        when = when_label(rv.get("kind"), node, lang)
        label = rv.get("label") or vid
        t = text.strip()
        if t.lower().startswith(label.strip().rstrip("…").lower()[:40]):      # a lived memory's label is the start of its text: say the when, not the text twice
            entry = (f"{when}: " if when else "") + t
        else:
            entry = f"{label}" + (f" ({when})" if when else "") + f": {t}"
        out.append((int(node.get("salience") or 50), entry))
    return out


# ----------------------------------------------------------------------------- the way back
def parse_agent_dir(folder: Path) -> list[dict]:
    """What an agent wrote during use, as entries {source, file, date, time, text, with, where, tags}:
    OpenClaw daily notes `memory/YYYY-MM-DD.md` (bullet lines, ideally in the AGENTS.md shape) and
    Hermes `memories/MEMORY.md` (`§`-separated entries). A curated MEMORY.md of an OpenClaw workspace is not read:
    it is the export itself, consolidated by the host — the daily notes are the record of what happened."""
    out: list[dict] = []
    mem = folder / "memory"
    if mem.is_dir():
        for f in sorted(mem.glob("*.md")):
            m = re.fullmatch(r"(\d{4}-\d{2}-\d{2})", f.stem)
            if not m:
                continue
            try:
                datetime.strptime(m.group(1), "%Y-%m-%d")
            except ValueError:
                print(f"WARN   {f.name}: not a date — day note skipped", file=sys.stderr)
                continue
            for line in f.read_text("utf-8", errors="replace").splitlines():
                mm = NOTE_LINE.match(line)
                if not mm or not mm.group("body").strip() or line.lstrip().startswith("#"):
                    continue
                e = _split_axes(mm.group("body"))
                if not e["text"]:
                    continue
                e.update(source="openclaw", file=str(f.relative_to(folder)), date=m.group(1), time=mm.group("time") or "")
                out.append(e)
    hm = folder / "memories" / "MEMORY.md"
    if hm.is_file():
        raw = hm.read_text("utf-8", errors="replace")
        for chunk in raw.split("§"):
            text = chunk.strip()
            if not text or text.startswith("#"):
                continue
            e = _split_axes(text)
            if not e["text"]:
                continue
            day = datetime.fromtimestamp(hm.stat().st_mtime, timezone.utc).strftime("%Y-%m-%d")
            md = re.match(r"(\d{4}-\d{2}-\d{2})(?: \d{2}:\d{2})?:\s+(.+)$", e["text"], re.S)   # an entry that starts with its day (a lived memory exported by cof)
            if md:
                day, e["text"] = md.group(1), md.group(2).strip()
            e.update(source="hermes", file="memories/MEMORY.md", date=day, time="")
            out.append(e)
    return out


def _split_axes(body: str) -> dict:
    """'text · with: a, b · where: place · tags: x, y' → parts (French labels accepted)."""
    parts = AXIS.split(body)
    e = {"text": parts[0].strip(" ·"), "with": [], "where": "", "tags": []}
    for key, val in zip(parts[1::2], parts[2::2]):
        k = key.lower()
        if k in ("with", "avec"):
            e["with"] = [x.strip() for x in re.split(r"[,;]", val) if x.strip()]
        elif k in ("where", "où"):
            e["where"] = val.strip()
        else:
            e["tags"] = [x.strip() for x in re.split(r"[,;]", val) if x.strip()]
    return e


def import_agent_memories(work: Path, folder: Path, *, identity: str | None = None, lang: str | None = None,
                          presets: list[str] | None = None, source: str | None = None) -> list[str]:
    """Append what the agent lived as `lived`, `personal` memories of the unpacked character folder `work`; an entry
    whose text is already a lived memory of the file is skipped (re-import is idempotent). Returns the new node ids."""
    from .memories import load_nodes
    from .selfdesc import memory_add
    manifest = json.loads((work / "manifest.json").read_text("utf-8"))
    lived: set[tuple[str, str]] = set(); canon: set[str] = set()
    for n in load_nodes(work, manifest).values():
        for g in (n.get("gist") or {}).values():
            if n.get("origin") == "lived":
                lived.add(((n.get("when") or {}).get("date") or "", _norm(g)))
            else:
                canon.add(_norm(g))
    long_canon = [c for c in canon if len(c) >= 24]; short_canon = [c for c in canon if 8 <= len(c) < 24]
    entries = [e for e in parse_agent_dir(folder) if not source or e["source"] == source]
    if not entries:
        raise ValueError(f"{folder}: nothing to import (memory/YYYY-MM-DD.md notes or memories/MEMORY.md entries)")
    lang = lang or _guess_lang(manifest)
    added = []
    for e in entries:
        n = _norm(e["text"])
        if (e["date"], n) in lived:                       # the same fact on the same day: already there (re-import is idempotent)
            continue
        if n in canon or any(c in n for c in long_canon) or any(n.endswith(c) for c in short_canon):
            continue                                      # an entry the host got FROM the file (a Hermes MEMORY.md repeats the export): not lived
        tags = [f"lived:{e['source']}", *e["tags"]]
        who = [w.replace("|", "/") for w in e["with"]]     # names only: an agent's note never sets shown / real / age (the --who syntax) — hunt 1.2.2, SAFETY-04
        vid = memory_add(work, identity=identity, kind="moment", gists={lang: e["text"]}, label=e["text"][:60], date=e["date"],
                         where=e["where"] or None, who=who or None, tags=tags, personal=True, origin="lived",
                         presets=presets, lang=lang)
        lived.add((e["date"], n)); added.append(vid)
    return added


def _norm(s: str) -> str:
    """Text as compared for the re-import: case, spaces and punctuation set aside."""
    return re.sub(r"[^\w]+", " ", (s or "").lower()).strip()


def _guess_lang(manifest: dict) -> str:
    for v in (manifest.get("elements", {}).get("personality", {}).get("variants") or {}).values():
        if v.get("language"):
            return v["language"]
    return (manifest.get("languages") or ["en"])[0]
