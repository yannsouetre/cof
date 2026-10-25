"""Reading the `memories` category (RFC 0002): node files, timeline order, gist language, effective media.

Shared by the validator, `cof export --agent`, `cof extract` and the coherence checks. Nothing here writes a file.
"""
from __future__ import annotations

import json
import re
from pathlib import Path

from .model import asset_index, first, resolve_preset_slots, resolve_variant, resolved, variant_owner

FIDELITY_WEIGHT = {"vivid": 1.0, "clear": 0.7, "faded": 0.4, "fragment": 0.15}     # RFC 0002 § 4.2, normative table


def load_nodes(src: Path, manifest: dict) -> dict[str, dict]:
    """variant id → node (memory.json content) for every memory variant whose file is readable."""
    out: dict[str, dict] = {}
    for vid in ((manifest.get("elements") or {}).get("memories") or {}).get("variants") or {}:
        rv = resolve_variant(manifest, "memories", vid) or {}
        rel = rv.get("memory")
        if not rel:
            continue
        try:
            node = json.loads((src / rel).read_text("utf-8"))
        except Exception:
            continue
        if isinstance(node, dict):
            out[vid] = node
    return out


def _age(a) -> float | None:
    if not isinstance(a, dict) or not isinstance(a.get("value"), (int, float)):
        return None
    return a["value"] / 12 if a.get("unit") == "months" else float(a["value"])


def _year(d) -> float | None:
    """Partial ISO date → a fractional year (YYYY, YYYY-MM, YYYY-MM-DD)."""
    if not isinstance(d, str):
        return None
    m = re.match(r"^(-?\d{1,4})(?:-(\d{2})(?:-(\d{2}))?)?$", d)
    if not m:
        return None
    y = int(m.group(1)); mo = int(m.group(2) or 7); da = int(m.group(3) or 15)
    return y + (mo - 1) / 12 + (da - 1) / 365


def node_point(kind: str | None, node: dict) -> tuple[float | None, float | None]:
    """(age, date-as-year) of a node: the point of a moment, the start of a period."""
    w = node.get("when") or {}
    if kind == "period":
        p = w.get("from") or w.get("to") or {}
        return _age(p.get("age")), _year(p.get("date"))
    return _age(w.get("age")), _year(w.get("date"))


def birth_years(manifest: dict, nodes: dict[str, dict]) -> list[float]:
    """Every birth year implied by a node carrying both an age and a date (RFC 0002 § 4.3)."""
    out = []
    for vid, node in nodes.items():
        kind = (resolve_variant(manifest, "memories", vid) or {}).get("kind")
        a, y = node_point(kind, node)
        if a is not None and y is not None:
            out.append(y - a)
    return out


