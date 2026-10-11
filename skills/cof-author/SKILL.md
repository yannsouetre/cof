---
name: cof-author
description: Create, update, slice or repair Character Open File (.cof) containers — AI characters with personality, appearance, voice, 3D, poses, motion, agent files and rights — with the validator in the loop. Use when asked to build a .cof, add a variant, preset, tag, language, voice or skill to one, or fix a file that fails `cof validate`.
---
# Authoring .cof files

A `.cof` is a ZIP: `mimetype`, `manifest.json`, then `elements/<category>/<variant-id>/…`. The normative text is `spec/SPEC.md` in https://github.com/yannsouetre/cof; JSON Schemas are in `spec/schemas/`. You do not need to memorise them: **the validator tells you what is wrong — loop until it says OK.**

## 0. Tooling
```bash
pip install "git+https://github.com/yannsouetre/cof#subdirectory=cli"   # provides `cof`
cof unpack in.cof -o work/        # edit a folder, never the ZIP
cof pack work/ -o out.cof --force # computes sha256, bytes, completeness, coverage, languages
cof validate out.cof              # errors (blocking) / warnings / completeness — fix, re-pack, repeat
```
Validator messages are in French for now (`ERREUR` = error, `AVERT.` = warning); each names the rule and the JSON path.
```bash
cof info out.cof                  # presets, ages, tokens
```
Other commands: `import` (PNG/JSON character card → folder), `export --format soul|card|png`, `extract --preset X` or `--tag A --tag B` (lighter slice), `merge`, `migrate`, `embed-text`, `read-text`.

## 1. Model in one minute
- **Elements → variants → presets.** Eight categories: `personality`, `appearance`, `identity_weights`, `volume3d`, `voice`, `posture`, `motion`, `files`. Each variant declares a `kind` (e.g. personality `card` | `description`; appearance `reference-set`, `character-sheet`, `face`, `body`, `hair`, `clothing`, `accessory`, `intimate`, `pilosity`, `feature`, `environment`, `description`; voice `samples` | `described`; files `skill` | `memory` | `document` | `other`).
- A **preset** picks variants per category in `slots`, may `extends` another preset (for each category the child lists, it replaces the parent's whole list; categories it does not list are inherited; it may add a category the parent lacks) and set `age_override`. `posture`, `motion` and `files` are **libraries**: several variants, none mandatory.
- **`preset_tags`** (container level, many-to-many, optional `facet`) organise presets: `{ "id": "agent", "label": "AI agent", "facet": "usage", "presets": [...] }`. Tag ids and preset ids are separate namespaces (a tag `en` and a preset `en` can coexist).
- **Personality**: `kind: "description"` keeps its free text **inline** in the variant's `text` field (no separate file, no asset); `kind: "card"` points to `elements/personality/<vid>/card.json` (Character Card V3) via `card`, and optionally `psyche` → `psyche.json`. Exports to `SOUL.md` / PNG card currently read `card` personalities only.
- Every file except `mimetype` and `manifest.json` is an entry in `assets[]` (`id`, `path`, `role`, `mediaType` — e.g. `text/markdown`, `image/png`, `audio/mpeg` — and `license`, an SPDX id, all required); `cof pack` fills `sha256` and `bytes` (validating the folder *before* packing reports them as missing — pack first, then validate the `.cof`). Asset `role` values: `view`, `sheet`, `reference` (appearance images), `pose-image`, `voice-sample`, `voice-consent`, `motion-clip`, `motion-reference`, `video`, `mesh`, `avatar`, `print`, `splat`, `texture`, `expression`, `weights`, `skill-file`, `memory`, `file`, `document`, `derived`, `engine-artifact`, `other`.
- **Completeness** is computed per preset; the file-level figure is the default preset's. Adding a preset does not raise the file-level score — set `default_preset` if the new one should be the face of the file.
- Variants carry `language` (BCP 47) when they contain language (personality, voice, skills, documents): the same images serve every language, only personality and voice change. Top-level `languages` lists every language the file contains, including that of `summary` and labels; `cof pack` adds the variant languages to it but never removes one.

## 2. Rules the validator enforces (know them before writing)
- **Age lives on the representation, never on the identity.** `face`, `body`, `character-sheet`, `reference-set` of a human-form character MUST carry `age: {value, unit: "years", basis: "canonical"|"apparent"}`. A preset's age = min(variant ages, `age_override`).
- **Minors**: a preset under 18 MUST NOT contain `intimate`, estimated body measurements or an effective `allowSexualUsage`. `intimate` variants require age ≥ 18 and `tags.content` containing `nudity` or `sexual`. Never try to work around these rules.
- **Rights**: `rights.permissions` (VRM-style: `avatarPermission`, `commercialUsage`, `modification`, `aiDisclosure` required; `allowVoiceCloning`, `allowTraining`…). A real person (`fictional: false`) requires `consent`.
- **3D = one self-contained file** per variant (VRM, GLB, USDZ, 3MF, SPZ/PLY/SPLAT) carrying meshes, textures and rig; OBJ and glTF with external files are refused — convert to GLB first.
- **No executable content** unless declared: `.py/.sh/.js` need `container.executableContent: "scripts"`; pickles (`.pt`, `.ckpt`, `.bin`, `.pkl`) are always refused; weights are safetensors.
- **Preserve what you do not understand**: unknown keys, `extensions`, `x-` categories round-trip unchanged.
- Ids: `manifest.id` is a ULID (26 chars, Crockford base32 — no I, L, O, U); variant ids are short and unique per category (`p1`, `a2`, `v10`, `f1`).

## 3. Recipes
- **Add a language**: new personality and voice variants with `language`; a preset per language that `extends` the base and only swaps personality + voice; tag them (`facet: "language"`). If the base has no personality yet, the new preset simply *adds* one; tag a preset with a language only if it actually contains text or voice in that language.
- **Agent persona**: personality `card` (Character Card V3 in `card.json`): keep `system_prompt` short — behaviour rules only. Persona facts go to `description` / `personality` / `scenario`, examples to `mes_example`, structured traits to `psyche.json`. **Know-how goes to a skill**, not to the prompt.
- **Skill**: variant in `files` with `kind: "skill"`, `files: [asset ids]`, `entry: "elements/files/<vid>/SKILL.md"`, `target: "agent-skills"`; `SKILL.md` starts with YAML `name` + `description`; `SKILL.md` and every extra file (`reference/…`, `examples/…`) are assets with `role: "skill-file"` (memories: `role: "memory"`). Slot it in the presets that may use it.
- **Voice**: `samples` = asset ids (`role: "voice-sample"`, `duration_s`, optional `transcript` = path of a `.txt` next to the audio), plus `profile.json`. Respect the licence of the TTS plan (free plans are often non-commercial).
- **Places**: `appearance` variants of `kind: "environment"` (images with `role: "environment"`, `use: "background"` or `"location"`, no age, several per preset); a 3D place is `volume3d` `kind: "environment"` (one GLB/USDZ/splat).
- **Thumbnail**: `cof pack` writes `Thumbnails/thumbnail.png` (≤ 256 px) from the default preset's best view; never edit it by hand.
- **Slice for a platform**: `cof extract big.cof --tag fr -o fr/` (parents outside the selection are flattened, unused assets dropped).

## 4. Before you hand the file back
1. `cof validate` on the packed `.cof` says **OK** (warnings explained to the user, not hidden).
2. Re-open the manifest: every preset's resolved ages, voices and languages are what the user asked for.
3. Report what changed, the completeness per preset, and anything you could not do.
