"""`cof psyche propose` — personality → psyche, as a proposal the author reviews (RFC 0004 § 3 octies; the contract is
`docs/psyche-propose.md`). This module builds the bundle a model reads, calls an OpenAI-compatible gateway or takes a
proposal from elsewhere (a file, the rule-based conversion of the 1.0 lists, the zodiac table), normalises and validates
the proposal against the contract, prints it as a reviewable table, and writes **only the candidates the author accepts**.
Nothing is written without an explicit accept."""
from __future__ import annotations

import json
import os
import re
import unicodedata
from pathlib import Path

from .psyche import ID_PREFIX, KINDS, RISK_TAGS, STABILITIES, load_nodes

CONTRACT = "psyche-propose/0.1"
MAX_NODES = 40
RISKS = ("none", "inappropriate", "dangerous")
CARD_FIELDS = ("description", "personality", "scenario", "first_mes", "mes_example", "system_prompt")
SOURCE_RE = re.compile(r"^(card\.(description|personality|scenario|first_mes|mes_example|system_prompt)|text|memory [a-z0-9][a-z0-9.-]*"
                       r"|list (goals|fears|values|behavior)\[\d+\]|inferred|zodiac)(@[a-z0-9][a-z0-9.-]*)?$")
CAND_RE = re.compile(r"^[a-z][a-z0-9_-]*$")

SYSTEM_PROMPT = "You decompose a fictional character's personality into psyche nodes (COF 1.2, RFC 0004). Answer in strict JSON only."

PROMPT = """Read the character bundle below and propose candidate psyche nodes. Answer ONLY with strict JSON of this shape:
{"contract":"psyche-propose/0.1","nodes":[{"id":"c1","kind":"value|belief|want|need|fear|wound|stance|taste|habit|contradiction|rule","gist":{"<lang>":"one sentence"},"strength":0-100,"stability":"core|settled|shifting|fragile","since":{"age":{"value":n}} or {"date":"YYYY[-MM[-DD]]"},"because":["memories/<id>"|"psyche/<id>"|"<candidate id>"],"supports":["psyche/<id>"|"<candidate id>"],"between":["<id>","<id>"] (contradiction only),"about":{"user":true}|{"identity":"<cast id>"}|{"node":"memories/<id>"}|{"label":{"<lang>":"..."}} (stance only),"false_but_held":true (belief only),"risk":{"value":"none|inappropriate|dangerous","why":"..."},"tags":["slug"],"source":"card.personality|card.description|card.scenario|card.mes_example|card.system_prompt|text|memory <id>|list goals[n]|inferred"}],"notes":"..."}
Rules:
1. One sentence per node, 100 to 300 characters per language, in every language of `languages` (the same meaning in each).
2. Kinds: value (what matters), belief (held true about the world or oneself), want (consciously pursued), need (what would heal, unseen), fear, wound (the founding injury, almost always because a memory), stance (a position toward a person, the user or a thing: set `about`), taste (likes and dislikes), habit (an observable recurring behaviour), contradiction (an owned tension between two nodes: `between` names them), rule (a boundary kept whatever the pressure; stability core).
3. `source` names where the node comes from: the card field, the free text, the memory (`memory ev3`), the list entry (`list goals[2]`), or `inferred` when you read it between the lines. Never invent a memory: `because` and `about` name only ids of the bundle. Prefer `because` to a memory over `because` to a node.
4. `strength`: how much it weighs in decisions (70 or more is said in full; the default is 50). `stability`: core never changes at use time, settled changes only through a declared lived node, shifting with evidence, fragile within one conversation.
5. A belief the character holds that is false (the lie it tells itself) is `false_but_held: true`. Propose a contradiction whenever a want and a fear, or a value and a habit, pull against each other.
6. Declare `risk` with a reason: `inappropriate` (unsuitable for some audiences, not harmful in itself: instability, deviant sexuality, self-destructive traits), `dangerous` (would make the character harmful if it acted on it: aggression, manipulation, contempt for others' safety). `none` otherwise.
7. Do not repeat an existing node of `psyche`; you may link to it. At most 40 nodes; fewer, well-sourced nodes beat many.
8. Nothing you propose is written: the author reviews every node.
"""


# ---- the bundle --------------------------------------------------------------------------------------------------

def _norm(text: str) -> str:
    return " ".join(unicodedata.normalize("NFKD", str(text)).encode("ascii", "ignore").decode().lower().split()).rstrip(".")


def _slug(t: str) -> str:
    return re.sub(r"[^a-z0-9:-]+", "-", unicodedata.normalize("NFKD", str(t)).encode("ascii", "ignore").decode().lower()).strip("-")


