---
name: cof-author
description: Create, update, slice or repair Character Open File (.cof) containers — AI characters with personality, appearance, voice, 3D, poses, motion, agent files and rights — with the validator in the loop. Use when asked to build a .cof, add a variant, preset, tag, language, voice or skill to one, or fix a file that fails `cof validate`.
---
# Authoring .cof files

A `.cof` is a ZIP: `mimetype`, `manifest.json`, then `elements/<category>/<variant-id>/…`. The normative text is `spec/SPEC.md` in https://github.com/yannsouetre/cof; JSON Schemas are in `spec/schemas/`. You do not need to memorise them: **the validator tells you what is wrong — loop until it says OK.**

## 0. Tooling
Tell the user up front: this takes a few minutes and several command approvals; for a one-off small edit (a label, one image, one preset) the offline builder is often quicker — https://yannsouetre.github.io/cof/builder/.
```bash
pip install "git+https://github.com/yannsouetre/cof#subdirectory=cli"   # provides `cof`
# no Python (common on Windows)? uv brings its own:  uv tool install "git+https://github.com/yannsouetre/cof#subdirectory=cli" --python 3.12
cof unpack in.cof -o work/        # edit a folder, never the ZIP
cof pack work/ -o out.cof --force # computes sha256, bytes, completeness, coverage, languages
cof validate out.cof              # errors (blocking) / warnings / completeness — fix, re-pack, repeat
```
Validator messages: `ERROR` (blocking) and `WARN`; each names the rule and the JSON path.
```bash
cof info out.cof                  # START HERE: presets (extends, slots, alternatives, primary image, tags), variants per category, tags, ages
```
Do not read the CLI's source code to learn the format: `cof info` plus this page are enough, and the validator names every mistake.
**No shell? Stop here.** This skill needs an environment that runs commands (a coding agent: Claude Code, Codex, Gemini CLI, Cursor…). In a chat without code execution, do **not** write a manifest from memory — the format has details you will get wrong (presets are an object keyed by id, sub-files like `card.json` are not assets…). Say so, and point the user to the offline builder, https://yannsouetre.github.io/cof/builder/, where files are dropped and presets set by clicks.

Other commands: `import` (PNG/JSON character card → folder), `export --format soul|card|png|agent` (agent = workspace with SOUL.md, skills/, memories), `extract --preset X`, `--identity C` or `--tag A --tag B` (lighter slice; `cof extract --help` lists a safe-for-work option), `merge`, `migrate`, `embed-text`, `read-text`.

