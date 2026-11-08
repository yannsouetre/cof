"""Import a platform export into COF (RFC 0006): the character from its card, and each conversation as ONE personal
`period` memory carrying the verbatim transcript (quoted Markdown).

Formats (detected by content, never by extension): CAI Tools card (flat PNG `chara` chunk, hybrid JSON), CAI Tools
"Tavern" chat (.jsonl) and history (.zip of chat_N.jsonl), CAI Tools legacy JSON (`histories`), PersonaText
(.personatext.json, a V2 card with `data.extensions.chat_history`), SillyTavern chat (.jsonl), Oobabooga chat (.json),
and the official Character.AI data export (.zip, undocumented: tolerant parser, `inspect` prints its key tree).

Input files are untrusted: nothing in them is executed, archives are bounded (entries, sizes, ratio, no `..` paths), an
illegible line is a line of the report, never a crash. No network, no account data copied. Standard library only."""
from __future__ import annotations

import base64
import binascii
import hashlib
import io
import json
import re
import shutil
import tempfile
import unicodedata
import zipfile
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from pathlib import Path, PurePosixPath

from . import __version__
from .convert import PNG_SIG, card_to_cof_dir, png_build, png_chunks, read_card_from_png, strip_card_payloads

COMPOSITE = "http://cv.iptc.org/newscodes/digitalsourcetype/compositeWithTrainedAlgorithmicMedia"
SPLIT_BYTES = 1_000_000                       # RFC 0006 § 3.3: a chat above 1 MB is split into parts
MAX_FILE = 512 * 1024 * 1024                  # one input file
MAX_ZIP_ENTRIES = 20_000
MAX_ZIP_TOTAL = 1024 * 1024 * 1024            # uncompressed, whole archive
MAX_ZIP_ENTRY = 256 * 1024 * 1024
MAX_RATIO = 100                               # uncompressed / compressed, for any entry above 1 MB
MAX_DEPTH = 64                                # nesting of a JSON value read from a file
MAX_NEST = 2                                  # zips inside zips
# account files are recognised by their whole name (user.json, account_settings.json, personas.json…), never by a part
# of it: "wren.personatext.json" or "Persona 5 Joker.jsonl" are chats. Objects carrying an e-mail or a password are
# skipped by content anyway (_official).
_ACCOUNT_FILE = re.compile(r"^(users?|accounts?|profiles?|settings?|personas?|auth|billing|subscriptions?|emails?)"
                           r"([_\-](settings?|data|info|profile|details|preferences))?\.(json|jsonl|txt|csv)$", re.I)
_SPEAKER_MAX = 80
MAX_AVATAR = 5 * 1024 * 1024
EARLIEST = datetime(2020, 1, 1, tzinfo=timezone.utc)    # before Character.AI: not a real date

PLATFORM = {"character.ai": "Character.AI", "sillytavern": "SillyTavern", "oobabooga": "Oobabooga"}


class ImportStop(Exception):
    """The import stops and writes nothing (code: 1 = a hostile file, 2 = an option the rules refuse, 3 = the user must answer)."""
    def __init__(self, msg: str, code: int = 3):
        super().__init__(msg)
        self.code = code


# ---------------------------------------------------------------- model

@dataclass
class Message:
    speaker: str
    is_user: bool
    text: str
    ts: datetime | None = None
    note: bool = False

    def __post_init__(self):                       # a lone surrogate (a truncated emoji, valid JSON) never aborts an import (hunt CLI-6)
        self.text = _LONE.sub("\ufffd", self.text) if isinstance(self.text, str) else self.text
        self.speaker = _LONE.sub("\ufffd", self.speaker) if isinstance(self.speaker, str) else self.speaker


_LONE = re.compile("[\ud800-\udfff]")


@dataclass
class Chat:
    messages: list
    fmt: str                                   # provenance format slug
    platform: str = "character.ai"
    character: str | None = None               # the character's name as the chat says it
    persona: str | None = None                 # the user's display name, when the file has a real one
    speaker_source: str = "platform"           # platform | inferred-from-greeting
    order: int = 0                             # 0 = oldest; position in the export, oldest first
    source_file: str = ""
    raw: bytes | None = None                   # the source bytes of this chat (--keep-source)
    raw_name: str = ""
    dated: bool = False
    group_key: str = ""                        # the export the chat came from (order links stay inside one export)
    export_year: int | None = None             # the year of the export instant, when a tool wrote it on the messages
    ordered: bool = False                      # the export gives the order of its chats


@dataclass
class Character:
    card: dict
    fmt: str
    platform: str = "character.ai"
    avatar: bytes | None = None
    avatar_type: str = ""                      # image/png, image/webp, image/jpeg
    source_file: str = ""

    @property
    def name(self) -> str:
        return str((self.card.get("data") or {}).get("name") or "").strip()


@dataclass
class Report:
    lines: list = field(default_factory=list)          # what was found and done
    ignored: list = field(default_factory=list)        # what was left out, with counts
    alerts: list = field(default_factory=list)         # what the user must check
    sources: list = field(default_factory=list)        # provenance.source entries

    def count(self, what: str, n: int = 1):
        for i, (w, k) in enumerate(self.ignored):
            if w == what:
                self.ignored[i] = (w, k + n); return
        self.ignored.append((what, n))


@dataclass
class Bundle:
    characters: list = field(default_factory=list)
    chats: list = field(default_factory=list)
    report: Report = field(default_factory=Report)


# ---------------------------------------------------------------- small helpers

def _decode(b: bytes, rep: Report, where: str) -> str:
    if b[:2] in (b"\xff\xfe", b"\xfe\xff"):          # UTF-16 with its BOM (a Windows redirection, hunt CLI-16)
        try:
            return b.decode("utf-16")
        except UnicodeDecodeError:
            pass
    try:
        return b.decode("utf-8-sig")
    except UnicodeDecodeError:
        rep.alerts.append(f"{where}: not valid UTF-8 — illegible bytes replaced by �")
        return b.decode("utf-8", errors="replace")


_MOJIBAKE = re.compile("Ã[\u0080-¿]|â€|Ã©|Ã¨")


def _fix_text(t: str, rep: Report) -> str:
    """Repairs UTF-8 read as Latin-1 (`CafÃ©` → `Café`), which a binary-string zip path can produce; keeps the text
    unchanged when the repair does not decode cleanly."""
    if _MOJIBAKE.search(t):
        try:
            fixed = t.encode("latin-1").decode("utf-8")
            rep.count("messages repaired from mojibake (UTF-8 read as Latin-1)")
            return fixed
        except (UnicodeEncodeError, UnicodeDecodeError):
            pass
    return t


_MONTHS = "%B %d, %Y %I:%M%p"
_ST_AT = re.compile(r"^\s*(\d{4})-(\d{1,2})-(\d{1,2})\s*@\s*(\d{1,2})h\s*(\d{1,2})m\s*(\d{1,2})s(?:\s*(\d{1,3})\s*ms)?\s*$")


def parse_ts(v) -> datetime | None:
    """A timestamp in any of SillyTavern's three families (ms/s number, ISO 8601, human strings) → aware UTC datetime,
    or None. A time zone is never given in these files: naive times are read as UTC (said in the transcript)."""
    if v is None or isinstance(v, bool):
        return None
    dt = None
    try:
        if isinstance(v, (int, float)):
            x = float(v)
            dt = datetime.fromtimestamp(x / 1000 if x > 1e11 else x, tz=timezone.utc)
        elif isinstance(v, str) and v.strip():
            s = v.strip()
            if re.fullmatch(r"\d{10,13}(\.\d+)?", s):
                return parse_ts(float(s))
            m = _ST_AT.match(s)
            if m:
                y, mo, d, h, mi, se, ms = m.groups()
                dt = datetime(int(y), int(mo), int(d), int(h), int(mi), int(se), int((ms or "0").ljust(3, "0")) * 1000, tzinfo=timezone.utc)
            else:
                try:
                    dt = datetime.fromisoformat(s.replace("Z", "+00:00"))
                except ValueError:
                    for fmt_ in (_MONTHS, "%B %d, %Y %I:%M %p"):
                        try:
                            dt = datetime.strptime(re.sub(r"\s+", " ", s), fmt_)
                            break
                        except ValueError:
                            continue
                    else:
                        return None
    except (OverflowError, OSError, ValueError):
        return None
    if dt is None:
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    dt = dt.astimezone(timezone.utc)
    if dt < EARLIEST or dt > datetime.now(timezone.utc) + timedelta(days=1):
        return None
    return dt


def settle_dates(chat: Chat, rep: Report, *, never: bool = False):
    """A chat is dated only by real timestamps. All equal (or within 5 s, as CAI Tools writes the export instant on every
    message), or a format known to lose them: undated, and the times are dropped — an export date is never a memory date."""
    ts = [m.ts for m in chat.messages if m.ts]
    if ts:
        chat.export_year = max(ts).year         # an upper bound only: kept for the undated label, never as a date
    if never or not ts:
        dated = False
    elif len(ts) >= 2 and (max(ts) - min(ts)).total_seconds() <= 5:
        dated = False
        rep.alerts.append(f"{chat.source_file}: every message carries the same instant (the export time, not the conversation's): undated")
    else:
        dated = True
    if not dated:
        for m in chat.messages:
            m.ts = None
    chat.dated = dated


# ---------------------------------------------------------------- sniffing

def _json_or_none(text: str):
    try:
        v = json.loads(text)
    except (json.JSONDecodeError, RecursionError, ValueError):
        return None
    return None if _too_deep(v) else v


def _too_deep(v, limit: int = MAX_DEPTH) -> bool:
    stack = [(v, 0)]
    while stack:
        o, d = stack.pop()
        if d > limit:
            return True
        if isinstance(o, dict):
            stack.extend((x, d + 1) for x in o.values())
        elif isinstance(o, list):
            stack.extend((x, d + 1) for x in o)
    return False


def _first_line_obj(text: str):
    for line in text.splitlines():
        if line.strip():
            o = _json_or_none(line)
            return o if isinstance(o, dict) else None
    return None