def character_of(manifest: dict, pid: str | None = None, identity: str | None = None) -> tuple[str | None, str | None]:
    """(character id, preset id): the preset's owner, else the identity asked for, else the default; the preset asked
    for, else the character's default preset, else the file's."""
    from .model import default_preset_id, preset_owner
    ids = manifest.get("identities") or {}
    if identity and ids and identity not in ids:
        raise ValueError(f"unknown character {identity!r}; known: {', '.join(ids)}")
    P = manifest.get("presets") or {}
    if pid and pid not in P:
        raise ValueError(f"unknown preset {pid!r}; known: {', '.join(P)}")
    iid = (preset_owner(manifest, pid) if pid else None) or identity or manifest.get("default_identity") or (next(iter(ids)) if ids else None)
    if not pid:
        pid = (ids.get(iid or "") or {}).get("default_preset")
        if pid not in P:
            pid = next((p for p in P if preset_owner(manifest, p) == iid), None) if ids and len(ids) > 1 else default_preset_id(manifest)
    return iid, pid


def build_bundle(src: Path, manifest: dict, pid: str | None = None, identity: str | None = None, langs: list[str] | None = None) -> dict:
    """What a model reads (docs/psyche-propose.md § 1): the character, the languages a gist must come in, the cast (for
    stances), the personality (the preset's variant first, then one variant per other language), the 1.0 lists, the
    memories as id + gist + when in the preset's language, the existing nodes (so that nothing is proposed twice)."""
    from .cast import identity_view
    from .memories import gist_text, load_nodes as load_memories, preset_language, when_label
    from .migrate import list_items
    from .model import preset_age, resolve_preset_slots, resolve_variant, variant_owner
    iid, pid = character_of(manifest, pid, identity)
    ids = manifest.get("identities") or {}
    view = identity_view(manifest, pid, iid)
    lang = (preset_language(manifest, pid) or view.get("language") or (manifest.get("languages") or ["en"])[0] or "en")
    L = [x.lower() for x in (langs or [])] or list(dict.fromkeys([lang.lower(), *[str(x).lower() for x in manifest.get("languages") or []]]))
    age = preset_age(manifest, pid) if pid else None
    out: dict = {"cof": "1.2", "contract": CONTRACT, "languages": L,
                 "character": {"id": iid, "name": view.get("name") or manifest.get("name"), "gender": view.get("gender"),
                               "age": age, "language": lang, "summary": view.get("summary") or manifest.get("summary") or ""},
                 "preset": pid,
                 "cast": [{"id": k, "name": (v or {}).get("name") or k, "gender": (v or {}).get("gender")} for k, v in ids.items() if k != iid],
                 "personality": [], "lists": {"goals": [], "fears": [], "values": [], "behavior": []}, "memories": [], "psyche": [], "max_nodes": MAX_NODES}
    # personality: the preset's variant, then one more per language the character writes in
    pers = (((manifest.get("elements") or {}).get("personality") or {}).get("variants")) or {}
    held = next(iter(resolve_preset_slots(manifest, pid).get("personality") or []), None) if pid else None
    order = ([held] if held in pers else []) + [v for v in pers if v != held]
    seen_lang: set[str] = set()
    for pvid in order:
        pv = pers[pvid]
        if pv.get("derives_from") or (ids and variant_owner(manifest, "personality", pvid) not in (iid, None)):
            continue
        vl = (pv.get("language") or lang).lower()
        if vl in seen_lang and pvid != held:
            continue
        seen_lang.add(vl)
        entry: dict = {"variant": pvid, "kind": pv.get("kind"), "language": vl}
        if pv.get("kind") == "card" and pv.get("card"):
            try:
                data = (json.loads((src / pv["card"]).read_text("utf-8")) or {}).get("data") or {}
            except (OSError, ValueError):
                data = {}
            for f in CARD_FIELDS:
                if str(data.get(f) or "").strip():
                    entry[f] = str(data[f]).strip()
        elif str(pv.get("text") or "").strip():
            entry["text"] = str(pv["text"]).strip()
        if len(entry) > 3:
            out["personality"].append(entry)
    # the 1.0 lists, merged across the character's variants (one entry per language)
    per_char, _ = list_items(src, manifest)
    keymap = {"want": "goals", "fear": "fears", "value": "values", "habit": "behavior"}
    for kind, items in (per_char.get(iid) or per_char.get(None) or {}).items():
        for it in items:
            g = {k: v for k, v in it.items() if not k.startswith("_")}
            out["lists"][keymap[kind]].append(g[lang] if lang in g else next(iter(g.values())))
    # memories: the character's; the copies (derives_from, or the same gist again — the manga copies) left out
    mems = load_memories(src, manifest)
    seen_gist: set[str] = set()
    for mid, node in mems.items():
        mv = resolve_variant(manifest, "memories", mid) or {}
        if mv.get("derives_from") or node.get("derives_from") or (ids and variant_owner(manifest, "memories", mid) not in (iid, None)):
            continue
        _, g = gist_text(manifest, mid, node, pid)
        if _norm(g) in seen_gist:
            continue
        seen_gist.add(_norm(g))
        out["memories"].append({"id": mid, "kind": mv.get("kind"), "gist": g, "when": when_label(mv.get("kind"), node, lang)})
    # existing nodes
    for vid, node in load_nodes(src, manifest).items():
        pv = resolve_variant(manifest, "psyche", vid) or {}
        if ids and variant_owner(manifest, "psyche", vid) not in (iid, None):
            continue
        _, g = gist_text(manifest, vid, node, pid, cat="psyche")
        e = {"id": vid, "kind": pv.get("kind"), "gist": g}
        if isinstance(node.get("strength"), int):
            e["strength"] = node["strength"]
        out["psyche"].append(e)
    return out


