"""RFC 0003 (1.1): gender, archetype, narrative role, relations between characters.

Shared by the validator (vocabularies, cast rules, coherence), the exports (IDENTITY.md / SOUL.md lines)
and `extract --identity` (relations whose target leaves the file).
"""
from __future__ import annotations

import json
from pathlib import Path

from .model import resolve_preset_slots, resolve_variant

GENDERS = ("female", "male", "non-binary", "none", "other")
RELATION_TYPES = ("parent", "child", "sibling", "partner", "ex-partner", "spouse", "friend", "colleague", "mentor", "student",
                  "rival", "enemy", "acquaintance", "creator", "creation", "owner", "pet", "other")
SYMMETRIC = {"sibling", "partner", "ex-partner", "spouse", "friend", "colleague", "rival", "enemy", "acquaintance"}
INVERSE = {"parent": "child", "child": "parent", "mentor": "student", "student": "mentor", "creator": "creation", "creation": "creator",
           "owner": "pet", "pet": "owner"}
ARCHETYPES = ("innocent", "everyman", "hero", "caregiver", "explorer", "rebel", "lover", "creator", "jester", "sage", "magician", "ruler")
ROLES = ("protagonist", "antagonist", "mentor", "ally", "sidekick", "foil", "love-interest", "narrator", "ensemble", "other")

GENDER_WORDS = {"en": {"female": "female", "male": "male", "non-binary": "non-binary", "none": "no gender (entity)", "other": "other"},
                "fr": {"female": "féminin", "male": "masculin", "non-binary": "non binaire", "none": "sans genre (entité)", "other": "autre"}}
ARCHETYPE_WORDS = {"en": {"innocent": "the Innocent", "everyman": "the Everyman", "hero": "the Hero", "caregiver": "the Caregiver", "explorer": "the Explorer",
                          "rebel": "the Rebel", "lover": "the Lover", "creator": "the Creator", "jester": "the Jester", "sage": "the Sage",
                          "magician": "the Magician", "ruler": "the Ruler"},
                   "fr": {"innocent": "l'Innocent", "everyman": "le Citoyen ordinaire", "hero": "le Héros", "caregiver": "le Protecteur", "explorer": "l'Explorateur",
                          "rebel": "le Rebelle", "lover": "l'Amoureux", "creator": "le Créateur", "jester": "le Bouffon", "sage": "le Sage",
                          "magician": "le Magicien", "ruler": "le Souverain"}}
RELATION_WORDS = {"en": {t: t.replace("-", " ") for t in RELATION_TYPES},
                  "fr": {"parent": "parent", "child": "enfant", "sibling": "frère / sœur", "partner": "partenaire", "ex-partner": "ex-partenaire", "spouse": "époux / épouse",
                         "friend": "ami(e)", "colleague": "collègue", "mentor": "mentor", "student": "élève", "rival": "rival(e)", "enemy": "ennemi(e)",
                         "acquaintance": "connaissance", "creator": "créateur", "creation": "création", "owner": "maître", "pet": "animal", "other": "autre"}}
ROLE_WORDS = {"en": {r: r.replace("-", " ") for r in ROLES},
              "fr": {"protagonist": "protagoniste", "antagonist": "antagoniste", "mentor": "mentor", "ally": "allié(e)", "sidekick": "acolyte", "foil": "faire-valoir",
                     "love-interest": "intérêt amoureux", "narrator": "narrateur", "ensemble": "ensemble", "other": "autre"}}

# the voice profile's gender_presentation vocabulary (voice-profile.schema.json) mapped onto RFC 0003 genders
VOICE_TO_GENDER = {"feminine": "female", "masculine": "male", "female": "female", "male": "male"}    # androgynous / neutral never conflict (RFC 0003 § 6)


def text_in(m, lang: str | None) -> str:
    """A language-map entry: the language, else its base, else the first (RFC 0002 § 3 reading rule, short texts)."""
    if isinstance(m, str):
        return m
    if not isinstance(m, dict) or not m:
        return ""
    if lang:
        if lang in m:
            return m[lang]
        base = lang.lower().split("-")[0]
        for k, v in m.items():
            if k.lower().split("-")[0] == base:
                return v
    return next(iter(m.values()))