def sniff_obj(obj) -> str | None:
    """The format of a parsed JSON value, or None."""
    if isinstance(obj, dict):
        if isinstance(obj.get("histories"), (dict, list)):
            return "caitools-histories-json"
        if isinstance(obj.get("data_visible"), list):
            return "oobabooga-json"
        data = obj.get("data")
        if obj.get("spec") in ("chara_card_v2", "chara_card_v3") and isinstance(data, dict):
            ext = data.get("extensions") or {}
            if isinstance(ext, dict) and (ext.get("source") == "character.ai" or "character_ai" in ext):
                return "personatext"           # a Character.AI card (PersonaText); a chat_history from another tool stays the 1.0 path
            return "card-json"
        tool = ((obj.get("metadata") or {}).get("tool") or {}) if isinstance(obj.get("metadata"), dict) else {}
        if isinstance(tool, dict) and str(tool.get("name", "")).lower() == "cai tools":
            return "caitools-card-json"
        if any(k in obj for k in ("email", "password", "date_of_birth", "birthday", "phone")) or any(_is_msg_array(v) for v in obj.values()):
            return None                        # an account object, or a conversation under any key: never a card
        if "spec" not in obj and ("name" in obj or "char_name" in obj) and any(k in obj for k in (
                "first_mes", "description", "personality", "scenario", "mes_example", "char_persona", "char_greeting")):
            return "card-json"                 # a plain V1 / TavernAI card: the 1.0 path
    return None


def sniff_jsonl(text: str) -> str | None:
    head = _first_line_obj(text)
    if not head or not ({"user_name", "chat_metadata", "name", "character_name"} & set(head)):
        return None
    if head.get("user_name") == "You" and "create_date" in head and "chat_metadata" not in head:
        return "caitools-tavern-chat"
    return "sillytavern-jsonl"


def sniff(path: Path) -> str:
    """The format of a file, by content. `unknown` when nothing matches."""
    if path.is_dir():
        return "folder"
    with open(path, "rb") as f:
        head = f.read(8)
    if head.startswith(PNG_SIG):
        try:
            card = read_card_from_png(path.read_bytes())
        except (ValueError, AttributeError, TypeError):
            return "unknown"
        if not isinstance(card, dict) or not isinstance(card.get("data", {}), dict):
            return "unknown"
        return "caitools-card-png" if _is_caitools_flat(card) else "card-png"
    if head.startswith(b"PK"):
        try:
            with zipfile.ZipFile(path) as z:
                names = [n for n in z.namelist() if not n.endswith("/") and not n.startswith("__MACOSX/") and not PurePosixPath(n).name.startswith(".")]
        except zipfile.BadZipFile:
            return "unknown"
        if names and all(re.fullmatch(r"(?:.*/)?chat_\d+\.jsonl", n) for n in names):
            return "caitools-tavern-history"
        return "zip"
    if path.stat().st_size > MAX_FILE:
        return "unknown"
    raw = path.read_bytes()
    text = raw.decode("utf-16", errors="replace") if raw[:2] in (b"\xff\xfe", b"\xfe\xff") else raw.decode("utf-8-sig", errors="replace")
    obj = _json_or_none(text)
    if obj is not None:
        return sniff_obj(obj) or "unknown-json"
    return sniff_jsonl(text) or "unknown"


def _is_caitools_flat(card: dict) -> bool:
    data = card.get("data") if isinstance(card, dict) else None
    if not isinstance(data, dict):
        return False
    tool = ((data.get("metadata") or {}).get("tool") or {}) if isinstance(data.get("metadata"), dict) else {}
    return isinstance(tool, dict) and str(tool.get("name", "")).lower() == "cai tools"


# ---------------------------------------------------------------- the key tree (--inspect)

def key_tree(obj, depth: int = 0, max_depth: int = 8, out: list | None = None, prefix: str = "") -> list:
    """Paths, types, array lengths and string lengths — never a value."""
    out = [] if out is None else out
    pad = "  " * depth
    if depth > max_depth:
        out.append(f"{pad}{prefix}…"); return out
    if isinstance(obj, dict):
        out.append(f"{pad}{prefix}{{{len(obj)} keys}}")
        for k in list(obj)[:200]:
            key_tree(obj[k], depth + 1, max_depth, out, f"{_safe_key(k)}: ")
        if len(obj) > 200:
            out.append(f"{pad}  … {len(obj) - 200} more keys")
    elif isinstance(obj, list):
        out.append(f"{pad}{prefix}[{len(obj)} items]")
        kinds = {}
        for x in obj[:500]:
            sig = type(x).__name__ if not isinstance(x, dict) else "object:" + ",".join(sorted(map(_safe_key, x))[:40])
            kinds.setdefault(sig, x)
        for sig, x in list(kinds.items())[:5]:
            key_tree(x, depth + 1, max_depth, out, "item: ")
    elif isinstance(obj, str):
        out.append(f"{pad}{prefix}string({len(obj)})")
    elif isinstance(obj, bool):
        out.append(f"{pad}{prefix}bool")
    elif isinstance(obj, (int, float)):
        out.append(f"{pad}{prefix}number")
    else:
        out.append(f"{pad}{prefix}null")
    return out


def _safe_key(k) -> str:
    """A key is shown only when it looks like a field name; anything else (an id, an e-mail used as a key) is redacted."""
    k = str(k)
    # field names are lower-case first (chat_id, createTime); a capitalised key or one with spaces is a name used as a key
    # — a character, a handle — and is redacted too (hunt CLI-10)
    return k if re.fullmatch(r"[a-z_][A-Za-z0-9_\-]{0,40}", k) and not re.search(r"\d{4,}", k) else f"<key({len(k)})>"


def inspect(path: Path) -> str:
    """The structure of a file or of every JSON entry of a zip, with every value redacted (RFC 0006 § 6)."""
    lines = [f"# cof import --inspect · {sniff(path)} · cof-cli {__version__} · values redacted"]
    if path.is_file() and path.read_bytes()[:2] == b"PK":
        for name, data in _zip_entries(path, Report(), skip_account=False):
            lines.append(f"\n## entry {_redact_name(name)} ({len(data)} bytes)")
            lines += _inspect_bytes(data)
    elif path.is_file():
        lines += _inspect_bytes(path.read_bytes())
    return "\n".join(lines) + "\n"


_STRUCTURAL = {"user", "users", "account", "accounts", "character", "characters", "chat", "chats", "message", "messages",
               "history", "histories", "persona", "personas", "settings", "export", "data", "conversations", "conversation",
               "index", "manifest", "turns", "rooms", "profile", "memories", "lorebooks", "lorebook", "voices", "images"}


def _redact_name(name: str) -> str:
    """An entry name is shown only when it is a structural word (chats.json, chat_3.jsonl); anything else — a character's
    or a person's name — is redacted to its length."""
    def one(p):
        stem, _, ext = p.rpartition(".") if "." in p else (p, "", "")
        if re.fullmatch(r"chat_\d+", stem) or stem.lower() in _STRUCTURAL:
            return p
        return f"<name({len(p)})>"
    return "/".join(one(p) for p in name.split("/"))


def _inspect_bytes(data: bytes) -> list:
    if data.startswith(PNG_SIG):
        try:
            return key_tree(read_card_from_png(data))
        except ValueError:
            return ["PNG without a character card"]
    text = data.decode("utf-8-sig", errors="replace")
    obj = _json_or_none(text)
    if obj is not None:
        return key_tree(obj)
    out = []
    for i, line in enumerate(text.splitlines()[:3]):
        o = _json_or_none(line)
        out += [f"line {i + 1}:"] + key_tree(o, 1) if o is not None else [f"line {i + 1}: not JSON ({len(line)} chars)"]
    n = text.count("\n")
    if n > 3:
        out.append(f"… {n} lines")
    return out


# ---------------------------------------------------------------- archives

def _zip_entries(path: Path, rep: Report, skip_account: bool = True):
    """(name, bytes) of the regular entries of a zip, within the limits; unsafe or oversized entries are reported."""
    try:
        z = zipfile.ZipFile(path)
    except zipfile.BadZipFile:
        rep.alerts.append(f"{path.name}: not a readable zip"); return
    with z:
        infos = [i for i in z.infolist() if not i.is_dir()]
        if len(infos) > MAX_ZIP_ENTRIES:
            raise ImportStop(f"{path.name}: {len(infos)} entries — more than {MAX_ZIP_ENTRIES}, refused (possible zip bomb)", 1)
        tot, comp = sum(i.file_size for i in infos), sum(i.compress_size for i in infos)
        if tot > MAX_ZIP_TOTAL:
            raise ImportStop(f"{path.name}: more than {MAX_ZIP_TOTAL // 2**20} MB once unpacked, refused (possible zip bomb)", 1)
        if tot > 50 * 2**20 and tot / max(comp, 1) > MAX_RATIO:
            raise ImportStop(f"{path.name}: {tot // 2**20} MB once unpacked from {comp // 2**10} KB — refused (possible zip bomb)", 1)
        for i in infos:
            n = i.filename.replace("\\", "/")
            parts = PurePosixPath(n).parts
            if n.startswith("/") or re.match(r"^[A-Za-z]:", n) or ".." in parts:
                rep.alerts.append(f"{path.name}: entry with an unsafe path skipped ({_redact_name(n)})"); continue
            if parts and (parts[0] == "__MACOSX" or PurePosixPath(n).name.startswith(".")):
                continue                            # macOS resource forks, .DS_Store: not part of the export (hunt CLI-9)
            if skip_account and _ACCOUNT_FILE.search(PurePosixPath(n).name):
                rep.count("account files never read (e-mail, birth date, settings…)"); continue
            if i.file_size > MAX_ZIP_ENTRY or (i.file_size > 2**20 and i.file_size / max(i.compress_size, 1) > MAX_RATIO):
                rep.alerts.append(f"{path.name}: entry {_redact_name(n)} too large or too compressed, skipped"); continue
            try:
                with z.open(i) as f:
                    data = f.read(MAX_ZIP_ENTRY + 1)
            except (zipfile.BadZipFile, OSError, RuntimeError, NotImplementedError) as e:
                rep.alerts.append(f"{path.name}: entry {_redact_name(n)} unreadable ({type(e).__name__})"); continue
            if len(data) > MAX_ZIP_ENTRY:
                rep.alerts.append(f"{path.name}: entry {_redact_name(n)} larger than declared, skipped"); continue
            yield n, data


