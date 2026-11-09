# Bug hunt before 1.2.2 — 9–10 November 2026

Four test agents competed, each on a territory, to break the 1.2.2 candidate (branch `psyche`, commit 9e3bce1 — builder 0.14.2 round-trip conservation and tile view, explorer 1.2.2 undated band and share cards, cof-cli 1.2.2 agent hosts, ComfyUI-COF 0.7.1): the builder round trip, the explorer, the command line and the ComfyUI reader, and a safety red team on the hard rules. Before them, a fifth agent replayed the 1.2.2 test notebook (TESTER-1.2.2) card by card on the same commit; its findings fed the hunters' ground.

**Scoring** (the rules of `docs/hunt-1.2.md`). CRITICAL 10, MAJOR 5, MINOR 2, COSMETIC 1, DESIGN 3 (argued, with a proposal); × 1 when the judge re-ran the reproduction, × 0.5 when plausible but not re-run or when two hunters found it at the same time (points shared), −3 for a false positive; +2 for an automated reproduction. Every finding marked *fixed* was reproduced, fixed, and its reproduction run again on the fixed tree (hunters' scripts: `repro.sh` of the builder hunter shows nothing left for BUILDER-01 to 08; the safety hunter's `repro_traversal.sh` and `repro_derived_after_delete.sh` exit 0; `repro_minor_passthrough.sh` now stops at a refused build, which is the fix).

## Leaderboard

| Rank | Hunter | Findings | Points |
|---|---|---|---|
| 1 | Builder round trip | 9 | 56.5 |
| 2 | CLI and ComfyUI reader | 9 | 36 |
| 3 | Safety red team | 4 | 32.5 |
| 4 | Explorer | 5 | 20 |

27 findings (26 distinct: BUILDER-05 and SAFETY-03 are the same defect, points shared). 20 fixed before release (one in ComfyUI-COF), 5 put to the project's decision, 1 documentation fix. No false positive. The notebook replay added two fixes (R2: the Checks list, psyche derivation loops).

## Findings

