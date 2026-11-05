"""The `psyche` category (RFC 0004, COF 1.2): node files, the nodes a preset holds, the gist language, the
"Who she is" section of SOUL.md, and the purges (personal nodes, declared risk) shared by `cof extract` and
`cof export --format agent`. The validator's semantic rules live in validate.py; `cof psyche add` in selfdesc.py.
"""
from __future__ import annotations

import json
import re
import shutil
from pathlib import Path

from .model import resolve_preset_slots, resolve_variant

KINDS = ("value", "belief", "want", "need", "fear", "wound", "stance", "taste", "habit", "contradiction", "rule")
KIND_ORDER = ("wound", "value", "belief", "want", "need", "fear", "stance", "taste", "habit", "contradiction", "rule")   # SOUL.md, § 3 quinquies
ID_PREFIX = {"value": "val", "belief": "bel", "want": "want", "need": "need", "fear": "fear", "wound": "wound", "stance": "stance",
             "taste": "taste", "habit": "hab", "contradiction": "contra", "rule": "rule"}                                 # § 3 bis
RISK_TAGS = {"inappropriate": "psyche-inappropriate", "dangerous": "psyche-dangerous"}                                   # node risk → tags.content (§ 3 septies)
STABILITIES = ("core", "settled", "shifting", "fragile")
FULL_LINE_STRENGTH = 70                                                                                                   # at or above: the whole gist; below: a short clause


def load_nodes(src: Path, manifest: dict) -> dict[str, dict]:
    """variant id → node (psyche-node.json content) for every psyche variant whose file is readable."""
    out: dict[str, dict] = {}
    for vid in ((manifest.get("elements") or {}).get("psyche") or {}).get("variants") or {}:
        rel = (resolve_variant(manifest, "psyche", vid) or {}).get("node")
        if not rel:
            continue
        try:
            node = json.loads((src / rel).read_text("utf-8"))
        except Exception:
            continue
        if isinstance(node, dict):
            out[vid] = node
    return out


def preset_nodes(manifest: dict, pid: str | None) -> list[str]:
    """The psyche variant ids a preset lists (through `extends`), in slot order."""
    return list((resolve_preset_slots(manifest, pid) if pid else {}).get("psyche") or [])


def node_kind(manifest: dict, vid: str) -> str | None:
    return (resolve_variant(manifest, "psyche", vid) or {}).get("kind")


def conflicts_of(node: dict) -> list[str]:
    """The psyche ids a contradiction's `conflicts` links point at."""
    return [str(ln.get("to", "")).partition("/")[2] for ln in node.get("links") or []
            if ln.get("type") == "conflicts" and str(ln.get("to", "")).startswith("psyche/")]


def prune_contradictions(manifest: dict, nodes: dict[str, dict], kept: list[str]) -> list[str]:
    """RFC 0004 § 3 sexies / § 3 septies: a contradiction whose two sides are not both kept is dropped too — the one
    rule for every purge (personal, risk, extraction). Returns `kept` without such contradictions, order preserved."""
    keep = list(kept)
    while True:
        gone = [v for v in keep if node_kind(manifest, v) == "contradiction" and sum(1 for t in conflicts_of(nodes.get(v) or {}) if t in keep) < 2]
        if not gone:
            return keep
        keep = [v for v in keep if v not in gone]


def select_nodes(manifest: dict, nodes: dict[str, dict], pid: str | None, keep_personal: bool = False, keep_dangerous: bool = False) -> tuple[list[str], dict]:
    """The nodes a preset renders for an agent: its list minus personal nodes (a user's data, § 3 ter) unless kept, minus
    `dangerous` nodes (an agent acts, § 3 septies) unless kept, minus the contradictions that lost a side.
    Returns (ids in slot order, counts of what was dropped)."""
    vids = [v for v in preset_nodes(manifest, pid) if v in nodes]
    stats = {"personal_dropped": 0, "dangerous_dropped": 0}
    keep = []
    for v in vids:
        n = nodes[v]
        if n.get("visibility") == "personal" and not keep_personal:
            stats["personal_dropped"] += 1; continue
        if n.get("risk") == "dangerous" and not keep_dangerous:
            stats["dangerous_dropped"] += 1; continue
        keep.append(v)
    pruned = prune_contradictions(manifest, nodes, keep)
    stats["contradictions_dropped"] = len(keep) - len(pruned)
    return pruned, stats


