# RFC 0004 — `psyche`: the character's inner life, as a graph of nodes

- Status: **early draft, design only** (private; announced in RFC 0002 § 2; targeted at COF **1.2**, shortly after 1.1 — no implementation yet)
- Author: Yann Souetre (with Claude)
- Date: 2026-10-25 (draft)
- Target: COF 1.2 — additive only; every 1.0 and 1.1 file stays valid and every earlier reader keeps working (§ 8)
- Companion note (French, private): "COF — Psyché : conception"

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

**Category `psyche`**, variants = nodes, node file `psyche.json` per variant, same conventions as memories: `label`, `identity`, a multilingual gist (the node in one sentence), `links[]` typed to `<category>/<id>`, the three axes `origin / visibility / disclosure` (identical), `tags`, `revisions[]` on `lived` nodes. No `when` (no timeline); instead two measures and one anchor:

| Field | Meaning |
|---|---|
| `strength` 0–100 | how much it weighs in decisions — the counterpart of `salience` |
| `stability` `core | settled | shifting | fragile` | the counterpart of `fidelity`: a `core` node does not move at use time; `fragile` is what one conversation can turn (normative table for engines, like fidelity's) |
| `since` (optional; age or date) | when it appeared, placing the node *relative to the memories* without making it an event |

**Kinds** (closed list, extension by RFC), chosen to cover the narrative and psychological models without aping them:

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

**Links** (same rules as RFC 0002; five types reused, two added): `because` (this node follows from… — a memory, a relation, another node: **the link that gives depth**), `about` (bears on…), `supports` / `conflicts` (between psyche nodes; a `contradiction` points two `conflicts`). `same-event`, `after`, `part-of` are meaningless here: no hierarchy — **constellations** are computed from links and tags, not folders.

**Size**: 15 to 60 nodes for a rich character; a node is 100–300 characters per language. Injection budget: an agent selects by tags and links; the agent export writes the whole `SOUL.md` in a fixed order (wound → values → beliefs → want / need → fears → stances → tastes → habits → contradictions), which is also a good reading order for a person.

## 4. What it enables (the leverage)

- **Explorer**: a **Constellation** view (force graph: nodes by kind, `because` edges to the memories — the past visibly pulling on the present); click → card; the same component as the memories graph; a list view too.
- **Builder**: a "Psyche" step with the grammar of the Memories step (cards, chips, 🔍), a link picker to memories and characters; "Decompose the sheet into nodes" (model-assisted, optional, reviewed) and "Write SOUL.md" (deterministic).
- **cof-cli**: `export --agent` recomposes `SOUL.md`; `coherence` compares psyche ↔ memories ↔ sheet (a `wound` without `because` → info; a `want` and a `fear` that contradict each other without a `contradiction` → finding; a `false_but_held` belief never contradicted by a memory → nothing, that is life).
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
4. The ten kinds above; the "lie" as a `belief` with a flag.
5. A separate RFC, published after the 1.1 launch, announced now (RFC 0002 § 2); implementation in the week that follows.

## 7. Open points for the full draft

- Exact vocabulary for `stance` targets (identity, memory, free text) and whether `about` may target an `appearance` element (a place she loves).
- Whether `strength` and `stability` deserve normative tables or recommendations only.
- The decomposition prompt (sheet → nodes) as a documented, model-agnostic recipe, not code.
- Clara's psyche as the proof of value, before any tool is written — a first cut is in § 7 bis; it still has to be read against her personality sheets and the dialogue examples.

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
| `stance1` | stance | Toward the Martian: protective curiosity — the one visitor who looked at the sheep before the screens. | 55 | shifting | 29 | about → `identities/martien` (the cast file, example 11), because → `memories/ev3` | martian |
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
