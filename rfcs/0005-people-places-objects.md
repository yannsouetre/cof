# RFC 0005 — people, places and objects: three axes shared by memories and the psyche

- Status: **proposed** (3 November 2026; implemented with COF 1.2 on a private branch, with RFC 0004)
- Author: Yann Souetre (with Claude)
- Date: 2026-11-03
- Target: COF **1.2** — additive only; every 1.0 and 1.1 file stays valid and every earlier reader keeps working (§ 6)
- Reference implementation (same branch): `cof-cli` 1.2.0 (schemas, validator, `cof memory add --what`, `cof psyche add --who / --where / --what`, exports), explorer 1.2 (an Objects row of tags in both graphs), builder 0.14.0, ComfyUI-COF 0.7.0, example 10 (Clara's three objects)

## 1. Motivation

RFC 0002 gave a memory two axes besides time: **who** was there and **where** it happened. RFC 0004 hangs a psyche node on memories, on other nodes and, in its draft, on identities. Reviewing the psyche in the explorer (3 November 2026), Yann raised two gaps:

- **A node is not only tied to memories.** A stance toward a grandmother, a fear tied to a place, a habit carried by a notebook: going through a memory to reach the person, the place or the thing is reductive. Sometimes there is no memory to go through at all (a fear of the sea, held since forever).
- **Objects are missing as an axis.** Affect clings to things: a cuddly toy, a favourite guitar, a pendant, a photo of one's parents. They appear in memories (the notebook in which Clara drew plans of huts at eight) and in the psyche (the habit of keeping a notebook within reach). Today an object can only be a tag (a slug that says nothing about the thing) or, for a memory, a link to an element.

The file already knows some of these people, places and things as data: cast identities (RFC 0003), `environment` variants (the places memories point to, `where.environment`) and `accessory` variants (Clara manga's folk guitar, `appearance/x1`; her drone and her armoured bike). The rest are names: « ma grand-mère », « Lyon », « le carnet ».

## 2. Proposal (normative)

### 2.1 Three entry shapes, defined once

| Axis | Entry | Reference | Free name |
|---|---|---|---|
| person | `{ identity?, label?, real? }` | `identity`: `"self"` or a cast identity id | `label` (language map) |
| place | `{ environment?, label?, geo? }` | `environment`: a qualified reference to an `environment` variant of the same character (`appearance/e1`, `volume3d/env1`) | `label`; `geo` `{ lat, lon }` for a real place |
| object | `{ item?, label? }` | `item`: a qualified reference to a variant of the same character that shows the object — in practice an `appearance` variant of kind `accessory` (`appearance/x1`) | `label` |

Each entry carries **at least one** of its reference or its `label`; a `label` beside a reference is a display label for this entry (as RFC 0002 § 4.2 says of `who`). The person and place shapes are those of RFC 0002, unchanged; the object shape is new and follows them.

### 2.2 Memories gain `what`

`what` — a list of object entries, each with an optional `shown` (the object appears in a media of the node; absent = only in the story), next to `who` and `where`. It is the object axis a reader indexes on. `tags` keep their role (free slugs for filtering); an object that matters to the character goes into `what`.

A memory `link` to an element (RFC 0002 § 3.2 allows `about` → `appearance/x1`) stays valid; readers SHOULD show a link to an `accessory` variant as an object of the memory, and builders write `what`.

### 2.3 Psyche nodes gain `who`, `where`, `what`

Three optional lists on `psyche-node.json`: the people, places and objects the node is **tied to** — whom it concerns, where it lives, what carries it. They are lists for the three axes (a node can be tied to several places; a memory happens in one, so a memory's `where` stays a single object). No `shown`, no `age`: a node is not an event and has no media.

Amendments to RFC 0004 (still « proposed », never published, so nothing released changes):

- `links[]` of a psyche node target **memories and psyche nodes only**. The draft's `identities/<id>` targets move to `who` (`{ "identity": "martien" }`): one place for people.
- A **stance** keeps its `about` field: it is the stance's subject, which may be a person, a node, the user or a free label (an idea, a group, a thing). Readers count `about.identity` and `about.user` among the node's people. A free `about.label` is shown as a person when the same name is a person entry elsewhere in the character (« le Martien » of Clara's meeting memory), otherwise as the stance's subject only — « les agences de design » is not a person.
- Constellations and selection (RFC 0004 § 3 quinquies) read the three axes: « what she thinks of X » matches X against the node's people, places and objects as well as its memories.

### 2.4 Which entries name the same thing

Two entries name the same person, place or object when they carry the same reference (`identity`, `environment`, `item`), or, for entries with a label only, the same label in one language once trimmed and case-folded. A reader MAY merge further (the part of a label before a comma, « Théo, mon mari » with « Théo »; a label equal to a cast identity's name) and says so in its interface. The format stores no registry of people, places or objects: a recurring person who needs a description, a picture or a voice is a cast identity (RFC 0003); a recurring place or object with a picture is an element. Whether a lighter registry is needed (aliases such as « Mamie » / « ma grand-mère » across thousands of memories) is left to the demonstration characters (§ 5).

### 2.5 Checks (`cof validate` 1.2)

Errors: an entry with neither its reference nor a `label`; an unresolved `identity`, `environment` or `item` (a file without an `identities` table knows only `"self"`); in a cast file, an `environment` or `item` of another character; a psyche `link` to `identities/…` (moved to `who`, § 2.3); a file that uses `what` on a memory or any of the three on a psyche node and declares `cof: "1.1"` or lower.
Warnings: an `item` whose variant is not of kind `accessory`; an `environment` whose variant is not of kind `environment` (both are legitimate stretches — a photo element, a vehicle used as a place — hence warnings); `real: true` on a person entry without an `identity` (as RFC 0002).

### 2.6 Extraction and exports

- `cof extract --preset`: the element an `item` (or a psyche node's `environment`) names travels with the memory or node that names it, whether or not the preset lists it — the rule RFC 0002 already applies to `where.environment` and to links towards elements. People entries follow what `cof extract` already does for a memory's `who[].identity` (renamed with the identity, RFC 0003).
- `cof export --format agent`: in `MEMORY.md` a memory's context line gains `objects: …` after `where: …` and `with: …` (an `item` without a label shows its element's label). `SOUL.md` « Who she is » is unchanged: the node's gist says what matters.
- Readers that inject part of a file (RFC 0004 § 3 quinquies) MAY select by person, place or object.

### 2.7 Readers and builders

- **Explorer**: an **Objects** row of tags (🧸) after People and Places, in the memories graph and in the psyche graph; in the psyche graph the people, places and objects a node names itself are direct tags, those reached only through its memories stay lighter, « via memories »; in the network view of the memories graph, objects with an element are drawn like places with an element; the cards list people, places and objects.
- **Builder**: an « Objects » field on the memory card (pick an accessory of the character or type a name) and « People », « Places », « Objects » on the psyche card, with the pickers of the memory card.

## 3. Worked example — Clara's objects (example 10)

| Object | Entry | Memories | Psyche nodes |
|---|---|---|---|
| the recycled-paper notebook | `{ "label": { "fr": "le carnet de papier recyclé", "en": "the recycled-paper notebook" } }` | `ev1` (her grandmother's house at eight) and its manga copy `ev11` | `hab1` « The notebook » — the habit comes from childhood |
| the folk guitar with the peace motif | `{ "item": "appearance/x1" }` | `ev2` (the first morning in her own studio: the guitar against the agency's box) and `ev12` | `contra1` « Slowness, at night » — a few chords before working through the night |
| her grandmother's pendant | `{ "label": { "fr": "le pendentif de ma grand-mère", "en": "my grandmother's pendant" } }` | `ev5` (the wedding: her grandmother puts it around her neck) | — |

The two names show that an object needs no picture; the guitar shows the element form. Clara's stance toward the Martian keeps `about: { "label": … }` and appears under People because her meeting memory names him.

## 4. Alternatives considered

- **Links instead of fields** (`links: [{ "type": "about", "to": "appearance/x1" }]`): links need a target in the file, so free names (the grandmother, Lyon, the notebook) cannot be linked; and a typed link says more than « tied to », which is all the author usually knows.
- **A registry** (`people`, `places`, `objects` tables at the root, entries referenced by id): consistent naming across thousands of memories, aliases, one place to describe each. Heavier, and it duplicates cast identities and elements, which already are the registries for people, places and things that carry data. Deferred to evidence (§ 5).
- **Tags with prefixes** (`person:grandmother`, `object:guitar`): no languages, no reference to an element, and a reader cannot tell a convention from a tag.

## 5. Open questions

- A registry with aliases, if the demonstration characters (Clara with 5,000 memories) show labels drifting.
- Objects in a preset: a preset that lists an accessory in its slots and a memory naming the same item — should the explorer show the bond? (No format change needed.)
- A `since` / `until` on objects (the guitar lost at forty) — later, by RFC, if a need appears.

## 6. Compatibility

Additive. Every reader ignores unknown keys (SPEC § 1.2): a 1.1 reader sees memories without objects, a 1.0 or 1.1 reader ignores the psyche category altogether (RFC 0004 § 8). A file that uses these fields declares `cof: "1.2"`. No existing file changes meaning: `who` and `where` of memories are untouched, and the `identities/…` psyche links removed in § 2.3 were never published.
