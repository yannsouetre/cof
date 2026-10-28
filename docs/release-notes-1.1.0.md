# COF 1.1.0 — release notes (draft — date to set on the day)

**AI characters now have memories.**

▶ [Why it matters](https://yannsouetre.github.io/cof/memories/) · [How much could a life weigh?](https://yannsouetre.github.io/cof/memories/how-much.html) · [Explore Clara's memories](https://yannsouetre.github.io/cof/viewer/#clara/memories) · [Build one](https://yannsouetre.github.io/cof/builder/) · [RFC 0002](https://github.com/yannsouetre/cof/blob/main/rfcs/0002-memories.md) · [RFC 0003](https://github.com/yannsouetre/cof/blob/main/rfcs/0003-identity-gender-archetype-relations.md)

COF 1.1 is the first minor version of the format, and it keeps the 1.0 promise: **everything it adds is optional**, every 1.0 file stays valid, and every 1.0 tool keeps reading a 1.1 file (the new category appears to it as a library, with a warning). A file that uses any 1.1 addition declares `cof: "1.1"`.

## What is new

- **Memories** (RFC 0002) — a character's past as a graph of **moments** and **periods**: a short text per language (the *gist*), when / where / with whom, how it felt then and now, a clarity (`vivid`, `clear`, `faded`, `fragment`), a few media (images, sound, a short video, a few remembered lines), typed links (`after`, `part-of`, `about`, `because`, `same-event`). Three axes on every memory: **origin** (authored by the creator, or lived during use), **visibility** (canon, or one user's personal data), **disclosure** (open, guarded, secret). The canon is read-only for tools; what the character lives with a user is added as new nodes, in the file — and leaves with it. Two characters sharing an evening keep two memories and share only the picture (`media_from`). The 1.0 rules follow: what is shown decides (a childhood memory in words shows no child and carries no age), every person shown in an explicit memory has a known adult age and the character's own age at the time is known and 18 or more — a memory lived as a minor is never explicit, even in words — a real person's memory needs their consent record and says whether it really happened, personal memories never leave a file unless asked (`--keep-personal`), and `--all-audiences` keeps every word of an explicit memory while dropping its media.
- **Gender, names, relations, archetype, role** (RFC 0003) — `gender` on the identity (never required, least of all for a real person) and per preset through `identity_override`; given and family names, several nicknames; **relations** between the characters of one file (18 closed types, declared on one side, the inverse computed); the character's **archetype** (the twelve of Mark & Pearson, or free) and **narrative role**; **default prompts** per preset (a scene for image and video generators, an opening line for dialogue) — the fields a generator asked for first.
- **The container describes itself** — every `.cof` now carries `COF.md`, a short note for a reader without the specification: what the file is, how to read it, the rules to honour, how to add what the character lives. `cof memory add` is the one-command write path for hosts and agents.
- **Reference implementation checked by a blind review** — a separate reviewer read both RFCs against the schemas, the code and the examples before publication: 38 findings, all treated (`docs/reviews/2026-10-25-blind-review-rfc-0002-0003.md`).

## Tools

- **Explorer**: a Memories tab with the timeline and a graph (periods above their moments, the people in them, the linked places), the gist in the preset's language, media on click (never an explicit one without the opt-in); tabs in the builder's order; a 🔍 on every element and memory that shows every parameter; gender badge, relations, archetype and role on the character card.
- **Builder 0.13**: a Memories step (step 3 of 7, advanced mode) with the grammar of the Elements step; presets pick memories like any library; checks for every rule of the RFCs; two build purges (all audiences, personal memories); the Build table opens any file; gender, names, relations, archetype and role on the cards; identity and prompts per preset; six interface languages, complete.
- **`cof-cli` 1.1.0** (`pip install cof-cli`): validates the 1.1 rules, exports memories to an agent workspace (`MEMORY.md` + media), extracts with the two purges, writes `COF.md` at pack, adds a lived memory with `cof memory add` (`--self-shown`, `--who "label|shown|age|real"`); `cof_cli/memories.py` and `cof_cli/cast.py` hold what every reader shares.
- **ComfyUI-COF 0.6.0**: a COF Memories node (the preset's memories as text and images), gender and the default scene in the prompt, archetype and role in the persona.

## For implementers

- `docs/IMPLEMENTING.md` § 7 bis: the 1.1 additions in one table, by reader profile.
- `docs/design-decisions.md`: why the format is the way it is, decision by decision, with the alternative each one rejected.
- Schemas at `https://yannsouetre.github.io/cof/schemas/1.1/` (`memory.schema.json` is the node file's schema); 1.0 schemas unchanged.
- Examples: `10-clara-mercier` is the first 1.1 file (16 memories, 31 media, four presentations of one life); `11-duo-clara-martien` is a 1.1 cast file (gender, a relation, two memories of one evening). Negative corpus: 63 cases (plus the valid base they derive from), 17 of them for the 1.1 rules (memories, cast), now shipped in the repository as the files themselves, not only as the script that builds them.

## Next

- **RFC 0004 — the psyche as a graph** (1.2): values, beliefs, wants, needs, fears, wounds, stances, tastes, habits and owned contradictions as nodes on the same mechanism, each linked `because` to the memory it comes from. Draft published with 1.1; implementation in the weeks after.
- A 3D viewer in the explorer; autosave and history in the builder when the adoption justifies it.

## Cite

See `CITATION.cff`; this release is archived with a DOI on Zenodo.

## Licences

Code MIT; specification, documentation and examples CC BY 4.0; schemas and vocabularies CC0.

Full history: `CHANGELOG.md`. Feedback: GitHub issues — format changes go through a public RFC (14 days).
