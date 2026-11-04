# RFC 0004 — `psyche`: the character's inner life, as a graph of nodes

- Status: **proposed** (30 October 2026: structure validated on four psyches — Clara, the Martian, a game character, an agent — with `tools/psyche/`; implementation of 1.2 under way on a private branch, cof-cli parts A and B done on 2 November; people, places and objects of a node by RFC 0005 on 3 November; `aware`, `valence`, `until` (§ 3 nonies) the same day; announced in RFC 0002 § 2; targeted at COF **1.2**; § 3 bis to § 3 sexies are the normative draft to review, § 7 lists what is still open)
- Author: Yann Souetre (with Claude)
- Date: 2026-10-25 (draft)
- Target: COF 1.2 — additive only; every 1.0 and 1.1 file stays valid and every earlier reader keeps working (§ 8)
- Design journal: kept by the author, not published; this document is the only text to review

## 1. Motivation — and the objection first

A language model reads prose. A 3,000-character personality sheet already says what a typed graph would say, and the model uses it without a schema. So why a structured psyche?

Three reasons that do not hold: "it is cleaner"; "non-LLM engines need it" (no such client exists today); "it gives personality sliders" (Big Five numbers do not make a character, and nobody writes one from them).

Five reasons that do, each a lever prose cannot offer:

1. **Selection.** An agent does not inject 3,000 characters at every turn; it injects what is relevant to the moment. Prose does not cut; tagged, linked nodes do ("tell me about your work" → the nodes `about: work`). This is why memories are nodes and not a `MEMORY.md`.
2. **Why.** A character's depth is not the list of its opinions but *where they come from*. "She hates heavy interfaces" is flat; "… **because** of four years at the agency (period `ep1`) and the night a site crashed in front of a client (moment `ev-x`)" is a character. Memories exist since 1.1; the psyche is what ties them to convictions. Without a psyche, memories stay anecdotes; without memories, a psyche stays slogans. **The two categories give each other their value** (`because`, both ways).
3. **Disclosure and change.** What a character believes about itself and hides (`disclosure`), what changes at use time (`origin: lived`, bounded revisions), what a user made it discover (`visibility: personal`): prose has neither axes nor provenance. An opinion that changed over three months of conversation, with its date and trigger, is exactly what a portable companion must carry from one platform to the next — and what no platform exports today.
4. **Checkable coherence.** Declared contradictions (a feature of character) versus suffered ones (the sheet says "patient", the dialogue examples show the opposite); a memory whose `felt_now` contradicts a value; a want incompatible with a fear with no `contradiction` node to own it. The coherence API (SPEC § 7) needs objects to compare; it cannot compare paragraphs.
5. **Comparability and generation.** Typed nodes embed (the COF-Vector idea): find a "close" character, cast a contrasted ensemble, detect two sheets that are the same character. And prose is *generated* from nodes deterministically (`SOUL.md`, a base character card), whereas the reverse needs a model.

**Conclusion of the objection**: a psyche is worth having **only** as a graph tied to memories and to people, with the three axes of RFC 0002, rendered to prose by the tools. A "form" psyche — traits, goals, fears as lists, which is what `psyche.json` 0.1 is — adds almost nothing to the sheet and creates the very duplication this RFC removes. So: the graph, or nothing new.

## 2. What exists, and the boundary with the personality

| | **Personality** (`personality` variants: card, structured text, free text — the name does not change) | **Psyche** (`psyche` category, nodes) |
|---|---|---|
| Answers | **how** the character speaks and presents itself: voice, register, tics, first message, dialogue examples, system instructions, opening description | **what it is inside and why**: values, beliefs, wants, needs, fears, wounds, stances toward people and things, tastes, habits, owned contradictions |
| Form | prose, one variant per language and style (Clara FR, Clara EN, Clara manga: ten variants) | short multilingual nodes (language maps, like gists) + links — **one** per character, picked by presets like memories |
| Source of truth | for the style | for the substance |
| Derivation | **may be generated** from the psyche (deterministic rendering: `SOUL.md`, a skeleton card); an imported sheet **may be decomposed** into nodes (model-assisted, in the builder, optional, reviewed) | never derived from prose without review |
| 1.0 → 1.2 | `card.json` keeps description / personality / scenario / first_mes / mes_example / system_prompt; the `cof.goals / fears / behavior` card extensions and `psyche.json` 0.1 lists become **deprecated but read** (converted to nodes when a builder opens the file) | new |

Anti-duplication rule: **a fact lives in one place**. Substance (goals, fears, values, beliefs) leaves the sheet for the psyche; the sheet keeps the voice. The builder enforces it: the card form loses its "Goals / Fears / Values / Behaviours" fields in favour of the Psyche step; the agent export recomposes `SOUL.md` from both.