## 1. Model in one minute
- **Elements → variants → presets.** Eight categories: `personality`, `appearance`, `identity_weights`, `volume3d`, `voice`, `posture`, `motion`, `files`. Each variant declares a `kind` (e.g. personality `card` | `description`; appearance `reference-set`, `character-sheet`, `face`, `body`, `hair`, `clothing`, `accessory`, `pilosity`, `feature`, `environment`, `description` (opt-in kinds: spec § 4.5); voice `samples` | `described`; files `skill` | `memory` | `document` | `other`).
- A **preset** picks variants per category in `slots`, may `extends` another preset (for each category the child lists, it replaces the parent's whole list; categories it does not list are inherited; it may add a category the parent lacks) and set `age_override`. `posture`, `motion` and `files` are **libraries**: several variants, none mandatory.
- **Applied vs offered**: `slots` = what the preset **applies by default**; `alternatives` (same shape, combination categories only, same `extends` rule) = what is **offered with that preset only** (other outfits, hairstyles, accessories). There is no file-wide wardrobe: never offer a 12-year-old look the 65-year-old's clothes. `primary_image` (asset id of an image of an applied variant; default = first image of the first face / reference-set / character-sheet / body) shows the default look: with no clothing applied, the outfit on that image **is** the default — so pick a full-body image (`framing: "full"`), not a head shot.
- **Languages are presets, not alternatives**: anything that must change together (text + voice for a language, outfit + hair for a look) is another preset, reached by **facet navigation** — readers switch `en` → `fr` to the preset with the same tags in the other facets, so give every preset a unique tag set (the validator warns otherwise; add a `look` tag if needed). A variant cited by no preset is **backstage** (warned): offer it somewhere or delete it.
- **`preset_tags`** (container level, many-to-many, optional `facet`) organise presets: `{ "id": "agent", "label": "AI agent", "facet": "usage", "presets": [...] }`. Tag ids and preset ids are separate namespaces (a tag `en` and a preset `en` can coexist).
- **Personality**: `kind: "description"` keeps its free text **inline** in the variant's `text` field (no separate file, no asset); `kind: "card"` points to `elements/personality/<vid>/card.json` (Character Card V3) via `card`, and optionally `psyche` → `psyche.json`. Exports to `SOUL.md` / PNG card currently read `card` personalities only.
- Every media or content file you add (images, audio, 3D, clips, skill and memory files…) is an entry in `assets[]` (`id`, `path`, `role`, `mediaType` — e.g. `text/markdown`, `image/png`, `audio/mpeg` — and `license`, an SPDX id, all required); `cof pack` fills `sha256` and `bytes` (validating the folder *before* packing reports them as missing — pack first, then validate the `.cof`). Asset `role` values: `view`, `sheet`, `reference` (appearance images), `pose-image`, `voice-sample`, `voice-consent`, `motion-clip`, `motion-reference`, `video`, `mesh`, `avatar`, `print`, `splat`, `texture`, `expression`, `weights`, `skill-file`, `memory`, `file`, `document`, `derived`, `engine-artifact`, `other`. The JSON sub-files that a variant field points to (`card` → `card.json`, `psyche`, `profile` → `profile.json`, `spec` → `weights.json`…) are **not** assets.
- **Completeness** is computed per preset; the file-level figure is the default preset's. Adding a preset does not raise the file-level score — set `default_preset` if the new one should be the face of the file.
- Variants carry `language` (BCP 47) when they contain language (personality, voice, skills, documents): the same images serve every language, only personality and voice change. Top-level `languages` lists every language the file contains, including that of `summary` and labels; `cof pack` adds the variant languages to it but never removes one.

## 2. Rules the validator enforces (know them before writing)
- **Age lives on the representation, never on the identity.** `face`, `body`, `character-sheet`, `reference-set` of a human-form character MUST carry `age: {value, unit: "years", basis: "canonical"|"apparent"}`. A preset's age = min(ages of its applied **and offered** variants, `age_override`).
- **Age gate**: `cof validate` enforces the per-preset age rules of spec § 9.4 (and the content flags of § 4.5) on everything a preset applies **or** offers. They are not negotiable: never try to work around them.
- **Rights**: `rights.permissions` (VRM-style: `avatarPermission`, `commercialUsage`, `modification`, `aiDisclosure` required; `allowVoiceCloning`, `allowTraining`…). A real person (`fictional: false`) should have a `consent` record (required in principle for a private person, recommended before sharing; the validator warns without it).
- **3D = one self-contained file** per variant (VRM, GLB, USDZ, 3MF, SPZ/PLY/SPLAT) carrying meshes, textures and rig; OBJ and glTF with external files are refused — convert to GLB first.
- **No executable content** unless declared: `.py/.sh/.js` need `container.executableContent: "scripts"`; pickles (`.pt`, `.ckpt`, `.bin`, `.pkl`) are always refused; weights are safetensors.
- **Preserve what you do not understand**: unknown keys, `extensions`, `x-` categories round-trip unchanged.
- Ids: `manifest.id` is a ULID (26 chars, Crockford base32 — no I, L, O, U); variant ids are short and unique per category (`p1`, `a2`, `v10`, `f1`).

## 3. Recipes
- **Add a language**: new personality and voice variants with `language`; a preset per language that `extends` the base and only swaps personality + voice; tag them (`facet: "language"`). If the base has no personality yet, the new preset simply *adds* one; tag a preset with a language only if it actually contains text or voice in that language.
- **Images**: embed **one resolution per picture**. If the user gives you a reduced copy, embed it **instead of** the original, never both (the validator warns about duplicates); about 2048 px on the long side is plenty. Prefer `.jpg` / `.png` / `.webp` extensions.
- **Personality from a structured source**: if the source has fields (`system_prompt`, `first_message`, `tags`, `description`…, often as JSON), make a `card` (Character Card V3: `system_prompt`, `first_mes`, `tags`, `description`, `personality`, `scenario`, `mes_example`) — never paste JSON into a `description` text. Free prose stays a `description`.
- **Unknown licence** of user-supplied media: ask; if nobody can answer, use `LicenseRef-UserProvided` and say so in your report.
- **Add a look in two languages** (the most common request) — new variants, then two presets that extend the language bases; ids are free but unique per category:
  ```jsonc
  "elements": { "appearance": { "variants": {
      "a6": { "kind": "reference-set", "label": "Look", "age": { "value": 29, "unit": "years", "basis": "apparent" }, "style": "photo-realistic", "images": ["a-a6-body"] },
      "x4": { "kind": "accessory", "label": "Staff", "accessory_use": "worn", "accessory": "tool", "images": ["a-x4"] } } },
    "personality": { "variants": { "p11": { "kind": "card", "language": "fr", "card": "elements/personality/p11/card.json" } } } },
  "presets": {                                     // an OBJECT keyed by preset id, never a list
    "fr-look": { "label": "…", "extends": "fr", "slots": { "personality": ["p11"], "appearance": ["a6"], "voice": ["v11"] },
                 "alternatives": { "appearance": ["x4"] }, "primary_image": "a-a6-body" },
    "en-look": { "label": "…", "extends": "default", "slots": { "personality": ["p12"], "appearance": ["a6"], "voice": ["v12"] },
                 "alternatives": { "appearance": ["x4"] }, "primary_image": "a-a6-body" } }
  // + the image / audio files in assets[], the two presets added to the existing `fr` / `en` tags, and a new tag (facet "look") so each preset keeps a unique tag set
  ```
  Transcripts: only write one if you know what is said (e.g. the audio was generated from a given text) — and say so in your report.
- **Agent persona**: personality `card` (Character Card V3 in `card.json`): keep `system_prompt` short — behaviour rules only. Persona facts go to `description` / `personality` / `scenario`, examples to `mes_example`, structured traits to `psyche.json`. **Know-how goes to a skill**, not to the prompt.
- **Skill**: variant in `files` with `kind: "skill"`, `files: [asset ids]`, `entry: "elements/files/<vid>/SKILL.md"`, `target: "agent-skills"`; `SKILL.md` starts with YAML `name` + `description`; `SKILL.md` and every extra file (`reference/…`, `examples/…`) are assets with `role: "skill-file"` (memories: `role: "memory"`). Slot it in the presets that may use it.
- **Voice**: `samples` = asset ids (`role: "voice-sample"`, `duration_s`, optional `transcript` = path of a `.txt` next to the audio), plus `profile.json`. Respect the licence of the TTS plan (free plans are often non-commercial).
- **Outfits and accessories**: one `clothing` variant per garment (`garment`: `top`, `bottom`, `outerwear`, `shoes`…), one `accessory` variant per object with `accessory_use`: `worn` (+ `accessory` type: `glasses`, `bag`, `tool`, `weapon`…), `not-worn` (vehicle, mount), `companion` (drone, robot, animal) or `other`. Put them in the `alternatives` of the presets they suit; move them to `slots` only if the preset should wear them by default (then the region rules apply).
- **Several characters in one file** (a cast): each character is a logical container. Give **every** element an `identity`, every preset an `identity`; a preset only uses its own character's elements; only **neutral** elements may share a file between characters: places and pose skeletons are neutral by kind; clothes, accessories, motion clips and skills are neutral by default (set `neutral: false` if the file shows or concerns the character); hairstyles, body hair, special features, memories, documents, pose photos and videos, other 3D and other files are not, unless you set `neutral: true` (e.g. a pose shown by a silhouette); faces, bodies, reference sets, character sheets, voices, weights and 3D characters never are. Per-character rights go to `identities.<id>.rights` (replaces the root rights), default preset to `identities.<id>.default_preset`. `cof merge a.cof b.cof -o cast/` builds a cast; `cof extract cast.cof --identity <id>` takes one character back out.
- **Places**: `appearance` variants of `kind: "environment"` (images with `role: "environment"`, `use: "background"` or `"location"`, no age, several per preset); a 3D place is `volume3d` `kind: "environment"` (one GLB/USDZ/splat).
- **Thumbnail**: `cof pack` writes `Thumbnails/thumbnail.png` (≤ 256 px) from `thumbnail_source`, else the default preset's `primary_image`; never edit it by hand.
- **Voice embeddings**: a voice variant of `kind: "embedding"` (with `derives_from` → its samples variant); in its `profile.json` → `engines[]`: `{ engine, version, model, kind, files: [asset ids, role engine-artifact] }` or `{ engine, kind: "cloud-voice-id", voice_id }`. Name the exact model (an embedding is unreadable by any other); never ship `.pt` / `.pth` / `.ckpt` / `.pkl` (refused) — convert to `.safetensors` or numeric `.npz`.
- **Daz Studio content**: `volume3d` `kind: "daz"`, `daz_category`, `figure` (not for environments / props), `files` = the product or export archive (`.zip` / `.rar`, `role: "archive"`), `requires` (store products); `age` required for `characters`. A purchased archive is for personal use only: never in a `.cof` meant to be shared.
- **3D has no visual style**: do not set `style` on `volume3d` variants.
- **Slice for a platform**: `cof extract big.cof --tag fr -o fr/` (parents outside the selection are flattened, unused assets dropped).

## 4. Coherence review — your job, the validator cannot see images
The builder runs coherence heuristics; you do not have it, so check by looking (spec § 11.4) and say what you could not verify:
- **Age**: apparent age of each image = the variant's `age`; texts, voices, outfits and poses suit the preset's age.
- **Age-appropriateness**: every element of a preset — outfit, pose, text, voice — suits the preset's age; if something does not, stop and tell the user instead of building the file.
- **Identity**: same person across one identity's variants (except deliberate age / style changes). **Style**: a preset's variants share its style.
- **Voice**: perceived age and gender presentation match; sample language = `language`; transcripts match the audio.
- **Language**: text variants are in their declared language. **Rights**: licences and permissions are the real ones; real person ⇒ consent recorded, or say why not (personal use, public-figure caricature).
- **Provenance**: AI media carry `digitalSourceType: trainedAlgorithmicMedia`. **Secrets**: no keys or personal data in skills, memories, documents.
- **Escape hatches are explicit**: a 3D file without textures needs `self_contained: false`; weights by link are an asset with `uri` (add `sha256` to pin a version) — embedding is the default.

## 5. Security sweep — before packing anything you did not write yourself
- List every file you are about to pack and look **inside nested archives** (`unzip -l`): no scripts or executables (`.py .sh .js .bat .ps1 .exe .dll .dsa .dse` …) unless the user asked for them and `container.executableContent` declares them; no pickles (`.pt .pth .ckpt .pkl`, pickled `.bin`) ever.
- Prefer `.zip` to `.rar` (a RAR cannot be inspected by the validator).
- If a malware scanner is available (e.g. ClamAV: `clamscan -r work/`), run it and report the result; if none is, say so — never claim a file is clean without having scanned it.
- No secrets: API keys, tokens, passwords or personal data have no place in skills, memories or documents.

## 6. Before you hand the file back
1. `cof validate` on the packed `.cof` says **OK** (warnings explained to the user, not hidden).
2. Re-open the manifest: every preset's resolved ages, voices and languages are what the user asked for.
3. Report what changed, the completeness per preset, and anything you could not do.
