# RFC 0003 — gender, pronouns, archetype, narrative role, relations between characters

- Status: draft (private until opened, with RFC 0002; then 14 days of comments from the opening of the PR)
- Author: Yann Souetre (with Claude)
- Date: 2026-10-25 (draft)
- Target: COF **1.1** — additive only; every 1.0 file stays valid and every 1.0 reader keeps working (§ 6)
- Reference implementation (same branch): `cof-cli` 1.1.0 (validator, coherence, `export --agent`, `extract --identity`), explorer 1.1, builder 0.13.0, examples 10 and 11

## 1. Motivation

COF 1.0 describes a character's looks, voice, body, personality and rights, and 1.1 adds its past (RFC 0002). Three things that any casting sheet states in its first line are still missing or scattered:

- **Gender.** The only place it appears is `voice/profile.json` (`gender_presentation`), and § 7 of the specification asks coherence checks to compare "gender across text, images and voice" without a field to compare against. A host that renders, voices or writes for a character guesses it from the pictures or the prose. A gender-swapped preset — a real practice — has no way to say so.
- **Who the character is in a story.** The personality card carries prose; `psyche.json` carries typed traits, goals, fears and values; nothing states the character's **archetype** (the pattern it embodies) or its **narrative role** (what it does in a story). Hosts that assemble a cast (video generators, game engines, writing tools) ask for exactly these two, and they are not the same thing: a *Creator* can be the protagonist or a foil.
- **Relations.** A cast file (example 11) holds several characters that are strangers to each other as far as the file knows. An agent playing one of them does not know the other is its friend, parent or rival.

The 1.0 vocabulary says nothing about any of this, so a 1.0 reader shows nothing wrong — it just does not know. This RFC adds the fields, all optional, and keeps the sensitive ones out of what a file must say.

## 2. What already exists, and the boundary

