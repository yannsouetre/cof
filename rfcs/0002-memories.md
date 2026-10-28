# RFC 0002 — `memories`: the character's past, as a graph of nodes

- Status: draft (private until opened; then 14 days of comments from the opening of the PR)
- Author: Yann Souetre (with Claude)
- Date: 2026-10-24 (draft)
- Target: COF **1.1** — additive only; every 1.0 file stays valid and every 1.0 reader keeps working (§ 7)
- Reference implementation (same branch): `cof-cli` 1.1.0 (validator, `export --format agent`, `extract` purges), explorer 1.1 (timeline), builder 0.13.0 (Memories step), ComfyUI-COF 0.6.0 (COF Memories node and preview workflow), example 10, the seed pipeline `tools/seed/memories.py`, fixture and negative corpus (§ 10)

## 1. Motivation

A character today travels with its personality, its looks, its voice, its body and its rights, but not with its **past**. What a companion remembers of its life with a user lives on the platform's server, as text (`MEMORY.md`, dated notes, vectors): change the app, lose the story. And what an author writes as the character's backstory is a paragraph in a card, not something a reader can place in time, show, or reason about.

A person's memories are not paragraphs. They are images, sounds, places, people, feelings, situated in time, some vivid and some faded, some told freely and some never. If synthetic characters are to come closer to people in depth, they must carry those memories **with them, in the file** — as media and structured text, next to the identity, with the rights that go with them.

What is new here is not episodic memory for agents (Generative Agents, 2023; MemGPT/Letta; lorebooks; companion apps all have one). It is an **open, portable container** for it: multimodal, dated, situated, per character, with consent and provenance, readable by any tool. This RFC calls it *the missing piece*, not a revolution; use will tell.

## 2. What already exists, and the boundary

- **`files` / `kind: memory`** (1.0, SPEC § 7 bis) carries an agent's memory file **in the host's own format** (`MEMORY.md`, dated notes): opaque, copied as-is by `cof export --format agent`. It stays. The new category is the **structured, portable** form; a file may hold both. The agent export combines them (§ 6.4).
- **`personality/psyche.json`** (typed traits, goals, fears, values) describes the character *now*. It is untouched. A later RFC — **RFC 0004, "psyche graph", targeted at COF 1.2 shortly after 1.1** — will add the inner life (values, beliefs, wants, needs, fears, wounds, stances) as nodes of the same mechanism, linked `because` to memories; this RFC defines the mechanism so that the two categories link to each other.
- **`appearance` / `volume3d` `environment`** are the places a character is tied to. A memory points to one (§ 4.6); it does not define places. A hierarchy of places (room ⊂ house ⊂ town) is world knowledge, left to a future "world" category built on the same mechanism (§ 9).
- The emotion structure of `psyche.json` (`baseline_emotion`: an EmotionML category and PAD dimensions) is reused as-is for feelings (§ 4.8). No new vocabulary.

## 3. The graph mechanism (normative, shared with later categories)

A **node** is a variant of a category that names a **node file** (its content) and carries on the **manifest variant** what tools read without opening the file — the 1.0 split between a variant (asset lists, `age`, `nudity`, `identity`, `label`) and its sub-file (`card`, `profile`, …). On the manifest variant:

| Field | Required | Meaning |
|---|---|---|
| `kind`, `label`, `identity` | as in 1.0 | |
| the node file path (`memory` for this category) | **yes** | The content, validated by the node schema. |
| `media[]` | no | Asset ids (image, audio, video, text, `other`). The verbatim trace, opened on demand. |
| `media_from` | no | Reference to another node whose `media` this node reuses (§ 4.5). Exclusive with `media`. |
| `age` | when a media shows the character | The character's age at the time (1.0 structure); enters the preset's lowest age (§ 5.2). |
| `nudity` | with `explicit` | The 1.0 flag, so that 1.0 tools see explicit nodes (§ 5.3). |

In the node file:

| Field | Required | Meaning |
|---|---|---|
| `gist` | **yes** | A short text, as a map of language → string (BCP 47 keys, at least one entry). The trace a reader always loads. |
| `when`, `where`, `who` | no | The axes (§ 4.2). |
| `felt_then`, `felt_now` | no | Feelings (§ 4.8). |
| `links[]` | no | Typed, directed references to other nodes (§ 3.2). |
| `tags[]` | no | Slugs (lowercase ASCII letters, digits, `-` and `:`, as `tags.*` in 1.0; builders slug what the author types): objects, events, public figures… — the axes a reader indexes on, with `when` / `where` / `who`. |
| `origin`, `visibility`, `disclosure` | no | The three policy axes (§ 3.3). |

