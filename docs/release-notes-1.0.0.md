# COF 1.0.0 — release notes (17 October 2026)

**Complete AI characters in one open file — portable, with their rights.**

▶ [Explore a .cof](https://yannsouetre.github.io/cof/viewer/) · [Build one](https://yannsouetre.github.io/cof/builder/) · [ComfyUI nodes](https://github.com/yannsouetre/ComfyUI-COF) · [38-second clip](https://yannsouetre.github.io/cof/#clip)

COF (Character Open File) is an open file format for AI characters: a `.cof` is a ZIP container that bundles everything that defines a character — personality, appearance, voice, 3D body, poses and motion, agent skills and memories — together with its **rights, consent and provenance**. Version 1.0 freezes the structure: files written today stay readable by every 1.x tool.

## What is in 1.0

- **One container, seven media categories.** Personality (a Character Card V3 inside, psyche, free text), appearance (photos, character sheets, codes for hair and body), identity weights (LoRA, embeddings, pre-encoded references such as MiniMax H3 RefMods), 3D (VRM, GLB, splats, Daz archives), voice (samples, profile, engine artifacts), postures and motion, plus a `files` library for agent skills and memories.
- **Elements → variants → presets.** A preset is a ready-to-use combination ("Clara, 29, stage outfit, English voice"). It **applies** a default look and **offers** compatible alternatives (other outfits, accessories) that a richer reader can swap in. Tags organise presets on facets (language, age, style), and switching one facet keeps the others (`en-12` → `fr-12`).
- **Several characters per file**, each a logical container with its own elements, presets, default preset and rights. Only neutral elements (places, clothes, poses, skills) may share a file between characters; a face or a voice never does.
- **Rights travel with the character.** VRM-style permissions extended for AI (voice cloning, training, impersonation, AI disclosure), per character and per preset; a consent record when a real person is depicted (a missing consent is a visible warning; intimate or nude content of a real person is refused without it); provenance and synthetic-content labelling per asset.
- **Age is a property of the representation, checked per preset.** A file can hold an adult preset and a childhood preset; intimate content is opt-in, isolated in its own files, never loaded by default, and impossible in any preset that touches a representation under 18. Before the freeze, a blind review by another model tried to get around these rules; every way around them it found is closed and covered by the negative test corpus. Nudity without genitals is a separate, declared flag (`nudity: true`), never under 18.
- **Safe by construction.** No executable content unless declared, no pickles (also inside archives), `.safetensors` headers checked, ZIP paths restricted, nothing encrypted or hidden.
- **Embrace, don't replace.** A `.cof` contains a valid Character Card V3 and exports to a `ccv3` PNG card, `SOUL.md` / `IDENTITY.md` and an agent workspace.

## Tools

- **Explorer** (browser, read-only): <https://yannsouetre.github.io/cof/viewer/> — opens any `.cof`: characters, presets by facet (language, age, style) with one-click switching, looks, voices, poses, skills, a rights summary and the full rights; light and dark themes.
- **Builder** (browser, nothing leaves your machine except the optional AI check you configure): <https://yannsouetre.github.io/cof/builder/> — six interface languages, simple and advanced modes, a short built-in guide for the advanced mode, guided deletion, character selector, preset import with rights check, a window that recommends recording consent for a real person.
- **ComfyUI nodes** ([ComfyUI-COF](https://github.com/yannsouetre/ComfyUI-COF), MIT): load a preset — primary image, reference views, prompt, LoRA, pre-encoded references, voice, persona text, poses, motion clips and 3D files — with the preset and character as dropdowns, and the file's rights and age rules enforced.
- **`cof-cli` 1.0.0** (Python, MIT, `pip install cof-cli`): `validate`, `pack`, `unpack`, `info`, `import` (PNG / JSON cards), `export` (png, card, soul, agent), `merge`, `extract` (a preset, a character, a tag slice, `--no-intimate`), `migrate`.
- **`cof-author` skill**: lets a coding agent create and update `.cof` files (in blind tests, Codex and Google Antigravity added presets with the skill alone and produced valid files).

## For implementers

- Specification: `spec/SPEC.md` (English) and `spec/SPEC.fr.md` (French), JSON Schemas (draft 2020-12) in `spec/schemas/`, published at `https://yannsouetre.github.io/cof/schemas/1.0/`.
- `docs/IMPLEMENTING.md`: reader algorithm, simple and advanced reader profiles, per-category mappings.
- Test vectors: 9 conformant examples in `spec/examples/` and 46 negative files in `tests/invalid/` (one rule violated per file, with the rule and the spec section).
- Compatibility promise: 1.x versions only add optional fields and enumeration values; a 1.0 validator warns on what it does not know and never refuses a later 1.x file for it.

## Known limits of 1.0

- No third-party integration yet; a SillyTavern extension and a public gallery are the next steps.
- JSON sub-files carry no hash (ZIP CRC only); an optional hash index is planned for 1.1.
- `.rar` and `.7z` archives are not inspected by the validator (warning); prefer `.zip`.
- Some consent scopes are warnings rather than errors in 1.0 (see the changelog).
- `.charx` export and the `skeletons-1.0` mapping vocabulary are planned for 1.1.
- Planned later (2027): **certification** of `.cof` files by an independent third party — a signature over the manifest's hash (which covers every asset), so that a certified file cannot be modified without breaking it, with a public revocation list.

## Cite

See `CITATION.cff`; each release is archived with a DOI on Zenodo.

## Licences

Code MIT; specification, documentation and examples CC BY 4.0; schemas and vocabularies CC0.

Full history: `CHANGELOG.md`. Feedback: GitHub issues — format changes go through a public RFC (14 days).