OVERRIDABLE = ("name", "given_name", "family_name", "nicknames", "gender", "gender_label", "summary")


def identity_override(manifest: dict, pid: str | None) -> dict:
    """The preset chain's identity_override, merged field by field (nearest declaration wins) — RFC 0003 § 4."""
    presets = manifest.get("presets") or {}
    out, q, seen = {}, pid, set()
    while q and q in presets and q not in seen:
        seen.add(q)
        for k, v in (presets[q].get("identity_override") or {}).items():
            if k in OVERRIDABLE and k not in out and v is not None:
                out[k] = v
        q = presets[q].get("extends")
    return out


def identity_view(manifest: dict, pid: str | None, iid: str | None = None) -> dict:
    """The identity as presented by a preset: the identity's record with the override applied (never morphology, fictional, consent, rights)."""
    presets = manifest.get("presets") or {}
    if iid is None and pid and pid in presets:
        iid = presets[pid].get("identity") or manifest.get("default_identity")
    base = dict((manifest.get("identities") or {}).get(iid or "", {}) or {})
    if not base:                                   # a root-only 1.0 file: the character's record is the root copy (SPEC § 2.1)
        base = {k: manifest[k] for k in ("name", "nickname", "summary", "fictional", "morphology", "language", "rights") if k in manifest}
    base.update(identity_override(manifest, pid))
    return base


def preset_prompts(manifest: dict, pid: str | None) -> dict:
    """The preset's own default prompts (`scene`, `greeting`) — not inherited through extends: a scene fits one presentation (RFC 0003 § 4 bis)."""
    p = (manifest.get("presets") or {}).get(pid or "") or {}
    return {k: v for k, v in (p.get("prompts") or {}).items() if k in ("scene", "greeting") and v}


def preset_gender(manifest: dict, pid: str | None, iid: str | None = None) -> str | None:
    """identity_override.gender of the preset chain (nearest wins), else the identity's gender, else None (RFC 0003 § 4)."""
    return identity_view(manifest, pid, iid).get("gender")


def nicknames(i: dict) -> list[str]:
    """Every nickname: `nicknames` (1.1) else `nickname` (1.0), semicolon-separated values accepted."""
    out = list(i.get("nicknames") or [])
    if not out and i.get("nickname"):
        out = [x.strip() for x in str(i["nickname"]).split(";") if x.strip()]
    return out


def uses_1_1_fields(manifest: dict, src: Path | None = None) -> list[str]:
    """Which RFC 0003 fields a manifest uses (for the 'declare 1.1' rule)."""
    used = []
    for iid, i in (manifest.get("identities") or {}).items():
        for k in ("gender", "gender_label", "relations", "given_name", "family_name", "nicknames"):
            if (i or {}).get(k) is not None:
                used.append(f"identities.{iid}.{k}")
    for pid, p in (manifest.get("presets") or {}).items():
        if (p or {}).get("identity_override") is not None:
            used.append(f"presets.{pid}.identity_override")
        if (p or {}).get("prompts") is not None:
            used.append(f"presets.{pid}.prompts")
    if src is not None:
        for vid, v in (((manifest.get("elements") or {}).get("personality") or {}).get("variants") or {}).items():
            if v.get("psyche") and (src / v["psyche"]).is_file():
                try:
                    ps = json.loads((src / v["psyche"]).read_text("utf-8"))
                except Exception:
                    continue
                for k in ("archetype", "role"):
                    if ps.get(k) is not None:
                        used.append(f"personality.{vid}.psyche.{k}")
    return used