# ---- the proposal: normalisation and validation ----------------------------------------------------------------------

def normalize(proposal) -> dict:
    """Tolerated shapes become the contract's: a bare list is `nodes`; a missing id becomes c<n>; a `risk` given as a
    string becomes {"value", "why": ""}; `because` / `supports` / `between` / `tags` given as one string become lists;
    `kind` and `stability` are lowercased; tags are slugged. Returns a new dict; never raises."""
    if isinstance(proposal, list):
        proposal = {"nodes": proposal}
    if not isinstance(proposal, dict):
        return {"contract": CONTRACT, "nodes": proposal}
    out = {"contract": proposal.get("contract") or CONTRACT, "nodes": [], "notes": proposal.get("notes") or ""}
    nodes = proposal.get("nodes")
    if nodes is None:
        nodes = proposal.get("candidates")
    if not isinstance(nodes, list):
        out["nodes"] = nodes
        return out
    used: set[str] = set()
    for i, n in enumerate(nodes, 1):
        if not isinstance(n, dict):
            out["nodes"].append(n); continue
        c = dict(n)
        if not isinstance(c.get("id"), str) or not c["id"].strip() or c["id"].strip() in used:
            cid = f"c{i}"
            while cid in used:
                cid += "x"
            c["id"] = cid
        c["id"] = c["id"].strip(); used.add(c["id"])
        for k in ("kind", "stability"):
            if isinstance(c.get(k), str):
                c[k] = c[k].strip().lower()
        if isinstance(c.get("risk"), str):
            c["risk"] = {"value": c["risk"].strip().lower() or "none", "why": ""}
        elif isinstance(c.get("risk"), dict) and isinstance(c["risk"].get("value"), str):
            c["risk"] = {"value": c["risk"]["value"].strip().lower(), "why": str(c["risk"].get("why") or "")}
        for k in ("because", "supports", "between", "tags"):
            if isinstance(c.get(k), str):
                c[k] = [x.strip() for x in c[k].split(",") if x.strip()]
        if isinstance(c.get("tags"), list):
            c["tags"] = [x for x in (_slug(t) for t in c["tags"] if isinstance(t, str)) if x]
        if isinstance(c.get("strength"), (float, str)):
            try:
                c["strength"] = int(round(float(c["strength"])))
            except ValueError:
                pass
        out["nodes"].append(c)
    return out


