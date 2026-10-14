# Blind review before the 1.0 structure freeze — 14 October 2026

**Reviewer**: an AI model other than the one that wrote the format (Claude Fable), started with no history of the project, read-only. It read `spec/SPEC.md`, `docs/IMPLEMENTING.md`, `spec/schemas/`, the examples and the negative corpus, ran `cof validate` on the examples, and probed the validator on scratch copies. 45 findings: 5 blockers, 19 major, 21 minor or editorial. Its conclusion: *"The modular design (presets, per-preset age, neutral/identity model) is sound; the gaps are in binding rules to assets and in enumerating what `extends` inherits."*

**Triage legend**: ✅ fixed in rc3 · 📝 wording fixed in rc3 · 🟨 decision for Yann (see roadmap, *Points à trancher*) · ⏭ deferred to 1.x (additive, no 1.0 file changes meaning)

| # | Severity | Finding | Status |
|---|---|---|---|
| F-1 | BLOCKER | § 4.5(3) says the intimate age rule is per file, § 9.4 says per preset | ✅ § 4.5 aligned on § 9.4 |
| F-2 | BLOCKER | one image could be "12-year-old face" in one variant and "intimate, 34" in another (example 09 did it) | ✅ an intimate variant's files are its own (own folder, no other user); a file whose users' ages straddle 18 is an error; example 09 fixed; 3 negative cases |
| F-3 | BLOCKER | `{value: 100, unit: months}` passed as an adult | ✅ comparisons in years; negative case `age-in-months` |
| F-4 | BLOCKER | what `extends` inherits was undefined (`permissions_override`!) | ✅ normative list (§ 2.3); `age_override` inherited, `permissions_override` never; cycle = error |
| F-5 | BLOCKER | `morphology.class: other` removed the age requirement next to an intimate variant | ✅ with an intimate element every body representation carries an age, whatever the class |
| F-6 | MAJOR | schema `required` vs "everything else is optional" | 📝 required root fields listed (Annex B), principle 2 reworded |
| F-7 | MAJOR | `use: pose-only` not in the schema enum | ✅ `pose-only` added to the `use` enum |
| F-8 | MAJOR | consent has four possible homes | 📝 one home: inline `identities.<id>.consent` (root copy `rights.consent` for one character), validated by `consent.schema.json`; `rights/consent.json` removed from the tree; `training.dataset_consent` in the example |
| F-9 | MAJOR | consent scopes not tied to what the file contains (intimate, voice, weights, 3D) | ✅ scopes follow the content: `intimate` without scope `intimate` = error, memories without `conversational-persona` = error, other likeness scopes = warnings · 🟨 turn the warnings into errors? |
| F-10 | MAJOR | `age.unit: unknown-adult` undefined | ✅ removed (never written by any tool) |
| F-11 | MAJOR | `manifest.thumbnail` dangled in 6 examples, not validated | ✅ must exist (error); examples fixed; negative case |
| F-12 | MAJOR | region conflicts: warning in § 2.3, blocking in § 11.4 | 📝 § 11.4 aligned (region overlaps are warnings) |
| F-13 | MAJOR | `single_per_kind: false` disables a "blocking" rule | 📝 `single_per_kind: false` is allowed, the author answers for it |
| F-14 | MAJOR | `spec/examples/manifest.example.json` is a v0.2 file | ✅ deleted |
| F-15 | MAJOR | which files must be assets is contradictory; JSON sub-files have no hash | 📝 every ZIP entry is an asset or a named sub-file; sub-files have no hash in 1.0 · ⏭ optional sub-file hash index in 1.1 |
| F-16 | MAJOR | closed enums break the "1.x only adds" promise | ✅ 1.x only adds; an unknown enum value / field in a later-minor file is a warning (validator implemented); `permissions_override` open like `permissions` |
| F-17 | MAJOR | spec vocabularies and schema enums disagree | 📝 roles, subject, derived methods, voice priorities, `morphology.class` (required, no default), `age.basis` defined · ⏭ `target` vocabulary |
| F-18 | MAJOR | zero-preset files: "first variant of each category" is non-deterministic | ✅ at least one preset + `default_preset` required (every tool already wrote one); `cof migrate` adds `default` to a file without presets |
| F-19 | MAJOR | "executable content" undefined; archives bypass the pickle / script rules | ✅ normative list of executable extensions + SVG / HTML with script; `.zip` archives inspected one level deep (pickles, executables); `.rar` / `.7z` warned |
| F-20 | MAJOR | § 4.5(1) gated on the root permission, not the effective one | ✅ effective `allowSexualUsage` |
| F-21 | MAJOR | examples 07 / 09: childhood preset inherited the adult LoRA | ✅ `"identity_weights": []`; validator warns when a preset mixes ages ≥ 10 years apart |
| F-22 | MAJOR | `files` and `x-` categories have no declared regime | 📝 `files` and `x-` categories are libraries |
| F-23 | MAJOR | example 10 `ps1` is photos typed `openpose`; fixed-neutral clips / openpose vs motion-capture consent | ✅ Clara's pose photos are three `photo` variants (`use: pose-only`) · 🟨 should motion clips and OpenPose stay *fixed* neutral? |
| F-24 | MAJOR | references to things that do not exist in 1.0 (`skeletons-1.0`, schema titles "v0.5") | 📝 `skeletons-1.0` marked 1.1, `skeleton.json` recommended for `rig: custom`, schema titles and README at 1.0 |
| F-25 | MINOR | `age_override` called a "floor" but applied as a minimum | 📝 defined as the age the preset declares for itself (it can only lower the age); name kept |
| F-26 | MINOR | root copy of the identity: copied fields unlisted, root rights unsaid | 📝 listed (`name`, `nickname`, `summary`, `fictional`, `morphology`); root rights = default character's |
| F-27 | MINOR | `languages` "computed union" vs examples declaring it | 📝 author MAY declare it, tools add (union, nothing removed) |
| F-28 | MINOR | `coverage.elements` mixes categories and kinds; layer keys | 📝 layer keys named (`physique`…) · ⏭ `coverage` vocabulary (computed field) |
| F-29 | MINOR | `body.estimated` in three places | ⏭ 1.1 (pick one, keep the others as aliases) |
| F-30 | MINOR | duplicated truths (`weights.json` vs variant / asset) | 📝 `weights.json` is authoritative, the copies are indexes |
| F-31 | MINOR | `outfit.json` `default: true` | ✅ removed from the spec and the examples |
| F-32 | MINOR | `extends` / `derives_from` cycles | ✅ both are errors |
| F-33 | MINOR | facet navigation: equality or inclusion? | 📝 set equality (as implemented) |
| F-34 | MINOR | default primary image: kind order or slot order? | 📝 kind order, then slot order, then first image (as implemented) |
| F-35 | MINOR | `permissions_override` may widen | 📝 it may, except `allowSexualUsage` under 18 |
| F-36 | MINOR | merge key ignores `fictional` / `morphology` | ✅ key = `name` + `nickname` + `fictional` + `morphology.class` (CLI and spec) |
| F-37 | MINOR | "all-audiences copy by deleting one folder" incomplete | ✅ procedure described; `cof extract --no-intimate` also drops a removed primary image and the `nudity` flag |
| F-38 | MINOR | MUSTs a program cannot check | 📝 § 11.1: they bind the author, validators check what is checkable; "80 % duplicates" → SHOULD, metric free; mimetype rule reworded for writers |
| F-39 | MINOR | robot (`mechanical`) with age 3 gets the auto tag `child` | 🟨 age buckets only for human-form classes? |
| F-40 | EDITORIAL | § 2.3 example cites variants not defined in § 2.2 | 📝 commented |
| F-41 | MINOR | `tags.content: ["none", "nudity"]`; `species: ""` | ✅ `none` is exclusive (error); empty species removed from example 10 · ⏭ `species` minLength (the builder writes `""` today) |
| F-42 | EDITORIAL | IMPLEMENTING stale on signatures and on the spec language | 📝 fixed |
| F-43 | MINOR | mimetype local header "no extra field" only in IMPLEMENTING | 📝 normative in § 1.1 |
| F-44 | MINOR | a voice perceived as a child in a preset with intimate content | ✅ warning |
| F-45 | EDITORIAL | debris: v0.3 headings, § 11.4 before § 11.3, `pt-unsafe-not-allowed` hack, stale `tags.auto`, adult dialogue in the 14-year-old card | ✅ headings renamed, sections reordered, `format: const safetensors`, `tags.auto` recomputed, childhood dialogue rewritten (examples 07 / 09; 09's childhood face aligned on its card: 14) |

## Second pass on rc3 (same reviewer)

F-1 to F-5 re-probed and confirmed closed, plus new probes (inherited images through `derives_from`, intimate only in `alternatives`, uppercase extensions and SVG handlers, pickles one level inside a zip): all caught. All 11 examples valid, every negative case fails for its expected reason, EN / FR aligned. Two more problems found, both fixed the same day:

| # | Severity | Finding | Status |
|---|---|---|---|
| R-1 | MAJOR | an unknown age `unit` in a later-minor file (`weeks`) was read as years — a bypass of F-3 through the § 12 relaxation | ✅ an age with a unit the validator does not understand is an unknown age, never adult (CLI and builder); negative case `age-unknown-unit` |
| R-2 | MAJOR | a zip nested in a zip was neither inspected nor warned | ✅ nested archives inspected up to three levels (by extension or magic), deeper nesting warned; negative case `nested-archive-pickle` |
| R-3 | MINOR | § 12 vs validator on an unknown `kind` | 📝 an unknown `kind` stays an error in every version (a kind may carry safety rules) |
| R-4 | EDITORIAL | example 09 label still said 12 years | ✅ fixed |

Reviewer's conclusion: *"With items 1 and 2 closed, the age/intimate rule set holds against every probe I could construct, and I consider the structure freezable."*
