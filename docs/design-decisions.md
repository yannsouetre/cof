# Design decisions — why COF is the way it is

A retrospective of the choices that shaped 1.0 and 1.1, each with the alternative that was rejected and why. The specification says *what*; this page says *why*, so that a later RFC does not undo a decision without knowing what it protected. Dates are those of the decision; the CHANGELOG has the details.

## The container

1. **A ZIP with `manifest.json` at its root, `mimetype` first and stored** (2026-10, phase 0). Alternatives: a folder, a single JSON, an OCI artifact. A ZIP opens everywhere, carries binaries, and the EPUB/ODF convention (`mimetype` as the first uncompressed entry) lets a file manager identify it without unpacking. An OCI mirror with the same digests stays possible later; nothing in the format depends on ZIP internals.
2. **Every file is declared in `assets` with its SHA-256, size, media type, licence and role** (phase 0). Rejected: trusting the ZIP directory. A declared index is what makes a file checkable (`cof validate`), diffable, and partially extractable (`cof extract`); per-asset licences come from the GGUF lesson (one global licence hides what each file allows).
3. **Elements, variants, presets** (phase 0): a category holds variants (one face, one voice, one place each); a preset applies some (`slots`) and offers others (`alternatives`). Rejected: one flat character per file (no "Clara at 12 / Clara manga"), and presets that copy data (a preset lists ids, never files). The rule "one variant = a consistent set of one thing" (0.11.7) came from users mixing several places in one environment variant.
4. **`extends` between presets, nearest declaration wins per field** (rc2). Rejected: full preset copies. Inheritance keeps a twelve-preset file (Clara) readable and makes "the same character in another language" a two-line preset.
5. **Characters are logical containers** (rc3): several characters in one file, every element and preset carrying `identity`, likeness never crossing characters. Rejected: one file per character with cross-file references (files travel alone; a reference to another file breaks the first time the two are separated).

## Age, nudity, real persons

6. **Age is a property of the representation, never of the identity** (v0.5): a face, a body, a LoRA carry `age`; a preset's age is the lowest age of what it applies; there is no birth date. Rejected: `identities.<id>.age`. A character is 12 in one preset and 65 in another; a single age would have made the minor rules unenforceable.
7. **A preset under 18 shows nothing nude or intimate, ever** (rc1–rc3); nudity without genitals (`nudity: true`) is distinct from `intimate` (genitals, acts), the only place they may appear; an intimate variant lives in its own folder so that `cof extract --no-intimate` removes it in one cut. Rejected: a single "NSFW" flag (too coarse to let a host allow a bare back and refuse a sexual act).
8. **`allowSexualUsage` is an opt-in a host must ask for explicitly** (0.4.2 "locked" became "opt-in"; rc3 gates it on the *effective* permission): even when true, intimate content is never loaded by default. Rejected: "true means allowed". The flag says what the author permits; the host still has to want it.
9. **A real person without consent is a warning, never a refusal** (decided 14 October): personal use and satire of public figures remain possible within local law; two hard rules stay (minors; intimate content of a real person without consent scope `intimate`). Rejected: refusing every unconsented real person — it would have pushed users to lie about `fictional`. Consent is a record (`rights.consent`, scopes, proof), copied at the root for the default character only; in a cast each real person carries their own.
10. **Age units are compared in years** (`months` divided by 12; `unknown-adult` removed): 100 months once passed as an adult. Small, but the kind of bug a safety rule cannot afford.

## Readers and tools

11. **Readers of 1.x read every 1.y; a later minor adds only optional things; an unknown category is read as a library with a warning** (rc1, then cof-cli 1.0.1 after the first 1.1 file was refused by 1.0.0). Rejected: strict schemas with `additionalProperties: false`. The cost of strictness is a format that cannot grow without breaking its own tools, which the 1.1 work demonstrated within a day.
12. **Unknown categories are written back unchanged by the builder** (0.11.8): a round-trip must never lose what a tool does not understand.
13. **Text is data, not instructions**: card text, memories and skills from an untrusted file are user content; executable content (`files` skills with scripts) must be declared (`container.executableContent`, rc2) and is never run without the user's approval. Rejected: running skills on import because "the author packaged them".
14. **One reference implementation, one explorer, one builder, one set of ComfyUI nodes, all reading the same manifest with the same rules** — and a coherence pass at every change (the `cof-coherence` discipline). Rejected: letting each tool interpret the spec. Every divergence found in testing (an explorer nesting rule, a purge that did less than the CLI) became a shared rule.
15. **Completeness is a weighted score of eight layers, computed, never declared** (v0.4): `identity` 10 %, `personality` 20 %, `appearance` 20 %, `physique` 5 %, `voice` 15 %, `volume` 10 %, `motion` 5 %, `rights` 15 %; memories do not enter it. Rejected: an author-declared "quality" — it would mean nothing across files.