def validate(proposal: dict, bundle: dict) -> tuple[list[str], list[str]]:
    """The contract (docs/psyche-propose.md § 2): errors (the proposal is refused) and notes (shown, not blocking)."""
    errors: list[str] = []
    notes: list[str] = []
    if not isinstance(proposal, dict) or not isinstance(proposal.get("nodes"), list):
        return ["the proposal is not an object with a `nodes` list"], notes
    if proposal.get("contract") != CONTRACT:
        notes.append(f"contract {proposal.get('contract')!r} (expected {CONTRACT})")
    nodes = proposal["nodes"]
    if len(nodes) > MAX_NODES:
        notes.append(f"{len(nodes)} candidates: more than the {MAX_NODES} the contract asks for")
    mem_ids = {str(m.get("id")) for m in bundle.get("memories") or []}
    psy_ids = {str(n.get("id")) for n in bundle.get("psyche") or []}
    cast_ids = {str(c.get("id")) for c in bundle.get("cast") or []} | {str((bundle.get("character") or {}).get("id"))}
    cand_ids = [n.get("id") for n in nodes if isinstance(n, dict)]
    cand = set(cand_ids)
    langs = [str(x).lower() for x in bundle.get("languages") or []]
    for i, n in enumerate(nodes):
        where = f"nodes[{i}]"
        if not isinstance(n, dict):
            errors.append(f"{where}: not an object"); continue
        cid = n.get("id")
        where = f"{where} ({cid})"
        if not isinstance(cid, str) or not CAND_RE.match(cid) or cid.startswith(("memories/", "psyche/")):
            errors.append(f"{where}: id must be a short slug (c1, c2…)")
        kind = n.get("kind")
        if kind not in KINDS:
            errors.append(f"{where}: unknown kind {kind!r} (one of {', '.join(KINDS)})"); kind = None
        g = n.get("gist")
        if not isinstance(g, dict) or not g or not all(isinstance(k, str) and isinstance(v, str) and v.strip() for k, v in g.items()):
            errors.append(f"{where}: gist must be a non-empty language map of texts")
        else:
            ruled = str(n.get("source") or "").startswith(("list ", "zodiac"))      # rule-based entries are short by nature: the author completes them
            for k, v in g.items():
                if len(v) > 600:
                    errors.append(f"{where}: gist[{k}] is {len(v)} characters (the node is one or two sentences)")
                elif not ruled and not 100 <= len(v) <= 300:
                    notes.append(f"{where}: gist[{k}] is {len(v)} characters (100–300 expected)")
            miss = [l for l in langs if not any(k.lower().split("-")[0] == l.split("-")[0] for k in g)]
            if miss and not ruled:
                notes.append(f"{where}: no gist in {', '.join(miss)}")
        s = n.get("strength")
        if s is not None and not (isinstance(s, int) and not isinstance(s, bool) and 0 <= s <= 100):
            errors.append(f"{where}: strength must be an integer between 0 and 100")
        st = n.get("stability")
        if st is not None and st not in STABILITIES:
            errors.append(f"{where}: stability must be one of {', '.join(STABILITIES)}")
        if kind == "rule" and st not in (None, "core"):
            notes.append(f"{where}: a rule is naturally core (stability {st})")
        good_pts = []
        for key in ("since", "until"):                                # until: when the character stopped holding it (RFC 0004 § 3 nonies)
            pt = n.get(key)
            if pt is None:
                continue
            if not isinstance(pt, dict) or not pt or not set(pt) <= {"age", "date", "approx"}:
                errors.append(f"{where}: {key} must be {{age: {{value}}}} and/or {{date}}"); continue
            a = pt.get("age")
            bad = len(errors)
            if a is not None and not (isinstance(a, dict) and isinstance(a.get("value"), (int, float)) and not isinstance(a["value"], bool) and a["value"] >= 0):
                errors.append(f"{where}: {key}.age must be {{value: n}}")
            d = pt.get("date")
            if d is not None and not (isinstance(d, str) and re.fullmatch(r"-?[0-9]{1,4}(-(0[1-9]|1[0-2])(-(0[1-9]|[12][0-9]|3[01]))?)?", d)):
                errors.append(f"{where}: {key}.date must be YYYY, YYYY-MM or YYYY-MM-DD")
            if len(errors) == bad:
                good_pts.append(key)
        if good_pts == ["since", "until"]:
            from .validate import _point_before
            if _point_before(n["until"], n["since"]):
                errors.append(f"{where}: until is before since")
        aw = n.get("aware")
        if aw is not None and aw not in ("yes", "partly", "no"):
            errors.append(f"{where}: aware must be yes, partly or no")
        va = n.get("valence")
        if va is not None:
            if kind not in ("stance", "taste"):
                errors.append(f"{where}: valence is for a stance or a taste only")
            elif not (isinstance(va, int) and not isinstance(va, bool) and -100 <= va <= 100):
                errors.append(f"{where}: valence must be an integer between -100 and 100")
        def ref_ok(r, allow_mem: bool) -> str | None:
            if not isinstance(r, str):
                return "not a string"
            if r.startswith("memories/"):
                return None if (allow_mem and r[9:] in mem_ids) else (f"unknown memory {r[9:]!r}" if allow_mem else "a memory cannot be a side here")
            if r.startswith("psyche/"):
                return None if r[7:] in psy_ids else f"unknown psyche node {r[7:]!r}"
            if r in cand:
                return "a node cannot point at itself" if r == cid else None
            return f"unknown reference {r!r} (memories/<id>, psyche/<id> or a candidate id)"
        for key, allow_mem in (("because", True), ("supports", False)):
            v = n.get(key)
            if v is None:
                continue
            if not isinstance(v, list):
                errors.append(f"{where}: {key} must be a list of references"); continue
            for r in v:
                e = ref_ok(r, allow_mem)
                if e:
                    errors.append(f"{where}: {key} → {e}")
        b = n.get("between")
        if kind == "contradiction":
            if not (isinstance(b, list) and len(b) == 2 and b[0] != b[1]):
                errors.append(f"{where}: a contradiction names exactly two different sides in `between`")
            else:
                for r in b:
                    e = ref_ok(r, False)
                    if e:
                        errors.append(f"{where}: between → {e}")
        elif b is not None:
            errors.append(f"{where}: between is for a contradiction only")
        ab = n.get("about")
        if ab is not None:
            if kind != "stance":
                errors.append(f"{where}: about is for a stance only")
            elif not isinstance(ab, dict) or len(ab) != 1:
                errors.append(f"{where}: about must be one of {{user: true}}, {{identity}}, {{node}}, {{label}}")
            else:
                k, v = next(iter(ab.items()))
                if k == "user":
                    if v is not True:
                        errors.append(f"{where}: about.user must be true")
                elif k == "identity":
                    if v not in cast_ids:
                        errors.append(f"{where}: about.identity {v!r} is not a character of the file")
                elif k == "node":
                    e = ref_ok(v, True)
                    if e:
                        errors.append(f"{where}: about.node → {e}")
                elif k == "label":
                    if not isinstance(v, dict) or not v or not all(isinstance(x, str) and x.strip() for x in v.values()):
                        errors.append(f"{where}: about.label must be a language map")
                else:
                    errors.append(f"{where}: about.{k} is not a subject")
        elif kind == "stance":
            notes.append(f"{where}: a stance with no subject (about)")
        if n.get("false_but_held") is not None:
            if kind != "belief":
                errors.append(f"{where}: false_but_held is for a belief only")
            elif not isinstance(n["false_but_held"], bool):
                errors.append(f"{where}: false_but_held must be true or false")
        r = n.get("risk")
        if r is not None:
            if not isinstance(r, dict) or r.get("value") not in RISKS:
                errors.append(f"{where}: risk must be {{value: none | inappropriate | dangerous, why}}")
            elif r["value"] != "none" and not str(r.get("why") or "").strip():
                notes.append(f"{where}: risk {r['value']} with no reason")
        tg = n.get("tags")
        if tg is not None and not (isinstance(tg, list) and all(isinstance(x, str) and re.fullmatch(r"[a-z0-9][a-z0-9:-]*", x) for x in tg)):
            errors.append(f"{where}: tags must be a list of slugs")
        src_ = n.get("source")
        if not isinstance(src_, str) or not SOURCE_RE.match(src_.strip()):
            errors.append(f"{where}: source must name a card field, `text`, `memory <id>`, `list <kind>[n]`, `inferred` or `zodiac` (got {src_!r})")
        elif src_.startswith("memory ") and src_.split("@")[0][7:] not in mem_ids:
            errors.append(f"{where}: source names a memory the character does not have ({src_[7:]!r})")
        for k in n:
            if k not in ("id", "kind", "gist", "strength", "stability", "since", "until", "aware", "valence", "because", "supports", "between", "about", "false_but_held", "risk", "tags", "source", "label", "note"):
                notes.append(f"{where}: field {k!r} is not part of the contract (ignored)")
    dup = [x for x in cand_ids if cand_ids.count(x) > 1]
    if dup:
        errors.append(f"duplicate candidate ids: {', '.join(sorted(set(dup)))}")
    return errors, notes


