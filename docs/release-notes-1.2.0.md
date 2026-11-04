# COF 1.2.0 — release notes (8 November 2026)

**AI characters now have an inner life.**

▶ [Explore Clara's psyche](https://yannsouetre.github.io/cof/viewer/#clara/psyche:graph) · [Build one](https://yannsouetre.github.io/cof/builder/) · [RFC 0004](https://github.com/yannsouetre/cof/blob/main/rfcs/0004-psyche-graph.md) · [RFC 0005](https://github.com/yannsouetre/cof/blob/main/rfcs/0005-people-places-objects.md) · [Changelog](https://github.com/yannsouetre/cof/blob/main/CHANGELOG.md)

COF 1.1 gave a character a past. COF 1.2 gives it what that past made of it: what it values, believes, wants, needs and fears; what hurt it; what it likes and dislikes; its habits; the contradictions it lives with. And it lets a memory or a belief name the people, places and objects it clings to — a grandmother, a house at the foot of the Alps, a guitar.

Like 1.1, it keeps the 1.0 promise: **everything it adds is optional**, every 1.0 and 1.1 file stays valid, and every 1.x tool keeps reading a 1.2 file. A file that uses a 1.2 addition declares `cof: "1.2"`.

## What is new

### For authors

- **A psyche, as a graph** (RFC 0004) — eleven kinds of short nodes: **wound, value, belief, want, need, fear, stance, taste, habit, contradiction, rule**. One or two sentences per language, tied by typed links to the memory a node comes from (*because*), to what it is about, to the nodes that support or oppose it. A contradiction is a pair of nodes that conflict, owned by the character. Each node carries how **strong** it is (0–100), how **stable** (core, settled, shifting, fragile — what a host may change at use time), **since** when, and the usual origin, visibility and disclosure. A belief can be *false but held*: the lie a character tells itself.
- **Awareness, valence, until** — three more optional fields on a node. **Awareness**: does the character know this about itself (yes, partly, no)? A node it does not know is acted on, never stated — that is not the same as keeping a secret. **Valence**, on a stance or a taste: which way it leans, from hostile or dislike (−100) to warm or love (+100); the affinity toward the user is a stance with a valence. **Until**: when the character stopped holding the node; a node that changes is a second node derived from the first.
- **People, places and objects** (RFC 0005) — a memory and a psyche node can both name who, where and what they are tied to, each either as a reference to something in the file (a character of the cast, an environment, an accessory) or as a plain name. A stance toward "my grandmother", a fear tied to a place, a habit around a notebook: no memory needed in between.
- **Illustrations on nodes** — a psyche node can carry one to three images; the first fills its bubble in the explorer, the others show in its card. The memory rules apply to them (who is shown, at what age, nudity, real people).
- **The declared age bounds a preset's life** — when a preset declares an age, that age is the end of its time: it keeps the memories and the psyche that had begun by then, and nothing after. If its variants show someone younger than the declared age, tools raise a coherence warning (never an error); the safety rules — minors, nudity, intimacy — keep reading the youngest age shown.
- **Risk, declared** — a node can be marked *inappropriate* or *dangerous*, with the matching content tag on the file. A host that gives a character tools never loads a dangerous node; fiction, which needs its villains, may load everything. A separate "no risk" purge removes them.

### The converter: from a personality to a psyche

Most characters already have a personality written somewhere. The converter reads it and **proposes** nodes — it never writes anything on its own: every proposal opens a review table where all boxes start unticked, and only the nodes you tick are added. The inputs:

- a **character card** (description, personality, scenario, first message, dialogue examples) or free text, read by an **AI gateway** you choose (your address, your key — the key is never saved or put on a command line), or a **proposal pasted** from any chat or file; the builder can **copy the bundle and the prompt** for any chat;
- the **1.0 lists** (goals, fears, values, behaviours): a goal becomes a want, a fear a fear, and so on;
- a **horoscope sign**;
- a **Myers-Briggs type** (four letters; used descriptively, no affiliation with the trademark holder);
- an **Enneagram** type (with or without its wing);
- **Big Five** scores (0–100: a high score proposes the trait's high pole, a low one the low pole, a middle one nothing).

The three profiles and the sign are an author's shorthand: they produce ordinary nodes to review, and none of them becomes a field of the format. The other direction exists too: **Text from the psyche** writes the "Who she is" section of an agent's `SOUL.md`, and can append it to the card's personality field.

### Tools

- **Explorer 1.2.0** — a **Psyche tab**: a list grouped by kind, and two graph views (a network of nodes hung on the memories, people and places they follow from, and a tags view with a "group by" choice). A **time cursor** ("In time") shows the character's nodes at a given age or year; **play** moves it one year per second (×1 to ×4), and **steps** jump to the previous or next year where something starts or ends. The same play and steps exist for the memories' time window. Memories and psyche cross-reference each other; objects, like people and places, are tags in both graphs; the feeling of a memory shows "then" and "now", with its pleasure and arousal.
- **Builder 0.14.0** — a **Psyche step** (4 of 8) with the grammar of the Memories step: a card per node, kind chips, filter, pages, derive; an Illustration row; people, places and objects; awareness, valence, until; the converter dialog with every input above and its review panel; "Text from the psyche"; presets that pick their nodes like a library, and whose age stops their memories and psyche (with a clear pop-up when an age change leaves items out of time); checks that mirror the validator; a "no risk" purge. Six interface languages. Opening a file with 5 000 memories takes seconds.
- **`cof-cli` 1.2.0** (`pip install cof-cli`) — validates the 1.2 rules; `cof psyche add`, `cof psyche propose` (all the converter inputs: `--rules`, `--zodiac`, `--mbti`, `--enneagram`, `--big-five`, a gateway or `--from-file`), `cof psyche text`; `cof memory add --what`; the agent export gains a "Who she is" section in `SOUL.md` and the objects in `MEMORY.md`; `cof extract` carries the psyche and the objects, with the risk and personal purges; `cof migrate --psyche` turns 1.0 lists into nodes.
- **ComfyUI-COF 0.7.0** — a **COF Psyche** node (the preset's psyche as text, with a "focus" to ask what the character thinks of something); the COF Memories text names where, with whom and with what objects.
- The `cof-author` skill for AI agents knows the psyche and the reviewed path from a proposal to the file.

## Compatibility

1.x adds only optional fields: **every 1.0 and 1.1 file stays valid**, and an older tool reads a 1.2 file — the new category appears to it as a library, with a warning. Nothing about the memories of 1.1 changed meaning. Schemas for 1.2 are published at `https://yannsouetre.github.io/cof/schemas/1.2/`; the 1.1 schemas are unchanged.

## For implementers

- The format changes in one place each: the `psyche` element category and its `psyche-node.json` file (RFC 0004), the `what` list on memories and the `who` / `where` / `what` lists on psyche nodes (RFC 0005), the optional `media` list of a psyche variant. The converter's contract is model-agnostic and documented in `docs/psyche-propose.md` (JSON in, JSON out, validation rules every tool shares).
- Reference implementation: `cof-cli` tests 79 → 101, a negative corpus extended with the psyche, objects and illustration rules, one example (`10-clara-mercier`) with 23 psyche nodes, three objects and a grandmother's pendant.
- `docs/builder-guide.md` describes the Psyche step in full.

## Next

- Demonstration characters at depth (Clara with 5 000 memories, branching by preset); weighted selection of memories (`cof select`); a date axis and coherence checks (1.1.2); a 3D viewer in the explorer; a desktop builder (Tauri) when the browser is no longer enough.

## Open for comments

RFC 0004 (psyche) and RFC 0005 (people, places, objects) open with this release and take comments until **8 December 2026** through the [issues](https://github.com/yannsouetre/cof/issues). 1.x is additive only, so what the comments change will ship in 1.2.1 rather than hold the release.

## Credits

Design, specification and tools: Yann Souetre, with Claude. Clara Mercier, the example character, was written and assembled with Claude. Comments on the RFCs are welcome, and will be credited in the next release notes.

## Cite

See `CITATION.cff`; this release is archived with a DOI on Zenodo.

## Licences

Code MIT; specification, documentation and examples CC BY 4.0; schemas and vocabularies CC0.

Full history: `CHANGELOG.md`. Feedback: GitHub issues.