def gist_text(manifest: dict, vid: str, node: dict, pid: str | None = None) -> tuple[str, str]:
    """(language, text): the preset's personality language → the character's primary language → the first entry."""
    from .memories import gist_text as _gist
    return _gist(manifest, vid, node, pid, cat="psyche")


def short_clause(text: str, limit: int = 100) -> str:
    """A node below the full-line strength is rendered as its first sentence, the elaboration after a dash dropped,
    cut at a word boundary past `limit` characters (deterministic: the same node always gives the same clause)."""
    t = " ".join(str(text).split())
    for sep in (" — ", " – "):
        i = t.find(sep)
        if i > 0:
            t = t[:i]
    m = re.search(r"[.!?](\s|$)", t)
    if m and m.start() > 0:
        t = t[:m.start()]
    t = t.rstrip(" ,;:")
    if len(t) > limit:
        cut = t.rfind(" ", 0, limit)
        t = (t[:cut] if cut > 0 else t[:limit]).rstrip(" ,;:") + "…"
    return t


_WORDS = {
    "en": {"title": "Who {pron} is", "pron": {"female": "she", "male": "he"}, "pron_default": "they",
           "intro": "Rendered from the psyche nodes (RFC 0004) in a fixed order: wound, values, beliefs, wants and needs, fears, stances, tastes, habits, contradictions, rules. "
                    "A whole sentence weighs most (strength {full} or more); a short clause weighs less. Markers: `lie` — a belief {pron} holds that is false; "
                    "`guarded` — not opened with, only when it matters; `lived` — came from use, not from the author.",
           "kinds": {"wound": "Wound", "value": "Values", "belief": "Beliefs", "want": "Wants", "need": "Needs", "fear": "Fears", "stance": "Stances",
                     "taste": "Tastes", "habit": "Habits", "contradiction": "Contradictions", "rule": "Rules"},
           "secret": "There are things {pron} does not tell.", "user": "the user", "private": "a private matter", "lie": "lie", "guarded": "guarded", "lived": "lived", "about": "about",
           "partly": "half aware", "unaware": "acts on it without knowing it — never says it", "warmth": "warmth", "likes": "Likes:", "dislikes": "Dislikes:"},
    "fr": {"title": "Qui {pron} est", "pron": {"female": "elle", "male": "il"}, "pron_default": "iel",
           "intro": "Rendu depuis les nœuds de la psyché (RFC 0004) dans un ordre fixe : blessure, valeurs, croyances, désirs et besoins, peurs, positions, goûts, habitudes, contradictions, règles. "
                    "Une phrase entière pèse le plus (force {full} ou plus) ; une courte proposition pèse moins. Marqueurs : `mensonge` — une croyance qu'{pron} tient pour vraie et qui est fausse ; "
                    "`réservé` — jamais d'emblée, seulement quand cela compte ; `vécu` — venu de l'usage, pas de l'auteur.",
           "kinds": {"wound": "Blessure", "value": "Valeurs", "belief": "Croyances", "want": "Désirs", "need": "Besoins", "fear": "Peurs", "stance": "Positions",
                     "taste": "Goûts", "habit": "Habitudes", "contradiction": "Contradictions", "rule": "Règles"},
           "secret": "Il y a des choses qu'{pron} ne dit pas.", "user": "l'utilisateur", "private": "une affaire privée", "lie": "mensonge", "guarded": "réservé", "lived": "vécu", "about": "envers",
           "partly": "en partie à son insu", "unaware": "agit ainsi à son insu — ne le dit jamais", "warmth": "chaleur", "likes": "Aime :", "dislikes": "N'aime pas :"},
}


def _subject(manifest: dict, about: dict | None, lang: str, W: dict, hidden: set | None = None) -> str:
    """What a stance bears on, as a short text: the user, a character's name, a node's label, or the free label."""
    from .cast import text_in
    if not isinstance(about, dict):
        return ""
    if about.get("user"):
        return W["user"]
    if about.get("identity"):
        return ((manifest.get("identities") or {}).get(about["identity"]) or {}).get("name") or about["identity"]
    if about.get("node"):
        cat, _, vid = str(about["node"]).partition("/")
        if hidden and about["node"] in hidden:
            return W.get("private", "")                 # a node left out (personal, not exported): its label is the user's data too (hunt H4-02)
        return (resolve_variant(manifest, cat, vid) or {}).get("label") or vid
    return text_in(about.get("label"), lang)