**Short texts attached to a node are multilingual inside the node** (`gist`, the `label` of `when`, `where`, `who`): a memory is one node whatever the languages, so that links and presets refer to one thing. Long texts stay per-language variants, as in 1.0. Choosing an entry: the language of the personality variant the preset applies → the identity's primary language (`identities.<id>.language`, new, optional, § 7) → the only entry; with several entries and no primary language, the first one, and a validator warns. A language matches by exact tag, else by base language (`fr-CA` reads `fr`).

**A node has a "when"; a media never does.** A lone image is a moment with one media. The same asset may be referenced by several nodes of the same character.

### 3.1 Node references

A reference to a node is **always qualified**: `"<category>/<variant id>"` (`memories/ev3`; tomorrow `psyche/n2`). One grammar for every category; no short form. An unresolved reference is a validation error, like every broken reference in 1.0.

### 3.2 Links

`links: [ { "to": "<category>/<id>", "type": <type>, "label"?: { lang: string } } ]`. Five types, each stored in **one direction** (the reader computes the inverse):

| Type | From → to | Use |
|---|---|---|
| `after` | later → earlier | Order when `when` does not settle it (undated nodes), and the one way to say that a moment is **not** inside a period whose dates would contain it (§ 4.3). Contradicting the dates — the later node starts before the earlier one ends; bounds that touch are not a contradiction: warning. |
| `part-of` | moment → period | The moment belongs to the period, whatever the dates say (undated, unbounded, deliberately out of range — or simply made explicit: **editors follow this link, never the dates**, § 4.3). Readers also nest by dates. A `part-of` moment outside the period's dates is informational, never an error. Never a list on the period. |
| `about` | node → node | This node is about that one (a dream about an event; a memory of a film about a period). |
| `because` | node → node | This node exists because of that one (a move because of a meeting; an opinion because of a memory — the psyche RFC's main link). |
| `same-event` | node ↔ node | Two characters' memories of one event (§ 4.5). Symmetric: either or both may carry it; readers merge. |

No free type. New types come by RFC, sparingly. Everything an axis says (same place, same person, same period by dates) is **not** a link: readers derive it.

### 3.3 Policy axes

| Field | Values | Default | Meaning |
|---|---|---|---|
| `origin` | `authored` \| `lived` | `authored` | Written by the character's author (ships with the file) / written by a tool during use with a user. |
| `visibility` | `canon` \| `personal` | `canon` | Part of the character, travels with the file / **a user's personal data**: stays in that user's copy. |
| `disclosure` | `open` \| `guarded` \| `secret` | `open` | The character tells it freely / only when asked or trusted / never — but it shapes behaviour. A reader never quotes a `secret` node in a reply; it uses it as context. |

The three are independent: a `lived` memory a user wants to share with their version of the character is `lived` + `canon`; an author's buried wound is `authored` + `canon` + `secret`. Validators are **silent** on an absent field (the default applies); builders write the three explicitly and show the default before saving.

**Canon is read-only for tools.** A tool MUST NOT modify an `authored` node. Everything that happens in use is a layer of `lived` nodes: when a feeling about a canon memory changes in use, the tool creates a `lived` + `personal` node linked `about` the canon one. A tool MAY rewrite the gist and `felt_now` of its own `lived` nodes at each recall, keeping the previous versions in `revisions[]` (`{ date, gist, felt_now?, by? }`, newest first, text only, bounded — ten is a reasonable cap). A media transformed at inference time is a new asset, declared like any generated media (`digitalSourceType`, `generator`), and **replaces** the previous one on that node; it does not accumulate.

## 4. The `memories` category

### 4.1 Regime, kinds, files

`memories` is a **library** category (SPEC § 2.3): a preset lists the memories available to it (`slots.memories`), inherited through `extends` like every slot; nothing is loaded by a reader that is not interested. Two kinds:

- `moment` — a point in the character's life (an afternoon, a meeting, a dream). `when` is a point.
- `period` — a span (the student years). `when` has `from` / `to`. Same schema; a period MAY carry media, but SHOULD stay light (a gist and a dominant feeling); large sets of media belong to a period rather than to each moment, and COF is not a photo album.

Variant ids are free, as everywhere in COF; the builder names moments `ev<n>` and periods `ep<n>` (prefixes no other category uses, so a code is readable on its own and never clashes with `p1` of a personality or `m1` of a mesh). Each variant names its node file: `"memory": "elements/memories/<v>/memory.json"` (schema `memory.schema.json`, § 7), lists its media and, when a media shows the character, carries the character's age at the time. Media are assets with the new role **`memory-media`** (an image of a memory is not a `view` of the character). A media is an image, an audio clip, a short video, or a **short text** (a few remembered lines of a conversation, `text/markdown` or `text/plain`): text and speech media carry `language`; a video SHOULD travel with a poster image (an image media `derived_from` it, `method: "thumbnail"`) so that readers show something before playing; the 1.0 cap of `motion` videos applies (20 MB unless `max_bytes_ack: true` on the memory variant, as on a `motion` variant). A text media is the memory's own words, not a transcript of an audio media (that is `assets[].transcript`).

```jsonc
"memories": { "variants": {
  "ev1": { "kind": "moment", "label": "Grandmother's house",     "memory": "elements/memories/ev1/memory.json", "media": ["a-ev1-drawing"] },
  "ep1": { "kind": "period", "label": "The student years",       "memory": "elements/memories/ep1/memory.json" },
  "ev2": { "kind": "moment", "label": "The office, rue de la Ré", "memory": "elements/memories/ev2/memory.json", "media": ["a-ev2-office"] },
  "ev3": { "kind": "moment", "label": "Meeting the Martian",     "memory": "elements/memories/ev3/memory.json", "media": ["a-ev3-meeting"],
          "age": { "value": 29, "unit": "years", "basis": "canonical" } },                    // Clara is shown, at 29
  "ev4": { "kind": "moment", "label": "The electric-sheep dream", "memory": "elements/memories/ev4/memory.json", "media": ["a-ev4-dream"],
          "age": { "value": 29, "unit": "years", "basis": "canonical" } } } }
// presets.default.slots.memories = ["ev1", "ep1", "ev2", "ev3", "ev4"]; presets.fr-12.slots.memories = ["ev1"]
```

### 4.2 `memory.json`

Clara is bilingual, so her short texts carry two entries; a monolingual character carries one.

```jsonc
{ "gist": { "en": "The summer I was eight: my grandmother's house in Oullins, the smell of the lime tree, the drawing I made of the garden.",
            "fr": "L'été de mes huit ans : la maison de ma grand-mère à Oullins, l'odeur du tilleul, le dessin que j'ai fait du jardin." },
  "nature": ["experienced"],
  "when":  { "age": { "value": 8, "unit": "years" }, "approx": true, "label": { "en": "the summer I was eight", "fr": "l'été de mes huit ans" } },
  "where": { "label": { "en": "my grandmother's house, in Oullins", "fr": "la maison de ma grand-mère, à Oullins" } },
  "who":   [ { "label": { "en": "my grandmother", "fr": "ma grand-mère" } } ],
  "felt_then": { "category": { "set": "everyday", "value": "content" },  "pad": { "pleasure": 0.7, "arousal": 0.2 } },
  "felt_now":  { "category": { "set": "everyday", "value": "affectionate" }, "pad": { "pleasure": 0.6, "arousal": -0.2 } },
  "salience": 70, "fidelity": "faded",
  "origin": "authored", "visibility": "canon", "disclosure": "open",
  "tags": ["childhood", "house", "garden"],
  "links": [] }
```

Fields, all optional unless stated:

- **`gist`** (required) — map of language → text. SHOULD stay under 1,000 characters per language (warning above).
- **`nature`** — list, one or more of `experienced` (the character was an actor), `learned` (a film, a book, a place, a context — third-party media follow `tags.ip` and the rights rules), `witnessed` (told by others; vicarious memory), `imagined` (a dream, a fantasy, a plan). Default `["experienced"]`. It is what says whether the character was there; there is no `present` field.
- **`when`** — for a moment: `{ age?, date?, approx?, label? }`; for a period: `{ from?: point, to?: point, approx?, label? }`, a point being `{ age?, date?, approx? }` (`approx` per bound: "from about 24"). `age` is the 1.0 age structure (`{ value, unit }`) — the character's age at the time; `date` is a partial ISO date (`YYYY`, `YYYY-MM`, `YYYY-MM-DD`; precision is read from its shape). Age and date combine. No `when` means "I no longer know when" (allowed). A dream is placed at the age it was dreamt.
- **`where`** — `{ label?, environment?, geo? }`: `environment` is a qualified reference to an `environment` variant of the **same character** (`appearance/e1`, `volume3d/env1`); `geo` is `{ lat, lon }` in decimal degrees (EXIF convention), for real places. No place hierarchy here (§ 9).
- **`who`** — list of entries with `identity` (`"self"` or a cast id — `"self"` is the only value a file without an `identities` table knows) and/or `label` (at least one of the two; a `label` beside an `identity` is a display label for this node), each with optional `shown` (appears in a media; absent = only in the story), `age` (that person's age then — the character's own is `when.age`), `real: true` (a real person who is not modelled as an identity; on an `identity` entry it is ignored: the identity's `fictional` decides). The character is listed only when `shown` — `{ "identity": "self", "shown": true }` is the declaration the validator relies on to know the character is in the picture (§ 5.9).
- **`felt_then`, `felt_now`** — the `baseline_emotion` structure of `psyche.json` (`category: { set, value }`, `pad`). "Now" is the character's canonical present (the default preset); `felt_now.as_of` (a point) MAY say when. Authors write both on `authored` nodes; tools write them on `lived` nodes only (§ 3.3).
- **`salience`** — 0–100, how much the memory matters. Absent: readers MAY derive it from the intensity of `felt_then`.
- **`fidelity`** — `vivid` | `clear` | `faded` | `fragment`; default `clear`. What the character remembers, per node, never per media. Tools that need a number use 1.0 / 0.7 / 0.4 / 0.15. A renderer MAY degrade a media (blur, desaturate, downscale) according to fidelity, and MUST NOT "upgrade" one; a text agent lets fidelity colour how the character speaks of it. The per-asset flag **`as_remembered: true`** (new, on `memory-media` assets) says the file already looks the way the memory does — do not degrade it. Fidelity is never set to fix rendering.
- **`factual`** — `true` | `false`, meaningful **only for a real-person identity** (`fictional: false`): did this really happen in that person's life. Absent = unknown; a validator warns for every memory **of** a real person (a node owned by that identity) without it (never blocks). A reader playing a real person never presents a memory as a fact unless `factual: true`. A real person's dream: `nature: ["imagined"]`, `factual: true`. Ignored for fictional identities.
- **`explicit`** — `nudity` | `intimate` (§ 5). Absent = all audiences.
- **`origin`, `visibility`, `disclosure`, `links`, `tags`, `revisions`** — § 3. (`media`, `media_from`, `age` and `nudity` live on the manifest variant.)

### 4.3 Order and timeline

A reader orders nodes by age, else by date, else by links (`after` and `part-of` first; `about`, `because` and `same-event` as hints that place an undated node just after its target), else "undated" (shown apart). A node with both an age and a date implies a birth year; two nodes implying different birth years are a coherence finding (§ 6.2), and a reader MAY derive the age of a node that has only a date. No birth date on the identity: age is a property of representations and presets in 1.0, and the memories reveal it.

**Membership of a moment in a period** (§ 3.2) is computed by a reader from the dates it shows: a moment whose point sits within both bounds of a period, on the same axis (ages, else dates at their common precision), belongs to it — *inside* means `start ≤ point ≤ end`, bounds inclusive; an explicit link wins over the dates: `part-of` settles the undated, unbounded and deliberately out-of-range cases, and a moment linked `after` a period is not inside it, whatever its dates say (Clara's first morning in the studio, at 28, is `after` the agency years 24–28: the ages touch, the link decides). An `after` link **contradicts** the dates only when the later node starts before the earlier one ends (`point < end`): touching bounds are the normal case the link exists for, and a validator warns on the contradiction (§ 6.1). A reader nests by that rule among the nodes the preset lists. An editor that lets a preset pick a whole period brings only the moments linked `part-of` with it: a moment that merely falls within the dates may belong to another line of the same file (a restyled set, an alternate timeline) and is picked on its own.

### 4.4 Memories and presets

Each node belongs to one character (`variant.identity`, as every element). A preset lists its memories in `slots.memories`; through `extends`, a file with many presets lists them once (Clara's `default`) and redeclares the subset where it differs (`fr-12`: childhood only). A preset younger than a memory it lists (Clara at 12 listing her memory at 30) is a **coherence finding**, never an error: incoherent characters are the author's right. A variant listed by no preset is backstage, as in 1.0.

### 4.5 Shared media, not shared memories

A memory is subjective: Clara and the Martian remember the same meeting with different gists, feelings and fidelity. So **one node per character**, linked `same-event`. The **media** may be shared: this RFC makes one narrow exception to the 1.0 rule that only neutral elements share files — a `memory-media` asset that shows several cast members MAY be referenced by one memory node of each character shown, **only** through the variant field **`media_from: "memories/<id>"`** ("my media are that node's": transitive, a cycle is an error, exclusive with `media`). Listing the same asset in two characters' `media` is the 1.0 error it always was (a `memories` variant is never neutral), so the exception exists only through this field and is easy to find and to check. `media_from` inherits the media and nothing else: the borrowing node declares its own `who`, and the safety flags are **not inherited and not inheritable** — a node whose effective media (through `media_from`, transitively) come from an `explicit` node MUST itself declare the same `explicit` value and `nudity: true`, and who is shown (§ 5.4); a validator refuses the file otherwise. The media of an explicit node are therefore used by no non-explicit node, whatever folder they sit in.

Guard at extraction: when a character is extracted (`cof extract --identity`), the other characters' consent records do not travel with it; memory media that show **another real person** are therefore dropped from the extracted file (gist kept, warning); media showing other fictional characters are kept.

### 4.6 Agent reading

A reader that plays the character loads the gists of the memories the preset lists (ordered by § 4.3), honours `disclosure`, and opens media on demand — never an `explicit` media without the gate of § 5. One agent reads a hundred gists for the price of one image: that is the point of the gist.

## 5. Safety and rights (normative)

The 1.0 rules apply unchanged; this section says how they read on memories.

1. **What is shown decides, not what is told.** A childhood memory in text, or illustrated by a house or a child's drawing, shows no minor and carries no age. A memory whose media show a person is a representation of that person **at that age**.
2. **A node with media showing the character carries an age on its manifest variant** (`age`, mirrored from `when.age`: the variant age is the one every age rule reads; on an explicit node the two MUST agree — error — and elsewhere a difference is a warning), and that age **enters the preset's lowest age** like every morphological variant (SPEC § 2.2, § 9.4). A preset that lists a memory showing a minor is a minor preset: no `intimate`, no `nudity`, no effective `allowSexualUsage` anywhere in it. The partition stays **the preset**, as in 1.0 — not the file; an author who wants both makes an adult preset that lists only adult memories.
3. **Explicit memories.** `explicit: nudity` (nudity without visible genitals) or `explicit: intimate` (visible genitals or a sexual act) marks a node whose media show it; the manifest variant **also** carries the 1.0 flag `nudity: true` and the file carries `tags.content` (`nudity`, and `sexual` for `intimate`), so that 1.0 tools — `cof extract --no-intimate`, readers that hide nude assets — already do the right thing without knowing this category. The three consequences of the 1.0 opt-in (SPEC § 4.5) extend to memory media: never loaded by default (the preset's effective `allowSexualUsage` **and** an explicit request of the host), used by no non-explicit node (§ 4.5 above — the counterpart of the intimate folder rule), flagged. A text agent reads the gist; the media stays closed. The gist itself is text and falls under `tags.content` like a card.
4. **Every person shown in an explicit memory must have a known age ≥ 18**: the character through the variant `age` (equal to `when.age`), others through `who[].age`. An absent age is unknown, and an unknown age never counts as adult (1.0 rule): the file is invalid. An explicit media shows someone, so an explicit node **declares at least one person shown** (`who[].shown`, `identity: "self"` for the character); a node with nobody declared shown is invalid — otherwise the age rule would have nobody to apply to. And **the character's own age at the time** (`when.age`, or the start of a period) **must be known and ≥ 18 on any explicit node, whoever is shown**: a memory lived as a minor is never explicit, even in words, even when only an adult appears — error.
5. **Real persons.** A real person shown in an explicit memory must be an identity of the cast whose consent record carries the matching scope — `intimate` for `explicit: intimate`, `nudity` or `intimate` for `explicit: nudity`, the 1.0 rule of `appearance/intimate` — each for their own body; several consenting real identities of one file may share memories of a scene. A real person shown nude who is not such an identity: error. A clothed real person who is not modelled (`who[].real: true`): warning, and the author's discipline of SPEC § 11.4. A memory **of** a real person (a node that identity owns) requires their consent scope `conversational-persona` (SPEC § 7 bis.4) and `factual` (§ 4.2); a memory that **names** a real identity of the file in `who`, shown or not, requires that person's `conversational-persona` scope (warning).
6. **The AI age check** (SPEC § 9.4.5) applies to memory media: a person who looks underage in an explicit node is `illegal`; undeclared nudity is `major`.
7. **Personal data.** `visibility: personal` nodes are a user's data. `cof pack` warns when a file holds any; `cof extract`, `cof export` and any sharing path drop them unless asked to keep them (`--keep-personal`); a builder's build keeps them only on an explicit option, unchecked by default; a platform whose governance refuses them drops them at import; a node that borrowed a personal node's media (`media_from`) loses them with it. Independent of the all-audiences purge.
8. **All-audiences purge.** `cof extract --all-audiences` (alias of `--no-intimate`) also drops the media of `explicit` nodes (gist kept). A builder offers it at build time; an importing platform MAY apply it at reception (implementing guide).
9. **What binds the author and the host, and no program checks** (as SPEC § 11.1): that `who[].shown` lists everyone a media shows — the validator reads the declaration, not the picture (the AI age check of point 6 is the only look at the pixels); that a tool never modifies an `authored` node (sub-files carry no hash: a host's discipline); that a renderer never upgrades a media against `fidelity`; that a reader honours `disclosure`. A host that adds media to a `lived` node says who is in them (`who[].shown`, `real: true` for the user; `cof memory add --self-shown` / `--who "…|shown|…|real"`); a lived node with image or video media and nobody declared shown gets a warning.

## 6. Tooling

### 6.1 Validator (`cof validate`, 1.1)
Errors: node file missing or invalid against `memory.schema.json`; `gist` absent or empty (an empty string is empty); unresolved `links[].to`, `media`, `media_from`, `where.environment`, `who[].identity` (a file without an `identities` table knows only `"self"`); `media_from` cycle, or `media` and `media_from` together; `where.environment` across characters; a period with a point `when` or a moment with `from`/`to`; `part-of` whose target is not a period, or from a node that is not a moment; a node whose media show the character without a variant `age`; an explicit node without `nudity: true` or without the matching `tags.content`; an explicit node with nobody declared shown; an explicit node whose variant `age` differs from `when.age`; an explicit node with any shown person of unknown age or under 18 (the character included); an explicit node in a preset under 18 (the 1.0 preset rule, through `nudity: true`); a node borrowing the media of an explicit node without declaring the same `explicit` value itself; a real person shown in an explicit node without the matching consent scope (`intimate` for `intimate`, `nudity` or `intimate` for `nudity`), or a real person shown who is not an identity of the file; `revisions` carrying media; a file that uses this category and declares `cof: "1.0"`.
Warnings: gist over 1,000 characters; `after` contradicting the dates (§ 4.3: the later node starts before the earlier one ends); ages and dates of one character implying birth years more than a year apart; gist without an entry in the identity's primary language; several gist languages with no primary language; a memory of a real person without `factual`; a memory naming a real identity of the file whose consent lacks `conversational-persona`; `who[].real` without an identity (a real person no consent can be recorded for); a variant `age` that differs from `when.age` (non-explicit node); a variant marked `nudity` whose node has no `explicit`; `revisions` on an `authored` node (default included); a lived node with image or video media and nobody declared shown; `personal` nodes present; a video over the `motion` cap (20 MB unless `max_bytes_ack` on the variant); a video without a poster image; a text media without `language`. The "mixes very different ages" warning of 1.0 ignores memories (a memory legitimately shows another age).
Coherence findings (the builder's checks step and the coherence API, never blocking, not in `cof validate`): a preset younger than a memory it lists; a `part-of` moment outside its period's dates; a memory "at 8" in a place the character never declared; a moment linked `after` a period whose dates contain it (information: the link wins).

### 6.2 Coherence API
The preset bundle gains the gists (ordered) and the thumbnails of memory media, labelled by node; the checks `age-legality`, `nudity`, `element-consistency` run on memory media too; a new check `memory-timeline` returns the findings above.

### 6.3 Completeness
Memories do not enter the completeness score in 1.1 (a new layer would change every 1.0 score). They appear in `coverage`, and in the automatic tag `has-memories`.

### 6.4 Exports
- `cof export --format agent`: `MEMORY.md` = the host memory file of `files/memory` when present, followed by a section "Memories" listing the canon gists in timeline order with their age/date, `disclosure` and fidelity as markers (`factual` marked for a real person's memories only; `secret` and `guarded` gists are exported with their marker — the workspace file is the agent's context, the rule of § 3.3 is about what it says in a reply); a `memories/<id>/` folder with the media of non-explicit nodes, minus the media that show another real person (the § 4.5 guard applies to the export as to the extract: the agent workspace carries no consent record at all). `personal` nodes are not exported unless `--keep-personal`.
- `cof extract`: § 4.5 and § 5.7–5.8.
- The explorer shows a timeline by age (undated apart), the gist in the preset's language, media on click (explicit never; nude only on opt-in on an adult preset). Its tabs follow the builder's categories, in the builder's order and with its icons (personality, look, identity weights, 3D, voice, postures, motions, skills and files, memories, rights); a 🔍 on every element and every memory opens every parameter read-only (the manifest entry, then the node file or sub-file). The graph labels a membership computed by dates "during".

### 6.5 Builder
A "Memories" step (0.12–0.13, step 3 of 7, advanced mode), with the grammar of the Elements step: one card per node — moment (green dot) or period (purple square), a free label and a fixed code (`ev1`, `ep2`: never reused, renamed on a merge collision), gist per language, when / where / who, feelings then and now, salience, a four-notch fidelity, nature, factual (real persons), the three policy axes as radio buttons with the defaults pre-selected and **written explicitly**, explicit (greyed out while any person shown is under 18 or of unknown age; with the nudity confirmation; the variant gets `nudity: true` and the file its `tags.content`), links with a node picker (`part-of` only from a moment to a period, said on the card; no one types `memories/m3`), tags, one to three media with the drop zone and thumbnails of the Elements step, or "same media as…" (`media_from`); the character's primary language on its identity card. **Presets pick their memories like any library**: a "Memories" fieldset lists the periods and the loose moments as chips in the style of the other libraries (○ / ✓, the moment or period icon, a 🔍 that opens the card read-only with a "go there" button — every chip of the presets step has that loupe); a ticked period brings the moments linked `part-of` with it (inherited through `extends`; § 4.3 on why not the moments by dates). Checks in the checks step (gist, when shape, shown without age, explicit under 18, a moment outside its period, a memory older than a preset listing it); the build files table lists memory media (0.13: a click on a row opens the media in a pop-up with a button to its card; a hover preview can be turned on instead; filters on format and medium, sort by size); the checks step carries the validator's memory rules and the coherence findings of § 6.1–6.2 (gist over 1,000 characters, no gist in the primary language, video without poster, text without language, `after` against the ages, `media_from` cycle, a borrower of explicit media that is not explicit, an explicit node with nobody shown or with disagreeing ages, real person without `factual`, different implied birth years, personal nodes present); the memories step filters its cards by the nodes' own `tags` (chips, no second tag system); two build purges, neither specific to memories: **"All audiences"** — the intimate and nude variants leave with the files only they used and the media of explicit memories go, gists kept, the same slice as `cof extract --all-audiences` — and "Drop personal memories" (ticked by default: both boxes remove something; unticking it keeps them, as `--keep-personal` does). A file with memories is written as `cof: "1.1"`; a 1.0 file stays 1.0. The checks step lists the memory findings (an information line counts the nodes that arrived without one of the four axes, until one is set on their card). Later (0.14): the timeline as the editor (a click adds a moment, a drag adds a period), an import pop-up when the three policy axes were absent.

### 6.6 ComfyUI
A **COF Memories** node (ComfyUI-COF 0.6.0): the preset's memories in timeline order as one text for a language model (gist in the preset's language, when-marker, `nature` / `disclosure` / `fidelity`, the short text media), their images as a batch, labels, count; `include personal` off by default; the media of an explicit node only when the loader allows adult content; a 1.0 file gives an empty text. The preview workflow gains a Memories row.

## 7. Impact on existing files and compatibility

- **1.0 files**: unchanged, nothing to migrate. The category is optional and additive.
- **1.0 readers**: ignore the category (`cof-cli` 1.0.1 and builder 0.11.8 preserve it and read it as a library; earlier 1.0.0 tools refused it — see CHANGELOG 1.0.1). Explicit memories are visible to 1.0 purges through `nudity: true` and `tags.content` (§ 5.3).
- **Schemas**: `schemas/1.1/` adds `memories` to the category pattern, the kinds `moment` / `period`, the variant field `memory`, the asset role `memory-media`, the asset flag `as_remembered`, and `identities.<id>.language`; `memory.schema.json` is the node file's schema. `$id`s under `https://yannsouetre.github.io/cof/schemas/1.1/`.
- **A file declares the lowest minor that defines everything it uses**: a file with memories declares `cof: "1.1"`.
- **Example**: `spec/examples/10-clara-mercier` becomes the first 1.1 file: 16 nodes and 31 media. The canon line — four moments (the grandmother's house: the house, the child's bedroom with her drawing, the grandmother, never the child; the first morning in her own studio; the meeting with the Martian of example 11; the electric-sheep dream, with a clip, `as_remembered`) and one period (the agency years, no media) — then, per preset, what the 65-year-old adds (wedding, graduation, family photo, the beach), the alternate line of the future-war preset (the AI war period with a briefing and a chase, `part-of` it) and the manga restyle of the four canon moments. The default preset lists the canon five; `fr-12` only the childhood. One to three media per memory; the sheet is `tools/seed/sheets/clara.memories.json`. Example 11 (the duo) becomes a 1.1 cast file with RFC 0003; the seven other examples stay 1.0.
- Negative corpus: `tests/invalid/cases.json` holds the memory cases of the § 5 safety rules (explicit flags, ages, real persons, 1.0 declaration); the structural errors of § 6.1 and the RFC 0003 rules are covered by `cli/tests/test_roundtrip.py`.

## 8. Alternatives considered

- *One node per language* (the 1.0 convention for text): doubles the graph and every link at each language, and leaves the psyche no single node to point to. Rejected for short texts (§ 3).
- *A graph database in the file* (adjacency, indexes): the index is the reader's business; the file carries nodes, five link types and axes. Rejected.
- *Sharing memories between characters*: a memory is subjective; sharing the media is enough (§ 4.5). Rejected.
- *A `truth` field*: for a fictional character everything is fictional; "did not really happen" is `nature: imagined`; references to real works are a media/rights matter; what remains is `factual`, for real persons only. Rejected.
- *A `breadth` / surface field, a `present` field, weather, typology, ambiance fields*: derivable (from media, from `nature`) or prose (the gist, `tags`). Not added; `breadth` is reserved as an open question, not as a field.
- *An `x-memories` category*: `x-` is for private extensions; renaming later would be a migration. Rejected; the 1.0.1 validator fix makes the official name safe.
- *Memory weights* (embeddings or LoRA compressing memories): phase 3 at the earliest; sources stay the reference.

## 9. Open questions (for the comment period)

- **Surface (`breadth`)**: a memory spans from a detail to a panorama; useful at inference, derivable from media. A candidate scale exists (an eight-degree gradient from a face to the cosmos). Added by a later minor when a reader needs it.
- **Intensity of feelings** vs `salience`; the psyche RFC will need an importance for values and opinions.
- **Places as nodes** (room ⊂ house ⊂ town), in a "world" category on the same mechanism; `where.environment` would then accept such a node.
- **Media in `revisions`** (a chain of transformed media), if file size stops mattering: an optional field on a revision, later.
- **Carrying another real person's consent** at extraction, instead of dropping the media.
- **Per-media fidelity**, if authors ask for it.
- **Audio memories**: nothing special in the schema (an asset is an asset); examples will follow the image prototype.

## 10. Implementation notes (this branch)

- `cof_cli/memories.py` holds what every reader shares: node loading, the timeline order of § 4.3 (age, else date and the birth year the file implies, else links — `after` / `part-of`, then the other types as hints —, undated last), the gist language rule of § 3, effective media through `media_from`, the real-person guard of § 4.5. The explorer and the ComfyUI node port the same three functions.
- `tags.auto` age buckets ignore the ages carried by memories (a memory legitimately shows another age; the builder, which computes the same buckets, does not read the category); the minor-preset rule of § 5.2 does not.
- Media types: image, audio, short video (with a poster image `derived_from` it, `method: thumbnail`; the 1.0 video cap), short text (`text/markdown` or `text/plain`, with `language`). The validator warns on a video without poster and a text without language.
- The seed pipeline (`tools/seed/memories.py`) generates images with Gemini from a sheet (one to three per memory, kept images reused without a call, edits from a base image with references), takes other media from files (`media_files`), packs and validates; a failed image is listed in the review sheet and skipped. Edits that replace a character on a photograph need the Pro model (see the `gemini-media-generation` skill).
