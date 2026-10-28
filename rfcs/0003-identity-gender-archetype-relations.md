# RFC 0003 — gender, archetype, narrative role, relations between characters

- Status: **open for comments until 14 November 2026** — published with COF 1.1.0 on 31 October 2026, which implements it, together with RFC 0002; what the comments change ships in 1.1.1
- Author: Yann Souetre (with Claude)
- Date: 2026-10-25 (draft)
- Target: COF **1.1** — additive only; every 1.0 file stays valid and every 1.0 reader keeps working (§ 6)
- Reference implementation (same branch): `cof-cli` 1.1.0 (validator, coherence, `export --format agent`, `extract --identity`, `COF.md` at pack, `cof memory add`), explorer 1.1, builder 0.13.0, examples 10 and 11

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
    "relations": [
      { "to": "martien", "type": "friend", "label": { "fr": "rencontré sur le quai de Saône", "en": "met on the Saône embankment" } }
    ]
  }
}
```

| Field | Required | Meaning |
|---|---|---|
| `given_name`, `family_name` | no | The first and family names. `name` stays the full **display** name (1.0 readers read it; the builder fills it from the two until edited). |
| `nicknames` | no | Every nickname, in order; `nickname` (1.0) stays the first one, so 1.0 readers see it. |
| `gender` | no | `female`, `male`, `non-binary`, `none` (a robot, an entity, a thing), `other` (then `gender_label` says which). Absent = not stated. Lowercase, closed list; extension by RFC. |
| `gender_label` | no | Language map (BCP 47 → text), free wording when `other`, or a nuance for any value. |
| `relations` | no | List of `{ to, type, label?, since?, mutual? }`. `to` is the id of **another identity of the same file** (never `self`, never an outside file). `type` is one of the closed list below; `label` a language map (the sentence that matters); `since` an `age`-or-`date` point as in RFC 0002 `when` (optional: when the relation began, **in the subject's life** — an age that means nothing for the other character); `mutual` (boolean, default `true` for every type) says whether readers compute the other side: `mutual: false` declares a one-sided relation (a friendship the other does not return, an enemy who does not know it) and no inverse is shown. These fields are defined on `identities.<id>` only: a single-character file that has no `identities` table introduces one (with `default_identity` and the root mirror of SPEC § 2.1) to use them — the builder always does. |

Relation types, directed **from the subject to `to`**: `parent`, `child`, `sibling`, `partner`, `ex-partner`, `spouse`, `friend`, `colleague`, `mentor`, `student`, `rival`, `enemy`, `acquaintance`, `creator` (the subject made `to`: a robot's maker, an author), `creation`, `owner`, `pet`, `other` (then `label` is required). Symmetric types (`sibling`, `partner`, `ex-partner`, `spouse`, `friend`, `colleague`, `rival`, `enemy`, `acquaintance`) SHOULD be **stored once**, on either side; a reader computes the other side, and merges a copy found on the other side (not an error). Asymmetric pairs (`parent`/`child`, `mentor`/`student`, `creator`/`creation`, `owner`/`pet`) are stored on one side and the inverse is computed; storing both sides is allowed and must agree (coherence finding otherwise, skipped when either side says `mutual: false`). `other` is never inverted: the other character does not see it unless it declares its own. The computed inverse carries the type only — **not** the `label` (the subject's own words, written from its side: Léo's "my mother" is not Clara's sentence) nor `since` (the subject's age); readers that show an inverse say who declared it.

Relations are **canon of the cast**: they do not vary by preset. A preset that tells another story (an alternate timeline, example 10's "AI war" line) describes it in its memories (RFC 0002) or its scenario, not by rewriting the cast. If a later need appears, a `presets.<id>.relations_override` can be added by RFC; nothing here prevents it.

A **real person** (`fictional: false`): `gender` and `relations` are personal data. They are optional, never required by a check, and `cof extract --identity` drops the relations whose `to` leaves the file (as it drops dangling links). A relation to a real person who is not an identity of the file is not representable — by design (SPEC § 11.4 discipline).

## 4. Preset field (normative)

| Field | Required | Meaning |
|---|---|---|
| `identity_override` | no | An object: how the character is **presented** in this preset, field by field — `name`, `given_name`, `family_name`, `nicknames`, `gender`, `gender_label`, `summary`. Absent fields are the identity's. Inherited through `extends`, nearest declaration wins **per field** (like `age_override`, which stays its own field for 1.0 compatibility). A gender-swapped version, a disguise, an alias, a shapeshifter's form, a summary that fits the preset's age. The identity itself is unchanged. |

What cannot be overridden, by design: `morphology` and `fictional` (another body or another person is another character), `consent` and `rights` (they are the person's), `language` (the preset's personality language already decides what the preset speaks, RFC 0002 § 3), `relations` (canon of the cast — a per-preset relation would have to be mirrored on the other character's presets and would break the computed inverses; if a real need appears, `relations_override` can be added by RFC), and the content flags, which are not an identity field at all: `tags.content` is file-level and **rises by itself** — a nude or intimate variant, an explicit memory, each adds its flag at build and `cof validate` checks the file carries them.

A reader that needs "the identity as this preset presents it" merges the override chain over the identity record (`cof_cli.cast.identity_view`); "the gender of this preset" is that view's `gender`.

### 4 bis. Default prompts (normative)

| Field | Required | Meaning |
|---|---|---|
| `prompts` | no | `{ "scene": <language map>, "greeting": <language map> }` — what a host uses when nothing more is asked: a **scene description** for image and video generators (framing, light, place), a **greeting** for dialogue generators (the preset's first line). **Not inherited** through `extends`: a scene fits one presentation (Clara at 12 does not sit at her desk), so each preset says its own. Neither replaces the card's `first_mes` (a host of cards keeps its own); `greeting` is the portable, per-language form. |

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

- **Validator** (`cof validate`, 1.1): vocabularies (errors: unknown `gender`, override field, relation `type`, archetype `model`, `value` out of the model, `role`); `relations[].to` must name another identity of the file (error); the same `(to, type)` twice (error — two relations to one character must differ in type: colleague and friend); `other` without `label` (error); `nickname` not among `nicknames`, `given_name` absent from `name` (warnings); a `cof: "1.0"` file that uses any of these fields: **error** "cof 1.0 declared but the file uses 1.1 additions — declare `cof: "1.1"`", the same rule as RFC 0002 § 6.1 (a file declares the lowest minor that defines everything it uses; the error is harmless to 1.0 readers, which ignore the fields — § 8); `relations[].to` unknown even when the `identities` table is absent (error).
- **Coherence** (warnings, never blocking): the preset's gender (§ 4) against the voice's `gender_presentation` — only the two clear conflicts, `female` × `masculine` and `male` × `feminine` (`androgynous` and `neutral` voices, `non-binary`, `none` and `other` characters never conflict; a voice legitimately differs on purpose); two sides of a relation that disagree (`parent` on one side, `friend` on the other — unless one side says `mutual: false`); a relation whose `since.age` is later than the age a preset shows (the character does not know that person yet); an archetype listed as both primary and secondary, a `free` model without a value.
- **Export `--agent`**: `IDENTITY.md` states the gender; `SOUL.md` states the archetype and the role in one line each ("Archetype: the Creator (secondary: Explorer). Role: protagonist.") and the relations as a short list ("Relations: Martien — friend (met on the Saône embankment)").
- **Extract `--identity`**: relations whose `to` leaves the file are dropped (a note names them).
- **Explorer**: the character card shows the gender as a badge, the preset's override when it differs, the relations as a list with the other character's name; the Personality tab shows the archetype and the role.
- **Builder**: given name, family name (the display name fills itself from them), nicknames separated by ";", a "Gender" select on the character card (step 1); "Relations" with its column headers (who, relation, description, since) when the file holds several characters, a new row defaulting to a type not yet used with that character; an "Identity in this preset" fieldset on the preset card (step 4, folded; names, nicknames, gender, summary, each empty = the character's; the hint says what cannot be overridden and why), "Archetype" (the twelve, or free) and "Role" on the personality card (step 2), "Relations" on the character card when the file holds several characters (the other character, the type, the sentence). All optional, nothing pre-filled.
- **ComfyUI-COF**: the COF Personality node's text block gains the archetype and role lines when present (0.6.x).

## 7. The container describes itself: `COF.md`

Every `.cof` written by `cof pack` or by the builder carries a short `COF.md` at its root (≈ 4 KB): what the file is, how to read `manifest.json`, the rules a host must honour (rights, ages, real persons, content flags, memory disclosure), and **how to write back** what the character lives — a `lived` / `personal` memory node, step by step, or `cof memory add`. It is a courtesy for a reader without the specification (an agent that opens the file, a script, a person); it is **never normative**: the specification and the manifest win, and the note says so. It is regenerated at every pack and is not part of the character (not an asset, no hash, dropped by nothing). The agent export already wrote a `COF.md` of its own (rights the host must honour); the two share the name and the intent.

`cof memory add <file.cof | folder> [--identity <id>] [--kind moment|period] --gist <lang>=<text> [--date] [--age] [--where] [--who "label[|shown][|age][|real]"] [--self-shown] [--tag] [--media] [--personal] [--preset]` is the matching write path (`--self-shown` with `--age` when the character is in the media — the variant then carries the age the minor rules read; `--who "Sam|shown|34|real"` for someone else, as the builder's "other people" line): it creates the node file, declares the variant and its media (`memory-media`, hashed), lists the node in the presets (copying an inherited list before adding to it), sets `cof: "1.1"`, validates, and repacks in place. A host or an agent can call it after a conversation; nothing else is required to make a `.cof` grow with its user.

## 8. Compatibility

Every field is optional and every reader ignores unknown keys (spec § 1.2): a 1.0 reader sees nothing. A file that uses them declares `cof: "1.1"`. Examples 10 and 11 use them (Clara `female`, Creator + Explorer, protagonist; the Martian `none`; a `friend` relation from Clara to the Martian in the cast file, which therefore becomes a 1.1 file too).

## 9. Open questions

- **Pronouns** (`pronouns`, a language map): considered and left out of 1.1 — almost always derivable from `gender` in the languages COF ships in; a field can be added when a host asks for it.

- A **reference date of the canon** (`identities.<id>.now`): would date ages and memories together; left out until a reader needs it (ties to RFC 0002 `felt_now.as_of`).
- **Languages spoken** (`languages: [{ code, level }]`): the primary `language` (RFC 0002) says what the gists fall back to, not what the character speaks; likely 1.2.
- **Relations in time**: `since` is the only temporal marker; a relation that ends (`until`) can be added without breaking anything.
- Whether the preset's gender deserves its own coherence check against the preset's images (needs an image classifier; out of scope for cof-cli).