def valence_text(v) -> str:
    """A valence as rendered after a stance's subject (§ 3 nonies): signed, « +60 », « -10 », « 0 »."""
    return f"{int(v):+d}" if int(v) else "0"


def has_valence(node: dict) -> bool:
    v = node.get("valence")
    return isinstance(v, int) and not isinstance(v, bool)


def soul_section(manifest: dict, nodes: dict[str, dict], pid: str | None, keep_personal: bool = False, keep_dangerous: bool = False, memory_nodes: dict | None = None) -> tuple[str, dict]:
    """The "Who she is" section of SOUL.md (RFC 0004 § 3 quinquies): one line per node in the fixed kind order, the whole
    gist at strength ≥ 70 and a short clause below, lies and guarded nodes marked, secret nodes left out with one line
    saying so; a stance's warmth after its subject, half-aware and unaware nodes marked, tastes split into likes and
    dislikes when one has a valence (§ 3 nonies). A node whose `until` is before the preset's age is still rendered when
    the preset holds it (the validator's coherence warning covers it). Texts in the preset's language, each node falling back to the languages it has. Returns (markdown, stats)."""
    from .cast import preset_gender
    from .memories import preset_language
    from .model import preset_owner
    vids, stats = select_nodes(manifest, nodes, pid, keep_personal, keep_dangerous)
    stats["rendered"] = 0; stats["secret"] = 0
    hidden: set[str] = set()                            # nodes a stance may name but this section must not: personal ones (memories and psyche) when not kept
    if not keep_personal:
        hidden = {f"psyche/{v}" for v, n in nodes.items() if n.get("visibility") == "personal"}
        hidden |= {f"memories/{v}" for v, n in (memory_nodes or {}).items() if n.get("visibility") == "personal"}
    if not vids:
        return "", stats
    me = preset_owner(manifest, pid)                       # the section's language: the preset's personality, else the character's, else the file's first
    lang = (preset_language(manifest, pid) or ((manifest.get("identities") or {}).get(me or "") or {}).get("language") or (manifest.get("languages") or ["en"])[0] or "en").lower()
    L = "fr" if lang.startswith("fr") else "en"
    W = _WORDS[L]
    pron = W["pron"].get(preset_gender(manifest, pid) or "", W["pron_default"])
    if L == "en" and pron == "they":                     # singular they takes the plural verb (hunt H4-15)
        W = {**W, "title": "Who they are", "secret": "There are things they do not tell.", "intro": W["intro"].replace("{pron} holds", "{pron} hold")}
    lines = [f"## {W['title'].format(pron=pron)}", "", W["intro"].format(full=FULL_LINE_STRENGTH, pron=pron), ""]
    by_kind: dict[str, list[str]] = {}
    for v in vids:
        by_kind.setdefault(node_kind(manifest, v) or "", []).append(v)
    secret = 0
    for kind in KIND_ORDER:
        rows = []
        for v in by_kind.get(kind) or []:
            n = nodes[v]
            if n.get("disclosure") == "secret":
                secret += 1; continue
            _, text = gist_text(manifest, v, n, pid)
            text = text.strip()
            if int(n.get("strength", 50)) < FULL_LINE_STRENGTH:
                text = short_clause(text)
            marks = []
            if kind == "belief" and n.get("false_but_held"):
                marks.append(W["lie"])
            if kind == "stance":
                subj = _subject(manifest, n.get("about"), lang, W, hidden)
                if subj:
                    marks.append(f"{W['about']}: {subj}")
                if has_valence(n):                                 # § 3 nonies: which way the stance leans, after its subject
                    marks.append(f"{W['warmth']} {valence_text(n['valence'])}")
            if n.get("aware") == "partly":                         # § 3 nonies: what the character knows of itself
                marks.append(W["partly"])
            elif n.get("aware") == "no":
                marks.append(W["unaware"])
            if n.get("disclosure") == "guarded":
                marks.append(W["guarded"])
            if n.get("origin") == "lived":
                marks.append(W["lived"])
            rows.append((n, f"- {text}" + (f"  ·  {' · '.join(marks)}" if marks else "")))
        if kind == "taste" and any(has_valence(n) for n, _ in rows):   # likes (> 0), dislikes (< 0), then the tastes without a lean
            likes = [r for n, r in rows if has_valence(n) and n["valence"] > 0]
            dislikes = [r for n, r in rows if has_valence(n) and n["valence"] < 0]
            plain = [r for n, r in rows if not (has_valence(n) and n["valence"])]
            rows = ([f"- {W['likes']}", *("  " + r for r in likes)] if likes else []) + \
                   ([f"- {W['dislikes']}", *("  " + r for r in dislikes)] if dislikes else []) + plain
        else:
            rows = [r for _, r in rows]
        if rows:
            lines += [f"### {W['kinds'][kind]}", *rows, ""]
    if secret:
        lines += [W["secret"].format(pron=pron), ""]
    stats["rendered"] = len(vids) - secret; stats["secret"] = secret
    return "\n".join(lines).rstrip() + "\n", stats