def cast_rules(manifest: dict, src: Path, rep) -> None:
    """Errors and warnings of RFC 0003 § 6 (vocabularies are enforced by the schema; this is what the schema cannot say)."""
    ids = manifest.get("identities") or {}
    for iid, i in ids.items():
        i = i or {}
        if i.get("gender") == "other" and not i.get("gender_label"):
            rep.warnings.append(f"identities.{iid}: gender 'other' without gender_label")
        for n, r in enumerate(i.get("relations") or []):
            where = f"identities.{iid}.relations[{n}]"
            to = r.get("to")
            if to == iid:
                rep.errors.append(f"{where}: a relation to oneself")
            elif to not in ids:
                rep.errors.append(f"{where}: unknown identity {to!r} (a relation names another character of the same file)")
            if r.get("type") == "other" and not r.get("label"):
                rep.errors.append(f"{where}: type 'other' needs a label")
        pairs = [(r.get("to"), r.get("type")) for r in i.get("relations") or []]
        for pr in {x for x in pairs if pairs.count(x) > 1}:
            rep.errors.append(f"identities.{iid}.relations: the same relation twice ({pr[1]} → {pr[0]}); two relations to one character must differ in type (colleague and friend)")
        if i.get("nicknames") and i.get("nickname") and i["nickname"] not in i["nicknames"]:
            rep.warnings.append(f"identities.{iid}: nickname {i['nickname']!r} is not among nicknames — 1.0 readers see `nickname`, keep it the first of `nicknames`")
        if i.get("given_name") and i.get("name") and i["given_name"].lower() not in i["name"].lower():
            rep.warnings.append(f"identities.{iid}: given_name {i['given_name']!r} does not appear in name {i['name']!r}")
    for pid, p in (manifest.get("presets") or {}).items():
        ov = (p or {}).get("identity_override") or {}
        if ov.get("gender") == "other" and not ov.get("gender_label") and not (ids.get((p or {}).get("identity") or manifest.get("default_identity") or "", {}) or {}).get("gender_label"):
            rep.warnings.append(f"presets.{pid}.identity_override: gender 'other' without gender_label")
    # both sides stored: they must agree (coherence)
    for iid, i in ids.items():
        for r in (i or {}).get("relations") or []:
            to, ty = r.get("to"), r.get("type")
            if to not in ids or to == iid:
                continue
            back = [b for b in ((ids[to] or {}).get("relations") or []) if b.get("to") == iid]
            if not back or r.get("mutual") is False or any(b.get("mutual") is False for b in back):     # a one-sided relation is declared on purpose
                continue
            want = ty if ty in SYMMETRIC else INVERSE.get(ty)
            if want and all(b.get("type") != want for b in back):
                rep.warnings.append(f"identities.{iid}.relations → {to}: '{ty}' on this side, {[b.get('type') for b in back]} on the other — the two sides disagree (coherence)")
    # a relation that began after the age the preset shows (coherence, RFC 0003 § 6)
    from .model import preset_age, preset_owner
    for pid in (manifest.get("presets") or {}):
        pa = preset_age(manifest, pid, ignore={"memories"})
        oid = preset_owner(manifest, pid)
        if pa is None or not oid:
            continue
        for r in ((ids.get(oid) or {}).get("relations") or []):
            sa = ((r.get("since") or {}).get("age") or {}).get("value") if isinstance(r.get("since"), dict) else None
            if isinstance(sa, (int, float)) and sa > pa:
                rep.warnings.append(f"presets.{pid}: relation {r.get('type')} → {r.get('to')} began at {sa:g}, after the age this preset shows ({pa:g}) — the character does not know that person yet (coherence)")
    # preset gender vs the voice's presentation (never blocking)
    for pid, p in (manifest.get("presets") or {}).items():
        g = preset_gender(manifest, pid)
        if not g or g in ("none", "other"):
            continue
        slots = resolve_preset_slots(manifest, pid)
        for vid in slots.get("voice") or []:
            v = resolve_variant(manifest, "voice", vid) or {}
            if not v.get("profile") or not (src / v["profile"]).is_file():
                continue
            try:
                prof = json.loads((src / v["profile"]).read_text("utf-8"))
            except Exception:
                continue
            if not isinstance(prof, dict) or not isinstance(prof.get("canonical"), dict):
                continue
            gp = str(((prof.get("canonical") or {}).get("gender_presentation") or "")).lower()
            vg = VOICE_TO_GENDER.get(gp)
            if vg and vg != g and g in ("female", "male"):      # only female × masculine and male × feminine are conflicts
                rep.warnings.append(f"presets.{pid}: gender {g} but voice {vid} presents as {gp} (coherence, not an error: a voice may differ on purpose)")