def timeline(manifest: dict, nodes: dict[str, dict], vids: list[str]) -> list[str]:
    """Order `vids` by age, else by date (an age derived from the implied birth year when the file gives one),
    else after the node an `after` / `part-of` link points to, else undated (kept last, in file order)."""
    by = birth_years(manifest, nodes)
    birth = sorted(by)[len(by) // 2] if by else None
    key: dict[str, float] = {}
    for vid in vids:
        node = nodes.get(vid) or {}
        kind = (resolve_variant(manifest, "memories", vid) or {}).get("kind")
        a, y = node_point(kind, node)
        if a is None and y is not None and birth is not None:
            a = y - birth
        if a is None and y is not None:
            a = 10_000 + y                      # dated but no age anywhere in the file: dates sort together, after ages
        if a is not None:
            key[vid] = a
    for _ in range(len(vids)):                  # linked nodes take the position of their target (+ epsilon); fixed point
        changed = False
        for vid in vids:
            if vid in key:
                continue
            for ln in (nodes.get(vid) or {}).get("links") or []:
                cat, _, tgt = str(ln.get("to", "")).partition("/")
                if cat == "memories" and tgt in key and ln.get("type") in ("after", "part-of", "about", "same-event", "because"):
                    key[vid] = key[tgt] + 0.001; changed = True; break
        if not changed:
            break
    dated = sorted((v for v in vids if v in key), key=lambda v: (key[v], vids.index(v)))
    return dated + [v for v in vids if v not in key]


def preset_memories(manifest: dict, pid: str | None) -> list[str]:
    """The memory variant ids a preset lists (through `extends`), in slot order."""
    slots = resolve_preset_slots(manifest, pid) if pid else {}
    return list(slots.get("memories") or [])


def preset_language(manifest: dict, pid: str | None) -> str | None:
    """The language of the personality the preset applies, else nothing (RFC 0002 § 3 reading rule, step 1)."""
    if not pid:
        return None
    p = first(resolved(manifest, pid), "personality")
    return (p or {}).get("language")


def gist_text(manifest: dict, vid: str, node: dict, pid: str | None = None) -> tuple[str, str]:
    """(language, text): the preset's personality language → the identity's primary language → the only / first entry."""
    gist = node.get("gist") or {}
    if not gist:
        return "", ""
    want = []
    pl = preset_language(manifest, pid)
    if pl:
        want.append(pl)
    me = variant_owner(manifest, "memories", vid)
    il = ((manifest.get("identities") or {}).get(me) or {}).get("language") if me else None
    if il:
        want.append(il)
    low = {k.lower(): k for k in gist}
    for w in want:
        w = w.lower()
        if w in low:
            return low[w], gist[low[w]]
        base = w.split("-")[0]
        for k in low:                            # fr-CA matches fr
            if k.split("-")[0] == base:
                return low[k], gist[low[k]]
    k = next(iter(gist))
    return k, gist[k]


def text_in(obj: dict | None, lang: str) -> str:
    """A language-keyed label in the wanted language, else its first entry."""
    if not isinstance(obj, dict) or not obj:
        return ""
    low = {k.lower(): v for k, v in obj.items()}
    return low.get(lang.lower()) or low.get(lang.split("-")[0].lower()) or next(iter(obj.values()))


def effective_media(manifest: dict, vid: str) -> list[str]:
    """Asset ids of a node's media, following `media_from` (RFC 0002 § 4.5); a cycle yields nothing."""
    seen, cur = set(), vid
    while cur and cur not in seen:
        seen.add(cur)
        rv = resolve_variant(manifest, "memories", cur) or {}
        if rv.get("media"):
            return list(rv["media"])
        cur = str(rv.get("media_from") or "").partition("/")[2]
    return []


def when_label(kind: str | None, node: dict, lang: str) -> str:
    """A short, human marker for the timeline: '8 ans', 'age 24–28', '2026-03', or the author's label."""
    w = node.get("when") or {}
    lab = text_in(w.get("label"), lang)
    if kind == "period":
        f, t = w.get("from") or {}, w.get("to") or {}
        fa, ta = _age(f.get("age")), _age(t.get("age"))
        if fa is not None or ta is not None:
            fig = f"age {fa:g}" if ta is None else (f"until age {ta:g}" if fa is None else f"age {fa:g}–{ta:g}")
        else:
            fig = " – ".join(x for x in (f.get("date"), t.get("date")) if x)
    else:
        a = _age(w.get("age"))
        fig = (("~" if w.get("approx") else "") + f"age {a:g}") if a is not None else ""
        if w.get("date"):
            fig = f"{fig}, {w['date']}" if fig else w["date"]
    if lab and fig:
        return f"{lab} ({fig})"
    return lab or fig


def shows_other_real_person(manifest: dict, vid: str, node: dict, kept_identities: set[str], identities: dict | None = None) -> bool:
    """Does a media of this node show a real person who is not one of `kept_identities`? (extraction guard, § 4.5)
    `identities`: the table to look real persons up in (the source file's, when the manifest is an extract)."""
    ids = identities if identities is not None else (manifest.get("identities") or {})
    for w in node.get("who") or []:
        if not w.get("shown"):
            continue
        iid = w.get("identity")
        if iid == "self" or iid is None:
            if iid is None and w.get("real"):
                return True
            continue
        if iid in kept_identities:
            continue
        if iid not in ids or (ids.get(iid) or {}).get("fictional") is False:      # unknown identity = no consent record = real for safety
            return True
    return False


def media_assets(manifest: dict, vid: str) -> list[dict]:
    A = asset_index(manifest)
    return [A[i] for i in effective_media(manifest, vid) if i in A]