# ---- purges on an unpacked folder (cof extract) ----------------------------------------------------------------------

def sync_risk_tags(m: dict, nodes: dict[str, dict]) -> None:
    """tags.content follows the nodes' declared risk both ways (§ 3 septies): a level present adds its tag, a level
    gone removes it; an empty list becomes ["none"]."""
    tags = m.setdefault("tags", {})
    content = [t for t in (tags.get("content") or []) if t != "none"]
    risks = {(n.get("risk") or "none") for n in nodes.values()}
    for r, tag in RISK_TAGS.items():
        if r in risks and tag not in content:
            content.append(tag)
        if r not in risks and tag in content:
            content.remove(tag)
    tags["content"] = content or ["none"]


def drop_nodes(dst: Path, m: dict, vids: list[str]) -> list[str]:
    """Remove psyche nodes from an unpacked folder: their files and folders, their variant, their place in every preset;
    the contradictions that lose a side go with them, the links that pointed at them are dropped from the other nodes,
    and tags.content follows the risk that remains. Returns every id removed, in order. The caller writes the manifest."""
    from .ops import drop_dangling_memory_links
    V = ((m.get("elements") or {}).get("psyche") or {}).get("variants") or {}
    nodes = load_nodes(dst, m)
    keep = prune_contradictions(m, nodes, [v for v in V if v not in set(vids)])
    gone = [v for v in V if v not in keep]
    if not gone:
        return []
    for vid in keep:                                    # a kept node derived from a removed one (§ 3 nonies: bel4 from bel3) keeps what it inherited — its words, not the removed node's images (they leave with it, § 3 decies; hunt H1-10)
        if V[vid].get("derives_from") in gone:
            own = V[vid]
            V[vid] = {k: x for k, x in (resolve_variant(m, "psyche", vid) or {}).items() if k not in ("_id", "derives_from")}
            for k in ("media", "nudity", "age"):
                if k not in own:
                    V[vid].pop(k, None)
    still = {str(V[k].get("node") or "") for k in keep if k in V}            # a node file a kept (derived) variant still reads stays
    from .model import variant_asset_ids
    from .ops import _prune_assets
    freed: set[str] = set()                                                 # the illustrations of a removed node leave with it (§ 3 decies); one a kept node shares stays
    for vid in gone:
        freed |= variant_asset_ids(V.get(vid) or {})
    for vid in gone:
        V.pop(vid, None)
        for p in (m.get("presets") or {}).values():
            for key in ("slots", "alternatives"):
                if (p.get(key) or {}).get("psyche"):
                    p[key]["psyche"] = [x for x in p[key]["psyche"] if x != vid]
                    if not p[key]["psyche"]:
                        del p[key]["psyche"]
    _prune_assets(dst, m, freed)
    kept_paths = {a.get("path") or "" for a in m.get("assets") or []}
    for vid in gone:
        folder = dst / "elements" / "psyche" / vid
        if folder.is_dir() and not any(r.startswith(f"elements/psyche/{vid}/") for r in still) and not any(r.startswith(f"elements/psyche/{vid}/") for r in kept_paths):
            shutil.rmtree(folder)
    if not V:
        m["elements"].pop("psyche", None)
        pd = dst / "elements/psyche"
        if pd.is_dir() and not any(pd.iterdir()):
            pd.rmdir()
    drop_dangling_memory_links(dst, m)
    sync_risk_tags(m, load_nodes(dst, m))
    return gone