- **`voice/profile.json` › `gender_presentation`** stays what it is: how the *voice* sounds, which may differ from the character's gender (a disguise, a synthetic voice). The coherence API (§ 5) compares the two and reports, never blocks.
- **Age** stays a property of representations and presets (`age`, `age_override`, spec v0.5); gender follows the same split: a property of the **identity**, overridable by a **preset**.
- **`psyche.json`** stays "the character now" (RFC 0002 § 2); archetype and role are typed statements about it, added there, not in the card (CCV3 is a closed schema the hosts own).
- **Memories** link nodes (`links[]`, RFC 0002 § 3.2); relations between characters reuse the same grammar — a typed link to a qualified target — but live on the identity, because they are canon of the cast, not of a preset.
- **Out of scope**, deliberately: a film genre, an era or a budget (they belong to the host's rendering, or to `scenario` and free tags); a character's race or ethnicity (sensitive, and the morphology and images already carry what a renderer needs); sexual orientation (a sensitive attribute with no rendering value; a story states it in prose when it matters); a birth date (RFC 0002 decision: age is per representation).

## 3. Identity fields (normative)

```json
"identities": {
  "clara-mercier": {
    "name": "Clara Mercier", "fictional": true, "morphology": { "class": "human" },
    "gender": "female",
    "pronouns": { "fr": "elle", "en": "she/her" },
    "relations": [
      { "to": "martien", "type": "friend", "label": { "fr": "rencontré sur le quai de Saône", "en": "met on the Saône embankment" } }
    ]
  }
}
```

| Field | Required | Meaning |
|---|---|---|
| `gender` | no | `female`, `male`, `non-binary`, `none` (a robot, an entity, a thing), `other` (then `gender_label` says which). Absent = not stated. Lowercase, closed list; extension by RFC. |
| `gender_label` | no | Language map (BCP 47 → text), free wording when `other`, or a nuance for any value. |
| `pronouns` | no | Language map → the pronouns to use in that language ("elle", "she/her", "they/them"). Not derived from `gender` by a reader: absent means "use the language's default for `gender`, or neutral". |
| `relations` | no | List of `{ to, type, label?, since?, mutual? }`. `to` is the id of **another identity of the same file** (never `self`, never an outside file). `type` is one of the closed list below; `label` a language map (the sentence that matters); `since` an `age`-or-`date` point as in RFC 0002 `when` (optional: when the relation began, in the subject's life); `mutual` (boolean, default true for symmetric types) says the other side holds the same relation. |

Relation types, directed **from the subject to `to`**: `parent`, `child`, `sibling`, `partner`, `ex-partner`, `spouse`, `friend`, `colleague`, `mentor`, `student`, `rival`, `enemy`, `acquaintance`, `creator` (the subject made `to`: a robot's maker, an author), `creation`, `owner`, `pet`, `other` (then `label` is required). Symmetric types (`sibling`, `partner`, `ex-partner`, `spouse`, `friend`, `colleague`, `rival`, `enemy`, `acquaintance`) are **stored once**, on either side; a reader computes the other side. Asymmetric pairs (`parent`/`child`, `mentor`/`student`, `creator`/`creation`, `owner`/`pet`) are stored on one side and the inverse is computed; storing both sides is allowed and must agree (coherence finding otherwise).

Relations are **canon of the cast**: they do not vary by preset. A preset that tells another story (an alternate timeline, example 10's "AI war" line) describes it in its memories (RFC 0002) or its scenario, not by rewriting the cast. If a later need appears, a `presets.<id>.relations_override` can be added by RFC; nothing here prevents it.

A **real person** (`fictional: false`): `gender`, `pronouns` and `relations` are personal data. They are optional, never required by a check, and `cof extract --identity` drops the relations whose `to` leaves the file (as it drops dangling links). A relation to a real person who is not an identity of the file is not representable — by design (RFC 0002 § 11.4 discipline).

## 4. Preset field (normative)

| Field | Required | Meaning |
|---|---|---|
| `gender_override` | no | Same vocabulary as `gender`. The character is presented with this gender in this preset (a gender-swapped version, a disguise, a shapeshifter's form). Inherited through `extends` like `age_override`. Does not change the identity. |

A reader that needs "the gender of this preset" takes `gender_override` of the preset chain, else the identity's `gender`, else nothing.

## 5. Psyche fields (normative)

`elements/personality/<v>/psyche.json` gains two optional top-level keys:

```json
"archetype": { "model": "pearson-12", "value": "creator", "secondary": ["explorer"], "label": { "fr": "la créatrice", "en": "the creator" }, "notes": "…" },
"role": "protagonist"
```

| Field | Required | Meaning |
|---|---|---|
| `archetype.model` | with `archetype` | `pearson-12` — the twelve archetypes of Mark & Pearson (*The Hero and the Outlaw*, 2001; Jungian): `innocent`, `everyman`, `hero`, `caregiver`, `explorer`, `rebel`, `lover`, `creator`, `jester`, `sage`, `magician`, `ruler` — or `free` (any `value`). Other models by RFC. |
| `archetype.value` | with `archetype` | Lowercase key of the model (or free text when `model: free`). |
| `archetype.secondary` | no | Up to two more keys of the same model. |
| `archetype.label`, `notes` | no | Language map; free prose. |
| `role` | no | What the character does in a story, closed list: `protagonist`, `antagonist`, `mentor`, `ally`, `sidekick`, `foil`, `love-interest`, `narrator`, `ensemble`, `other`. Independent of the archetype: a *Creator* can be the antagonist. A super-power or a profession is neither — they belong to the card's prose and to `files`/skills. |

Why in `psyche.json` and not in the card: the card is a host-owned closed format (CCV3) and prose; the psyche is COF's typed layer, already versioned (`model: cof-psyche/0.1`, unchanged — both keys are optional). A personality variant without `psyche.json` has no archetype; the builder writes the file when either field is set.

## 6. Readers, writers, checks

- **Validator** (`cof validate`, 1.1): vocabularies (errors: unknown `gender`, `gender_override`, relation `type`, archetype `model`, `value` out of the model, `role`); `relations[].to` must name another identity of the file (error); `other` without `label` (error); a `cof: "1.0"` file that uses any of these fields: warning "this file uses 1.1 fields; declare `cof: "1.1"`" (1.0 readers ignore them anyway).
- **Coherence** (never blocking): the preset's gender (§ 4) against the voice's `gender_presentation` when both are stated and differ (`female` vs `masculine`…); two sides of a relation that disagree (`parent` on one side, `friend` on the other); a relation `since` after the subject's age in a preset (as RFC 0002's "older than the preset").
- **Export `--agent`**: `IDENTITY.md` states the gender and the pronouns of the preset's language; `SOUL.md` states the archetype and the role in one line each ("Archetype: the Creator (secondary: Explorer). Role: protagonist.") and the relations as a short list ("Relations: Martien — friend (met on the Saône embankment)").
- **Extract `--identity`**: relations whose `to` leaves the file are dropped (a note names them).
- **Explorer**: the character card shows the gender (and pronouns) as a badge, the preset's override when it differs, the relations as a list with the other character's name; the Personality tab shows the archetype and the role.
- **Builder**: a "Gender" select and a "Pronouns" field on the character card (step 1), "Gender in this preset" next to "Age in this preset" (step 4), "Archetype" (the twelve, or free) and "Role" on the personality card (step 2), "Relations" on the character card when the file holds several characters (the other character, the type, the sentence). All optional, nothing pre-filled.
- **ComfyUI-COF**: the COF Personality node's text block gains the archetype and role lines when present (0.6.x).

## 7. Compatibility

Every field is optional and every reader ignores unknown keys (spec § 1.2): a 1.0 reader sees nothing. A file that uses them declares `cof: "1.1"`. Examples 10 and 11 use them (Clara `female`, `elle` / `she/her`, Creator + Explorer, protagonist; the Martian `none`; a `friend` relation from Clara to the Martian in the cast file, which therefore becomes a 1.1 file too).

## 8. Open questions

- A **reference date of the canon** (`identities.<id>.now`): would date ages and memories together; left out until a reader needs it (ties to RFC 0002 `felt_now.as_of`).
- **Languages spoken** (`languages: [{ code, level }]`): the primary `language` (RFC 0002) says what the gists fall back to, not what the character speaks; likely 1.2.
- **Relations in time**: `since` is the only temporal marker; a relation that ends (`until`) can be added without breaking anything.
- Whether `gender_override` deserves its own coherence check against the preset's images (needs an image classifier; out of scope for cof-cli).