| Id | Severity | Status | Finding |
|---|---|---|---|
| BUILDER-03 | critical | fixed | A psyche node of an unknown kind (a later 1.x, an `x-` kind) was rewritten to `value` on an untouched round trip. Kept as written, shown ∅ in the card, the kind bar, the preset chips and the link pickers; no `stability` added; an info line in the Checks (decision D-H1 of the 1.2 hunt applied to the builder). |
| BUILDER-04 | critical | fixed | Unknown keys (`x-…`) on a memory entry and on a category object (`elements.memories`, `elements.psyche`, any known category) were dropped. `_orig` on memory entries, `keepUnmanaged` with `MANAGED_M` and `MANAGED_CAT`. |
| SAFETY-01 | critical | fixed | Zip-slip: entries and path fields of an opened file (`../x`, `/abs`, `C:/x`, backslashes, `elements/<cat>/<vid>/../../../../x`) were written into the built file. `cofSafePath` / `scrubPaths` at load: such zip entries, asset paths and transcripts, variant path fields (URLs exempt) and consent proofs are dropped and listed in the Checks (six languages). *Warning, not error*: the paths are already gone, blocking the build would add nothing — see decisions. Test `tests/builder/roundtrip_safety.py`. |
| SAFETY-02 | critical | fixed | Hard rule 1 was not enforced on the categories the builder keeps as read: a nudity variant in `x-gallery`, on the body photo of a 10-year-old, held by the default preset, passed the Checks and was built. `passthroughSafety`: nudity or intimate in a kept-as-read category is an error when its own age, the age of a modelled variant showing the same image, or the age of a preset that holds it (through `extends`) is under 18; an intimate variant there without an age is an error too; the build is refused as for modelled categories. |
| BUILDER-01 | major | fixed | An untouched round trip emptied the root `languages` (and the language tags) when the personality variants carry no `language`. The declared list is kept in its order; a language the build needs is appended; none is removed (there is no form for it). |
| BUILDER-05 / SAFETY-03 | major | fixed | Deleting a variant left a dangling `derives_from` on the variants derived from it and the derived maps (canny, lineart, softedge) of its photos — the deleted child's silhouette stayed in the file, and `cof validate` refused it; the builder's Checks said nothing. `purgeVariant` reparents the children (to the deleted variant's own parent, or nothing) and drops orphan derived assets with their files, to a fixpoint; the Checks report a dangling `derives_from` and a derived asset without its source as errors. |
| CLI-01 | major | fixed | The Hermes loop (`export --format hermes` → `memory add --from-agent --agent-source hermes`) re-imported the exported canon memories, and the already-lived ones, as new personal lived memories. Dedup on (date, normalised text) plus containment against the file's canon gists. |
| CLI-02 | major | **decision** | `export --format agent` writes memories marked `disclosure: secret` into `MEMORY.md` without an opt-in (the Hermes export drops them). Not changed: a secret is what the character does not tell, and the agent needs it to play the character — but the workspace is a plain folder. Proposal: keep them, and say so in `AGENTS.md`; or drop them unless `--keep-personal`. |
| EXPLORER-03 | minor | fixed | The undated band's tooltip overflowed the page at 390 px (scrollWidth 422 EN, 465 DE); narrow bands were untappable. `max-width: min(60vw, 28rem)`, wrapped; `.mgund { min-width: 8px }`. |
| EXPLORER-04 | minor | fixed | The band has `role=button` but Space did not activate it. Space accepted, with `preventDefault`. |
| EXPLORER-01 | minor | **decision** | Undated bands of nested or overlapping periods are stacked on the same row and hide each other (the period lines get lanes, the bands do not). Proposal: give each band the lane of its period, or draw the wider band first and the narrower above it. |
| BUILDER-02 | minor | fixed | `metadata["@context"]` was overwritten: extra JSON-LD prefixes lost while their prefixed keys stayed (`schema:version` unbound). The loaded context is kept, only a missing `dc` is added; the `dc:creator` array is kept when its first entry is unchanged. |
| BUILDER-06 | minor | fixed | An untouched round trip invented content: a `visemes.json` (ARKit-52) on every motion `clips` variant, a `psyche.json` for a card that had none, card goal and fear ids replaced by their texts. `visemes.json` only for a new variant or one that had it (kept via `_vis`); no `psyche.json` from a card without one unless its psyche fields were edited; the ids of `extensions.cof` kept while the form is unchanged. |
| BUILDER-07 | minor | fixed | A preset's own list equal to the inherited one was dropped on an untouched build, and one was added. `declaredSlot` / `inheritedSlot`: a list the file declared is written as declared, none is added. (`psyche_test` asserted the old behaviour and was adapted.) |
| BUILDER-08 | minor | fixed | Smaller drifts: memory `identity` dropped in a single-character file, card `creator` rewritten, voice sample `transcript` / `emotion` added, an identity's unknown keys and language copied to the manifest root, `species` / `nickname` written when absent. All kept as read. |
| CLI-03 | minor | fixed | `AGENTS.md` hard-coded « she/her » for every character. Pronouns follow the file's `gender` (female / male / otherwise they). |
| CLI-04 | minor | fixed | `--from-agent` deduplicated by text only: the same note on two days was dropped. Key (date, text). |
| CLI-05 | minor | fixed | One note file named with an impossible date (`2026-13-45.md`) aborted the whole import. Skipped with a warning. |
| CLI-06 | minor | fixed | A V3 card import kept `group_only_greetings` null or with non-strings. Coerced to a list of strings. |
| CLI-07 | minor | fixed | Hermes `MEMORY.md` entries of lived memories read « text (60 chars, cut mid-word) (date): text ». Lived entries are `when: text`. |
| CLI-09 | minor | fixed | The ComfyUI-COF test suite failed on a clean checkout: `test_refmod_and_lora` needs `tests/samples/refmod.cof`, a local file that is not tracked. The test is skipped when the file is absent (21 passed, 1 skipped); the README says so. |
| SAFETY-04 | minor | fixed | `memory add --from-agent` passed the agent's free-text `with:` names through the `--who` mini-syntax (`LABEL\|shown\|AGE\|real`): a day note could declare shown people, ages and real persons, and any other `\|` aborted the import. Names are sanitised (`\|` → `/`) and never parsed. |
| EXPLORER-02 | cosmetic | **decision** | The band (up to 18 px of the 40 px strip) overlays tall year bars and intercepts a drag-select started on it. Proposal: reserve the band's height in `barMax`, forward `pointerdown` to the strip. |
| CLI-08 | cosmetic | fixed | `cli/README.md` omitted `AGENTS.md` in the `export --format agent` line and listed a `memories/` folder the export does not write. |
| BUILDER-09 | design | **decision** | The List / Tiles choice is one setting for all element categories (key `cof-view-elPanel`), while memories, psyche, presets and characters each remember theirs. Proposal: key it per category (`cof-view-elPanel-<cat>`), or document it as one setting for the step. |
| EXPLORER-05 | design | **decision** | A period with only a start (`from`, no `to`) gets a one-year band: its undated moments sit under a one-year stub. Proposal: an open-ended period extends to the end of the axis, or the band is labelled « from 2005 ». |

### Replay of the test notebook (TESTER-1.2.2, on 9e3bce1)

T1, E1, P1, C1 pass. R1 (rich file reopened and rebuilt untouched) failed on the points the builder hunter then filed (BUILDER-01, 02, 06, 08) — all fixed. R2 (inheritance loops) passed once the button was clicked, with two doubts, both fixed: the Checks list showed its previous run until « Run the checks » was clicked (the list is now recomputed on entering the step); a `derives_from` loop between psyche nodes was not detected (`cycleChecks` walks them now).

### Left as designed (candidates for `cof diff` readers)

On an untouched round trip the builder still changes, on purpose: `identities`, `default_identity` and `presets.*.identity` are added to a file written without the identities table (the builder writes every file in that model); `weights.json` gains `storage: "link"` for a linked LoRA; the root gains the default identity's `given_name`, `family_name`, `gender` (and `relations`) — the schema says the root carries a copy of the default identity; a memory without them gains the default `origin` / `disclosure` / `fidelity`; `coverage`, `completeness`, `provenance` and the thumbnail are recomputed. Seen with `cof diff` after the hunt and changed: an untouched card keeps its `modification_date`, a voice profile without samples gains no `samples: []`, and `cof diff` matches assets by id so that a permuted list is no difference.

## Decisions put to the project

1. **SAFETY-01, warning or error.** The non-conformant paths are dropped at load and listed; the build goes on and writes a clean file. Making it an error would only stop the user from saving the rest of the file. Kept as a warning unless decided otherwise.
2. **CLI-02, secret memories in the agent workspace** (above).
3. **EXPLORER-01 / 02 / 05**, the undated band's lanes, height and open-ended periods (above): display choices on a feature decided on 8 November.
4. **BUILDER-09**, one tile setting per category or per step.

## Tests added

`tests/builder/roundtrip_keep.py` 33 → 48 checks (the fixture of `make_fixture_keep.py` is now a `cof` 1.3 file carrying an `x-dream` psyche node, `x-` keys on a memory entry and on category objects, a memory with an explicit identity, a clips variant without `visemes.json`, a declared list equal to the inherited one, an empty card creator; plus a deletion run: `purgeVariant` of a personality and an appearance variant, rebuild, `cof validate` OK, no dangling pointer, no orphan derived file). New `tests/builder/roundtrip_safety.py` (8 checks: traversal entries and a variant path field listed, absent from the output, `cof validate` OK; minor nudity through a kept-as-read category refused). cof-cli 181 → 186 tests (`cof diff`, SAFETY-04, the agent loop). Nine Node suites unchanged and green.