def drop_personal_nodes(dst: Path) -> list[str]:
    """§ 3 ter: `visibility: personal` nodes leave a file exactly as personal memories do (RFC 0002 § 5.7)."""
    m = json.loads((dst / "manifest.json").read_text("utf-8"))
    nodes = load_nodes(dst, m)
    hit = [vid for vid, n in nodes.items() if n.get("visibility") == "personal"]
    if not hit:
        return []
    from .ops import _with_heirs
    gone = drop_nodes(dst, m, _with_heirs(m, "psyche", "node", hit))
    (dst / "manifest.json").write_text(json.dumps(m, ensure_ascii=False, indent=2) + "\n", "utf-8")
    return gone


def _images_off(dst: Path, m: dict, vid: str) -> set[str]:
    """Take the illustrations off one node (the words stay): the variant's `media`, `nudity` and `age` (the age was that of an
    image), the `shown` / `age` of the node's people. Returns the freed asset ids."""
    v = (((m.get("elements") or {}).get("psyche") or {}).get("variants") or {}).get(vid) or {}
    freed = set(v.pop("media", None) or [])
    v.pop("nudity", None); v.pop("age", None)
    rel = v.get("node")
    if rel and (dst / rel).is_file():
        try:
            node = json.loads((dst / rel).read_text("utf-8"))
            for w in node.get("who") or []:
                w.pop("shown", None); w.pop("age", None)
            (dst / rel).write_text(json.dumps(node, ensure_ascii=False, indent=2) + "\n", "utf-8")
        except (OSError, ValueError):
            pass
    return freed


def strip_nude_images(dst: Path) -> list[str]:
    """§ 3 decies, all-audiences purge: a node whose images show nudity (variant `nudity: true`) keeps its words and loses its
    images. Returns the ids touched."""
    from .ops import _prune_assets
    m = json.loads((dst / "manifest.json").read_text("utf-8"))
    V = ((m.get("elements") or {}).get("psyche") or {}).get("variants") or {}
    hit = [vid for vid in V if (resolve_variant(m, "psyche", vid) or {}).get("nudity") is True]
    if not hit:
        return []
    freed: set[str] = set()
    for vid in hit:
        freed |= _images_off(dst, m, vid)
    _prune_assets(dst, m, freed)
    (dst / "manifest.json").write_text(json.dumps(m, ensure_ascii=False, indent=2) + "\n", "utf-8")
    return hit


def strip_foreign_real_images(dst: Path, kept_identities: set[str], identities: dict | None = None) -> list[str]:
    """Extraction guard (RFC 0002 § 4.5, read for § 3 decies): the images of a node that show a real person who is not among
    `kept_identities` are dropped, the node stays. Returns the ids touched."""
    from .memories import shows_other_real_person
    from .ops import _prune_assets
    m = json.loads((dst / "manifest.json").read_text("utf-8"))
    V = ((m.get("elements") or {}).get("psyche") or {}).get("variants") or {}
    nodes = load_nodes(dst, m)
    hit = [vid for vid, node in nodes.items() if (resolve_variant(m, "psyche", vid) or {}).get("media") and shows_other_real_person(m, vid, node, kept_identities, identities)]
    if not hit:
        return []
    freed: set[str] = set()
    for vid in hit:
        freed |= _images_off(dst, m, vid)
    _prune_assets(dst, m, freed)
    (dst / "manifest.json").write_text(json.dumps(m, ensure_ascii=False, indent=2) + "\n", "utf-8")
    return hit


def strip_risk(dst: Path, levels: tuple[str, ...] = ("inappropriate", "dangerous")) -> list[str]:
    """§ 3 septies, the risk purge: nodes whose `risk` is one of `levels` leave the file (contradictions that lose a side
    too); tags.content is corrected. Returns the ids removed."""
    m = json.loads((dst / "manifest.json").read_text("utf-8"))
    nodes = load_nodes(dst, m)
    hit = [vid for vid, n in nodes.items() if (n.get("risk") or "none") in levels]
    if not hit:
        return []
    gone = drop_nodes(dst, m, hit)
    (dst / "manifest.json").write_text(json.dumps(m, ensure_ascii=False, indent=2) + "\n", "utf-8")
    return gone


def prune_orphan_contradictions(dst: Path, m: dict) -> list[str]:
    """After an extraction: a contradiction kept by the preset while one of its sides was not (§ 3 sexies)."""
    return drop_nodes(dst, m, [])