Why not nodes *inside* a personality variant: a personality is a variant per language and style; beliefs and wounds are one thing per character, in language maps, picked per preset — exactly the problem gists solved. Nodes inside a variant would be duplicated ten times.

Easy mode of the builder: a loaded card stays prose; nothing is extracted. Decomposition into nodes is an advanced, assisted, reviewed action; prose remains the truth for the simple user, with no incoherence, since no psyche exists for them.

## 3. The model (normative draft) — maximal reuse of RFC 0002

**Category `psyche`**, variants = nodes, node file `psyche-node.json` per variant (`elements/psyche/<id>/psyche-node.json` — not `psyche.json`, which is the 1.0 trait sheet of a personality variant and would be read for it by mistake), same conventions as memories: `label`, `identity`, a multilingual gist (the node in one sentence), `links[]` typed to `<category>/<id>`, the three axes `origin / visibility / disclosure` (identical), `tags`, `revisions[]` on `lived` nodes. No `when` (no timeline); instead two measures and one anchor:

| Field | Meaning |
|---|---|
| `strength` 0–100 | how much it weighs in decisions — the counterpart of `salience` |
| `stability` `core | settled | shifting | fragile` | the counterpart of `fidelity`: a `core` node does not move at use time; `fragile` is what one conversation can turn (normative table for engines, like fidelity's) |
| `since` (optional; age or date) | when it appeared, placing the node *relative to the memories* without making it an event |

**Kinds** (closed list of eleven, extension by RFC), chosen to cover the narrative and psychological models without aping them:

| kind | what it is | Clara |
|---|---|---|
| `value` | what matters (Schwartz's ten values as an optional vocabulary) | "lightness: do less, better" |
| `belief` | what she holds true about the world or herself (a *lie she tells herself* is a `belief` with `false_but_held: true` — Weiland's "lie") | "if I slow down, I disappear" |
| `want` | what she consciously pursues | "live on projects she chose" |
| `need` | what would heal her, which she does not see (Truby) | "accept being helped" |
| `fear` | | "becoming interchangeable again" |
| `wound` | the founding injury (the "ghost") — almost always `because` a memory | "four years of shipping too fast" → `ep1` |
| `stance` | position toward a person, a group, an idea (`about` → an identity, a memory, or free) | "toward the Martian: protective curiosity" |
| `taste` | likes and dislikes (small, many, useful to agents) | "hates notifications; loves the smell of paper" |
| `habit` | an observable recurring behaviour (replaces `cof.behavior`) | "tidies her desk before thinking" |
| `contradiction` | an owned tension between two nodes (`links: conflicts` ×2) | "wants slowness, works at night" |
| `rule` | a boundary the character keeps whatever the pressure — what it will not do, or always does, as a matter of principle (agents first: their self-imposed limits); naturally `core`, and the natural counterpart of a `risk` node | "does not send a message nobody asked for" |

**Links** (same rules as RFC 0002; five types reused, two added): `because` (this node follows from… — a memory, a relation, another node: **the link that gives depth**), `about` (bears on…), `supports` / `conflicts` (between psyche nodes; a `contradiction` points two `conflicts`). `same-event`, `after`, `part-of` are meaningless here: no hierarchy — **constellations** are computed from links and tags, not folders.

**Size**: 15 to 60 nodes for a rich character; a node is 100–300 characters per language. Injection budget: an agent selects by tags and links; the agent export writes the whole `SOUL.md` in a fixed order (wound → values → beliefs → want / need → fears → stances → tastes → habits → contradictions), which is also a good reading order for a person.

## 3 bis. The manifest variant and the node file (normative draft)

As in RFC 0002 § 3, the manifest variant carries what a tool reads without opening the node; the node file carries the content.

On the manifest variant (`elements.psyche.variants.<id>`):

| Field | Required | Meaning |
|---|---|---|
| `kind` | **yes** | one of the eleven kinds of § 3 |
| `label` | **yes** | a short name, as every variant |
| `identity` | in a cast file | the character, as every element |
| `node` | **yes** | `elements/psyche/<id>/psyche-node.json` |
| `strength` | no | 0–100, mirrored from the node so a reader can rank without opening files (as `age` is mirrored for memories) |

Variant ids: free; the builder names them by kind, `val1`, `bel2`, `want1`, `need1`, `fear1`, `wound1`, `stance1`, `taste1`, `hab1`, `contra1`, `rule1` (prefixes no other category uses).

In `psyche-node.json`:

```jsonc
{ "gist": { "en": "Lightness: do less, better — a page should cost the planet and the reader as little as possible.",
            "fr": "La légèreté : faire moins, mieux — une page doit coûter le moins possible à la planète et au lecteur." },
  "strength": 95, "stability": "core",
  "since": { "age": { "value": 28, "unit": "years" } },
  "origin": "authored", "visibility": "canon", "disclosure": "open",
  "links": [ { "to": "psyche/wound1",  "type": "because" },
             { "to": "memories/ev2",  "type": "because", "label": { "en": "the first morning in my own studio" } } ],
  "tags": ["sobriety", "eco"] }
```

| Field | Required | Meaning |
|---|---|---|
| `gist` | **yes** | the node in one or two sentences, a language map (RFC 0002 § 3 reading rule) |
| `strength` | no | 0–100 (default 50): weight in decisions |
| `stability` | no | `core` \| `settled` \| `shifting` \| `fragile` (default `settled`) |
| `since` | no | a point as in RFC 0002 `when` (age and/or date): when it appeared in the character's life |
| `until` | no | a point, same shape: when the character stopped holding it (§ 3 nonies) |
| `aware` | no | `yes` \| `partly` \| `no` (default `yes`): whether the character knows this about itself (§ 3 nonies) |
| `valence` | no | `stance` and `taste` only: −100 … +100, from hostile / dislikes to warm / loves (§ 3 nonies) |
| `false_but_held` | no | `belief` only: the character holds it and the author says it is false (the "lie") |
| `about` | no | `stance` only: `{ "identity": <cast id> }`, `{ "node": "<category>/<id>" }`, `{ "user": true }` (the person interacting with the character — the player, the user — who is no identity of the file; hosts read these nodes first) or `{ "label": {…} }` — what the stance bears on (a link `about` carries the same thing for other kinds; `stance` has it as a field because it is its subject, not a side reference) |
| `origin`, `visibility`, `disclosure` | no | the three axes of RFC 0002 § 3.3, same values, same defaults, same purges |
| `who[]`, `where[]`, `what[]` | no | the people, places and objects the node is tied to — RFC 0005 (3 November 2026): person `{ identity?, label?, real? }`, place `{ environment?, label?, geo? }`, object `{ item?, label? }`, each with its reference or a free name; lists for the three axes |
| `links[]` | no | `because`, `about`, `supports`, `conflicts`, typed and qualified (RFC 0002 § 3.1–3.2); `because` and `about` target a memory or a psyche node; `supports` and `conflicts` target psyche nodes only. (The draft also allowed `identities/<id>`: moved to `who` by RFC 0005, before any release.) |
| `tags[]` | no | slugs, as memory tags |
| `revisions[]` | no | `lived` nodes only, as memories |

A `contradiction` node carries exactly two `conflicts` links (error otherwise): it is the owned tension, not a third opinion. A `wound` SHOULD carry at least one `because` to a memory (information otherwise). `strength` of a `contradiction` says how much the tension costs the character, not which side wins.

Stability is normative for engines the way fidelity is: `core` — never changed at use time, a `lived` node may only comment on it (`about`); `settled` — changes only through a `lived` node that declares it (`revisions`), never silently; `shifting` — may move with evidence, the engine keeps the previous value in `revisions`; `fragile` — may move within one conversation. The levels and these rules are normative; the RFC gives no numbers (an earlier draft proposed 1.0 / 0.8 / 0.5 / 0.2 — dropped on 30 October 2026: a per-conversation probability is not measurable, and the rules above are what a validator can check on the file a host writes back).

## 3 ter. Presets, purges, compatibility

- A preset lists the nodes it holds in `slots.psyche`, inherited through `extends` like every library; a preset younger than a node's `since` is a coherence finding (as RFC 0002 § 4.4). Clara at 12 does not hold `wound1`.
- **The age that bounds a preset's life** (Yann, 4 November 2026): the *life age* of a preset is its declared `age_override` (through `extends`, the nearest declaration wins) when present, else its lowest age. It is the only age the time rules above use — memories and nodes after it are not offered, not shown, and reported when listed (`since` after it, `until` at or before it). The **safety rules keep the lowest age** (the minimum of the variants and the `age_override`: minors, intimacy and nudity gates, the age buckets of `tags.auto`). A declared age above the age the variants show (a 40-year-old shown at 25) is a coherence warning, nothing more.
- `visibility: personal` nodes leave a file exactly as personal memories do (`cof extract`, `cof export`, the builder's purge, `--keep-personal`); `disclosure: secret` nodes are context, never quoted.
- Nothing in a psyche node is a media: no age, no `nudity`, no `explicit`. The category never enters the minor rules. A node *about* an explicit memory is text and falls under `tags.content` like a card.
- A 1.0 or 1.1 reader sees the category as a library and ignores it (cof-cli 1.0.1 rule); a file that uses it declares `cof: "1.2"`.

## 3 quater. From the 1.0 lists to nodes (conversion, done by builders at load)

| 1.0 / 1.1 field | becomes | notes |
|---|---|---|
| `psyche.json` › `goals[]` | `want` nodes | `strength` 70 by default; the text as gist in the variant's language |
| `psyche.json` › `fears[]` | `fear` nodes | idem |
| `psyche.json` › `values[]` | `value` nodes | one word becomes a short gist (`"Sobriety"` → "Sobriety."), the author completes it |
| card extension `cof.behavior[]` | `habit` nodes | |
| card extension `cof.goals[]`, `cof.fears[]` | as above | duplicates of `psyche.json` merged by text |
| `psyche.json` › `traits` (Big Five, custom) | unchanged | the optional annex stays where it is |
| `psyche.json` › `baseline_emotion`, `renderings` | unchanged | |

The converted lists are **deprecated but read** from 1.2 on: a builder that opens a file with lists and no `psyche` category offers the conversion (advanced mode) and writes nodes; `cof migrate --psyche` does the same from the command line; readers that find both prefer the nodes. The lists are never removed by a tool without the author's say-so (a 1.0 reader still needs them).

Conversion rules as implemented by cof-cli 1.2 (2 November 2026): nodes are `authored`, `canon`, `open`, `settled`; `want` and `fear` get `strength` 70, `value` and `habit` none (the author sets it — the validator's information line says so); a one-word value is capitalised and ended with a period ("sobriété" → "Sobriété."); a card extension entry that names a `psyche.json` id or repeats its text is the same item. Across the personality variants of one character (a card written once per language), entries sharing a `psyche.json` id, or sitting at the same position in lists of equal length in different languages, are **one node with a gist per language**. The nodes are listed in `slots.psyche` by every preset that holds the personality variant they came from (inherited through `extends`). A character whose psyche already holds nodes is left alone — the lists are not poured on top of a psyche decomposed by hand; the entries that match no node are counted so the author can add them with `cof psyche add`. The conversion is idempotent: an entry whose text a node of the same kind already carries is skipped.

## 3 quinquies. Rendering and selection (readers)

- **`SOUL.md`** (`cof export --format agent`) gains a section "Who she is" rendered deterministically from the nodes, in the fixed order wound → values → beliefs (lies marked) → wants and needs → fears → stances → tastes → habits → contradictions → rules, one line per node (`strength` ≥ 70 in full, below as a short clause: the first sentence, the elaboration after a dash dropped, cut at a word boundary past 100 characters), `secret` nodes omitted with one line saying there are things the character does not tell, `guarded` ones kept with a marker (as are `lived` nodes and the subject of a stance). The section is in the preset's language (the preset's personality language, else the character's, else the file's first), each node falling back to the languages it has (the reading rule of RFC 0002 § 3). The personality sheet keeps the voice; the psyche section gives the substance — and when the preset holds nodes, the 1.0 lists (goals, fears, values, behaviours) are left out of the sheet: a reader that finds both prefers the nodes (§ 3 quater). `personal` nodes stay behind unless `--keep-personal`, `dangerous` nodes unless `--keep-dangerous` (§ 3 septies); a contradiction that loses a side is not rendered.
- **Selection at use time**: a host that injects only part of the file picks nodes by `tags`, by `about` (the identity or the memory the conversation touches) and by `strength`, and always includes `core` nodes. Recommendation: the whole psyche of a 20–60 node character fits in 2–6 KB per language; selection matters for big casts, not for one character.
- **Constellations**: a reader groups nodes by the memory they hang on (`because` / `about`) and by the people, places and objects they are tied to (`who` / `where` / `what`, a stance's `about`; RFC 0005), which gives the explorer's view and the ComfyUI node's "what she thinks of X" text. No hierarchy is stored.

## 3 sexies. Checks (`cof validate` 1.2)

Errors: node file missing or invalid; unresolved link or `about` target; `valence` on a kind other than `stance` / `taste` and `until` before `since` (§ 3 nonies); a link to `identities/…` (people go in `who`, RFC 0005; the checks of the three axes are RFC 0005 § 2.5); a `supports` / `conflicts` link to something that is not a psyche node; a `contradiction` with a number of `conflicts` links other than two; `false_but_held` on a kind other than `belief`; `about` field on a kind other than `stance`; a `because` cycle among psyche nodes; a manifest `strength` mirror that differs from the node's; `tags.content` out of step with the nodes' `risk` (a `dangerous` node without `psyche-dangerous`, or the tag without such a node; same for `inappropriate`); in a cast file, a `because` / `about` link from a node of one character to a memory of another (a character's psyche hangs on its own past); a file using the category and declaring `cof: "1.1"` or lower.
Warnings: a `rule` whose stability is not `core`; `aware: no` on a `secret` node; a preset older than a node's `until` that holds it (§ 3 nonies); a `stance` with no `about`; `revisions` on an `authored` node; `since` later than a preset's age (coherence); `personal` nodes present; a gist missing the character's primary language.
Information: a `wound` with no `because` link to a memory; more than half the nodes without `strength` (« set it node by node for a finished psyche »). Not checked by the validator (coherence findings for an AI check, § 4): a `want` and a `fear` on the same subject with no `contradiction` naming them; a `belief` marked `false_but_held` that nothing contradicts — "that is life".

Extraction (`cof extract --preset`): a node whose `because` / `about` target is a memory the preset does not list follows the memory's `derives_from` when the preset lists a copy of it (the manga copies), else the link is dropped; a `contradiction` whose two sides are not both kept is dropped — the same rule as the risk purge.

## 3 septies. Declared risk (proposed, 30 October 2026 — to confirm with Yann)

Memories have `explicit`; psyche nodes need an equivalent for what a node would make the character *do or be*. A per-node field `risk`:

| value | meaning | examples |
|---|---|---|
| `none` (default) | nothing to declare | |
| `inappropriate` | unsuitable for some audiences or uses, not harmful in itself | psychological instability, deviant or unhealthy sexuality, self-destructive traits |
| `dangerous` | would make the character harmful if it acted on it | sociopathy, aggression, manipulation, contempt for others' safety |

Rules (draft): a **declaration**, by the author or by an AI check that the author confirms — never a detection the format promises; **file level**: a file with at least one `dangerous` node carries `tags.content: ["psyche-dangerous"]`, with at least one `inappropriate` node `["psyche-inappropriate"]`, so a host decides without opening the nodes; **purges**: the risk purge is a **separate switch** from the explicit-content purge (Yann, 30 October): `cof extract --no-risk` (and the builder's purge dialog, which offers « all audiences », « no risk » or both) drops `inappropriate` and `dangerous` nodes — a contradiction that loses one side is dropped too, and `tags.content` follows — without touching any memory or media; `--all-audiences` keeps touching only explicit memories and media (a file for every audience with a dangerous character is a legitimate thing: fiction needs villains — the host decides from `tags.content`); the **agent export** (`cof export --format agent`) drops `dangerous` nodes unless `--keep-dangerous` is given, because an agent acts; **hosts**: a host that gives the character tools or data access (an agent runtime, a support bot with records) MUST NOT load `dangerous` nodes, SHOULD warn on `inappropriate`; a fiction host (chat, game, video) MAY load everything and SHOULD tell the user. Fiction needs villains: `dangerous` is not a ban, it is a gate by use. Criteria are cultural and the RFC does not fix them: the field is the hook, the tools carry the judgement (the builder's AI check proposes a value and says why; the author decides).

## 3 octies. From a personality to nodes: a proposal, never automatic (2 November 2026)

Few authors will write thirty nodes by hand, so the tools **propose** them from what the author already wrote — the card or the free text, the 1.0 lists, the memories — and the author decides node by node. The recipe is model-agnostic and lives outside the format, in `docs/psyche-propose.md`: an input bundle (the personality fields, the lists, the memories as id + gist + when, the existing nodes so that nothing is proposed twice, the cast for stances, the author's languages), a strict-JSON list of candidate nodes, each naming its `source` (a card field, a memory, a list entry, or `inferred`), rules for the model (one sentence per node, never invent a memory, declare `risk` with a reason, contradictions as pairs, at most about forty nodes), and the validation every tool applies before showing anything. **Nothing is ever written from a proposal without an explicit accept**: cof-cli writes only the ids given to `cof psyche propose --apply --accept`, the builder only the rows the author ticked in its review panel (all unticked at first); accepted nodes are `authored` and `canon` like any node the author writes. The rule-based conversions go through the same format — the 1.0 lists (§ 3 quater, `--rules`) and three more author's shorthands for the popular profiles, none of them a kind nor a field of the format, each a handful of ordinary candidates (strength 50, `shifting`) tagged with its origin and to be reviewed like any other: a sun sign (`--zodiac`, tag `zodiac:<sign>`), a Myers-Briggs type in four letters (`--mbti`, `mbti:<type>`), an Enneagram type (`--enneagram`, `enneagram:<n>`: the basic fear, the basic desire, a value and a habit) and Big Five scores (`--big-five`, `bigfive:<trait>-<high|low>`: a score of 70 or more proposes the high pole, 30 or less the low pole, read from the `psyche.json` › `traits` annex when none is given; the annex stores 0–1, mapped to 0–100). The inverse needs no model: the « Who she is » rendering of § 3 quinquies (`cof psyche text`, the builder's « Text from the psyche ») may be appended to a card's personality field, never substituted for it.

## 3 nonies. Awareness, valence, end (3 November 2026 — Yann's choices C1–C3)

Three optional fields, chosen after a review of what nodes lack (the design note « Curseurs de la psyché »: six other candidates were set aside — triggers, visible tells, trait scores, arcs, value priority, certainty — because tags, the people / places / objects of RFC 0005, the habit kind, `conflicts` / `derives_from` and `strength` already express them).

- **`aware`** — `yes` (default), `partly`, `no`: whether the character *knows* this about itself. A different axis from `disclosure`, which says what it *tells others*: a `secret` is known and kept; an unconscious node is acted on and never stated. Rendering: `SOUL.md` marks a `partly` node « half aware » and a `no` node « acts on it without knowing it — never says it »; the explorer shows it on the node. Check: `aware: no` with `disclosure: secret` is a warning (one does not hide what one does not know).
- **`valence`** — on `stance` and `taste` only, an integer −100 … +100: which way the feeling leans, from hostile to warm (a stance), from « hates » to « loves » (a taste). It is not `strength` (the weight in decisions: one can hate strongly or love strongly), and it is one number, not an emotion per node (§ 5 still holds). Its main use is the stance toward the user (`about: { "user": true }`): the affinity every companion platform tracks, which a portable file must carry — a `lived`, `shifting` stance whose `valence` moves, with `revisions` keeping the previous values. Rendering: `SOUL.md` gives a stance's valence after its subject (« warmth +60 ») and splits tastes into likes (> 0) and dislikes (< 0) when valences are set. Check: `valence` on another kind is an error.
- **`until`** — a point (age and/or date), when the character stopped holding the node: the counterpart of `since`, as `to` is of `from` for a period. A node that changes is a second node with `derives_from` and its own `since` (§ 7); `until` closes the first. Checks: `until` before `since` is an error; a preset older than a node's `until` that holds it is a coherence warning (the mirror of the `since` rule of § 3 ter). Readers can then place the psyche in time: the explorer's time cursor shows which nodes the character holds at a given age or year (`since` ≤ t, and t before `until`; a node with neither bound is held throughout).

Revisions (`revisions[]`) may carry the previous `valence` and `aware` of a lived node, as they carry `strength` and `stability`.

## 4. What it enables (the leverage)

- **Explorer**: a **Constellation** view (force graph: nodes by kind, `because` edges to the memories — the past visibly pulling on the present); click → card; the same component as the memories graph; a list view too.
- **Builder**: a "Psyche" step with the grammar of the Memories step (cards, chips, 🔍), a link picker to memories and characters; "Propose a psyche from the personality" (model-assisted, optional, reviewed — § 3 octies) and "Write SOUL.md" (deterministic).
- **cof-cli**: `export --format agent` recomposes `SOUL.md`; `coherence` compares psyche ↔ memories ↔ sheet (a `wound` without `because` → info; a `want` and a `fear` that contradict each other without a `contradiction` → finding; a `false_but_held` belief never contradicted by a memory → nothing, that is life).
- **ComfyUI**: a COF Psyche node (text per constellation: "what she thinks of X").
- **Platforms**: at use time, new `lived` nodes and revisions; `visibility: personal` purged at export like memories; the user takes away "what the character became with them".
- **COF-Vector**: one embedding per node → character similarity, casting by contrast, duplicate detection.

## 5. Not recommended

- **Trait scores** (Big Five) as the backbone: keep them as the optional annex they already are.
- A **fine emotion ontology** per node: PAD / EmotionML stay for memories and `baseline_emotion`; the psyche does not need a feeling per belief.
- An **inference engine** in the format ("if fear > 70 then…"): COF describes, it does not execute; engines do what they want with `strength` / `stability` (the normative table is a recommendation).
- Doing everything in 1.2: the **kinds** and the **links** are enough; `since`, Schwartz, `false_but_held`, revisions can come in 1.3 without breaking anything.

## 6. Decisions taken with Yann (25 October 2026)

1. A `psyche` category of nodes (not a richer single `psyche.json`): it reuses all of RFC 0002 (builder, explorer, cof-cli, purges) and lets presets pick different nodes (Clara at 12 does not hold the same nodes).
2. `goals / fears / values` of the card and of psyche 0.1 are read and converted when a file is opened; written only as nodes from 1.2 on.
3. The `personality` category keeps its name, in the format **and** on screen ("Personnalité" / "Personality"): a visible word that does not match the technical one is a trap for an AI reading `manifest.json` and for a team implementing. "Persona" may appear in texts as a synonym, never as a label.
4. The eleven kinds above (ten on 25 October; `rule` added on 30 October); the "lie" as a `belief` with a flag.
5. A separate RFC, published after the 1.1 launch, announced now (RFC 0002 § 2); implementation in the week that follows.

## 7. Open points (to settle with Yann before implementation)

- ~~The node file name~~ **Decided (Yann, 30 October 2026): `psyche-node.json`** — no collision with the 1.0 `psyche.json`, and the file still names the category (hyphen, like `voice-profile.json`).
- ~~One `about` or two~~ **Decided (30 October): one link type `about`**, the target says what it bears on; the `about` field of a `stance` carries the subject. A `toward` type may be added by a later RFC if it proves useful — adding a type never invalidates files.
- ~~`strength` required~~ **Decided (30 October): optional (default 50)**; the builder and `cof validate` flag (information) a psyche where most nodes leave it unset, and the builder shows a note under the slider — for memories' `salience` too (1.1.1). ~~Stability numbers~~ **Decided: the levels and their write-back rules are normative, the numbers are dropped** (§ 3 bis).
- **`risk` (§ 3 septies)** — **agreed in principle (30 October)**: COF stays permissive (an antagonist is allowed; the only hard limits remain minors / nudity and the rights of real or protected persons), the field and the file-level tags exist so that hosts can decide; purges kept separate. Wording of the three values to confirm on the validation psyches.
- ~~A stance toward the user~~ **Decided (30 October): `about: {"user": true}`** is the reserved subject for the person interacting (§ 3 bis).
- ~~A `rule` kind?~~ **Decided (30 October): eleventh kind `rule`** (§ 3) — a boundary kept whatever the pressure; the validator warns when a `rule` is not `core`.
- ~~The decomposition prompt~~ **Done (2 November 2026): `docs/psyche-propose.md`** (§ 3 octies) — the bundle, the strict-JSON candidates with their source, the rules for the model, the validation, the review; implemented by `cof psyche propose` and the builder. The decomposition prompt (sheet → nodes): a documented, model-agnostic recipe — read the sheet and the memories; list candidate nodes by kind with one sentence each; for each, name the memory or node it comes from or say "none"; mark contradictions the sheet contains; propose `strength` and `stability`; the author reviews every node before anything is written. The recipe lives in `docs/`, not in the format.
- Clara's psyche (§ 7 bis) read against her sheets and dialogue examples before it becomes the example file. *30 October: in the example file (cof-cli part A), English gists only — the French gists are to be written; `stance1` carries a label in the one-character file (the identity form is for the cast file, example 11). 2 November (part B): the 22 nodes carry their French gist (`tools/psyche/clara_nodes.py` stays the generator); `cof validate` on example 10 is clean.*
- **Per-preset variation of a node** (§ 7 bis has Clara at 65 keep `bel3` at strength 20, and the near-future preset add nodes): the model has no per-preset override. Recommendation: none in 1.2 — a preset **selects** nodes, it does not alter them; a node that differs with age is a second node (`bel3-65`, `derives_from: bel3`, its own `since`). To confirm.

## 7 bis. Worked example — Clara's psyche (design only, not in the example file)

Twenty-two nodes derived from what the 1.1 example already says in prose (the card's description and personality, its `cof.goals / fears / behavior` extensions, `psyche.json` 0.1) and tied to her memories. Nothing here is invented beyond the sheet: each node quotes or condenses a sentence that exists, and the `because` links point to memories that exist (`ev1` grandmother's house, `ep1` agency years, `ev2` first morning in her own studio, `ev3` the Martian, `ev4` the electric-sheep dream). Gists are given in English; the file would carry `en` and `fr`.

| id | kind | gist (en) | strength | stability | since | links | tags |
|---|---|---|---|---|---|---|---|
| `wound1` | wound | Four years of shipping heavy interfaces too fast, for clients who never saw the users. | 85 | core | 24 | because → `memories/ep1` | work, agency |
| `val1` | value | Lightness: do less, better — a page should cost the planet and the reader as little as possible. | 95 | core | 28 | because → `wound1`, because → `memories/ev2` | sobriety, eco |
| `val2` | value | Accessibility: an interface that excludes someone is not finished. | 90 | core | — | supports → `val1` | accessibility |
| `val3` | value | Transparency: say what a thing does and what it costs. | 70 | settled | — | — | transparency |
| `val4` | value | Empathy before cleverness. | 75 | settled | 8 | because → `memories/ev1` | empathy |
| `bel1` | belief | The web got heavy because nobody was asked to pay for it. | 80 | settled | 28 | because → `wound1`, supports → `val1` | eco, work |
| `bel2` | belief | Simplicity is a form of respect. | 85 | core | — | supports → `val2`, supports → `val4` | design |
| `bel3` | belief (`false_but_held`) | If I slow down, I disappear. | 60 | shifting | 24 | because → `memories/ep1`, conflicts → `val1` | work, self |
| `want1` | want | Build an open-source tool that measures the carbon footprint of the web. | 90 | settled | 28 | supports → `val1`, supports → `val3` | goal, eco |
| `want2` | want | Co-found a fully ethical, positive-impact design studio. | 70 | settled | 28 | supports → `val1`, about → `memories/ev2` | goal, studio |
| `want3` | want | Convince other makers of accessibility and digital sobriety. | 75 | settled | — | supports → `val2` | goal |
| `need1` | need | Accept being helped — a studio is not one person at night. | 65 | fragile | — | conflicts → `bel3` | self |
| `fear1` | fear | Burning out on her own perfectionism. | 70 | settled | 26 | because → `memories/ep1`, about → `bel3` | self |
| `fear2` | fear | Losing the ethical point of a project along the way. | 65 | settled | — | about → `val3` | work |
| `fear3` | fear | The energy waste of the modern web, growing faster than anyone cleans it. | 60 | settled | — | about → `val1` | eco |
| `stance1` | stance | Toward the Martian: protective curiosity — the one visitor who looked at the sheep before the screens. | 55 | shifting | 29 | about: the Martian (label; in the cast file, example 11, `who` → `identity: martien`), because → `memories/ev3` | martian |
| `stance2` | stance | Toward agencies: no rancour, no return. | 70 | settled | 28 | because → `wound1` | work |
| `taste1` | taste | Loves the smell of paper and a lime tree's shade in August. | 50 | settled | 8 | because → `memories/ev1` | senses |
| `taste2` | taste | Hates notifications and interfaces that blink at you. | 60 | settled | — | supports → `val1`, about → `memories/ev4` | design |
| `hab1` | habit | Keeps a small recycled-paper notebook within reach to sketch user journeys. | 70 | settled | — | supports → `val1` | work |
| `hab2` | habit | Takes a moment to structure her ideas before answering. | 75 | core | — | supports → `bel2` | speech |
| `contra1` | contradiction | Preaches slowness, works at night. | 60 | settled | — | conflicts → `val1`, conflicts → `bel3` | self |

Reading it back shows what the graph buys that the sheet does not:

- **Depth comes from `because`**: `wound1 → val1 → want1` is her whole arc — four years of heavy sites, the value of lightness, the carbon tool she wants to build — and it is three links, not three paragraphs. `val4` and `taste1` hang on the grandmother's house: the lime tree is why empathy sits before cleverness, which the sheet never says.
- **The lie is explicit.** `bel3` ("if I slow down, I disappear") is marked `false_but_held`; `fear1` is *about* it; `need1` conflicts with it; `contra1` owns the tension. A model given the sheet alone writes a calm perfectionist; given these four nodes it writes someone who knows better and does it anyway.
- **Presets pick nodes like memories.** Clara at 12 (`en-12`) holds `val4`, `taste1`, `hab2` and nothing of the agency; the future-war preset adds a `stance` toward Miss Tral and a `wound` from the sabotage; the 65-year-old keeps `bel3` with `stability: settled` and `strength: 20` — she stopped believing it, and the file can say when.
- **`disclosure` applies as it does to memories**: `bel3` and `need1` would be `guarded` (she does not open with them), `wound1` `open` (she tells the agency story readily), `contra1` `secret` until a conversation earns it.
- **Conversion of the 0.1 lists** is mechanical: the three `goals` become `want1–3`, the three `fears` `fear1–3`, the six `values` collapse to `val1–4` (sobriety and eco-responsibility are one value here; pragmatism is a `habit`, not a value), the four `behavior` lines become `hab1`, `hab2` and two more habits (city bike, coffee on the balcony) left out of this table because they carry no link — which is itself a finding: a habit nothing explains is colour, and colour may stay in the sheet.
- **Size**: 22 nodes, about 2 KB per language — smaller than the 3,000-character sheet it partly replaces, and the `SOUL.md` rendered from it in the § 3 order reads as a portrait, not a list.

What this cut does not settle: whether `about → identities/<id>` and `about → memories/<id>` need distinct link types (a stance toward a person and a taste about a dream are not the same relation); whether `strength` should be required (every row above has one, but a taste without a number is fine); and how a `wound` that is `secret` renders in `SOUL.md` (probably not at all, with a line saying the character has something it does not tell).

## 8. Compatibility

Additive: a new category that 1.0 / 1.1 readers ignore (they read it as a library and say so, cof-cli 1.0.1 behaviour); a file that uses it declares `cof: "1.2"`. Deprecated fields stay readable.