def duplicates(proposal: dict, bundle: dict) -> dict[str, str]:
    """candidate id → the existing node (psyche/<id>) or earlier candidate whose gist says the same thing: the same text
    once normalised, or most of the same words (Jaccard ≥ 0.6 on words of 4+ letters). A warning for the review, never a
    refusal: the author decides."""
    def words(t):
        return {w for w in re.findall(r"[a-z0-9]{4,}", _norm(t))}
    def same(a: str, b: str) -> bool:
        if _norm(a) == _norm(b):
            return True
        A, B = words(a), words(b)
        return bool(A) and bool(B) and len(A & B) / len(A | B) >= 0.6
    out: dict[str, str] = {}
    seen: list[tuple[str, dict]] = [(f"psyche/{n['id']}", {"x": n.get("gist") or ""}) for n in bundle.get("psyche") or []]
    for n in proposal.get("nodes") or []:
        if not isinstance(n, dict) or not isinstance(n.get("gist"), dict):
            continue
        hit = None
        for ref, g in seen:
            if any(same(a, b) for a in n["gist"].values() for b in g.values() if isinstance(a, str) and isinstance(b, str)):
                hit = ref; break
        if hit:
            out[n["id"]] = hit
        seen.append((n["id"], n["gist"]))
    return out


# ---- the sources of a proposal -------------------------------------------------------------------------------------

