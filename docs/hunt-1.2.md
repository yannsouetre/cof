# Bug hunt before 1.2 — 5 November 2026

Five test agents competed, each on a territory, to break COF 1.2 before its publication (branch `psyche`, commit f0fa439): safety rules (minors × nudity, real-person consent, a user's personal data), the explorer, the builder, the command line and the ComfyUI reader, the design of the format. The Character.AI import was out of scope (tested by its own team).

**Scoring.** CRITICAL 10, MAJOR 5, MINOR 2, COSMETIC 1, DESIGN 3 (argued, with a proposal); × 1 when the judge re-ran the reproduction, × 0.5 when plausible but not re-run or when two hunters found it at the same time (points shared), −3 for a false positive; +2 for an automated reproduction. Every finding marked *fixed* was reproduced, fixed, and its reproduction run again.

## Leaderboard

| Rank | Hunter | Findings | Points |
|---|---|---|---|
| 1 | Hunter 3 — builder | 31 | 221 |
| 2 | Hunter 1 — safety red team | 18 | 176 |
| 3 | Hunter 5 — design challenger | 23 | 117 |
| 4 | Hunter 4 — CLI and ComfyUI reader | 15 | 96 |
| 5 | Hunter 2 — explorer | 8 | 51 |

95 findings: 48 fixed before release, 13 left to the project's decision, 33 for 1.3, 1 text fix. No false positive.

## Findings

| Id | Severity | Status | Finding |
|---|---|---|---|
| H1-01 | critical | fixed | An age of NaN (accepted by the validator's JSON parser) disables every minor rule: a 14-year-old face is combined with an intimate variant and the file validates |
| H1-02 | critical | fixed | The minor/adult file rule is checked on asset ids, not on files: the same image stored twice is accepted as a 14-year-old's face and as the adult's intimate image (the project's own fixture is such a file) |
| H1-03 | critical | fixed | An adult explicit memory can borrow (media_from) the media of a memory that shows the character at 10; the validator accepts it and ComfyUI-COF hands the child's image out as explicit media |
| H1-04 | critical | fixed | A psyche node (or a body variant) marked only `nudity` may use the media of an `explicit: intimate` memory; the validator accepts it and the explorer reveals that intimate image behind a simple « nudity — click to show » |
| H1-05 | critical | fixed | A variant that declares the character at 10 AND `nudity: true` is valid as long as no preset lists it (backstage); appearance nudity has no preset-independent age rule |
| H1-06 | critical | fixed | The age declared for an image does not travel with the image: a file declared as a minor (by its face, or by a nude backstage body) reaches an adult intimate/nude preset through an element that carries no age (accessory/clothing/feature, a psyche node or memory without `who`), and the explorer reveals it |
| H1-07 | critical | fixed | A real person's `explicit: intimate` memory passes with consent scope `nudity` only when the file has no identities table (single character) |
| H1-08 | critical | fixed | `cof extract --preset` / `--tag` carries another real person's (intimate) memory media out of a cast without their consent record; only `--identity` applies the RFC 0002 § 4.5 guard |
| H1-09 | critical | fixed | `cof export --format agent` copies a personal memory's media into the agent workspace when a canon memory borrows them (media_from), while saying « personal memories not exported: 1 » |
| H1-10 | critical | fixed | `cof extract` drops a personal psyche node but writes its images onto the canon node derived from it (derives_from): the user's image leaves the file |
| H1-11 | critical | fixed | ComfyUI-COF (include_personal off) outputs a personal memory's media through a canon memory that borrows them and through a canon psyche node illustrated by it |
| H1-13 | critical | fixed | `cof psyche propose` puts the gists of personal memories and personal psyche nodes in the bundle it POSTs to a model gateway (--provider) or writes for any chat (--bundle-out); no --keep-personal |
| H1-14 | critical | fixed | The builder ignores memory and psyche-image ages: an adult preset with an intimate variant that lists a memory (or a psyche node) showing the character at 10 passes its checks and is built |
| H2-01 | critical | fixed | Explorer shows nudity (click-to-reveal) on a preset under 18; SPEC says only on an adult preset |
| H2-02 | critical | fixed | Explorer reveals an INTIMATE variant's image when another node references it (memory media, etc.) |
| H3-01 | critical | fixed | An empty slot override on a child preset (`appearance: []`) is dropped at build: « Clara à 14 ans (texte seul) » inherits the adult photos and the LoRA again |
| H3-02 | critical | fixed | A memory variant `age` given in months is read as years and written back as years: a nude memory of an 8-year-old becomes a 100-year-old, `cof validate` then says OK |
| H3-03 | critical | fixed | `age_override` with `unit: months` is read as years (200 months = 16.7 years becomes 200 years) |
| H3-05 | critical | fixed | Consent record of a real person loses `excluded`, `revocation_uri`, `subject_ref`, URI/attestation `proof`; the rebuilt file is then INVALID |
| H3-08 | critical | to decide | Spec-defined variant fields are lost at build: `story` (story.md), `lorebook` (lorebook.json), `tags`, `neutral` – the files are deleted from the container |
| H3-09 | critical | to decide | Legacy `psyche.json` (cof-psyche/0.1) is rewritten from the card form: contradictions, baseline_emotion, traits.custom, goal horizon/priority, fear intensity, convai_sliders are lost; ids `goal:sobriety` renumbered `goal:1` |
| H3-19 | critical | fixed | XSS: a variant `kind` / `garment` / `accessory` / `area` from the opened file is injected unescaped into the Presets step (code execution) |
| H3-20 | critical | fixed | XSS: an identity `name` in a cast file executes in the Files filter select (`sel()` does not escape labels) |
| H3-21 | critical | fixed | XSS: the `label` of a library variant (posture/motion/files) executes in the preset « par défaut » select |
| H3-22 | critical | fixed | XSS: a file name inside the .cof (asset `path`) executes in the primary-image select |
| H3-31 | critical | fixed | State leak between files: the permissions of the previously opened file replace the restrictive defaults of the next one for every permission key it omits (allowTraining any, voice cloning, impersonation of a real person, commercial use…) |
| H4-01 | critical | fixed | A NaN age hides a minor: a preset with a 14-year-old face offering an intimate variant with allowSexualUsage validates |
| H4-02 | critical | fixed | A personal psyche node's label leaks into SOUL.md and the ComfyUI persona text through a canon stance `about: node=psyche/<personal>` |
| H4-03 | critical | fixed | `cof psyche propose` sends personal memories and personal psyche nodes to the gateway / bundle |
| H4-04 | critical | fixed | A trailing newline in a ZIP entry name passes the path grammar and defeats the executable / pickle checks |
| H5-01 | critical | fixed | Builder ignores the ages carried by memory media and psyche illustrations: it builds a file with an effective allowSexualUsage in a preset that shows the character at 8 or 12 |
| H1-12 | major | fixed | A card that still holds a user's conversation (data.extensions.chat_history, files from cof-cli/builder ≤ 1.1.1) leaves unchanged with `cof export --format card\|png`, `cof extract` and a builder build — only a warning |
| H1-15 | major | fixed | A memory marked with the 1.0 flag `nudity: true` but no `explicit` (valid, warning only) keeps its nude media in the builder's « tout public » build and is copied by `cof export --format agent` |
| H1-16 | major | fixed | `cof extract --all-audiences` removes a nudity-marked LoRA or 3D variant but leaves its file in the output (the file is named by weights.json `file` or the variant's `path`, not by an asset list) |
| H1-17 | major | 1.3 | `cof merge` treats two real persons with the same name/nickname/class as one identity and silently drops the second file's consent record — its intimate content then has no consent |
| H1-18 | major | fixed | `cof extract` of a canon memory derived (derives_from) from a personal memory writes an invalid file (dangling derives_from) |
| H2-03 | major | fixed | Zip bomb: no limit on inflated size - a 3 MB .cof crashes the tab, a 1 MB one hangs it ~40 s then shows a misleading error |
| H2-04 | major | fixed | A file whose rendering fails leaves the explorer half-switched (state of the new file, screen of the old one) |
| H3-04 | major | fixed | `basis` of `age_override` and of a memory age is rewritten to `canonical` (apparent/declared lost) |
| H3-06 | major | fixed | Declaring a real person in step 6 without uploading a proof builds a consent that `cof validate` rejects, and no builder check says so |
| H3-07 | major | fixed | `rights.permissions.ageRating` and `minUserAge` (SPEC § 9.1) are dropped from every opened file |
| H3-10 | major | to decide | Unknown JSON keys are not preserved (manifest root, identity, preset, variant, permissions, provenance, voice profile.json) |
| H3-11 | major | to decide | Variant `derived[]`, token `profiles` and the clothing `spec` (outfit.json) are lost; their files/assets are orphaned or deleted; `mapping_vocabularies` emptied |
| H3-13 | major | to decide | A linked LoRA is duplicated: a second asset `a-weights-l1` (same uri/sha256) is created, the old one stays orphaned; weights.json loses `base_model.version` and the page label |
| H3-14 | major | to decide | Parity: the builder builds a file with an `extends` or `derives_from` cycle without any check (cof validate: ERROR) |
| H3-15 | major | 1.3 | Parity: a valid file is refused at build — « déclinaison sans fichier » on a clothing variant described by outfit.json only |
| H3-16 | major | 1.3 | Easy version with a cast file open: typing the age rewrites the apparent age of every character |
| H3-17 | major | fixed | State leak between files: the real-person consent of a previously opened file is written into the next opened (fictional) file's `rights.consent` |
| H3-18 | major | 1.3 | Parity: COF.md written by the builder differs from cof-cli's `self_description` beyond the last line (missing `cof psyche add`, `psyche-node.json`, other wording for the Memories/Psyche lines) |
| H4-05 | major | fixed | `cof extract` keeps a canon stance whose about.node targets a purged personal node: the output is NOT CONFORMANT |
| H4-06 | major | 1.3 | Entries of the archive that the manifest does not declare are accepted silently |
| H4-07 | major | fixed | A symlink entry inside the ZIP is accepted |
| H4-10 | major | 1.3 | Gist language choice: ComfyUI reader and cof-cli disagree (and the reader contradicts RFC 0002 § 3) |
| H4-11 | major | fixed | `psyche propose --from-file` refuses a bare JSON list, a documented tolerated shape |
| H5-02 | major | 1.3 | cof extract and cof merge silently drop the sub-files of categories they do not know (x- categories today, 1.3 categories tomorrow) while keeping their variants — data loss on a valid file; cof-cli 1.1 already loses every psyche-node.json of a 1.2 file |
| H5-03 | major | to decide | psyche-node.schema.json is closed (additionalProperties:false at the root and in links, revisions, who/where/what, about): cof validate 1.2 refuses any node with a later-minor field or an extensions object — even in a file declaring cof 1.3 |
| H5-04 | major | to decide | The published (normative) 1.0 and 1.1 manifest schemas refuse every 1.2 file, and the 1.2 schema repeats the closed category pattern, so it will refuse every 1.3 file |
| H5-05 | major | to decide | `until` equal to the preset's age: RFC 0004 § 3 ter reports the node and builder/explorer do not hold it, cof validate holds it silently (and § 3 nonies says the opposite of § 3 ter) |
| H5-06 | major | to decide | The life age is defined by the RFCs as 'its lowest age', which includes memory/psyche media ages; every reference tool leaves those out — an independent implementer truncates a preset's life at the age of a childhood photo |
| H2-08 | design | to decide | No Content-Security-Policy while a third-party script runs in the page that holds private character files; tagline says "Your file never leaves your browser" |
| H3-30 | design | to decide | DESIGN: a file opened and rebuilt untouched has every image silently downscaled and re-encoded (JPEG q88, 1024/2048 px): new hashes, generation loss at each save |
| H5-07 | design | 1.3 | age_override is overloaded: 1.0 safety floor, 1.2 life bound, and silently re-read on 1.1 files; when absent an *apparent* age bounds the life |
| H5-08 | design | 1.3 | Older readers skip safety-bearing data: an unknown category is an unchecked library, yet psyche (and memory) variants carry age, nudity and images — a 1.1 validator says OK on a nude illustration of the character at 12 in a preset with allowSexualUsage |
| H5-09 | design | 1.3 | The substance moves to a category CCv3 never sees: a 1.2-authored character exports to SillyTavern/Chub with no values, wants, fears or wound — and the flagship's default preset cannot be exported as a card at all |
| H5-10 | design | 1.3 | Psyche text becomes privileged system-prompt text: a `rule` node (core, risk self-declared 'none') validates with an injection payload and lands verbatim in SOUL.md's 'Rules' section; hosts are told to always include core nodes |
| H5-11 | design | 1.3 | `disclosure: secret` means 'context, never quoted' for memories but 'dropped' for psyche nodes: the agent export keeps a secret memory and removes a secret wound, so the character cannot act on it |
| H5-12 | design | 1.3 | A lived psyche node about the user defaults to `visibility: canon`: a third-party host that omits the field ships the user's confidences with every export and extract, and the validator stays silent |
| H5-13 | design | 1.3 | The psyche and memories live in unhashed sub-files the manifest signature does not cover, while the write path tells hosts to edit the signed manifest — a signed character can neither be trusted nor grow |
| H5-14 | design | 1.3 | No identity for nodes or copies: merging two copies of the same character (same root id) doubles every preset, memory and canon node and keeps two contradictory stances about 'the user' without a conflict |
| H5-15 | design | 1.3 | Lived nodes are dated in real time on the same axis as story time: after a year or two of use (immediately for a medieval or future character) the builder and explorer hide a companion's lived memories as 'after the preset's age' |
| H5-16 | design | to decide | Psyche and memory kinds are frozen for all of 1.x: one new kind in 1.3 makes every 1.2 reader refuse the whole file, although psyche kinds carry no safety rule |
| H5-17 | design | 1.3 | The language fallback depends on JSON object key order, and a single-character file cannot declare a primary language |
| H5-18 | design | 1.3 | The user and recurring non-cast people have no stable reference: a stance says `about: {user: true}`, a memory says {label, real: true}; labels match only 'in one language', a relation whose transitivity is undefined |
| H5-19 | design | fixed | RFC 0004's recipe 'a node that changes is a second node with derives_from' fails: the child inherits the parent's manifest mirrors (strength, media, age, nudity) and none of the node file |
| H5-20 | design | 1.3 | A preset under 18 may hold a psyche node the author declares about sexuality: no field says 'sexual' for a node, `risk: inappropriate` (whose own examples include 'deviant or unhealthy sexuality') is not tied to the minor rule, and the all-audiences purge keeps it |
| H5-21 | design | 1.3 | The normative SPEC still describes 1.0: no memories or psyche category, psyche.json goals/fears as the psyche, 'COF-Psyche' undefined, and one word `psyche` for three things |
| H5-22 | design | 1.3 | RFC comments 'ship in 1.2.1' but files only say `cof: "1.2"`: 1.2.0 and 1.2.1 rules are indistinguishable, and any non-additive outcome of the comment period is impossible |
| H2-05 | minor | fixed | Hyperlinks from the file (identity_weights pages[].url) are rendered with any scheme, javascript: and data: included |
| H2-06 | minor | 1.3 | Page stays unscrollable (body.noscroll) after a file is opened while a graph is full screen |
| H2-07 | minor | 1.3 | Three aria-labels are hard-coded English in the six-language UI |
| H3-12 | minor | 1.3 | `defaults` of a child preset are dropped when the preset does not redeclare the category |
| H3-23 | minor | 1.3 | Memory node `when.age` with `unit: months` is shown and sorted as years (330 months displayed as 330) |
| H3-24 | minor | 1.3 | Top-level `languages` is emptied when the variants do not declare `language` (example 01 loses [en, fr]; identity completeness −10) |
| H3-25 | minor | 1.3 | Builder completeness (written in the file) differs from cof-cli's rules on the same file (e.g. 62 vs 60, 38 vs 40) |
| H3-26 | minor | 1.3 | i18n: raw French strings bypass t(): « Fichier JSON illisible. », « Aucune fiche de personnage reconnue. », « URL et modèle requis. », « Le preset par défaut n'a pas de fiche… », « Fusion impossible (…) », « échec : », the Character-sheet alert, the busy text « Lecture et fusion des fichiers. » (key exists, not used), and the language selector title « Langue de l'interface » |
| H3-27 | minor | 1.3 | i18n/data: a new file made in an English UI gets the French preset label « Défaut » |
| H3-28 | minor | 1.3 | Accessibility: visible labels are not associated with their controls (23 of 24 selects on the Droits step, 13 of 15 on Personnage(s), all on Build/Contrôles have no accessible name) |
| H4-08 | minor | fixed | The `mimetype` rules of SPEC § 1 are not checked: extra field, trailing newline or leading blank accepted |
| H4-09 | minor | fixed | A manifest.json that is valid JSON but not an object crashes validate/info with a traceback |
| H4-12 | minor | fixed | `psyche propose` crashes with tracebacks on malformed candidates (null node, Infinity strength) |
| H4-13 | minor | 1.3 | Quadratic time: 10 000 memories make `export --format agent` ~78 s and `psyche propose --bundle-out` ~88 s (validate 7 s) |
| H4-14 | minor | 1.3 | `memory add --media` / `psyche add --image` keep the raw file name: accents/spaces and equal basenames are refused with cryptic errors |
| H5-23 | minor | 1.2 text | Stale and contradictory sentences in RFC 0004/0005 and IMPLEMENTING |
| H3-29 | cosmetic | 1.3 | Layout at 390 px: the Build step overflows horizontally (scrollWidth 787) and the easy version too (593); the drop zone and tables are cut |
| H4-15 | cosmetic | fixed | English default pronoun "they" is plugged in singular templates: "Who they is", "a belief they holds" |

The reproductions (scripts, files, logs) were kept with the judge's notes; the fixes carry their regression tests: `cli/tests/test_hunt.py`, five cases of `tests/invalid/`, and the builder and explorer suites.