## 1.1 — memories (RFC 0002)

16. **Memories are nodes of a category, not a `MEMORY.md`** (23 October): a `moment` or a `period`, with a node file (gist per language, when, where, who, feelings, fidelity, links) and the manifest variant carrying what tools read without opening the file (`media`, `age`, `nudity`, `identity`). Rejected: the host's memory file alone (opaque, non-portable; it stays as `files/kind: memory`). Nodes select, link and purge; prose does not.
17. **Short texts are language maps, long texts are variants per language** (decision 4): a gist is `{"fr": …, "en": …}`; a personality is one variant per language. Rejected: a node per language (duplicated media and links).
18. **Links are typed, qualified (`<category>/<id>`), stored in one direction; membership of a moment in a period is computed from dates, and an explicit link (`part-of`, `after`) wins** (decisions 5 and 44, after a real contradiction in the example: a moment `after` a period whose ages touched it). Rejected: a `moments[]` list on the period (two places to keep in step).
19. **Three axes per node — `origin` (authored / lived), `visibility` (canon / personal), `disclosure` (open / guarded / secret)** — with defaults written explicitly. Rejected: `private` for user data (it sounded like "intimate"); `personal` is the GDPR word. The canon is read-only for tools; use-time change is a new `lived` node.
20. **Fidelity is four words, never a knob to fix a rendering** (`vivid | clear | faded | fragment`, with `as_remembered` on a media that already looks like the memory). Rejected: a 0–1 blur factor — authors would have tuned it for looks.
21. **An explicit memory carries the 1.0 flag `nudity: true` and the file its `tags.content`**, so that 1.0 purges and readers do the right thing without knowing 1.1. Rejected: a 1.1-only flag (invisible to the installed base).
22. **Shared media, not shared memories** (`media_from`): each character keeps its own node (its subjectivity); only files are shared, and a real person's likeness never travels to another character's extract.
23. **Two purges, independent**: `--all-audiences` (intimate and nude variants out, media of explicit nodes out, gists kept) and personal nodes dropped by default (`--keep-personal`). The builder does at build exactly what the CLI does to a file (decision 43: a purge that did less in one tool than in the other was a bug).

## 1.1 — cast fields (RFC 0003)

24. **Gender on the identity, overridable per preset through one `identity_override` object** (24–25 October), with `given_name` / `family_name` / `nicknames` while `name` and `nickname` stay for 1.0 readers. Rejected: one override field per attribute; overriding morphology, fictional, consent, rights, language or relations (another body or person is another character; language is the preset's personality; relations are canon of the cast; content flags rise by themselves). Pronouns left out (derivable; a field can come when a host asks).
25. **Archetype (Mark & Pearson's twelve, or free) and narrative role are two fields, in `psyche.json`**: a Creator can be the antagonist; a super-power is neither. Rejected: a single "archetype" mixing pattern, role and ability (the confusion other tools show).
26. **Relations live on the identity, stored once, inverses computed**: canon of the cast, identical in every preset. Rejected: per-preset relations (mirrored on the other character's presets, breaking the computed inverses).
27. **Default prompts (`scene`, `greeting`) are per preset and not inherited**: a scene fits one presentation (Clara at 12 does not sit at her desk).
28. **The container describes itself** (`COF.md`, never normative) **and has a write path** (`cof memory add`): a file that explains how to add to it is only useful if adding is one command.

## Still open (see the RFCs' "open questions")

A reference date of the canon; languages spoken; relations in time (`until`); the psyche graph (RFC 0004, 1.2); a 3D viewer in the explorer; autosave and history in the builder.