def rules_proposal(src: Path, manifest: dict, iid: str | None, langs: list[str] | None = None) -> dict:
    """`--rules`: the conversion of the 1.0 lists (RFC 0004 § 3 quater, the same merge as `migrate --psyche`) presented
    as a proposal: want (70) / fear (70) / value (« Sobriété. ») / habit candidates, source `list <kind>[n]`."""
    from .migrate import list_items
    per_char, _ = list_items(src, manifest)
    keymap = {"want": "goals", "fear": "fears", "value": "values", "habit": "behavior"}
    nodes = []
    for kind in ("value", "want", "fear", "habit"):
        for i, it in enumerate((per_char.get(iid) or per_char.get(None) or {}).get(kind) or []):
            g = {k: v for k, v in it.items() if not k.startswith("_")}
            c = {"id": f"l{len(nodes) + 1}", "kind": kind, "gist": g, "stability": "settled", "source": f"list {keymap[kind]}[{i}]"}
            if kind in ("want", "fear"):
                c["strength"] = 70
            nodes.append(c)
    return {"contract": CONTRACT, "nodes": nodes, "notes": "rule-based: the 1.0 lists of the personality (goals, fears, values, behaviours); to complete by the author"}


def zodiac_proposal(sign: str, langs: list[str] | None, start: int = 1) -> dict:
    from .zodiac import candidates, normalize_sign, NAMES
    sid = normalize_sign(sign)
    if not sid:
        from .zodiac import SIGNS
        raise ValueError(f"unknown zodiac sign {sign!r}; known: {', '.join(SIGNS)}")
    return {"contract": CONTRACT, "nodes": candidates(sid, langs, start),
            "notes": f"zodiac: {NAMES[sid]['en']} / {NAMES[sid]['fr']} — traits a sun sign suggests, to review by the author; a sign is not a field of the format"}


def merge(*proposals: dict) -> dict:
    out = {"contract": CONTRACT, "nodes": [], "notes": " · ".join(str(p.get("notes") or "") for p in proposals if p.get("notes"))}
    used: set[str] = set()
    for p in proposals:
        for n in p.get("nodes") or []:
            n = dict(n)
            if n.get("id") in used:
                base = n["id"]; k = 2
                while f"{base}-{k}" in used:
                    k += 1
                n["id"] = f"{base}-{k}"
            used.add(n["id"]); out["nodes"].append(n)
    return out


def call_gateway(base_url: str, model: str, bundle: dict, key: str | None = None, timeout: int = 180) -> dict:
    """POST {base_url}/chat/completions (OpenAI-compatible), the key from the environment (`COF_AI_KEY`), the bundle after
    the prompt; the first JSON object of the answer is the proposal (raw: normalise and validate it)."""
    import urllib.request
    url = base_url.rstrip("/") + "/chat/completions"
    body = {"model": model, "temperature": 0,
            "messages": [{"role": "system", "content": SYSTEM_PROMPT}, {"role": "user", "content": PROMPT + "\n" + json.dumps(bundle, ensure_ascii=False)}]}
    req = urllib.request.Request(url, data=json.dumps(body).encode("utf-8"), method="POST",
                                 headers={"Content-Type": "application/json", **({"Authorization": f"Bearer {key}"} if key else {})})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        raw = json.loads(r.read().decode("utf-8"))
    return parse_answer(raw)


def parse_answer(raw) -> dict:
    """The proposal inside a chat completion (or a bare proposal): the message's content, its first {...} block."""
    txt = raw
    if isinstance(raw, dict) and "choices" in raw:
        txt = (((raw.get("choices") or [{}])[0].get("message") or {}).get("content")) or ""
    if isinstance(txt, dict):
        return txt
    txt = str(txt)
    m = re.search(r"\{[\s\S]*\}", txt)
    try:
        return json.loads(m.group(0) if m else txt)
    except ValueError as e:
        raise ValueError(f"the answer is not JSON: {e}") from e


# ---- the review table ----------------------------------------------------------------------------------------------