# ---------------------------------------------------------------- parsers

def _st_messages(lines, rep: Report, where: str, *, caitools: bool) -> tuple[list, dict]:
    """SillyTavern-family JSONL → messages (header returned apart). Swipes dropped (the chosen `mes` is kept), system
    lines kept as [note], empty or illegible lines counted."""
    header, msgs = {}, []
    for i, line in enumerate(lines):
        if not line.strip():
            continue
        o = _json_or_none(line)
        if not isinstance(o, dict):
            rep.count("illegible lines (not JSON)"); continue
        if not msgs and not header and ("user_name" in o or "chat_metadata" in o) and "mes" not in o:
            header = o; continue
        text = o.get("mes")
        if not isinstance(text, str):
            rep.count("messages without text"); continue
        if not text.strip():
            rep.count("empty messages"); continue
        sw = o.get("swipes")
        if isinstance(sw, list) and len(sw) > 1:
            rep.count("alternative replies (swipes) dropped", len(sw) - 1)
        extra = o.get("extra") if isinstance(o.get("extra"), dict) else {}
        nm = o.get("name") if isinstance(o.get("name"), str) else ""
        # a narrator / system line is a [note]; SillyTavern also flags hidden messages is_system: those keep their speaker
        note = extra.get("type") == "narrator" or (bool(o.get("is_system")) and not o.get("is_user") and nm.strip().lower() in ("system", ""))
        if note:
            rep.count("system / narrator lines kept as [note]")
        msgs.append(Message(speaker="[note]" if note else clean_speaker(nm or ("You" if o.get("is_user") else "?")),
                            is_user=bool(o.get("is_user")), text=_fix_text(text, rep), ts=parse_ts(o.get("send_date")), note=note))
    return msgs, header


def _names(msgs) -> tuple[str | None, str | None]:
    char = next((m.speaker for m in msgs if not m.is_user and not m.note and m.speaker not in ("?", "")), None)
    user = next((m.speaker for m in msgs if m.is_user and m.speaker not in ("You", "unused", "?", "")), None)
    return char, user


def parse_jsonl(text: str, fmt: str, rep: Report, where: str, raw: bytes | None = None) -> Chat | None:
    caitools = fmt.startswith("caitools")
    msgs, header = _st_messages(text.splitlines(), rep, where, caitools=caitools)
    if not msgs:
        rep.alerts.append(f"{where}: no message found"); return None
    char, user = _names(msgs)
    if not char and isinstance(header.get("character_name"), str) and header["character_name"] not in ("unused", ""):
        char = header["character_name"]
    chat = Chat(messages=msgs, fmt=fmt, platform="character.ai" if caitools else "sillytavern", character=char, persona=user,
                source_file=where, raw=raw, raw_name=Path(where).name)
    settle_dates(chat, rep, never=caitools)
    if caitools:
        rep.count("CAI Tools chats without real dates (the extension writes the export time)")
    return chat


def _first(d: dict, *paths):
    """The first present value among dotted paths (`src.is_human`) and flat keys (`src__is_human`)."""
    for p in paths:
        cur = d
        for part in p.split("."):
            if isinstance(cur, dict) and part in cur:
                cur = cur[part]
            else:
                cur = None; break
        if cur is not None:
            return cur
    return None


_TEXT_PATHS = ("text", "raw_content", "content", "mes", "message")
_HUMAN_PATHS = ("src.is_human", "src__is_human", "author.is_human", "is_human", "isHuman", "is_user", "isUser")
_NAME_PATHS = ("src.name", "src__name", "author.name", "name", "src__user__username", "author", "speaker")
_TS_PATHS = ("create_time", "created", "timestamp", "send_date", "created_at", "date", "time")


def _msg_text(o: dict):
    t = _first(o, *_TEXT_PATHS)
    if t is None and isinstance(o.get("candidates"), list) and o["candidates"]:
        c = o["candidates"][-1]                 # the chosen candidate is the last one CAI Tools keeps
        t = c.get("raw_content") or c.get("text") if isinstance(c, dict) else None
    return t if isinstance(t, str) else None


def _messages_from_list(items: list, rep: Report, character: str | None) -> tuple[list, str]:
    """Generic message objects → messages; authors from the platform's flags, else names, else inferred."""
    rows = []
    for o in items:
        if not isinstance(o, dict):
            continue
        if o.get("is_alternative") is True:
            rep.count("alternative replies (swipes) dropped"); continue
        t = _msg_text(o)
        if t is None:
            rep.count("messages without text"); continue
        if not t.strip():
            rep.count("empty messages"); continue
        human = _first(o, *_HUMAN_PATHS)
        role = o.get("role")
        if role == "system":
            rows.append(("note", None, _fix_text(t, rep), parse_ts(_first(o, *_TS_PATHS))))
            rep.count("system / narrator lines kept as [note]"); continue
        if human is None and role in ("user", "assistant", "model", "char", "bot"):
            human = role == "user"
        name = _first(o, *_NAME_PATHS)
        rows.append((human if isinstance(human, bool) else None, clean_speaker(name) if isinstance(name, str) else None, _fix_text(t, rep), parse_ts(_first(o, *_TS_PATHS))))
    if not rows:
        return [], "platform"
    source = "platform"
    talk = [r_ for r_ in rows if r_[0] != "note"]
    if talk and all(h is None for h, *_ in talk):
        names = {n for _, n, *_ in talk if n}
        cl = (character or "").strip().lower()
        if cl and cl in {n.strip().lower() for n in names}:
            source = "names"                    # the character's name tells its lines apart (RFC 0006 § 3.4)
            out = []
            for h, n, t, ts in rows:
                nl = (n or "").strip().lower()
                if h == "note" or nl in ("narrator", "system", "[note]"):
                    out.append(("note", None, t, ts))
                else:
                    out.append((nl != cl, n, t, ts))
            rows = out
        else:                                   # nothing says who speaks: the first message is the greeting, then turns alternate
            source = "inferred-from-greeting"
            k, out = 0, []
            for r_ in rows:
                if r_[0] == "note":
                    out.append(r_); continue
                out.append((k % 2 == 1, r_[1], r_[2], r_[3])); k += 1
            rows = out
    msgs = [Message(speaker="[note]", is_user=False, text=t, ts=ts, note=True) if h == "note" else
            Message(speaker=(n or ("You" if h else (character or "Character"))), is_user=bool(h), text=t, ts=ts) for h, n, t, ts in rows]
    return msgs, source


def clean_speaker(s) -> str:
    """A speaker name as a heading can carry it: one line, no heading separator, bounded."""
    s = re.sub(r"[\r\n\t]+", " ", str(s)).replace("·", "-").strip()
    return s[:_SPEAKER_MAX] or "?"


def parse_histories(obj: dict, rep: Report, where: str, raw: bytes | None) -> list:
    h = obj.get("histories")
    lst = h.get("histories") if isinstance(h, dict) else h
    chats = []
    for i, entry in enumerate(lst if isinstance(lst, list) else []):
        if not isinstance(entry, dict):
            continue
        msgs, source = _messages_from_list(entry.get("msgs") or entry.get("messages") or [], rep, None)
        if not msgs:
            continue
        char, user = _names(msgs) if source == "platform" else (None, None)    # never a name taken from inferred speakers
        c = Chat(messages=msgs, fmt="caitools-histories-json", character=char, persona=user, speaker_source=source,
                 source_file=f"{where} #{i + 1}", group_key=where)              # no raw copy: the entry may carry account ids
        created = parse_ts(entry.get("created") or entry.get("create_time"))
        settle_dates(c, rep, never=True)       # message dates are not in this file; the chat's creation date is not a span
        if created:
            c._created = created                 # ordering hint only
        chats.append(c)
    # order only when every chat carries its creation date; otherwise the file's order is kept but not claimed (no `after`)
    if chats and all(getattr(c, "_created", None) for c in chats):
        chats.sort(key=lambda c: c._created)
        for c in chats:
            c.ordered = True
    for k, c in enumerate(chats):
        c.order = k
    return chats


def parse_oobabooga(obj: dict, rep: Report, where: str, raw: bytes | None) -> Chat | None:
    msgs = []
    for pair in obj.get("data_visible") or obj.get("internal") or []:
        if isinstance(pair, list) and len(pair) == 2:
            for k, t in enumerate(pair):
                if isinstance(t, str) and t.strip():
                    msgs.append(Message(speaker="You" if k == 0 else "Character", is_user=k == 0, text=_fix_text(t, rep)))
    if not msgs:
        rep.alerts.append(f"{where}: no message found"); return None
    rep.count("Oobabooga chats: the greeting is not in the file, names and dates neither")
    return Chat(messages=msgs, fmt="oobabooga-json", platform="oobabooga", source_file=where, raw=raw, raw_name=Path(where).name)


def parse_personatext(obj: dict, rep: Report, where: str, raw: bytes | None) -> tuple[Character, Chat | None]:
    data = obj.get("data") or {}
    ext = data.get("extensions") or {}
    hist = ext.get("chat_history") if isinstance(ext, dict) else None
    char = Character(card=obj, fmt="personatext", source_file=where)
    url = ext.get("avatar_data_url") if isinstance(ext, dict) else None
    if isinstance(url, str) and url:
        m = re.fullmatch(r"data:(image/(?:webp|png|jpeg));base64,([A-Za-z0-9+/=\s]+)", url, re.S)
        if not m:
            rep.alerts.append(f"{where}: avatar data URL not understood, left out")
        else:
            try:
                img = base64.b64decode(m.group(2), validate=False)
                if len(img) > MAX_AVATAR:
                    rep.alerts.append(f"{where}: avatar larger than {MAX_AVATAR // 2**20} MB, left out")
                elif _image_ok(img, m.group(1)):
                    char.avatar, char.avatar_type = img, m.group(1)
                else:
                    rep.alerts.append(f"{where}: avatar is not the image it claims to be, left out")
            except (binascii.Error, ValueError):
                rep.alerts.append(f"{where}: avatar data URL not decodable, left out")
    chat = None
    if isinstance(hist, list) and hist:
        msgs, source = _messages_from_list(hist, rep, char.name or None)
        name = char.name or "Character"
        for m in msgs:                          # PersonaText says user / assistant: give them their names
            if m.speaker in ("user", "assistant", "You", "Character") or m.speaker == name:
                m.speaker = "You" if m.is_user else name
        if msgs:
            chat = Chat(messages=msgs, fmt="personatext", character=char.name, speaker_source=source, source_file=where, raw=raw, raw_name=Path(where).name)
            settle_dates(chat, rep)
            if not chat.dated:
                rep.count("PersonaText chats without timestamps (the page-reading fallback loses them)")
    return char, chat


