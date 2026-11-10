# COF 1.2.2 — release notes (DATE_TBD)

**Open, edit, build: nothing else moves.** A tooling release: no change to the format — a 1.2.2 tool reads and writes exactly the files a 1.2.0 tool does, `cof: "1.2"` stays what a file declares.

▶ [Build one](https://yannsouetre.github.io/cof/builder/) · [Explore Clara](https://yannsouetre.github.io/cof/viewer/#clara/psyche:graph) · [Changelog](https://github.com/yannsouetre/cof/blob/main/CHANGELOG.md)

The 1.2.0 notes carried a known issue: opening an existing file in the builder and building it again could lose what the builder does not model. The five-agent bug hunt had listed it in detail (findings H3-08 to H3-14 of [`docs/hunt-1.2.md`](https://github.com/yannsouetre/cof/blob/main/docs/hunt-1.2.md)). This release closes it, and adds a tile view to every list of the builder.

## Builder 0.14.2

- **A reopened file keeps what the builder does not model.** The builder now edits only what its forms show; everything else it read is written back as it was — on every record (manifest root, identity, preset, variant, asset, voice profile, `weights.json`, legacy `psyche.json`): fields it does not model (`story`, `lorebook`, variant `tags`, `derived`, token `profiles`, a clothing `spec`), unknown keys at every level (`x-…`), `mapping_vocabularies`, `priorities.by_target`, and every file of a variant it does not regenerate (`story.md`, `lorebook.json`, `outfit.json`, `face.json`…), plus `rights/` and the other root files. What you delete in the builder is gone from the file; what you never saw is kept. The declared `cof` minor never goes down.
- **Legacy `psyche.json` edited on top of itself**: a goal or fear whose text is unchanged keeps its id, horizon, priority or intensity; contradictions, baseline emotion, custom traits and renderings are kept; an emptied form does not erase the file.
- **A linked LoRA keeps the asset id the file gave it** (no more duplicate `a-weights-…`), with `base_model.version` and the page label of `weights.json`.
- **A child preset's default on an inherited category is kept** (hunt H3-12).
- **Inheritance loops are errors**: a preset that `extends` itself through a chain, or a variant that `derives_from` itself, stops the build at the Checks step — `cof validate` refused such files already (hunt H3-14).
- **Tile view**: a ☰ List / ▦ Tiles switch in the fold bar of every list (elements, memories, psyche, presets, characters). The same cards, forms and actions, laid out as a grid that follows the width (four columns at 1 400 px, two at 900, one under 560); a tile opens full width on click; image variants show their first picture. List remains the default; the choice is remembered per list, in the browser. Six languages.
- **Tiles of one size, magnifier**: every folded tile is 300 px high in every section (« + » top-left, code top-right, picture or its empty place, then the name — long names end in « … »); a preset's tile shows the top of its main photo (the face of its default look, else the file's thumbnail); « Skills and files » gets the fold bar (filter, List / Tiles) even with a single card; a 🔍 in the top-right corner of every image preview (element variants, memory media, psyche illustrations, preset photo, tiles, build thumbnail) opens it full screen in one shared pop-up (Escape, × or backdrop click closes it). Display only: the built file does not change.
- Test: `tests/builder/make_fixture_keep.py` writes a file that carries everything the 1.2.0 builder used to lose; `tests/builder/roundtrip_keep.py` opens it, builds it untouched and checks 48 points (a deletion run included), then runs `cof validate` on the result; `tests/builder/roundtrip_safety.py` checks that a crafted file's non-conformant paths never reach the output and that a nude variant of a minor in a category the builder keeps as read is refused.
- **Reviewed before release by four competing test agents** (builder round trip, explorer, CLI and ComfyUI reader, safety red team — 27 findings, 20 fixed, report [`docs/hunt-1.2.2.md`](https://github.com/yannsouetre/cof/blob/main/docs/hunt-1.2.2.md)). Two of them mattered for safety: a crafted file could carry `../` paths through the builder into the built file, and hard rule 1 (no nudity or intimate content with a minor) was not enforced on the categories the builder keeps as read. Both are closed.

- **Share card**: a link to the builder now unfurls on Discord, X, Reddit or Slack with an English description and a 1200 × 630 picture (`builder/og-builder.jpg`); the page declares `lang="en"` (the interface still follows the language button).

## Explorer 1.2.2

- **Undated memories inside a period get a mark of their own.** An imported conversation has no date, only the period it belongs to (« Conversations on Character.AI », 2022 to the export year). The time bar used to place it at the start of its period, which read like a date; now each period that holds undated memories carries a small grey dot in the middle of its line — grey, in the time bar, means « undated », as for the final « n.d. » column — with the count on hover (« 3 undated memories, during… ») and the period as time window on click. The « n.d. » column keeps only the memories that belong to no period at all. The time bar also sits in a frame you can make taller by dragging its handle (the lanes of overlapping periods and the year bars grow with it; double-click resets), and the psyche's « in time » bar gets the same frame.
- **Share card** for the main explorer too (`viewer/og-explorer.jpg`, Clara's file open in dark theme); the Character.AI version keeps its own, generated by `tools/viewer-cai/gen.py`. Both pictures are made by `tools/og-cards/make.js` from fresh screenshots of the tools.
- English footer: straight quotes around “Checks” (the French guillemets had leaked into the English text).

## `cof-cli` 1.2.2

- **Agent hosts.** `export --format agent` also writes an `AGENTS.md` (how the host must treat the workspace: who the character is, where memories go, what the notes look like); new `export --format hermes` writes a Hermes Agent profile (`SOUL.md`, `memories/MEMORY.md` as `§` entries within the host's limit, salience first, `skills/`); new `memory add --from-agent DIR` reads back the day notes an OpenClaw workspace or a Hermes profile wrote and adds them as lived, personal memories (tag `lived:<host>`), idempotently. One character, several hosts, one memory — the demo of the agents note.
- `cof import` of a V2 card relabelled V3 now writes `group_only_greetings` (the V3 spec says MUST).
- **`cof diff a.cof b.cof`** — what differs between two files or folders (records with an `id`, such as assets, are matched by id, not by position): members on one side only, members whose bytes differ, and the flattened JSON keys added, removed or changed; exit code 1 when different. The tool of the round-trip promise: open a file in the builder, build it again, `cof diff` the two.
- The PyPI workflow skips a version that already exists.

## Credits

Design, specification and tools: Yann Souetre, with Claude. The round-trip findings come from the bug hunt of 5 November (Hunter 3 — builder).

## Cite

See `CITATION.cff`; this release is archived with a DOI on Zenodo.

## Licences

Code MIT; specification, documentation and examples CC BY 4.0; schemas and vocabularies CC0.

Full history: `CHANGELOG.md`. Feedback: GitHub issues.