def table(proposal: dict, bundle: dict, notes: list[str] | None = None, applying: str | None = None) -> str:
    """One row per candidate (id, kind, strength, stability, risk, source, duplicate), the gist in the character's
    language under it with the links, the risk's reason and the duplicate it echoes."""
    lang = str((bundle.get("character") or {}).get("language") or (bundle.get("languages") or ["en"])[0]).lower()
    dups = duplicates(proposal, bundle)
    rows = [f"{'id':<6} {'kind':<14} {'str':>3}  {'stability':<9} {'risk':<13} {'source':<22} {'dup':<12}"]
    rows.append("-" * len(rows[0]))
    for n in proposal.get("nodes") or []:
        g = n.get("gist") or {}
        text = g.get(lang) or next((v for k, v in g.items() if k.split("-")[0] == lang.split("-")[0]), None) or next(iter(g.values()), "")
        r = n.get("risk") or {}
        risk = r.get("value", "none") if isinstance(r, dict) else str(r)
        rows.append(f"{n.get('id', ''):<6} {str(n.get('kind', '')) + (' (lie)' if n.get('false_but_held') else ''):<14} {str(n.get('strength', '—')):>3}  {str(n.get('stability') or '—'):<9} {risk:<13} {str(n.get('source', '')):<22} {dups.get(n.get('id'), ''):<12}")
        rows.append(f"       {text}")
        extra = []
        if n.get("because"):
            extra.append("because → " + ", ".join(n["because"]))
        if n.get("supports"):
            extra.append("supports → " + ", ".join(n["supports"]))
        if n.get("between"):
            extra.append("between " + " ⇄ ".join(n["between"]))
        ab = n.get("about")
        if isinstance(ab, dict):
            k, v = next(iter(ab.items()))
            extra.append("about: " + ("the user" if k == "user" else (v if isinstance(v, str) else next(iter(v.values()), "")) if k != "label" else next(iter(v.values()), "")))
        for key in ("since", "until"):
            if n.get(key):
                s = n[key]; extra.append(f"{key} " + (f"age {s['age']['value']}" if s.get("age") else "") + (f" {s['date']}" if s.get("date") else ""))
        if n.get("aware") in ("partly", "no"):
            extra.append("aware " + n["aware"])
        if isinstance(n.get("valence"), int):
            extra.append(f"valence {n['valence']:+d}")
        if isinstance(r, dict) and r.get("value", "none") != "none":
            extra.append(f"risk {r['value']}: {r.get('why') or '(no reason given)'}")
        if n.get("tags"):
            extra.append("tags " + ", ".join(n["tags"]))
        if extra:
            rows.append("       " + " · ".join(extra))
    if proposal.get("notes"):
        rows.append(""); rows.append(f"notes: {proposal['notes']}")
    for x in notes or []:
        rows.append(f"NOTE   {x}")
    rows.append(""); rows.append(f"{len(proposal.get('nodes') or [])} candidate(s). " + (f"Writing --accept {applying}." if applying else "Nothing is written without --apply --accept <id,id | all>."))
    return "\n".join(rows)


# ---- the write of the accepted candidates ---------------------------------------------------------------------------