def _image_ok(b: bytes, mt: str) -> bool:
    # the signature and the first chunk an image needs: a header alone is not a picture (hunt CLI-19)
    return (mt == "image/png" and b.startswith(PNG_SIG) and b[12:16] == b"IHDR" and b"IDAT" in b) or \
           (mt == "image/jpeg" and b[:3] == b"\xff\xd8\xff" and len(b) > 100) or \
           (mt == "image/webp" and b[:4] == b"RIFF" and b[8:12] == b"WEBP" and b[12:15] == b"VP8" and len(b) > 30)


def _card_from_png(png: bytes, fmt: str, where: str) -> Character:
    card = read_card_from_png(png)
    return Character(card=card, fmt=fmt, avatar=_strip_card_chunks(png), avatar_type="image/png", source_file=where)


_PNG_IMAGE_CHUNKS = {b"IHDR", b"PLTE", b"IDAT", b"IEND", b"tRNS", b"gAMA", b"cHRM", b"sRGB", b"iCCP", b"sBIT", b"pHYs"}


def _strip_card_chunks(png: bytes) -> bytes:
    """The avatar as an image only: the card lives in the personality, not twice, and no other text chunk (a comment, a
    description, a hidden second card) travels unread (hunt SAF-5). Same list as the import page."""
    try:
        return png_build([(t, b) for t, b in png_chunks(png) if t in _PNG_IMAGE_CHUNKS])
    except Exception:
        return png


def _flat_card(obj: dict) -> dict:
    return obj if obj.get("spec") else {"spec": "chara_card_v2", "spec_version": "2.0", "data": obj}


