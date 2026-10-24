"""RFC 0003 (1.1): gender, pronouns, archetype, narrative role, relations between characters.

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
VOICE_TO_GENDER = {"feminine": "female", "masculine": "male", "androgynous": "non-binary", "female": "female", "male": "male", "neutral": "non-binary"}


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


def preset_gender(manifest: dict, pid: str | None, iid: str | None = None) -> str | None:
    """gender_override of the preset chain (nearest wins), else the identity's gender, else None (RFC 0003 § 4)."""
    presets = manifest.get("presets") or {}
    q, seen = pid, set()
    while q and q in presets and q not in seen:
        seen.add(q)
        if presets[q].get("gender_override") in GENDERS:
            return presets[q]["gender_override"]
        q = presets[q].get("extends")
    if iid is None and pid and pid in presets:
        iid = presets[pid].get("identity") or manifest.get("default_identity")
    return ((manifest.get("identities") or {}).get(iid or "", {}) or {}).get("gender")


def uses_1_1_fields(manifest: dict, src: Path | None = None) -> list[str]:
    """Which RFC 0003 fields a manifest uses (for the 'declare 1.1' rule)."""
    used = []
    for iid, i in (manifest.get("identities") or {}).items():
        for k in ("gender", "gender_label", "pronouns", "relations"):
            if (i or {}).get(k) is not None:
                used.append(f"identities.{iid}.{k}")
    for pid, p in (manifest.get("presets") or {}).items():
        if (p or {}).get("gender_override") is not None:
            used.append(f"presets.{pid}.gender_override")
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
    # both sides stored: they must agree (coherence)
    for iid, i in ids.items():
        for r in (i or {}).get("relations") or []:
            to, ty = r.get("to"), r.get("type")
            if to not in ids or to == iid:
                continue
            back = [b for b in ((ids[to] or {}).get("relations") or []) if b.get("to") == iid]
            if not back:
                continue
            want = ty if ty in SYMMETRIC else INVERSE.get(ty)
            if want and all(b.get("type") != want for b in back):
                rep.warnings.append(f"identities.{iid}.relations → {to}: '{ty}' on this side, {[b.get('type') for b in back]} on the other — the two sides disagree (coherence)")
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
            gp = str(((prof.get("canonical") or {}).get("gender_presentation") or "")).lower()
            vg = VOICE_TO_GENDER.get(gp)
            if vg and vg != g:
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
            if inv and (oid, inv) not in seen:
                out.append({"to": oid, "type": inv, "label": r.get("label"), "since": r.get("since"), "_stored": False})
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
    """Lines for IDENTITY.md / a character card: gender (preset override first), pronouns, relations."""
    L = "fr" if str(lang).lower().startswith("fr") else "en"
    i = (manifest.get("identities") or {}).get(iid) or {}
    out = []
    g = preset_gender(manifest, pid, iid)
    if g:
        word = GENDER_WORDS[L].get(g, g)
        lab = text_in(i.get("gender_label"), lang)
        if g == "other" and lab:
            word = lab
        elif lab:
            word += f" ({lab})"
        if i.get("gender") and g != i.get("gender"):
            word += " — " + ("dans ce preset" if L == "fr" else "in this preset") + f" ({GENDER_WORDS[L].get(i['gender'], i['gender'])} " + ("au canon" if L == "fr" else "in canon") + ")"
        out.append(("Genre" if L == "fr" else "Gender") + f": {word}")
    pr = text_in(i.get("pronouns"), lang)
    if pr:
        out.append(("Pronoms" if L == "fr" else "Pronouns") + f": {pr}")
    rels = relations_of(manifest, iid)
    if rels:
        ids = manifest.get("identities") or {}
        items = []
        for r in rels:
            name = (ids.get(r["to"]) or {}).get("name") or r["to"]
            word = RELATION_WORDS[L].get(r["type"], r["type"])
            lab = text_in(r.get("label"), lang)
            items.append(f"{name} — {word}" + (f" ({lab})" if lab else ""))
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