def apply(src: Path, proposal: dict, accept: list[str] | str, iid: str | None = None, bundle: dict | None = None) -> tuple[list[str], list[str]]:
    """Write the accepted candidates into an unpacked folder: `origin: authored`, `visibility: canon`, `disclosure: open`,
    listed in `slots.psyche` by every preset of the character that holds one of the personality variants the bundle
    read (else any personality variant, else its presets, else the default one), ids by kind, inter-candidate references mapped, a contradiction refused unless both its sides are
    accepted or exist, `tags.content` following the risk, `cof: "1.2"`. Returns (written ids, notes). The caller
    validates and writes back (the CLI edits a copy)."""
    from .migrate import _label
    from .model import preset_owner, resolve_preset_slots, variant_owner
    from .psyche import sync_risk_tags
    from .selfdesc import _next_id
    mpath = src / "manifest.json"
    m = json.loads(mpath.read_text("utf-8"))
    nodes = [n for n in proposal.get("nodes") or [] if isinstance(n, dict)]
    by_id = {n["id"]: n for n in nodes}
    if accept == "all" or accept == ["all"]:
        chosen = [n["id"] for n in nodes]
    else:
        chosen = [x.strip() for x in (accept.split(",") if isinstance(accept, str) else accept) if str(x).strip()]
        unknown = [x for x in chosen if x not in by_id]
        if unknown:
            raise ValueError(f"--accept names unknown candidate(s): {', '.join(unknown)} (known: {', '.join(by_id) or 'none'})")
    if not chosen:
        raise ValueError("nothing accepted: pass --accept <id,id> or --accept all")
    chosen = list(dict.fromkeys(chosen))
    ids = m.get("identities") or {}
    iid = iid or m.get("default_identity") or (next(iter(ids)) if ids else None)
    E = m.setdefault("elements", {})
    V = E.setdefault("psyche", {}).setdefault("variants", {})
    existing = set(V)
    accepted = set(chosen)
    for cid in chosen:                                                  # a contradiction needs both sides
        n = by_id[cid]
        if n.get("kind") == "contradiction":
            for side in n.get("between") or []:
                ok = (side.startswith("psyche/") and side[7:] in existing) or side in accepted
                if not ok:
                    raise ValueError(f"contradiction {cid}: its side {side!r} is neither accepted nor an existing node (accept both sides or leave it out)")
    vids: dict[str, str] = {}
    for cid in chosen:
        vids[cid] = _next_id(V, ID_PREFIX[by_id[cid]["kind"]])
        V[vids[cid]] = {"kind": by_id[cid]["kind"]}                      # reserved so the next id moves on; filled below
    notes: list[str] = []
    cast = len(ids) > 1 or (ids and any(v.get("identity") for e in E.values() for v in (e.get("variants") or {}).values()))
    lang = ((ids.get(iid or "") or {}).get("language") or (m.get("languages") or ["en"])[0]).lower()
    def ref(r: str, cid: str) -> str | None:
        if r.startswith(("memories/", "psyche/")):
            return r
        if r in vids:
            return "psyche/" + vids[r]
        notes.append(f"{cid}: reference to {r!r} dropped (not accepted)")
        return None
    written = []
    for cid in chosen:
        n = by_id[cid]; vid = vids[cid]
        node: dict = {"gist": dict(n["gist"])}
        if isinstance(n.get("strength"), int):
            node["strength"] = n["strength"]
        node["stability"] = n.get("stability") or ("core" if n["kind"] == "rule" else "settled")
        if n.get("since"):
            node["since"] = n["since"]
        if n.get("until"):                                               # § 3 nonies: optional, kept as given
            node["until"] = n["until"]
        if n["kind"] == "belief" and n.get("false_but_held"):
            node["false_but_held"] = True
        if n.get("aware") in ("partly", "no"):
            node["aware"] = n["aware"]
        if n["kind"] in ("stance", "taste") and isinstance(n.get("valence"), int) and not isinstance(n.get("valence"), bool):
            node["valence"] = n["valence"]
        if n["kind"] == "stance" and isinstance(n.get("about"), dict):
            k, v = next(iter(n["about"].items()))
            if k == "node":
                t = ref(v, cid)
                if t:
                    node["about"] = {"node": t}
            else:
                node["about"] = {k: v}
        L = []
        for key, ty in (("because", "because"), ("supports", "supports")):
            for r in n.get(key) or []:
                t = ref(r, cid)
                if t:
                    L.append({"to": t, "type": ty})
        if n["kind"] == "contradiction":
            for r in n.get("between") or []:
                L.append({"to": ref(r, cid), "type": "conflicts"})
        if L:
            node["links"] = L
        r = n.get("risk")
        if isinstance(r, dict) and r.get("value") in RISK_TAGS:
            node["risk"] = r["value"]
        node.update({"origin": "authored", "visibility": "canon", "disclosure": "open"})
        if n.get("tags"):
            node["tags"] = list(n["tags"])
        d = src / "elements" / "psyche" / vid
        d.mkdir(parents=True, exist_ok=True)
        (d / "psyche-node.json").write_text(json.dumps(node, ensure_ascii=False, indent=2) + "\n", "utf-8")
        g = node["gist"]
        first = g.get(lang) or next((v for k, v in g.items() if k.split("-")[0] == lang.split("-")[0]), None) or next(iter(g.values()))
        var: dict = {"kind": n["kind"], "label": str(n.get("label") or _label(first)), "node": f"elements/psyche/{vid}/psyche-node.json"}
        if iid and cast:
            var["identity"] = iid
        if "strength" in node:
            var["strength"] = node["strength"]
        V[vid] = var
        written.append(vid)
    # presets: those of the character that hold a personality variant; else the character's; else the default
    P = m.get("presets") or {}
    mine = [p for p in P if (preset_owner(m, p) or iid) == iid]
    read = {str(e.get("variant")) for e in (bundle or {}).get("personality") or []}
    with_pers = [p for p in mine if resolve_preset_slots(m, p).get("personality")]
    targets = [p for p in with_pers if read & set(resolve_preset_slots(m, p).get("personality") or [])] or with_pers or mine or ([m.get("default_preset") or next(iter(P))] if P else [])
    for pid in targets:
        sl = P[pid].setdefault("slots", {})
        if "psyche" not in sl:
            have = resolve_preset_slots(m, pid).get("psyche") or []
            if all(vid in have for vid in written):                  # inherited from a parent updated above: not materialised
                continue
            sl["psyche"] = list(have)
        for vid in written:
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
    auto = m.setdefault("tags", {}).setdefault("auto", [])
    if "has-psyche" not in auto:
        auto.append("has-psyche")
    sync_risk_tags(m, load_nodes(src, m))
    from datetime import datetime, timezone
    m.setdefault("provenance", {})["modified"] = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    mpath.write_text(json.dumps(m, ensure_ascii=False, indent=2) + "\n", "utf-8")
    return written, notes


def key_from_env() -> str | None:
    """The gateway key is never an argument (it would land in shell histories): `COF_AI_KEY`."""
    return os.environ.get("COF_AI_KEY") or None