def _official(entries: list, rep: Report, where: str) -> tuple[list, list]:
    """Tolerant reading of an unknown export (the official Character.AI zip): characters are objects with a name and a
    greeting / definition; chats are lists of message-like objects, attached to the character named around them.
    Account, persona and settings files are skipped by name (_zip_entries); an object carrying an e-mail or a password
    is never a character; the creator handle is not mapped (in this export it may be the user's own)."""
    chars, chats, ids = [], [], {}
    SPLIT = ("chat_id", "chatId", "conversation_id", "history_id", "thread_id")

    def add_chat(dicts, ctx_name, cid):
        msgs, source = _messages_from_list(dicts, rep, ctx_name)
        if not msgs:
            return
        c = Chat(messages=msgs, fmt="official-zip", speaker_source=source, source_file=f"{where} (list of {len(msgs)})", group_key=where)
        c._cid = cid
        if ctx_name:
            c.character = clean_speaker(ctx_name)
            if source == "platform":
                c.persona = _names(msgs)[1]
        elif source == "platform":
            c.character, c.persona = _names(msgs)
        chats.append(c)

    def walk(o, ctx_name=None, depth=0):
        if depth > MAX_DEPTH:
            return
        if isinstance(o, dict):
            if any(k in o for k in ("email", "password", "date_of_birth", "birthday", "phone")):
                rep.count("account-like objects ignored"); return
            nm = o.get("name") or o.get("participant__name") or o.get("character_name")
            if isinstance(nm, str) and nm.strip():          # a character's id → its name, even without a definition (hunt DES-1)
                for k in ("external_id", "character_id", "id"):
                    if isinstance(o.get(k), (str, int)) and str(o[k]) not in ids:
                        ids[str(o[k])] = clean_speaker(nm)
            if isinstance(nm, str) and nm.strip() and any(isinstance(o.get(k), str) for k in ("greeting", "definition", "first_message", "first_mes")) \
                    and not any(isinstance(o.get(k), list) for k in ("msgs", "turns", "messages")):
                card = {"spec": "chara_card_v2", "spec_version": "2.0", "data": {
                    "name": clean_speaker(nm), "description": _s(o.get("description") or o.get("title")),
                    "personality": _s(o.get("title")), "scenario": "",
                    "first_mes": _s(o.get("greeting") or o.get("first_message") or o.get("first_mes")),
                    "mes_example": _s(o.get("definition")), "creator": "", "tags": [], "extensions": {}}}
                chars.append(Character(card=card, fmt="official-zip", source_file=where))
                for k in ("character_id", "external_id", "id"):
                    if isinstance(o.get(k), (str, int)):
                        ids[str(o[k])] = clean_speaker(nm)
                return
            ctx = o.get("character_name") or o.get("participant__name") or ctx_name
            for v in o.values():
                walk(v, ctx if isinstance(ctx, str) else ctx_name, depth + 1)
        elif isinstance(o, list):
            dicts = [x for x in o if isinstance(x, dict)]
            if dicts and sum(1 for x in dicts if _msg_text(x) is not None) >= max(1, len(dicts) // 2):
                key = next((k for k in SPLIT if sum(1 for x in dicts if isinstance(x.get(k), (str, int))) > len(dicts) // 2), None)
                if not key:
                    add_chat(dicts, ctx_name, None)
                    return
                groups = {}                         # one flat list of every message, keyed by chat (hunt DES-1)
                for x in dicts:
                    groups.setdefault(str(x.get(key)), []).append(x)
                for g in groups.values():
                    cid = next((str(x[k]) for x in g for k in ("character_id", "characterId") if isinstance(x.get(k), (str, int))), None)
                    add_chat(g, g[0].get("character_name") if isinstance(g[0].get("character_name"), str) else ctx_name, cid)
                return
            for v in o:
                walk(v, ctx_name, depth + 1)

    for name, data in entries:
        if not name.lower().endswith((".json", ".jsonl")):
            rep.count("archive entries that are not JSON, ignored"); continue
        text = _decode(data, rep, _redact_name(name))
        obj = _json_or_none(text)
        if obj is None:
            objs = [_json_or_none(l) for l in text.splitlines() if l.strip()]
            obj = [x for x in objs if x is not None]
        walk(obj)
    for c in chats:                             # a chat's character by its id, once every character is known
        cid = getattr(c, "_cid", None)
        if cid and cid in ids and not c.character:
            c.character = ids[cid]
    for k, c in enumerate(chats):
        c.order = k                             # § 3.2: n follows the export's order
        settle_dates(c, rep)
    if chats:
        rep.alerts.append("official export: its structure is undocumented — check the first messages of each transcript (who speaks)")
    return chars, chats


def _s(v) -> str:
    return v if isinstance(v, str) else ""


def read_file(path: Path, rep: Report, depth: int = 0) -> Bundle:
    """Parse one input (file, zip or folder) into characters and chats; never raises on a bad file (it is reported)."""
    b = Bundle(report=rep)
    where = path.name
    try:
        return _read_file(path, rep, depth, b)
    except ImportStop:
        raise
    except (ValueError, TypeError, KeyError, AttributeError, RecursionError, OSError, zipfile.BadZipFile) as e:
        rep.alerts.append(f"{where}: could not be read ({type(e).__name__}) — skipped")
        return Bundle(report=rep)


def _read_file(path: Path, rep: Report, depth: int, b: Bundle) -> Bundle:
    fmt = sniff(path)
    where = path.name
    if fmt == "folder":
        files = sorted(p for p in path.rglob("*") if p.is_file())[:MAX_ZIP_ENTRIES]
        for p in files:
            if _ACCOUNT_FILE.search(p.name):
                rep.count("account files never read (e-mail, birth date, settings…)"); continue
            sub = read_file(p, rep, depth)
            b.characters += sub.characters; b.chats += sub.chats
        return b
    if fmt in ("unknown", "unknown-json"):
        rep.alerts.append(f"{where}: not a recognised export (try `cof import --inspect {where}` and send the key tree)")
        return b
    rep.lines.append(f"{where}: {fmt}")
    if fmt in ("caitools-card-png", "card-png"):
        ch = _card_from_png(path.read_bytes(), fmt, where)
        if fmt == "card-png":
            ch.platform = "card"
        b.characters.append(ch)
        return b
    if fmt == "caitools-tavern-history":
        entries = list(_zip_entries(path, rep))
        entries.sort(key=lambda e: int(re.search(r"chat_(\d+)", e[0]).group(1)), reverse=True)    # chat_1 is the newest
        for k, (name, data) in enumerate(entries):
            c = parse_jsonl(_decode(data, rep, name), "caitools-tavern-history", rep, f"{where}/{name}", data)
            if c:
                c.order, c.raw_name, c.group_key, c.ordered = k, PurePosixPath(name).name, where, True
                b.chats.append(c)
        if b.chats:
            rep.lines.append(f"  {len(b.chats)} chats, ordered oldest first from the file numbers (chat_1 is the newest)")
        return b
    if fmt == "zip":
        if depth >= MAX_NEST:
            rep.alerts.append(f"{where}: archive nested too deep, skipped"); return b
        entries = list(_zip_entries(path, rep))
        def known_fmt(data):
            if data.startswith(PNG_SIG) or data.startswith(b"PK"):
                return "binary"
            t = data.decode("utf-8-sig", errors="replace")
            o = _json_or_none(t)
            return sniff_obj(o) if o is not None else sniff_jsonl(t)
        listed = [e for e in entries if e[0].lower().endswith((".json", ".jsonl", ".png", ".zip"))]
        if listed and all(known_fmt(d) for _, d in listed):        # a zip of known files (a folder zipped by the user)
            with tempfile.TemporaryDirectory(prefix="cof-import-") as td:
                for i, (name, data) in enumerate(listed):
                    base = re.sub(r"[^\w.\-]+", "-", PurePosixPath(name).name)[-80:].lstrip(".") or "entry"
                    p = Path(td) / f"{i:05d}-{base}"                # a generated name: no collision, no traversal, no '.'
                    try:
                        p.write_bytes(data)
                    except OSError:
                        rep.alerts.append(f"{where}: entry {_redact_name(name)} could not be unpacked, skipped"); continue
                    sub = read_file(p, rep, depth + 1)
                    for c in sub.chats:
                        c.source_file = f"{where}/{PurePosixPath(name).name}"
                    b.characters += sub.characters; b.chats += sub.chats
            return b
        chars, chats = _official(entries, rep, where)
        rep.lines[-1] = f"{where}: official-zip (tolerant reading: {len(chars)} character(s), {len(chats)} chat(s))"
        b.characters += chars; b.chats += chats
        return b
    raw = path.read_bytes()
    if len(raw) > MAX_FILE:
        rep.alerts.append(f"{where}: larger than {MAX_FILE // 2**20} MB, refused"); return b
    text = _decode(raw, rep, where)
    if fmt in ("caitools-tavern-chat", "sillytavern-jsonl"):
        c = parse_jsonl(text, fmt, rep, where, raw)
        if c:
            b.chats.append(c)
        return b
    obj = _json_or_none(text)
    if fmt == "personatext":
        ch, c = parse_personatext(obj, rep, where, raw)
        b.characters.append(ch)
        if c:
            b.chats.append(c)
    elif fmt in ("caitools-card-json", "card-json"):
        ch = Character(card=_flat_card(obj), fmt=fmt, source_file=where)
        if fmt == "card-json":
            ch.platform = "card"
        b.characters.append(ch)
    elif fmt == "caitools-histories-json":
        b.chats += parse_histories(obj, rep, where, raw)
    elif fmt == "oobabooga-json":
        c = parse_oobabooga(obj, rep, where, raw)
        if c:
            b.chats.append(c)
    return b


# ---------------------------------------------------------------- the card (RFC 0006 § 3.1)

_CAI_DUPES = {"char_name": "name", "char_persona": "description", "char_greeting": "first_mes", "world_scenario": "scenario", "example_dialogue": "mes_example"}


def _is_msg_array(v) -> bool:
    return isinstance(v, list) and any(isinstance(x, dict) and any(isinstance(x.get(k), str) for k in ("text", "mes", "content", "message", "raw_content")) for x in v)


def _purge_msg_arrays(o, depth: int = 0, out: list | None = None) -> list:
    """Removes every array of messages from a card, at any depth (the root, data, extensions, a tool's nested history —
    hunt CLI-3, STU-1); the lorebook (character_book) is the card's own text, never a conversation."""
    out = [] if out is None else out
    if depth > 64:
        return out
    if isinstance(o, dict):
        for k in list(o):
            if k == "character_book":
                continue
            if _is_msg_array(o[k]):
                del o[k]
                out.append(k)
            else:
                _purge_msg_arrays(o[k], depth + 1, out)
    elif isinstance(o, list):
        if any(_is_msg_array(x) for x in o):        # a list of conversations
            out.append("[conversations]")
            o[:] = [x for x in o if not _is_msg_array(x)]
        for x in o:
            _purge_msg_arrays(x, depth + 1, out)
    return out


def normalise_card(card: dict) -> dict:
    """A clean V2 card: foreign keys a tool added to `data` move to data.extensions.cai_tools (duplicates equal to their
    V2 key dropped), chat payloads removed (strip_card_payloads), text fields made strings, lists made lists. A
    malformed value is dropped and counted, never a crash."""
    import copy
    if not isinstance(card, dict):
        raise ValueError("a card must be a JSON object")
    card = copy.deepcopy(_flat_card(card))
    if not isinstance(card.get("data"), dict):
        raise ValueError("the card's data is not an object")
    data = card["data"]
    if not isinstance(data.get("extensions"), dict):
        data["extensions"] = {}
    strip_card_payloads(card)
    _purge_msg_arrays(card)                     # RFC 0006 § 3.1.2: a conversation never stays in the card, whatever its key or depth
    for k, v2 in _CAI_DUPES.items():            # a card with only the TavernAI keys: fill the V2 ones first
        if isinstance(data.get(k), str) and data[k].strip() and not (isinstance(data.get(v2), str) and data[v2].strip()):
            data[v2] = data[k]
    moved = {}
    for k in ("metadata", *_CAI_DUPES):
        if k in data:
            v = data.pop(k)
            if k in _CAI_DUPES and v == data.get(_CAI_DUPES[k]):
                continue
            moved[k] = v
    if moved:
        if not isinstance(data["extensions"].get("cai_tools"), dict):
            data["extensions"]["cai_tools"] = {}
        data["extensions"]["cai_tools"].update(moved)
    for k in ("name", "description", "personality", "scenario", "first_mes", "mes_example", "creator_notes", "system_prompt",
              "post_history_instructions", "creator", "character_version", "nickname"):
        if k in data and not isinstance(data[k], str):
            data[k] = ""
    for k in ("description", "personality", "scenario", "first_mes", "mes_example"):
        data.setdefault(k, "")
    for k in ("tags", "alternate_greetings", "source", "group_only_greetings"):
        if k in data and not (isinstance(data[k], list) and all(isinstance(x, str) for x in data[k])):
            data[k] = [x for x in data[k] if isinstance(x, str)] if isinstance(data[k], list) else []
    if "character_book" in data and not isinstance(data["character_book"], dict):
        del data["character_book"]
    data["name"] = re.sub(r"[\r\n\t]+", " ", data.get("name") or "").strip()     # one line; otherwise as written
    return card


def card_texts(card: dict) -> list:
    """Every string of the card's data (greetings, lorebook, system prompt, extensions…), one by one, for the keyword pass."""
    out, stack = [], [card.get("data") if isinstance(card, dict) else None]
    while stack:
        o = stack.pop()
        if isinstance(o, str):
            out.append(o)
        elif isinstance(o, dict):
            stack.extend(o.values())
        elif isinstance(o, list):
            stack.extend(o)
    return out


# ---------------------------------------------------------------- content keyword pass (RFC 0006 § 3.6) — no AI

# One content lexicon for the three implementations (cof import, the builder's <shared:cai-core>, the import page): the
# same words in the same order, compiled the same way — test_content_lexicon_is_the_same_in_python_and_js compares the
# lists. It only suggests the content tags (§ 3.6); it never stops an import. Words match whole (a letter or digit on
# neither side); CJK terms match anywhere. Text is NFKC-folded, zero-width characters and soft hyphens removed, lower-cased.
CONTENT_LEXICON = {
    "sexual": ["sex", "sexes", "sexual", "sexually", "sexy", "nude", "nudes", "naked", "porn\\w*", "fuck\\w*", "cum", "orgasm\\w*",
               "erotic\\w*", "nsfw", "horny", "intercourse", "lewd", "sexe", "sexuel\\w*", "nue?s?", "porno\\w*", "baiser", "jouir",
               "nackt\\w*", "sexuell\\w*", "geschlechtsverkehr", "sexo", "sexuales", "desnud[oa]s?", "follar", "coito"],
    "sexual_cjk": ["性交", "做爱", "做愛", "色情", "裸体", "裸體", "セックス", "性行為", "性行为", "エロ"],
    "violence": ["kill\\w*", "murder\\w*", "stab\\w*", "blood\\w*", "gore", "torture\\w*", "tuer", "meurtre\\w*", "torturer?"],
}


def _lex(words: list, cjk: list | None = None):
    pat = r"(?<![^\W_])(?:" + "|".join(words) + r")(?![^\W_])"
    if cjk:
        pat += "|" + "|".join(cjk)
    return re.compile(pat)


_RX = {"sexual": _lex(CONTENT_LEXICON["sexual"], CONTENT_LEXICON["sexual_cjk"]),
       "violence": _lex(CONTENT_LEXICON["violence"])}
_INVISIBLE = re.compile("[­​-‏⁠﻿]")


def fold(t: str) -> str:
    """What the keyword pass reads: NFKC (fullwidth letters, ligatures, the Kelvin sign…), no invisible characters, lower case."""
    return _INVISIBLE.sub("", unicodedata.normalize("NFKC", t)).lower()


def content_pass(texts) -> dict:
    """{'sexual': n, 'violence': n} over (where, text) pairs: a cheap pass, no AI, that only suggests the content tags."""
    found = {"sexual": 0, "violence": 0}
    for _where, t in texts:
        if not isinstance(t, str) or not t:
            continue
        t = fold(t)
        if _RX["sexual"].search(t):
            found["sexual"] += 1
        if _RX["violence"].search(t):
            found["violence"] += 1
    return found


# ---------------------------------------------------------------- transcript (RFC 0006 § 3.3)

def _iso(dt: datetime | None) -> str:
    return dt.strftime("%Y-%m-%dT%H:%M:%SZ") if dt else "undated"


def transcript_parts(chat: Chat, character: str, persona: str, source: str) -> list[str]:
    """The quoted-Markdown transcript, split above SPLIT_BYTES (each part with its own front matter)."""
    blocks = []
    for i, m in enumerate(chat.messages, 1):
        who = "[note]" if m.note else (persona if m.is_user else (m.speaker if m.speaker not in ("?", "", "Character", "assistant") else character))
        lines = re.split(r"\r\n|\r|\n", m.text)    # every line ending becomes \n: no line can escape its quote (RFC 0006 § 3.3)
        body = "\n".join(("> " + l) if l else ">" for l in lines)
        blocks.append(f"## {i} · {who} · {_iso(m.ts)}\n{body}\n")
    parts, cur, size = [], [], 0
    for b in blocks:
        n = len(b.encode("utf-8")) + 1              # + the newline that joins blocks
        if cur and size + n > SPLIT_BYTES:
            parts.append(cur); cur, size = [], 0
        cur.append(b); size += n
    parts.append(cur)
    first = min((m.ts for m in chat.messages if m.ts), default=None)      # the earliest and the latest, whatever the order (hunt CLI-12)
    last = max((m.ts for m in chat.messages if m.ts), default=None)
    out = []
    for k, p in enumerate(parts, 1):
        fm = ["---", "cof_transcript: 1", f"source: {source}", f"character: {_yaml(character)}", f"user_persona: {_yaml(persona)}",
              f"messages: {len(chat.messages)}", f"speaker_source: {chat.speaker_source}", f"dated: {'true' if chat.dated else 'false'}"]
        if chat.dated:
            fm += [f"first: {_iso(first)}", f"last: {_iso(last)}", "timezone: UTC"]
        if chat.source_file:
            fm.append(f"source_file: {_yaml(chat.raw_name or Path(chat.source_file).name)}")
        if len(parts) > 1:
            fm.append(f"part: {k}/{len(parts)}")
        fm += [f"exported_by: cof-cli {__version__}", "---", ""]
        out.append("\n".join(fm) + "\n" + "\n".join(p))
    return out


def _yaml(s: str) -> str:
    s = str(s).replace("\n", " ")
    return json.dumps(s, ensure_ascii=False) if re.search(r"[:#\[\]{}&*!|>'\"%@`,]|^\s|\s$|^-", s) or s == "" else s


def read_transcript(md: str) -> list[tuple[str, str]]:
    """(heading, text) pairs from a transcript: the inverse of the quoting (tests, and any reader)."""
    body = md.split("\n---\n", 1)[1] if md.startswith("---\n") else md
    out, head, lines = [], None, []
    for line in body.split("\n"):
        if line.startswith("## "):
            if head is not None:
                out.append((head, "\n".join(lines)))
            head, lines = line[3:], []
        elif head is not None and (line.startswith("> ") or line == ">"):
            lines.append(line[2:] if line.startswith("> ") else "")
    if head is not None:
        out.append((head, "\n".join(lines)))
    return out


# ---------------------------------------------------------------- language (RFC 0006: the card's and the chats')

_STOP = {
    "en": "the and you to of is it that in i my me your what this with for are was not have be but on so just do",
    "fr": "le la les et de des un une est je tu vous il elle pas que qui ne en du pour sur avec mais mon ton ça",
    "de": "der die das und ich du nicht ist ein eine zu mit den sie es was mir auf für aber wie dich",
    "es": "el la los las y de que en un una es no yo tu te por con para pero lo se mi más muy",
}
_STOPSETS = {k: set(v.split()) for k, v in _STOP.items()}


_UNSURE: dict = {}


def detect_lang(texts) -> str | None:
    """A cheap guess (no AI, no library): Japanese by kana, Chinese by Han characters, else the most frequent stop words
    of en / fr / de / es — None when the text is too short or the guess too close."""
    sample = " ".join(t for t in texts if isinstance(t, str))[:200_000]
    if not sample.strip():
        return None
    kana = len(re.findall(r"[\u3040-\u30ff]", sample))
    han = len(re.findall(r"[\u4e00-\u9fff]", sample))
    if kana > 20:
        return "ja"
    if han > 20:
        return "zh"
    words = re.findall(r"[a-zà-ÿñ]+", sample.lower())
    if len(words) < 20:
        return None
    score = {k: sum(1 for w in words if w in st) for k, st in _STOPSETS.items()}
    best = sorted(score.items(), key=lambda kv: -kv[1])
    if best[0][1] < 5 or best[0][1] < 1.5 * max(best[1][1], 1):
        return None
    return best[0][0]


# ---------------------------------------------------------------- gists (6 languages, mechanical)

# (moment gist, dated, undated, moment label, moment label with a title, period label, period gist, period gist for one conversation) — RFC 0006 § 3.2
_GIST = {
    "en": ("My conversation with {c} on {p}: {m} messages{d}. The verbatim transcript is attached (opened on demand).", ", from {a} to {b}",
           ", dates not in the export", "Chat {n}", "Chat {n} · {t}", "Conversations on {p}",
           "My conversations with {c} on {p}: {k} conversations, {m} messages{d}. Each one is a memory of its own, with its transcript.", "My conversation with {c} on {p}, {m} messages{d}. It is a memory of its own, with its transcript."),
    "fr": ("Ma conversation avec {c} sur {p} : {m} messages{d}. La transcription intégrale est jointe (ouverte à la demande).", ", du {a} au {b}",
           ", dates absentes de l'export", "Conversation {n}", "Conversation {n} · {t}", "Conversations sur {p}",
           "Mes conversations avec {c} sur {p} : {k} conversations, {m} messages{d}. Chacune est un souvenir à part, avec sa transcription.", "Ma conversation avec {c} sur {p}, {m} messages{d}. C'est un souvenir à part, avec sa transcription."),
    "de": ("Mein Gespräch mit {c} auf {p}: {m} Nachrichten{d}. Das wörtliche Protokoll liegt bei (wird bei Bedarf geöffnet).", ", vom {a} bis {b}",
           ", Daten nicht im Export", "Chat {n}", "Chat {n} · {t}", "Gespräche auf {p}",
           "Meine Gespräche mit {c} auf {p}: {k} Gespräche, {m} Nachrichten{d}. Jedes ist eine eigene Erinnerung, mit seinem Protokoll.", "Mein Gespräch mit {c} auf {p}, {m} Nachrichten{d}. Es ist eine eigene Erinnerung, mit seinem Protokoll."),
    "es": ("Mi conversación con {c} en {p}: {m} mensajes{d}. La transcripción literal va adjunta (se abre cuando se pide).", ", del {a} al {b}",
           ", fechas no incluidas en la exportación", "Chat {n}", "Chat {n} · {t}", "Conversaciones en {p}",
           "Mis conversaciones con {c} en {p}: {k} conversaciones, {m} mensajes{d}. Cada una es un recuerdo propio, con su transcripción.", "Mi conversación con {c} en {p}, {m} mensajes{d}. Es un recuerdo propio, con su transcripción."),
    "zh": ("我在 {p} 上与 {c} 的一次对话：共 {m} 条消息{d}。附有逐字记录（按需打开）。", "，从 {a} 到 {b}", "，导出文件中没有日期",
           "对话 {n}", "对话 {n} · {t}", "在 {p} 上的对话", "我在 {p} 上与 {c} 的对话：{k} 次对话，共 {m} 条消息{d}。每次对话都是一段独立的记忆，附有记录。", "我在 {p} 上与 {c} 的一次对话，共 {m} 条消息{d}。它是一段独立的记忆，附有记录。"),
    "ja": ("{p} での {c} との会話：メッセージ {m} 件{d}。逐語の記録を添付（必要なときに開く）。", "、{a} から {b} まで", "、エクスポートに日付なし",
           "会話 {n}", "会話 {n} · {t}", "{p} での会話", "{p} での {c} との会話：会話 {k} 件、メッセージ {m} 件{d}。それぞれが記録つきの独立した記憶です。", "{p} での {c} との会話 1 件、メッセージ {m} 件{d}。記録つきの独立した記憶です。"),
}


CAI_OPENED = 2022                               # Character.AI's public beta (September 2022): no chat is older

_UNDATED = {"en": "on Character.AI, between {a} and {b} (exact dates not in the export)",
            "fr": "sur Character.AI, entre {a} et {b} (dates exactes absentes de l'export)",
            "de": "auf Character.AI, zwischen {a} und {b} (genaue Daten nicht im Export)",
            "es": "en Character.AI, entre {a} y {b} (fechas exactas no incluidas en la exportación)",
            "zh": "在 Character.AI 上，{a} 年至 {b} 年之间（导出文件中没有确切日期）",
            "ja": "Character.AI で、{a} 年から {b} 年のあいだ（エクスポートに正確な日付なし）"}


def undated_label(lang: str, export_year: int | None) -> str:
    b = export_year or datetime.now(timezone.utc).year
    return _UNDATED.get(lang.split("-")[0].lower(), _UNDATED["en"]).format(a=CAI_OPENED, b=max(b, CAI_OPENED))


def _g(lang: str) -> tuple:
    return _GIST.get(lang.split("-")[0].lower(), _GIST["en"])


def chat_title(ch) -> str:
    """A title for a conversation the export does not name (RFC 0006 § 3.2): the start of the user's first message, else of
    the first message — whitespace collapsed, 48 characters at most, cut at a space when one is near, « … » when cut."""
    first = next((m for m in ch.messages if m.is_user and not m.note and m.text.strip()), None) \
        or next((m for m in ch.messages if not m.note and m.text.strip()), None)
    if not first:
        return ""
    t = " ".join(first.text.split())
    if len(t) <= 48:
        return t
    cut = t[:48]
    sp = cut.rfind(" ")
    if sp >= 24:
        cut = cut[:sp]
    return cut.rstrip(" .,;:") + "…"


def gist(lang: str, character: str, platform: str, n: int, m: int, a: str | None, b: str | None, title: str = "") -> tuple[str, str]:
    g = _g(lang)
    d = g[1].format(a=a, b=b) if a else g[2]
    p = PLATFORM.get(platform, platform)
    return g[0].format(c=character, p=p, m=m, d=d), (g[4].format(n=n, t=title) if title else g[3].format(n=n))


def period_gist(lang: str, character: str, platform: str, k: int, m: int, a: str | None, b: str | None) -> tuple[str, str]:
    g = _g(lang)
    d = g[1].format(a=a, b=b) if a else g[2]
    p = PLATFORM.get(platform, platform)
    return g[6 if k > 1 else 7].format(c=character, p=p, k=k, m=m, d=d), g[5].format(p=p)


# ---------------------------------------------------------------- writer

@dataclass
class Options:
    lang: str = "en"
    age: dict = field(default_factory=dict)          # name or "" → (value, basis)
    real: bool = False
    original: bool = False
    persona: str | None = None
    no_avatar: bool = False
    no_chats: bool = False
    keep_source: bool = False
    content: list | None = None
    apparent: bool = False
    card_lang: str | None = None                 # None = detected from the card, else --lang, else en


def _age_for(opts: Options, name: str):
    return opts.age.get(name.lower(), opts.age.get(""))


def _key(n) -> str:
    """How two names are compared: the speaker form (« · » → « - », 80 characters), NFC, case-folded (hunt CLI-7, CLI-8)."""
    return unicodedata.normalize("NFC", clean_speaker(n)).casefold() if n else ""


def group(bundle: Bundle) -> list[tuple[Character, list]]:
    """Characters with their chats: by name; a lone character takes every chat; chats with no character get one made
    from the chat's character NAME only (never its text: a conversation never goes into the card), never discarded."""
    by_name = {}
    for c in bundle.characters:
        if c.name and _key(c.name) in by_name:
            bundle.report.alerts.append(f"{c.source_file}: a second card for {c.name} ignored (the first one is kept)")
            continue
        by_name[_key(c.name)] = (c, [])
    orphans = []
    for chat in bundle.chats:
        key = _key(chat.character)
        if key and key in by_name:
            by_name[key][1].append(chat)
        elif len(by_name) == 1 and (not key or _same_person(key, next(iter(by_name)))):
            only = next(iter(by_name.values()))
            if key:
                bundle.report.alerts.append(f"{chat.source_file}: chat with {chat.character!r} attached to {only[0].name!r} (same first name)")
            only[1].append(chat)
        else:
            orphans.append(chat)
    for chat in orphans:
        name = chat.character or "Unknown character"
        if _key(name) not in by_name:
            card = {"spec": "chara_card_v2", "spec_version": "2.0", "data": {"name": name, "description": "", "personality": "", "scenario": "",
                    "first_mes": "", "mes_example": "", "creator": "", "tags": [], "extensions": {}}}
            by_name[_key(name)] = (Character(card=card, fmt="from-chat", platform=chat.platform, source_file=chat.source_file), [])
            bundle.report.alerts.append(f"no card for {name!r}: character made with its name only (the conversation stays in the memories)")
        by_name[_key(name)][1].append(chat)
    out = []
    for c, chats in by_name.values():
        seen, keep = set(), []
        for ch in sorted(chats, key=lambda x: (x.group_key, x.order, x.source_file)):
            h = hashlib.sha256("\x00".join(unicodedata.normalize("NFC", m.text.strip()) for m in ch.messages).encode()).hexdigest()
            if h in seen:
                bundle.report.alerts.append(f"{ch.source_file}: same conversation as another file, imported once")
                continue
            seen.add(h); keep.append(ch)
        dated = sorted([x for x in keep if x.dated], key=lambda x: next(m.ts for m in x.messages if m.ts))
        undated = [x for x in keep if not x.dated]
        out.append((c, dated + undated))
    return out


def _same_person(a: str, b: str) -> bool:
    """'wren' and 'wren calloway' are one character; 'mira' and 'wren calloway' are two."""
    wa, wb = a.split(), b.split()
    return bool(wa and wb) and (wa == wb[:len(wa)] or wb == wa[:len(wb)])


@dataclass
class Plan:
    char: Character
    chats: list
    card: dict
    name: str
    flags: dict                                # keyword pass on the card
    chat_flags: dict                           # keyword pass on the conversations (reported, never written)
    avatar: bytes | None
    age: float | None
    basis: str
    sources: list
    dest: Path | None = None
    card_lang: str = "en"
    chat_lang: str = "en"


def plan_character(char: Character, chats: list, opts: Options) -> Plan:
    """Every check that can stop an import, with nothing written: card shape, the avatar's age (RFC 0006 § 3.1.6); and the
    content suggestion (§ 3.6) over every string of the card and every message."""
    card = normalise_card(char.card)
    name = card["data"].get("name") or (clean_speaker(chats[0].character) if chats and chats[0].character else "") or "Unnamed"
    name = " ".join(str(name).split())[:120].strip() or "Unnamed"       # a variant label holds 120 characters at most
    card["data"]["name"] = name
    fm = " ".join(_s(card["data"].get("first_mes")).split())
    for ch in chats:                            # CAI Tools may swap you and the character (its known issue): the card's greeting
        m0 = ch.messages[0] if ch.messages else None   # credited to you gives it away; turned back and said (hunt DES-2)
        if fm and m0 and m0.is_user and not m0.note and " ".join(m0.text.split()) == fm:
            for m in ch.messages:
                if not m.note:
                    m.is_user = not m.is_user
                    if not m.is_user:
                        m.speaker = name            # the user's lines become the character's, under its name
            ch.speaker_source = "swapped"
    flags = content_pass([(f"{name}: card", x) for x in card_texts(card)])
    chat_flags = content_pass([(f"{name}: chat {k}, message {i}", m.text) for k, ch in enumerate(chats, 1) for i, m in enumerate(ch.messages, 1)]
                              + [(f"{name}: chat {k}, source file", ch.raw.decode("utf-8", "replace")) for k, ch in enumerate(chats, 1)
                                 if opts.keep_source and ch.raw]) \
        if not opts.no_chats else {"sexual": 0, "violence": 0}   # --keep-source copies swipes too: they are read (hunt CLI-4)
    avatar = None if opts.no_avatar else char.avatar
    age = _age_for(opts, name)
    if avatar and age is None:
        raise ImportStop(f"{name}: the avatar needs an age (COF requires one for every face). Give it with --age N "
                         f"(declared; --age {_q(name + '=N')} when several characters), add --apparent for an apparent age, "
                         "or import without the avatar: --no-avatar. Nothing written.", 3)
    sources = []
    if char.fmt != "from-chat":
        sources.append(f"import:{char.platform}/{char.fmt}")
    if not opts.no_chats:
        sources += [f"import:{ch.platform}/{ch.fmt}" for ch in chats]
    texts = [m.text for ch in chats for m in ch.messages][:5000]
    dl, dc = detect_lang(texts), detect_lang(card_texts(card))
    chat_lang = opts.lang or dl or "en"
    card_lang = opts.card_lang or dc or opts.lang or chat_lang
    _UNSURE[id(card)] = (not opts.lang and not dl, not opts.card_lang and not dc)   # « en by default », never « detected » (hunt CLI-14)
    if avatar and age is not None and age < 18 and {"sexual", "nudity"} & set(opts.content or []):
        raise ImportStop(f"{name}: a face under 18 cannot be tagged sexual or nudity (COF's age rule). Check the age (--age) or the "
                         "content (--content); nothing was written.", 2)
    return Plan(char=char, chats=chats, card=card, name=name, flags=flags, chat_flags=chat_flags, avatar=avatar, age=age,
                basis="apparent" if opts.apparent else "declared", sources=_uniq(sources), card_lang=card_lang, chat_lang=chat_lang)


_RESERVED = {"con", "prn", "aux", "nul", *(f"com{i}" for i in range(1, 10)), *(f"lpt{i}" for i in range(1, 10))}


def folder_name(name: str) -> str:
    """A folder name from a character's name, any script (ウィン stays ウィン), safe on Windows."""
    n = re.sub(r"[^\w.\-]+", "-", unicodedata.normalize("NFC", name)).strip("-. ")[:80] or "character"
    return n + "-cof" if n.lower() in _RESERVED else n


def assign_destinations(plans: list, out: Path | None):
    """Unique destinations, checked before anything is written: an existing non-empty folder stops the whole import."""
    used = set()
    for pl in plans:
        if out is not None and len(plans) == 1:
            dest = out
        else:
            base = folder_name(pl.name)
            n, k = base, 2
            while n.lower() in used:
                n, k = f"{base}-{k}", k + 1
            used.add(n.lower())
            dest = (out / n) if out is not None else Path(n)
        if dest.exists() and (not dest.is_dir() or any(dest.iterdir())):
            raise ImportStop(f"{dest}: exists and is not an empty folder — choose another -o. Nothing written.", 2)
        pl.dest = dest


def write_character(pl: Plan, opts: Options, rep: Report) -> Path:
    """One COF folder from a checked plan: the character (RFC 0006 § 3.1) one personal period per platform and one personal moment per chat, part-of it (§ 3.2-3.4).
    Built in a temporary folder, moved into place at the end."""
    char, chats, name, avatar, av_val, basis = pl.char, pl.chats, pl.name, pl.avatar, pl.age, pl.basis
    if char.avatar and opts.no_avatar:
        rep.alerts.append(f"{name}: avatar left out on request (--no-avatar)")
    tmp = Path(tempfile.mkdtemp(prefix="cof-import-"))
    try:
        work = tmp / "x"
        card_to_cof_dir(pl.card, work, png=avatar if (avatar and char.avatar_type == "image/png") else None, age=av_val if avatar else None,   # no face, no age (hunt CLI-18)
                        fictional=not opts.real, language=pl.card_lang, removed=[])
        lang = pl.chat_lang
        mpath = work / "manifest.json"
        m = json.loads(mpath.read_text("utf-8"))
        if avatar and char.avatar_type != "image/png":
            ext = {"image/webp": "webp", "image/jpeg": "jpg"}[char.avatar_type]
            fdir = work / "elements" / "appearance" / "f1"; fdir.mkdir(parents=True, exist_ok=True)
            (fdir / f"head.front.{ext}").write_bytes(avatar)
            m["assets"].append({"id": "a-face-f1-front", "path": f"elements/appearance/f1/head.front.{ext}", "role": "view", "subject": "head",
                                "angle": "front", "framing": "head", "mediaType": char.avatar_type, "bytes": len(avatar),
                                "sha256": hashlib.sha256(avatar).hexdigest(), "license": "LicenseRef-Unknown"})
            m["elements"]["appearance"] = {"variants": {"f1": {"kind": "face", "label": "Face (avatar)", "images": ["a-face-f1-front"],
                                                               "age": {"value": av_val, "unit": "years", "basis": basis}}}}
            m["presets"]["default"]["slots"]["appearance"] = ["f1"]
        if avatar:
            m["elements"]["appearance"]["variants"]["f1"]["age"]["basis"] = basis
            m["elements"]["appearance"]["variants"]["f1"]["label"] = "Face (avatar)"
        if "age_override" in m["presets"]["default"]:
            m["presets"]["default"]["age_override"]["basis"] = basis
        m["presets"]["default"]["label"] = m["name"]   # the explorer lists presets by label: the character's name, not « Default »
        tags = m["tags"]
        tags["ip"] = {"original": bool(opts.original), "franchise": None, "based_on": None}       # § 3.1.3, whatever the card
        plat = char.platform if char.platform != "card" else (chats[0].platform if chats else "card")
        if plat != "card":
            tags["manual"] = _uniq(tags.get("manual", []) + [f"imported-{_slug(plat)}"])
        # the explorer's left column filters presets by these facets: the avatar's age and where the character comes from
        ptags = []
        if avatar and av_val is not None:
            lab = str(int(av_val)) if float(av_val).is_integer() else str(av_val)
            ptags.append({"id": "age-" + lab.replace(".", "-"), "label": lab, "facet": "age", "presets": ["default"]})
        if plat != "card":
            ptags.append({"id": _slug(plat), "label": PLATFORM.get(plat, plat), "facet": "source", "presets": ["default"]})
        if ptags:
            m["preset_tags"] = ptags
        # content (§ 3.6): what the card shows; the conversations' flags are reported, never written (they would outlive
        # the personal memories in an extracted file)
        if opts.content:
            tags["content"] = opts.content
        else:
            minor_face = pl.avatar is not None and pl.age is not None and pl.age < 18          # COF's age rule: never sexual for a minor face
            flagged = [k for k in ("sexual", "violence") if pl.flags[k] and not (k == "sexual" and minor_face)]
            tags["content"] = flagged or ["none"]
            tags["manual"] = _uniq(tags.get("manual", []) + ["content-unreviewed"])
            if flagged:
                rep.alerts.append(f"{name}: the card mentions {', '.join(flagged)} — tags.content set to it; confirm after reading (--content …)")
        ours = [x for x in tags.get("manual", []) if x == "content-unreviewed" or x.startswith("imported-")]
        if len(tags.get("manual", [])) > 30:                # the schema holds 30: the card's own tags give way to ours (hunt CLI-11)
            tags["manual"] = [x for x in tags["manual"] if x not in ours][:30 - len(ours)] + ours
        cf = [f"{k} ({pl.chat_flags[k]} message(s))" for k in ("sexual", "violence") if pl.chat_flags[k]]
        if cf:
            rep.alerts.append(f"{name}: your conversations mention {', '.join(cf)} — they stay personal; not written in tags.content")
        m["provenance"]["source"] = _uniq(list(m["provenance"].get("source") or []) + pl.sources)
        creator = str(pl.card["data"].get("creator") or "").strip()
        if creator:
            m["metadata"]["dc:creator"] = [creator]
        n_msgs = 0
        if chats and not opts.no_chats:
            V = m["elements"].setdefault("memories", {}).setdefault("variants", {})
            slots = m["presets"]["default"]["slots"].setdefault("memories", [])
            prev = None
            default_persona = next((c.persona for c in chats if c.persona), None)
            # RFC 0006 § 3.2: one period per platform (« Conversations on Character.AI »), each conversation a moment
            # linked `part-of` it — an undated moment needs no date to sit in its period
            periods = {}
            for ch in chats:
                periods.setdefault(ch.platform, []).append(ch)
            pid_of = {}
            for k, ch in enumerate(chats, 1):
                if ch.platform not in pid_of:
                    grp = periods[ch.platform]
                    pid = f"ep{len(pid_of) + 1}"
                    pid_of[ch.platform] = pid
                    gp = clean_speaker(opts.persona or next((c.persona for c in grp if c.persona), None) or default_persona or "You")
                    ts = [x.ts for c in grp for x in c.messages if x.ts]
                    all_dated = all(c.dated for c in grp) and ts
                    g, plabel = period_gist(lang, name, ch.platform, len(grp), sum(len(c.messages) for c in grp),
                                            min(ts).date().isoformat() if all_dated else None, max(ts).date().isoformat() if all_dated else None)
                    pnode = {"gist": {lang: g}, "nature": ["experienced"]}
                    if all_dated:
                        pnode["when"] = {"from": {"date": min(ts).date().isoformat()}, "to": {"date": max(ts).date().isoformat()}}
                    elif ch.platform == "character.ai":   # undated chats: the period spans the service's lifetime, both bounds approximate
                        yb = max((c.export_year or 0) for c in grp) or datetime.now(timezone.utc).year
                        pnode["when"] = {"from": {"date": str(CAI_OPENED), "approx": True}, "to": {"date": str(max(yb, CAI_OPENED)), "approx": True},
                                         "label": {lang: undated_label(lang, yb)}}
                    pnode["who"] = [{"label": {lang: gp}}]
                    pnode.update({"fidelity": "clear", "origin": "lived", "visibility": "personal", "disclosure": "guarded", "tags": [_slug(ch.platform), "imported"]})
                    d = work / "elements" / "memories" / pid
                    d.mkdir(parents=True, exist_ok=True)
                    (d / "memory.json").write_text(json.dumps(pnode, ensure_ascii=False, indent=2) + "\n", "utf-8")
                    V[pid] = {"kind": "period", "label": plabel, "memory": f"elements/memories/{pid}/memory.json"}
                    slots.append(pid)
                vid = f"ev{k}"
                persona = clean_speaker(opts.persona or ch.persona or default_persona or "You")   # a chat without a name takes the one another chat gives
                for msg in ch.messages:
                    if msg.is_user and not msg.note:
                        msg.speaker = persona
                first = min((x.ts for x in ch.messages if x.ts), default=None)
                last = max((x.ts for x in ch.messages if x.ts), default=None)
                g, label = gist(lang, name, ch.platform, k, len(ch.messages), first.date().isoformat() if first else None,
                                last.date().isoformat() if last else None, chat_title(ch))
                node = {"gist": {lang: g}, "nature": ["experienced"]}
                if ch.dated and first:
                    node["when"] = {"date": first.date().isoformat()}
                node["who"] = [{"label": {lang: persona}}]
                node.update({"fidelity": "clear", "origin": "lived", "visibility": "personal", "disclosure": "guarded",
                             "tags": [_slug(ch.platform), "imported"]})
                links = [{"to": f"memories/{pid_of[ch.platform]}", "type": "part-of"}]
                # § 3.2: `after` only between consecutive undated chats of one export that gives their order
                if prev is not None and not ch.dated and not prev.dated and ch.ordered and prev.ordered and ch.group_key == prev.group_key:
                    links.append({"to": f"memories/ev{k - 1}", "type": "after"})
                node["links"] = links
                d = work / "elements" / "memories" / vid
                d.mkdir(parents=True, exist_ok=True)
                (d / "memory.json").write_text(json.dumps(node, ensure_ascii=False, indent=2) + "\n", "utf-8")
                parts = transcript_parts(ch, name, persona, f"import:{ch.platform}/{ch.fmt}")
                media = []
                for pi, text in enumerate(parts, 1):
                    fn = f"chat-{k}.md" if len(parts) == 1 else f"chat-{k}.part-{pi}.md"
                    data = text.encode("utf-8")
                    (d / fn).write_bytes(data)
                    aid = f"a-mem-{vid}-chat-{k}" + ("" if len(parts) == 1 else f"-part-{pi}")
                    m["assets"].append({"id": aid, "path": f"elements/memories/{vid}/{fn}", "role": "memory-media", "mediaType": "text/markdown",
                                        "language": lang, "bytes": len(data), "sha256": hashlib.sha256(data).hexdigest(),
                                        "license": "LicenseRef-Personal", "digitalSourceType": COMPOSITE})
                    media.append(aid)
                if opts.keep_source:
                    if ch.raw:
                        fn = "source-" + re.sub(r"[^A-Za-z0-9._-]+", "-", ch.raw_name or "chat.json")
                        (d / fn).write_bytes(ch.raw)
                        aid = f"a-mem-{vid}-source"
                        m["assets"].append({"id": aid, "path": f"elements/memories/{vid}/{fn}", "role": "memory-media",
                                            "mediaType": "application/x-ndjson" if fn.endswith(".jsonl") else "application/json",
                                            "bytes": len(ch.raw), "sha256": hashlib.sha256(ch.raw).hexdigest(), "license": "LicenseRef-Personal",
                                            "digitalSourceType": COMPOSITE})
                        media.append(aid)
                    else:
                        rep.count("source files not kept (an export file that may hold account data: only the transcript is written)")
                V[vid] = {"kind": "moment", "label": label, "memory": f"elements/memories/{vid}/memory.json", "media": media}
                slots.append(vid)
                prev = ch
                n_msgs += len(ch.messages)
                if ch.speaker_source != "platform":
                    how = {"names": "from the names", "swapped": "the export had you and the character swapped — the card's greeting was yours; turned back"}.get(ch.speaker_source, "greeting first, then turns")
                    heads = [f"{'You' if x.is_user else name}: {x.text[:40]!r}" for x in ch.messages[:3]]
                    rep.alerts.append(f"{name}, chat {k}: who speaks was inferred ({how}) — check: " + " | ".join(heads))
            m["cof"] = "1.1" if str(m.get("cof", "1.0")) == "1.0" else m["cof"]
            m["languages"] = _uniq(list(m.get("languages") or []) + [lang])
            cov = m.setdefault("coverage", {})
            cov["elements"] = sorted(set(cov.get("elements") or []) | {"memories"})
        mpath.write_text(json.dumps(m, ensure_ascii=False, indent=2) + "\n", "utf-8")
        unsure_chat, unsure_card = _UNSURE.get(id(pl.card), (False, False))
        how = lambda given, v, unsure: f"{v} ({'given' if given else 'not detected — set it' if unsure else 'detected'})"
        rep.lines.append(f"{name}: languages — card {how(opts.card_lang, pl.card_lang, unsure_card)}"
                         + (f", conversations {how(opts.lang, lang, unsure_chat)}" if n_msgs else "") + " (--card-lang / --lang to change)")
        rep.lines.append(f"{name}: {len(chats) if not opts.no_chats else 0} chat(s), {n_msgs} message(s)"
                         + (f", avatar kept (age {av_val}, {basis})" if avatar else (", no avatar in the export" if not char.avatar else "")))
        dest = pl.dest
        if dest.exists():
            dest.rmdir()                          # checked empty by assign_destinations
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.move(str(work), str(dest))
        return dest
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def _q(s: str) -> str:
    return json.dumps(s, ensure_ascii=False) if re.search(r"\s", s) else s


def _slug(s: str) -> str:
    return re.sub(r"[^a-z0-9-]+", "-", unicodedata.normalize("NFKD", str(s)).encode("ascii", "ignore").decode().lower()).strip("-") or "x"


def _uniq(xs: list) -> list:
    out = []
    for x in xs:
        if x not in out:
            out.append(x)
    return out


def parse_age(values: list | None) -> dict:
    """--age 30 | --age "Wren Calloway=30" (repeatable) → {name|"" : value}."""
    out = {}
    for v in values or []:
        v = str(v)
        name, _, num = v.rpartition("=") if "=" in v else ("", "", v)
        try:
            n = float(num)
        except ValueError:
            raise ValueError(f"--age {v!r}: expected a number of years, or NAME=N")
        if not (0 <= n <= 10000):
            raise ValueError(f"--age {v!r}: out of range")
        out[name.strip().lower() if name else ""] = int(n) if n == int(n) else n
    return out