def relations_of(manifest: dict, iid: str) -> list[dict]:
    """The relations of a character, stored on either side: own entries, plus the inverse of what others declare (RFC 0003 § 3)."""
    ids = manifest.get("identities") or {}
    out = [dict(r, _stored=True) for r in ((ids.get(iid) or {}).get("relations") or []) if r.get("to") in ids and r.get("to") != iid]
    seen = {(r["to"], r.get("type")) for r in out}
    for oid, o in ids.items():
        if oid == iid:
            continue
        for r in (o or {}).get("relations") or []:
            if r.get("to") != iid or r.get("mutual") is False:
                continue
            ty = r.get("type")
            inv = ty if ty in SYMMETRIC else INVERSE.get(ty)
            if inv and inv != "other" and (oid, inv) not in seen:
                out.append({"to": oid, "type": inv, "_stored": False, "_declared_by": oid})     # the label and `since` are the other side's words and age: not carried over
                seen.add((oid, inv))
    return out


def drop_foreign_relations(manifest: dict) -> list[str]:
    """After an extract: relations whose target is no longer an identity of the file leave; returns what was dropped."""
    ids = manifest.get("identities") or {}
    gone = []
    for iid, i in ids.items():
        rel = (i or {}).get("relations")
        if not rel:
            continue
        keep = [r for r in rel if r.get("to") in ids and r.get("to") != iid]
        for r in rel:
            if r not in keep:
                gone.append(f"identities.{iid} → {r.get('to')} ({r.get('type')})")
        if keep:
            i["relations"] = keep
        else:
            i.pop("relations", None)
    return gone


def identity_lines(manifest: dict, iid: str, pid: str | None, lang: str) -> list[str]:
    """Lines for IDENTITY.md / a character card: gender (preset override first), relations."""
    L = "fr" if str(lang).lower().startswith("fr") else "en"
    i = identity_view(manifest, pid, iid)
    base = (manifest.get("identities") or {}).get(iid) or {}
    out = []
    nk = nicknames(i)
    if nk:
        out.append(("Surnoms" if L == "fr" else "Nicknames") + ": " + ", ".join(nk))
    g = preset_gender(manifest, pid, iid)
    if g:
        word = GENDER_WORDS[L].get(g, g)
        lab = text_in(i.get("gender_label"), lang)
        if g == "other" and lab:
            word = lab
        elif lab:
            word += f" ({lab})"
        if base.get("gender") and g != base.get("gender"):
            word += " — " + ("dans ce preset" if L == "fr" else "in this preset") + f" ({GENDER_WORDS[L].get(base['gender'], base['gender'])} " + ("au canon" if L == "fr" else "in canon") + ")"
        out.append(("Genre" if L == "fr" else "Gender") + f": {word}")
    rels = relations_of(manifest, iid)
    if rels:
        ids = manifest.get("identities") or {}
        items = []
        for r in rels:
            name = (ids.get(r["to"]) or {}).get("name") or r["to"]
            word = RELATION_WORDS[L].get(r["type"], r["type"])
            lab = text_in(r.get("label"), lang)
            items.append(f"{name} — {word}" + (f" ({lab})" if lab else "") + ((" (" + ("déclaré par " if L == "fr" else "declared by ") + name + ")") if r.get("_declared_by") else ""))
        out.append("Relations: " + " · ".join(items))
    return out


def psyche_lines(psyche: dict | None, lang: str) -> list[str]:
    """Lines for SOUL.md: the archetype and the role (RFC 0003 § 5)."""
    if not psyche:
        return []
    L = "fr" if str(lang).lower().startswith("fr") else "en"
    out = []
    a = psyche.get("archetype")
    if isinstance(a, dict) and a.get("value"):
        word = text_in(a.get("label"), lang) or (ARCHETYPE_WORDS[L].get(a["value"], a["value"]) if a.get("model") == "pearson-12" else a["value"])
        sec = [ARCHETYPE_WORDS[L].get(x, x) for x in (a.get("secondary") or [])]
        line = ("Archétype" if L == "fr" else "Archetype") + f": {word}"
        if sec:
            line += " (" + ("secondaire" if L == "fr" else "secondary") + ": " + ", ".join(sec) + ")"
        if a.get("model") == "pearson-12":
            line += " — Mark & Pearson" if L == "en" else " — modèle Mark & Pearson"
        out.append(line)
    if psyche.get("role"):
        out.append(("Rôle narratif" if L == "fr" else "Narrative role") + f": {ROLE_WORDS[L].get(psyche['role'], psyche['role'])}")
    return out
