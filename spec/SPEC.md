# COF — Character Open File
## Specification 1.0 (release candidate, October 12, 2026 — structure frozen October 14, release October 17)

> Normative text. A French translation is available in [SPEC.fr.md](SPEC.fr.md).

> **Status**: author's draft, public RFC on GitHub (`rfcs/`).
> **License**: specification CC-BY-4.0; reference implementation MIT; vocabularies and schemas CC0.
> **Author**: Yann Souetre.
> **Name**: *COF — Character Open File*, extension `.cof`, MIME type `application/vnd.cof.character+zip`.
> **1.0**: first stable version. The structure is frozen; 1.x versions only add optional fields, and every 1.0 reader keeps working with them. JSON Schemas are published at `https://yannsouetre.github.io/cof/schemas/1.0/`; a negative conformance corpus ships in `tests/invalid/`.
>
> **v0.5**: **age leaves the identity** and becomes a property of the **representation** (morphological variants, per-preset floor); protection rules **per preset**: no `intimate` (itself required to be ≥ 18) may be combined with an element under 18 — a single file may therefore contain an adult preset with intimate content and a minor preset without; AI "age-legality" check.
> **v0.4**: elements organized into **7 categories by media type**, each variant declaring its **type** (`kind`); presets with **multiple slots** and stacking rules by **body region** (clothing, accessories, body/facial hair, special features, LoRA); **multiple identities** in one file with attached presets; languages carried by variants; merging and extraction of presets; capped motion videos.
> v0.3: modular architecture, identity weights, meshes, styles, optional derived files, coherence, priorities.
> Choices are grounded in the state of the art (`docs/state-of-the-art.md`). Parts "to be invented" are marked **[NEW]**.

---

## 0. One-page overview

A `.cof` file is a **ZIP container** that gathers everything defining one or more synthetic characters, in a **modular** form:

```
.cof file
 ├─ Identity(ies)      (name, morphology; several identities possible = cast — age lives on variants)
 ├─ Elements, in 8 categories by media type:
 │    personality (text) · appearance (photos) · identity weights (LoRA) · 3D · voice · postures · motion · files
 │    └─ Variants, each with a TYPE: face f1, f2…; clothing "dress" o1, "boots" o2; voice v1 "deep"…
 ├─ Presets             (one identity + a combination of variants; one default preset)
 └─ Rights, provenance, KPIs (completeness, coherence)
```

| Layer | Content | Reused building block |
|---|---|---|
| Identity & manifest | who, which elements/presets, which assets, which rights | JSON Schema 2020-12, SPDX, IPTC, JSON-LD |
| Personality | personality, goals, fears, backstory, lore, typed traits | embedded **Character Card V3** + `psyche.json` |
| Appearance | face, hair, body/facial hair, body, outfits — as images, meshes, parameters, description | JPEG/PNG, glTF/FLAME/Anny, Fashionpedia, GarmentCode, Monk |
| Identity weights **[NEW]** | LoRA / embeddings tied to a base model | safetensors, Civitai/HF |
| Physical attitude | motion signature, OpenPose postures | LMA, BAP, BML, OpenPose |
| Voice | samples (optional transcript), typed profile, voice code | WAV, SSML, EmotionML, VPA |
| Volumetry | rigged avatar, splat, printable version | VRM 1.0 / glTF, SPZ, 3MF |
| Motion | clips, viseme mapping | BVH, VRMA |
| Derived **[NEW]** | optional post-processing (Canny/lineart/softedge… maps) | ControlNet preprocessors |
| Rights | permissions, consent, provenance, signature | extended `VRMC_vrm.meta`, C2PA |

Six principles:
1. **Encompass, do not replace** — embedded CCv3; exports to PNG `ccv3`, `.charx`, `SOUL.md`, `.vrm`.
2. **Everything is optional except identity and rights** (plus the bookkeeping that tools write: tags, provenance, one preset — Annex B); a "text-only", "appearance-only" or "voice-only" character is valid. Completeness is an indicator, not a constraint (§ 2.5).
3. **Modularity** — each element can have several variants; presets combine them; a default preset is loaded on opening (§ 2.3).
4. **One truth, many projections** — each piece of information is written only once; the others refer to it (§ 6.1).
5. **Readable by a human and by an LLM** — JSON + Markdown; every compact code also has a sentence form.
6. **No executable code, nothing encrypted, consent first.**

### 0.1 Target uses (`targets`)

| Target | What the tool reads first | Examples |
|---|---|---|
| `chat-text` | personality, lore, token profiles | SillyTavern, Risu, any LLM |
| `chat-voice` | + voice (samples, voice code) | Unmute, OpenAI Realtime, Hume |
| `video-realtime` | + face (images/mesh), visemes, attitude | HeyGen, Tavus, LiveKit + Audio2Face |
| `image-video-gen` | identity weights, images, derived files, prompts | Flux/SDXL + ControlNet, Kling, Veo, Runway, Sora |
| `game-3d` | rigged avatar, motion, visemes, rights → VRM `meta` | Unity, Unreal, Godot, VRChat, Blender |
| `agent-persona` | derived SOUL/IDENTITY, psyche, `aiDisclosure` | OpenClaw, OpenAI/Anthropic/xAI agents |
| `agent-runtime` | + `files`: skills (`SKILL.md`), memories (`MEMORY.md`), documents | OpenClaw, Hermes Agent, Claude, any Agent Skills host |
| `print-3d` | 3MF, license | slicers |
| `archive` | everything, hashes, C2PA, consent | repositories, registries, compliance |

### 0.2 Representation levels

| Level | Nature | Who produces it |
|---|---|---|
| **L2 — Media** | images (JPEG/PNG/WebP), audio, video, meshes, avatars, splats | the author |
| **L1 — Parametric** | FLAME/Anny, measurements, blendshapes, measured voice code, OpenPose keypoints | the builder from L2, or a tool |
| **L0 — Descriptive** | closed vocabularies + sentences | the author or the builder |
| **Derived** (outside the levels) | line maps, OpenPose stick figures, depth… **optional**, regenerable on the fly by any platform | the builder, on request |

A moderate-resolution JPEG is already a compact and complete representation; derived files exist only as ready-to-use *control images*, never as an imposed substitute (§ 4.8).

### 0.3 Morphological scope

No constraint on the nature of the character. `morphology.class` (REQUIRED) ∈ `human | humanoid | anthropomorphic-animal | quadruped | avian | aquatic | mechanical | amorphous | other`. Codes and detectors are designed primarily for anthropomorphic characters; elsewhere they apply "without guarantee" (warning, not error).

---

## 1. Physical container

### 1.1 Archive
- **ZIP**; zip64 accepted for reading.
- 1st entry: `mimetype`, stored uncompressed, = `application/vnd.cof.character+zip`.
- 2nd entry: `manifest.json`. Writers MUST put these two entries first, `mimetype` with no extra field in its local header (so that the media type sits at byte offset 38 for magic-number detection, zip64 included), so that a reader identifies the file and reads the manifest without reading further.
- Optional 3rd entry: `Thumbnails/thumbnail.png` (reserved path, ODF convention), a PNG of at most 256 px on its longest side, stored uncompressed, derived from the default preset's best view (asset `role: derived`, `method: thumbnail`) and referenced by `manifest.thumbnail`; the author MAY pick the source image with `manifest.thumbnail_source` (an asset id), otherwise it is the default preset's primary image (`primary_image`, § 2.3) — for an exported preset or tag, that of the exported slice. File-manager thumbnailers (Windows, macOS Quick Look, freedesktop) read this fixed path without parsing the manifest. Writers SHOULD include it; it is regenerated, never edited.
- ASCII paths `[A-Za-z0-9._/-]`, no `..`, no absolute paths, no symbolic links.
- High-entropy binaries stored uncompressed (`store`), JSON/text as `deflate`.
- Optional 64-byte alignment (`container.aligned`); encryption forbidden.

### 1.2 Normative tree (1.0)

```
mimetype
manifest.json                              ← identities, elements, presets, assets, rights (§ 2)
Thumbnails/thumbnail.png                   ← optional OS thumbnail, ≤ 256 px (§ 1.1)
elements/
  personality/<v>/   card.json  psyche.json  story.md  lorebook.json  SOUL.md  IDENTITY.md
  appearance/<v>/    images (head.front.jpg…), face.json / body.json / hair.json / outfit.json depending on the type
  identity_weights/<v>/  weights.json  [weights.safetensors]
  volume3d/<v>/      avatar.vrm | mesh.glb | face.glb | splat.spz | figurine.3mf | environment.glb  skeleton.json
  voice/<v>/         profile.json  voice.vec.json  samples/  engines/
  posture/<v>/       photos, pose.json (OpenPose), silhouette.png, attitude.json
  motion/<v>/        clips/ (BVH, VRMA)  videos/ (short, low resolution)  visemes.json
  files/<v>/         SKILL.md + resources | MEMORY.md | documents
derived/<cat>/<v>/   optional post-processing (§ 4.8)
sheets/              original character sheets + regions (§ 4.1)
rights/              consent proofs (assets)  licenses/  manifest.c2pa      — the consent record is inline: identities.<id>.consent (§ 9.2)
extensions/<vendor>/…
```
`<v>` = variant identifier (`f1`, `robe-rouge`, …), `[a-z0-9.-]`. Any unknown JSON key is preserved; `extensions/` is never purged.

### 1.3 Compatibility envelopes (exports)
PNG `chara`+`ccv3` (text + thumbnail), `.charx`, `SOUL.md`/`IDENTITY.md`, `.vrm`, OCI artifact (§ 10). Always computed from the **default preset** (or a chosen preset).

---

## 2. `manifest.json`

### 2.1 Identity(ies)

**Required** identity fields: `name`, `fictional`, `morphology` (`class` ∈ `human` | `humanoid` (human-shaped non-human: elf, android, alien) | `anthropomorphic-animal` | `quadruped` | `avian` | `aquatic` | `mechanical` | `amorphous` | `other`, + free-form `species`). Everything else (`nickname`, `summary`, tags) is optional. **The identity carries no age**: age is a property of the *representation* — the same character can be depicted at the different ages of their life (§ 2.2, `variant.age`), and a preset can set a floor (`age_override`, useful for presets without any morphological element, e.g. text only). A "mysterious" age is not a value: it is an **apparent** age (`basis: apparent`) on visual elements, and the absence of age on a purely textual preset. **Languages** are not a property of the identity: they are carried by personality variants (`language`) and by each voice sample; the root `languages` (catalogs, filters) MAY be declared by the author and tools **add** to it every language found on variants and samples (union; nothing is removed, so a text written in two languages without per-variant tags keeps both).

**Multiple identities** **[NEW]**: a file can describe a cast. `identities: { "<id>": { name, nickname, summary, fictional, morphology, consent } }` + `default_identity`. **Each character is a logical container**: its identity record, **its** elements, **its** presets, **its** default preset (`identities.<id>.default_preset`) and **its** rights. Every element belongs to one character (`variant.identity`, REQUIRED as soon as the file holds several characters; inherited through `derives_from`; otherwise the default character); every preset belongs to one character (`presets.<p>.identity`, inherited through `extends`, default = `default_identity`). A preset only applies or offers **its own character's** elements, a child preset only extends a preset of the same character, an element only derives from an element of the same character — all blocking errors. **Only neutral elements share files**: an element is *neutral* when it carries nothing of a particular character (no likeness, no voice, no personal content). A file used by elements of several characters MUST be used only by neutral elements — each character keeps its own element (label, use), and exporting a character copies every file it uses. Neutrality is fixed by kind, or chosen by the author (`neutral: true|false`) where the kind is ambiguous — see the table below; `neutral: false` is always allowed (stricter), `neutral: true` on a never-neutral kind is an error. Whoever wants Marc's face on Clara's body creates a third character with its own copies. **Rights per character**: `identities.<id>.rights` (`{ permissions }`) **replaces** the root `rights` for that character, without merging; characters without it use the root rights; `permissions_override` per preset applies on top. **Consent is per identity** (one real person = one identity). Tags (`preset_tags`) are container-level and may list presets of several characters, but facet navigation never leaves the current character. To keep simple readers simple, the **root carries a copy** of the default identity's fields (`name`, `nickname`, `summary`, `fictional`, `morphology`) — the validator checks that they are equal; the root `rights` are the default character's, unless `identities.<default>.rights` exists (they then MUST be equal). File merging (§ 11.3) treats two identities as the same if `name`, `nickname`, `fictional` and `morphology.class` are identical.

| Neutral (fixed by kind) | Chosen by the author (default) | Never neutral (fixed by kind) |
|---|---|---|
| appearance `environment`; volume3d `environment` and Daz content other than `characters`; posture `openpose`, `silhouette`, `attitude`; motion `attitude` | appearance `clothing`, `accessory` (yes — no when the image shows the character), `hair`, `pilosity`, `feature` (no — yes when the image shows only the hairstyle / the feature); posture `photo` / `photos` and motion `video` (no — yes for a pose shown by a silhouette or a mannequin); volume3d `other`, files `other` (no — unknown formats); files `skill` (yes), `memory`, `document` (no); motion `clips` (yes — no for a motion capture of a particular person, which is personal data: scope `motion-capture`) | personality; appearance `face`, `body`, `reference-set`, `character-sheet`, `intimate`; every `identity_weights` and `voice`; volume3d `mesh`, `face-mesh`, `point-cloud`, `print`, Daz `characters` |


```jsonc
{ "cof": "1.0", "id": "01J9…", "name": "Léa Marchand", "nickname": "Léa", "fictional": true,   // no age here: age is carried by the variants
  "morphology": { "class": "human", "species": "human" }, "summary": "…", "languages": ["fr", "en"],   // computed
  "identities": { "lea": { "name": "Léa Marchand", "nickname": "Léa", "fictional": true, "morphology": {…} },
                  "marc": { "name": "Marc", "fictional": true, "morphology": {…} } },
  "default_identity": "lea",
  "tags": {…}, "thumbnail": "elements/appearance/f1/head.front.jpg", … }
```

### 2.2 Elements: 8 categories, one type per variant

| Category | Nature | Variant types (`kind`) |
|---|---|---|
| `personality` | text | `card` (Character Card V3 + psyche, story, lore), `description` (free text) |
| `appearance` | photos | `reference-set` (loose photos, the AI works it out), `character-sheet` (several angles in one image), `face`, `body`, `hair`, `clothing` (+ `garment`), `accessory` (+ `accessory_use`: worn / not-worn / companion / other, and the `accessory` type when worn), `intimate`, `pilosity` (+ `area` face/body), `feature` (special features: horns, tail, prosthesis… + `region`), `environment` (backgrounds and places tied to the character + `use`: `background` for chat / video-avatar backgrounds, `location` for home, workplace…), `description` |
| `identity_weights` | weights | `lora`, `lycoris`, `dora`, `textual-inversion`, `ip-adapter-embedding`, `reference-latent` (pre-encoded reference, e.g. RefMods), `dreambooth`, `other` (+ `covers`) |
| `volume3d` | 3D | `mesh` (rigged avatar / complete mesh), `face-mesh`, `point-cloud` (splat), `print` (3MF), `other`, `environment` (a place, as one self-contained GLB, USDZ or splat), `daz` (Daz Studio DSON content, preferably **kept as the product or export archive** — `.zip` / `.rar`, `role: archive`, often hundreds of `.duf` / `.dsf` / texture files whose folder tree matters; loose files are accepted after a warning; `entry` = main `.duf` when loose; `daz_category` ∈ characters / wearables / hair / environments / props / poses-animations, `figure` e.g. Genesis 9, `requires[]` = the store products it depends on, not embedded; `age` REQUIRED for a human-form `characters` item; exempt from the self-contained rule because DSON references a content library by design; the standard Daz licence covers renders, not redistribution of store 3D files: a purchased archive is embedded for personal use only (backup, moving between one's machines) and that `.cof` is not shared — a shareable `.cof` embeds only one's own creations and lists the rest in `requires`; scripts inside archives (`.dsa`) are flagged by validators) — **every 3D variant is one self-contained file** carrying meshes, textures and rig (VRM, GLB, USDZ, 3MF, SPZ/PLY/SPLAT); OBJ and glTF with external resources are refused unless the variant declares `self_contained: false` (e.g. an untextured mesh used for posing; the builder asks first), FBX is discouraged |
| `voice` | audio | `samples` (samples, optional transcript), `described` (profile without audio), `embedding` (engine artifacts only — speaker embeddings, fine-tuned weights, cloud voice ids — in `profile.json` `engines[]`; `derives_from` links it to the samples it comes from) |
| `posture` | pose (**library**) | `photo` (one pose), `photos` (several views of the same pose), `openpose`, `silhouette`, `attitude` (motion signature), `description` — with `use: pose-only` (inference retains only the pose) |
| `motion` | motion (**library**) | `clips` (BVH / VRMA), `video` (very short, low resolution, 20 MB cap unless `max_bytes_ack`), `attitude`, `description` |
| `files` | free-form files (**library**) | `skill` (agent skill folder: `SKILL.md` + resources, `entry`), `memory` (`MEMORY.md`, dated notes…), `document` (knowledge, lore, rules), `other` (any type not anticipated by the format) — `files[]` (assets, roles `skill-file` / `memory` / `document` / `file`), `entry`, `target` (`agent-skills` \| `openclaw` \| `hermes` \| `claude` \| `custom`) |

Rules:
- Each variant declares `kind` (REQUIRED), `label`, `style` / `style_tags` (visual), `language` (text/voice), `derives_from` (field inheritance; the only "hierarchy"), `identity` (the character it belongs to — § 2.1), and its representations (`images[]`, `samples[]`, `clips[]`, `videos[]` = asset identifiers; `card`, `psyche`, `params`, `code`, `spec`, `profile`, `path`, `mesh`…).
- A `face` / `body` / `hair` / `clothing` / `accessory` / `pilosity` / `feature` variant describes **a single** coherent face / body / haircut / garment / accessory — for another one, create another variant. Subdivision is **possible, never mandatory**: with a single character sheet, filling in `character-sheet` is valid.
- Images are referenced by asset identifier and MAY be shared between variants — except that **an `intimate` variant's files are its own** (§ 4.5) and **one file never represents both a person under 18 and an adult** (a file used by two variants whose ages fall on both sides of 18 is an error).
- **`age` per variant** (`{ value, unit?: years|months, basis?: declared|apparent|canonical }` — `declared` = stated by the author or the person, `apparent` = how old the representation looks, `canonical` = the age in the character's own story; **every comparison is made in years**, `months` being divided by 12; an age whose `unit` a validator does not understand is an **unknown age**, which never counts as 18 or more) on everything related to morphology: `appearance` except `clothing` / `accessory` / `feature` / `environment` / `description`, `volume3d` (except `environment`), `identity_weights`. **Required** on `face`, `body`, `character-sheet`, `reference-set` when the identity's morphology is human-shaped (`human`, `humanoid`, `anthropomorphic-animal`) — a human-shaped body always has an apparent age, hence `basis: apparent` when the canonical age is unknown — and on `intimate` (**≥ 18**); optional on `hair`, `pilosity`, 3D, weights; not required for the `mechanical`, `amorphous`, etc. classes (a declared age is still honoured by every rule) — **except** in a preset that applies or offers an `intimate` element: there every `face`, `body`, `character-sheet`, `reference-set`, identity weight and 3D character MUST carry an age, whatever the class (§ 9.4). The **age of a preset** = the lowest of the ages of its resolved variants — applied and offered — and of its `age_override`; unknown if there is none.
- `character-sheet`: **a single character sheet per variant** by default; `allow_multiple_sheets: true` allows several, the author being responsible for ensuring the character's coherence across them. `reference-set`: several photos by design, with the same coherence requirement (the builder reminds the author).
- The same type of information can legitimately belong to **two categories**: `attitude` (LMA motion signature, habitual postures, gestures) is allowed in `posture` *and* in `motion`; a variant lives in one of the two, and readers look in both.

```jsonc
"elements": {
  "personality": { "variants": { "p1": { "kind": "card", "label": "Léa", "language": "fr", "card": "elements/personality/p1/card.json", "psyche": "…" },
                                 "p2": { "kind": "card", "label": "Léa in English", "language": "en", "derives_from": "p1", "card": "…" } } },
  "appearance":  { "variants": { "f1": { "kind": "face", "style": "photo-realistic", "images": ["a-f1-front", "a-f1-left"], "params": "…/face.json" },
                                 "b1": { "kind": "body", "images": ["a-b1-front"] },
                                 "h1": { "kind": "hair", "code": "…/hair.json" }, "h2": { "kind": "hair", "label": "Short blond" },
                                 "o1": { "kind": "clothing", "garment": "dress", "label": "Green dress", "images": [...] },
                                 "o2": { "kind": "clothing", "garment": "shoes", "label": "Boots" },
                                 "a1": { "kind": "accessory", "accessory": "glasses" },
                                 "pi1": { "kind": "pilosity", "area": "face", "label": "Three-day stubble" },
                                 "x1": { "kind": "feature", "region": "head", "label": "Horns", "images": [...] },
                                 "s1": { "kind": "character-sheet", "images": ["a-sheet-1"] } } },
  "identity_weights": { "variants": { "l1": { "kind": "lora", "spec": "…/weights.json", "covers": ["face", "hair"] } } },
  "volume3d": { "variants": { "m1": { "kind": "mesh", "path": "…/avatar.vrm", "rig": "VRMC_vrm-1.0" }, "fm1": { "kind": "face-mesh", "mesh": { "path": "…", "topology": "FLAME-2023" } } } },
  "voice":    { "variants": { "v1": { "kind": "samples", "label": "Deep, measured", "profile": "…", "samples": ["a-v1-30s"] } } },
  "posture":  { "variants": { "ps1": { "kind": "photo", "use": "pose-only", "images": ["a-pose-1"] }, "at1": { "kind": "attitude", "spec": "…/attitude.json" } } },
  "motion":   { "variants": { "mo1": { "kind": "clips", "clips": ["a-clip-idle"], "visemes": "…" }, "vd1": { "kind": "video", "videos": ["a-vid-1"] } } }
}
```

### 2.3 Presets: multiple slots and stacking rules **[NEW]**

```jsonc
"presets": {
  "default": { "label": "Léa today", "identity": "lea", "style": "photo-realistic",
               "slots": { "personality": ["p1"], "appearance": ["f1", "b1", "h1", "o1", "o2", "a1"], "voice": ["v1"], "posture": ["at1"], "volume3d": ["m1"], "identity_weights": ["l1"] },
               "alternatives": { "appearance": ["h3", "o4", "o5", "a3"] },   // h3, o4, o5, a3, v2…: further variants, not shown above
               "primary_image": "a-body-front",
               "rules": { "single_per_kind": true, "exclusive_regions": true } },
  "soiree":  { "label": "Evening out", "extends": "default", "slots": { "appearance": ["f1", "b1", "h2", "o3", "o2", "a2"] } },
  "en":      { "label": "Léa in English", "extends": "default", "slots": { "personality": ["p2"], "voice": ["v2"] } }
},
"default_preset": "default"
```
- Slots are **lists per category**, with **two regimes**:
  - **Combination** (`personality`, `appearance`, `identity_weights`, `volume3d`, `voice`): what the preset *is* / *wears*. Rule `single_per_kind` (default true): at most one variant per type, except the stackable `clothing`, `accessory`, `pilosity`, `feature`, `environment` (and several `identity_weights` with disjoint `covers`). The slots are what the preset **applies by default** — its default look.
  - **Library** (`posture`, `motion`, `files`): the preset lists the **repertoire** of the character's *typical* poses and movements — several variants of any type, **none of which is mandatory at inference time**; the tool draws on it when it needs to (a reference pose, a walk cycle) and MAY ignore it. `defaults` (optional) designates the variant to prefer when the tool must choose one (`"defaults": { "posture": "ps1", "motion": "mo1" }`). The point is to **associate** a character with their characteristic postures and movements, not to impose them. `x-` categories are libraries unless an RFC says otherwise.
- **Applied and offered** — `slots` = what is **applied by default**; `alternatives` (optional, `{category: [variant ids]}`, combination categories only — never `posture`, `motion`, `files`) = compatible elements **offered with this preset only**: other outfits, hairstyles, accessories, another voice… A 16-year-old Clara is never offered the 65-year-old Clara's sweater: there is **no file-wide wardrobe**, each preset says what goes with it. An offered element is never applied unless a reader (or the user) swaps it in. A builder shows, per variant and per combination category, three states: **absent / offered / default**; the libraries stay two-state.
- **Primary image** (`primary_image`, optional, asset id) — the image that shows the preset's default look. It MUST be an image of a variant the preset applies. Default: by kind in this order — `face`, then `reference-set`, `character-sheet`, `body` — the first applied variant of that kind (slot order) and its first image. When the preset applies **no clothing** (or no `hair`), the outfit (or the hair) **visible on the primary image is the default**; a validator SHOULD warn when that image is head-only (`framing` closeup / head / bust) and no clothing is applied, since the default outfit is then undefined. Inherited through `extends`.
- **Reader profiles** (same terms as the builder's two modes): a **simple** reader uses the default preset, applies its slots and nothing else, and lets the user switch preset; an **advanced** reader also offers the preset's alternatives and MAY recombine them (change the outfit, add an accessory), re-checking the age rules, the region rules and the style before applying. Neither ever draws on another preset's elements without switching to that preset.
- **Backstage** — a variant referenced by no preset (neither applied, offered, nor `derives_from` parent of one that is) is **backstage**: kept, never applied nor offered. A validator warns, an explorer MAY list it apart from the presets, a builder SHOULD ask at build time whether to offer it in a preset, keep it backstage or delete it. Backstage is computed by readers, never written in the file (no catch-all preset: a preset is a coherent combination, and the age rules cannot be waived).
- **What goes in `alternatives`** — only what can be swapped **on its own** without breaking the preset's coherence (a sweater, a hairstyle, an accessory, a second voice in the same language). A change that must move several elements together — a **language** (text + voice + skills), a look (outfit + hair) — is **another preset**, reached by facet navigation (below).
- **Accessory nature** (`accessory_use`, on `kind: accessory`): `worn` (worn or carried — default; then `accessory` gives the type and its body region from `garments-1.0`), `not-worn` (vehicle, mount, furniture…), `companion` (drone, robot, animal…), `other`. Only worn accessories have a body region.
- Rule `exclusive_regions` (default true, can be disabled per preset; checked on the **applied** set only — `slots`): two garments conflict if they cover the **same body region on the same layer** (`garments-1.0` vocabulary: `full-outfit` exclusive; `top`/`bottom`/`dress`/`jumpsuit` on the base layer; `outerwear`/`shoes`/`headwear`/`gloves`/`scarf`/`belt`/`armor` on the outer layer; underwear and socks on the under layer; `cape`/`other` stackable); two **worn** accessories conflict on the same region unless stackable (`necklace`, `bracelet`, `ring`, `bag`); one body/facial hair variant per area (`face`, `body`); special features stack freely. Conflicts are **warnings** (the format does not forbid), type duplicates are **errors**.
- `extends` inherits the parent's lists and **replaces** an entire category when it is redeclared (`"identity_weights": []` drops an inherited LoRA). **Inherited** through `extends`: `slots`, `alternatives` (per category), `primary_image`, `identity`, `age_override` (the nearest declaration wins — inheriting can only lower an age). **Never inherited**: `label`, `style`, `style_tags`, `rules`, `defaults`, `permissions_override` (a child that needs wider permissions restates them, so a minor child never receives an adult parent's `allowSexualUsage`), `completeness`, `coherence`. A cycle of `extends` is an error. `identity` attaches the preset to a character (inherited through `extends`); a preset only uses its own character's elements (§ 2.1).
- A file declares **at least one preset** and its `default_preset` (both REQUIRED); a file without presets is migrated by `cof migrate`, which adds `default` applying every variant except intimate ones. Thumbnail = `thumbnail_source` if set, else the default preset's primary image (§ 1.1).
- KPIs per preset (completeness, coherence); file KPIs = default preset.
- `age_override` per preset — the age the preset declares for itself (typically a text-only childhood preset); it enters the minimum, so it can only lower the preset's age; **per-preset age rules** (§ 9.4), checked on what the preset applies **and** offers (`slots` ∪ `alternatives`): a preset with an element under 18 admits neither `intimate`, nor `body.estimated`, nor an effective `allowSexualUsage`. Optional `permissions_override`: it MAY widen or narrow the character's permissions for that preset, except that it never makes `allowSexualUsage` effective in a preset under 18.
- **Preset tags** (`preset_tags`, optional): `[{ "id", "label", "facet"?, "description"?, "presets": [preset ids] }]` at **container level** — never inside a preset, so nothing is inherited through `extends` and an exported preset carries no tag unless the export keeps it. Tags are **many-to-many**: a preset MAY carry any number of tags (e.g. `en` *and* `age-12`), untagged presets are allowed. The optional `facet` names the family a tag belongs to (`language`, `age`, `style`…): when filtering, tags of the **same facet are alternatives** (selecting `fr` replaces `en`) and tags of **different facets combine** (intersection: `en` + `age-12` → the English 12-year-old presets). **Facet navigation**: tags are the axes of a grid whose cells are presets; switching the value of a facet (e.g. `en` → `fr`) leads to the preset that carries the **same tags in every other facet** (set equality, not inclusion) (`en-12` → `fr-12`) — one click changes text and voice together; with no match, or several, the reader lists the candidates (a validator warns when two presets carry exactly the same tags; tags without a facet count as their own facet). Tags are pure organisation: readers MAY ignore them; builders SHOULD show a filter bar grouped by facet and MUST NOT display a preset twice. `cof extract --tag <id> [--tag <id>…]` exports the intersection as a lighter `.cof` (presets whose parent is outside the selection are flattened; the kept tags are restricted to the exported presets). A tag id is unique; every listed preset MUST exist. *(Supersedes `preset_groups` from builder 0.8.0, which readers MAY import as tags without facet.)*
- **Save as / merge**: § 11.3.

### 2.4 Multi-character files

Handled by **multiple identities** (§ 2.1): a `.cof` is a container of **characters**, each a logical container (identity record, elements, presets, default preset, rights, consent); only the file store, the tag definitions and the file metadata are shared. A tool extracts a character (`cof extract --identity <id>`: all its presets, elements, files and rights — its rights become the file's) or a preset as a standalone `.cof`; merging several `.cof` files preserves the identity ↔ preset links, renames colliding variants and deduplicates assets by `sha256`.

### 2.5 Completeness, coherence, priorities

**Completeness** (computed, 0–100, levels A ≥ 85 / B ≥ 60 / C ≥ 35 / D): per preset, by resolving its slots; layer weighting (keys of `completeness.layers`) `identity` 10 %, `personality` 20 %, `appearance` 20 %, `physique` 5 %, voice 15 %, volume 10 %, motion 5 %, rights 15 %; public rules in `docs/completeness-rules.md`. Derived files do not count. At file level: KPIs of the default preset + `coverage` (list of element types present, number of variants and presets).

**Coherence [NEW]** (declared, 0–100, optional): measures whether the variants of a preset tell the *same* character — gender/age/species across text, images and voice; homogeneous visual style; language of the samples vs `languages`; manifest age vs appearance. It is produced at build time (toggleable checks, § 11.2) by local heuristics **or by an AI of the user's choice** through an API gateway; stored with `computed_by`, `method`, `issues[]`. An incoherent file remains **valid**: the format forbids nothing, it makes things visible. A platform MAY filter on this KPI.

**Priorities [NEW]**: when several representations describe the same thing, which one wins? Declared in the manifest, adjustable at build time and at load time:
```jsonc
"priorities": {
  "visual": ["identity_weights", "images", "avatar", "descriptive"],   // general default (LoRA > images > 3D > text)
  "voice":  ["samples", "described", "engines"],                                   // WAV > described voice
  "by_target": {                                                        // defaults per target use, overridable
    "game-3d":        { "visual": ["avatar", "images", "identity_weights", "descriptive"] },
    "chat-text":      { "visual": ["descriptive", "images"] },
    "video-realtime": { "visual": ["avatar", "images", "identity_weights", "descriptive"] }
  }
}
```
Priorities are also the means to **mitigate** a known incoherence ("the image takes precedence over the text").

### 2.6 Assets

Index of every entry of the container except `mimetype`, `manifest.json` and the JSON / text **sub-files** named by a variant or asset field (`card`, `psyche`, `spec`, `profile`, `pose`, `transcript`…) — any other entry MUST be an asset, with its hash — each with an **`id`** (referenced by the variants), `path` (or external `uri` + hash), `role` (`view`, `expression`, `reference`, `sheet`, `voice-sample`, `voice-consent`, `engine-artifact`, `weights`, `avatar`, `splat`, `print`, `motion-clip`, `motion-reference`, `mesh`, `derived`, `document`, `pose-image`, `texture`, `video`, `environment`, `archive`, `skill-file`, `memory`, `file`, `other` — the schema enum is the normative list), `mediaType`, `bytes`, `sha256`, `license` (SPDX), `digitalSourceType` (IPTC), and depending on the role: `subject`/`angle`/`framing`/`style` (images), `duration_s`/`transcript`/`emotion` (audio), `rig`/`fps` (clips), `method`/`source` (derived), `regions[]` (character sheets), `base_model` (weights), `derived_from`, `estimated`. Sub-files carry no hash in 1.0: their integrity relies on the ZIP CRC, and the optional manifest signature (§ 9.3) covers the manifest and, through their hashes, the assets.

---

## 3. `personality` element
**Text-bearing images.** An image can carry its character profile: a Character Card V2/V3 (`tEXt chara` / `ccv3`, base64 JSON) or **free descriptive text** in a standard field — PNG `iTXt`/`tEXt`/`zTXt` with the keyword `Description` (or `Comment`), XMP `dc:description`, EXIF `ImageDescription` / `UserComment` / `XPComment` (including the raw profile `Raw profile type APP1` written by ImageMagick), JPEG `COM`. A reader or builder that receives such an image creates **two** variants: the personality (card → `card`, text → `description`) and the appearance (`reference-set`, image retained). To write: `cof embed-text image.png fiche.md` (iTXt `Description`, UTF-8); to check: `cof read-text image.png`.


Variant = a complete **Character Card V3** (`card`), optionally `psyche.json` (typed OCEAN/HEXACO traits, goals, fears, values, contradictions, EmotionML base emotion, rendered as sentences and as sliders), `story.md` (long-form), `lorebook.json` (`lorebook_v3`), `SOUL.md`/`IDENTITY.md` projections (OpenClaw, truncated at 20,000 characters). Conventions unchanged since v0.2: `creator_notes` never in the prompt, COF keys under `data.extensions.cof`, `behavior` = observable manifestations (distinct from the dispositions in `psyche`), `trait:`/`goal:`/`fear:` identifiers for cross-references. Token profiles (`summary` ≤ 512, `standard` 1–2 k, `full` ~4 k, `lore` ≤ 32 k per entry) declared per variant.

---

## 4. Visual elements

### 4.1 Images: separate views, character sheets, framing
- Normative view naming: `<subject>.<angle>.<ext>` with subject ∈ `head | body | hands | hair | outfit | detail` (`assets[].subject`; a file name MAY refine `detail` as `detail-<part>`), angle ∈ `front | left34 | left | leftback34 | back | rightback34 | right | right34 | top | low34`; canonical `head.front` = `head` framing (top of the hair → chin, 1024² square, centered on the pupils); tight close-ups accepted as `framing: closeup`.
- **Separate views = canonical form** (common denominator of generators: 1 to N reference images; thumbnails and chat apps load `head.front` directly). **Character sheet retained as an option** (`role: sheet`, normalized `regions[]`, `confidence`, `human_confirmed`); the builder slices it, removes titles/separators, classifies and frames the views, and derives `head.front` from the body view if the close-up is cropped.
- Each image carries a **`style`** (§ 4.7).

### 4.2 `face` — images, parameters, **spatial mesh [NEW]**
A face variant can carry up to four coherent representations:
- `images[]` (head views, named expressions);
- `params`: `face.json` — FLAME 2023 Open (300 shape + 100 expression), open descriptive vocabulary COF-FDV, skin tone (Monk + hex), standard expressions (VRM/Ekman name + intensity + ARKit-52 vector);
- `mesh`: **3D head mesh** — `path` (glTF/GLB recommended; OBJ/PLY accepted), `topology` (`FLAME-2023 | MediaPipe-468 | ARKit | ICT-FaceKit | MetaHuman | custom`), `blendshapes` (`ARKit-52 | UnifiedExpressions-1.0 | VRM-presets | none`), `textures` (albedo/normal/roughness as assets), `units`, `landmarks` (set of named points if known); a scanned mesh (photogrammetry, frozen Gaussian avatar) is accepted with `topology: custom` and `watertight`;
- `derived[]` (optional, § 4.8).
The validator checks the consistency of measurements between `params` and `mesh` when both exist (warning). No **biometric embedding** (ArcFace…) is allowed.

### 4.3 `hair`, `pilosity` (facial and body hair)
`hair.json` = COF-HAIR-1 code (length, curl, density, thickness, colors, style, parting, hairline, ~200 bytes) + optional dedicated images (neutral background or mask). `facial_hair` and `body_hair`: same fields, restricted. If the author does not isolate the hair, it remains implicit in the `face`/`body` images — this is permitted.

### 4.4 `body`
`body.json`: Anny (phenotypes [0,1]), SMPL-X β for interop, ISO 7250 measurements, skin tone, description, `renderings.prompt`; `body.*` views. **Estimated morphology under clothing** (`body.estimated`, optional, marked `estimated` + `confidence`): pose + silhouette corrected by a clothing offset + anthropometric priors; **forbidden if `age < 18`**, not applied to the `mechanical`/`amorphous` classes, never on a real person without `consent.scope` ∋ `likeness-3d`.

### 4.5 `intimate` (optional, explicit activation — *opt-in*)
Appearance variant type (`kind: intimate`), same schema as `face`/`body`. **Nothing is encrypted or hidden** (a principle of the format); "opt-in" has three precise technical consequences:
1. **Not loaded by default**: a conforming reader MUST NOT open the images of this variant, inject them into any prompt or display them, unless *both* the **effective** `allowSexualUsage` of the selected preset (§ 9.1: the character's permissions, then `permissions_override`) is true **and** the host application explicitly requests it (an opening parameter, never a default).
2. **Physical isolation**: its files MUST live in its own folder `elements/appearance/<v>/` and MUST be referenced by no other variant (validation errors), so that an "all-audiences" copy only removes that folder, the variant, its assets, its references in presets and the `nudity` flag (`sexual` stays when set: texts may still be concerned) — `cof extract --no-intimate` does exactly this.
3. **Mandatory flagging**: `tags.content` MUST contain `nudity` or `sexual` as soon as such a variant exists (validation error otherwise), and a preset that applies or offers it is **invalid** if that preset's age is < 18 (§ 9.4).

**What goes where.** `intimate` holds every image where **genitals are visible** or a **sexual act** is shown, whatever the angle or the framing — it is the only place where they may appear. **Nudity without visible genitals** (bare chest, buttocks…) MAY appear in other variants (`body`, `character-sheet`, `reference-set`…), which then carry `nudity: true`; what counts as nudity differs between countries, so the author declares it and readers apply their user's content settings. Rules (validation errors): a variant marked `nudity` requires `tags.content` `nudity`; a file showing nudity is used only by variants marked `nudity` (or `intimate`); **no nudity of any kind in a preset under 18**; nudity of a **real person** (public or private) requires their consent scope `nudity` or `intimate` — satire of a public figure needs no consent, their nudity does. With a nude or intimate element in a preset, every body representation carries an age whatever the morphology class. Readers SHOULD NOT display nudity by default when their user has not chosen to; they never display it in a preset under 18 (such a file is invalid anyway). An image with visible genitals outside `intimate` is a misclassification: the AI check (§ 9.4) reports it as `illegal`.

### 4.6 `identity_weights` — LoRA and embeddings **[NEW]**
```jsonc
// elements/identity_weights/l1/weights.json
{ "kind": "lora",                                 // lora | lycoris | dora | textual-inversion | ip-adapter-embedding | reference-latent | dreambooth | other
  "base_model": { "name": "FLUX.1-dev", "family": "flux", "version": "1.0", "hash": "sha256:…" },   // the base model is MANDATORY: a LoRA without a base is unusable
  "file": "a-lora-l1",                            // asset (safetensors): embedded by default; or by link (asset with `uri`)
  "format": "safetensors", "rank": 16, "bytes": 171000000,
  "trigger_words": ["leamarchand", "woman"], "recommended_weight": 0.8, "weight_range": [0.6, 1.0],
  "covers": ["face", "hair", "body"],             // what the LoRA encodes (for coherence and priorities)
  "pages": [ { "label": "Civitai", "url": "https://civitai.com/models/…" } ],
  "notes": "Trained on 40 images, 1500 steps; avoid > 1.0; works best with the trigger word at the start of the prompt.",
  "training": { "images": 40, "steps": 1500, "resolution": 1024, "dataset_consent": true },
  "style": "photo-realistic", "license": "CC-BY-NC-4.0" }
```
Rules: `weights.json` is **authoritative** — `covers`, `style`, `license` or `base_model` repeated on the variant or the asset are indexes for quick reading, and a validator MAY warn when they differ; `base_model.name` REQUIRED; `trigger_words` and `recommended_weight` RECOMMENDED; the weights file is an asset with `role: weights`. **Storage**: embedded in the container by default — reproducible even if the model disappears online, but heavy (tens to hundreds of MB); or **by link**, an asset with `uri` and no `path` — with `sha256` the link is pinned to one exact file, without it the link follows the latest version published at that address (not reproducible). Links rot or move (model removed, account deleted, platform closed): validators warn on every linked asset; `allowTraining` and `consent` apply; a LoRA of a real person without consent is invalid. IP-Adapter / "face ID" embeddings are accepted *only* if they are not recognition embeddings (§ 4.2).

**Pre-encoded references** (`kind: "reference-latent"`): reference images or videos encoded once into a model's conditioning space and reused at inference without training — e.g. MiniMax H3 *RefMods*, cached IP-Adapter / reference latents. The name is deliberately generic: the technique outlives any one model, the files do not (a latent is only valid for the encoder it came from). `base_model` REQUIRED as for a LoRA; optional `encoding` = `{ method (e.g. "minimax-h3-refmod"), mode: full | pooled, pool: [h, w], frames, resolution, sources: [asset ids] }`. `encoding.sources` SHOULD list the images / videos that were encoded, embedded in the same `.cof`: **the file keeps the sources, the latent is a cache** — a tool can re-encode it for the next model. A validator warns when `sources` is absent and refuses an unknown asset id. An audio reference goes to `voice` `embedding` (`engines[]`). Like every identity weight, a reference-latent carries a likeness: never neutral, age and consent rules apply.

**Safetensors check**: every `.safetensors` in the container MUST have a readable header (8-byte length + JSON object) whose tensors fit in the file; a validator reads only the header — no tensor data, no code — and refuses a file that fails (truncated download, renamed pickle).

### 4.7 Visual styles **[NEW]**
`visual-styles-1.0` vocabulary (CC0, extensible): `photo-realistic`, `cinematic`, `3d-render`, `anime`, `manga`, `comic`, `cartoon`, `pixel-art`, `lego`, `clay`, `watercolor`, `oil-painting`, `ink-sketch`, `lineart`, `low-poly`, `voxel`, `chibi`, `other:<free>`. Carried by **each image** (`assets[].style`), by **each 2D visual variant** (`appearance`, `identity_weights` — not `volume3d`: the look of a 3D model depends on the rendering engine, not on the file), and expected by **each preset** (`presets.<p>.style`). The base list stays **short**; refinements go through **complementary tags** `style_tags[]` (e.g. `anime-90s`, `ghibli-like`, `ukiyo-e`) rather than by lengthening the list. The builder proposes it automatically (lightweight classifier or external AI); the author confirms. The coherence check flags a preset that mixes styles without declaring it.

### 4.8 Derived files: optional post-processing **[NEW]**
`derived/<type>/<v>/<view>.<method>.png` (+ SVG), `assets[].role: "derived"`, `method` ∈ `canny | lineart | lineart-anime | softedge | hed | pidinet | teed | depth | normal | openpose | segmentation | thumbnail | other`, `source` = id of the original asset. **Optional**; generated by the builder on request; **never counted** as base images or in completeness; isolated in their own block; the author can choose to ship *only* derived files for a view (the author's choice, not the format's). Platforms regenerate them on the fly from the images when they are absent.

### 4.9 `clothing`, `accessory`
`outfit.json`: Fashionpedia categories/attributes, colors, optional GarmentCode pattern; optional dedicated images. Several outfits = several variants, combined by the presets.

---

## 5. `attitude` element (physical)
`attitude.json`: LMA Effort motion signature (4 axes −1…+1, dominant action, Shape), tempo, postures (BAP), BML gesture lexemes with `expresses: ["trait:…"]`, gaze, proxemics, gait, 100STYLE/BABEL labels; **postures as normalized OpenPose keypoints** (`poses/<name>.pose.json`, skeletons `openpose-body25 | coco-18 | coco-wholebody-133 | mediapipe-pose-33`) with a "stick figure" rendering for ControlNet.

---

## 6. `voice` element

### 6.1 "One truth, many projections" rule
| Question | Where it lives |
|---|---|
| *Why* the character acts this way | `personality` (psyche, card) |
| *How the body* shows it | `attitude` |
| *How the voice* shows it | `voice` (acoustics, prosody, register) |
| *What is said* | `card.mes_example` |
Sections refer to each other by identifiers; a validator SHOULD flag near-duplicate texts between sections (the metric is its choice).

### 6.2 Content of a voice variant
`profile.json` (typed canonical profile: perceived gender, age, accent, pitch, speech rate, volume, timbre, expressiveness; ordinal VPA; `speech_style`; EmotionML `emotion_range`; samples in canonical durations ≈ 8 s / 30 s / 2 min, **transcript optional but recommended** (`.txt` file alongside, referenced by `assets[].transcript`): zero-shot cloning engines (ElevenLabs, XTTS, OpenVoice, Chatterbox) do not need it; text-alignment engines (F5-TTS, CosyVoice, Fish Speech) and coherence checks benefit from it — hence a completeness bonus, never an obligation; `engines[]` = **engine artifacts that carry the voice to another machine or platform running the same model, without retraining** — no universal voice-profile format exists, so each entry is tied to the exact model that can read it: `{ engine, version, model, model_sha256?, kind: speaker-embedding | fine-tuned-weights | index | cloud-voice-id, files: [asset ids, role engine-artifact], voice_id?, sample_rate?, notes? }` — e.g. XTTS speaker latents, OpenVoice tone-colour embedding, CosyVoice `spk2info`, RVC weights + `.index`, Piper `.onnx`, an ElevenLabs or Typecast `voice_id`. Formats: `.safetensors`, numeric `.npz` / `.npy`, `.json`, `.onnx`, `.index`; **pickles (`.pt`, `.pth`, `.ckpt`, `.pkl`) are always refused** — loading one runs code — and are converted once to safetensors. Engine artifacts are voice-cloning material: `allowVoiceCloning`, consent and licences apply; the audio samples remain the universal source; `prompt_renderings`; `ssml_template`; ECAPA `fingerprint` for verification only) and `voice.vec.json` (COF-Voice voice code: computed acoustic measurements F0/rate/pauses/HNR/jitter/shimmer, ordinal quality, manner of speaking, sentence/SSML/Parler renderings). Consent REQUIRED if the voice is a real person's.

---

## 7. `volume3d` and `motion` elements
- `avatar`: VRM 1.0 as pivot (`meta` **derived** from `rights` on export), GLB accepted with a declared `rig`; `skeleton.json` RECOMMENDED for a non-standard rig (`rig: custom`); the `skeletons-1.0` vocabulary (**planned for 1.1**; canonical VRM humanoid; Unity/Mixamo, Unreal/MetaHuman, SMPL-X, Anny, MHR; OpenPose/MediaPipe 2D skeletons) with mapping tables; splat (SPZ, external by default) linked to the avatar by `splat.json` (no native skeleton); `print/*.3mf` printable derivative.
- `motion`: BVH clips (pivot) / VRMA (humanoid + expressions + gaze), `rig`, `fps`, BABEL labels, `derived_from_video`; `visemes.json` = declared vocabulary (ARKit-52 / Oculus-15 / A–X).
- Khronos hook: `mapping_vocabularies` may name `KHR_character*` if these extensions appear in the registry (existence not confirmed).

---

## 7 bis. **Agent** use: structured personality, skills, memories

A `.cof` can describe an **agent** just as well as a character to be displayed. The mapping to common agent architectures (verified against OpenClaw and Hermes Agent, October 2026) is deliberately a projection, never a coupling:

| Agent concept | Where it lives in COF | Projection (export) |
|---|---|---|
| Soul / style (`SOUL.md`) | `personality` — structured text (V3 card: `description`, `personality`, `system_prompt`, examples) or free text; `psyche.json` for typed traits | `cof export --format soul` → `SOUL.md` + `IDENTITY.md`; `cof export --format agent` → a whole workspace (`SOUL.md`, `IDENTITY.md`, avatar, `skills/<name>/`, memories, `docs/`, `COF.md` with the permissions the host must honour) |
| Short identity (`IDENTITY.md`) | identity (`name`, `summary`, `morphology`) + `thumbnail` | same |
| Skills (`skills/<name>/SKILL.md`, YAML header `name`, `description`, then instructions; resources and scripts alongside) | `files` / `kind: skill` — one variant per skill, `entry` = `SKILL.md`, `target` indicates the dialect if the skill is not portable | copy of the folder `elements/files/<v>/` to `skills/<name>/` |
| Persistent memory (`MEMORY.md`, `USER.md`, dated notes) | `files` / `kind: memory` — `entry` = main file | copy to the root of the agent's workspace |
| Knowledge (lore, rules, FAQ) | `files` / `kind: document` | indexing or context, at the host's discretion |
| Tools (`TOOLS.md`, `AGENTS.md`, routing) | **out of scope**: they describe the host, not the character. A `document` can carry them, without COF semantics | — |

Rules:
1. `files` is a **library** (§ 2.3): a preset lists the *available* skills and memories; nothing is loaded by a reader that is not an agent (image generator, voice engine…). Non-agent readers **ignore** the category.
2. A skill that embeds scripts (executable content, § 9.3) requires `container.executableContent: "scripts"`; otherwise the file is invalid (§ 9.3). The host remains free not to execute them; the declaration ensures that an "inert" `.cof` really is inert.
3. The `SKILL.md` format follows the open **Agent Skills** standard (`agentskills.io`) when `target` is `agent-skills` or absent; a specific `target` signals a dialect (OpenClaw: `version`, `os`, `requires`, `triggers` in the header; Hermes: skills organized by category, created by the agent itself).
4. Memories are **character data**, not user data: a `.cof` MUST NOT carry the memory of a real person without `consent.scope ∋ conversational-persona`.
5. `targets_ready` gains `agent-runtime` as soon as a preset references at least one skill or memory; automatic tags `has-skills`, `has-memory`.

## 8. Sizes

**Token profiles** per personality variant: `summary` ≤ 512, `standard` 1–2 k, `full` ~4 k, `lore` ≤ 32 k activated per entry; no permanent block > 2,500 tokens without justification; injection order `identity → rules → lore → history → identity_recap`.

**Size classes** (per channel, not by powers of 2): `lite` ≤ 20 MB, `standard` ≤ 100 MB, `full` unlimited. Large assets MAY be externalized (`uri`, `sha256` recommended), but **embedding is the default**, identity weights included: links rot, and a character must survive its sources. Binaries stored uncompressed. A modular file can be large (dozens of variants): the "save as" option for a preset produces a lightweight version.

---

## 9. Rights

### 9.1 Permissions (modeled on `VRMC_vrm.meta`, restrictive defaults)
`avatarPermission`, `commercialUsage`, `modification`, `allowRedistribution`, `creditNotation`, `allowExcessivelyViolentUsage`, `allowSexualUsage`, `allowPoliticalOrReligiousUsage`, `allowAntisocialOrHateUsage`, **+** `allowVoiceCloning`, `allowTraining` (`none | finetune-private | finetune-public | any`), `allowImpersonationOfRealPerson`, `ageRating`, `minUserAge`, `aiDisclosure` (default `true`). Age rules are in § 9.4.

**Per character** (§ 2.1): in a file with several characters, `identities.<id>.rights.permissions` replaces the root permissions for that character; the effective permissions of a preset = its character's, then `permissions_override`.

### 9.2 Consent
A **consent record** (`identities.<id>.consent`; in a single-character file `rights.consent`, the root copy — both validated against `consent.schema.json`, the proofs being assets) is **recommended** — required in principle for a private person — as soon as `fictional: false`, an asset comes from a real person, or an identity weight has been trained on a real person: `subject_is_real_person`, `scope[]` (`voice-synthesis | likeness-image | likeness-3d | conversational-persona | motion-capture | training | intimate | nudity`), `excluded[]`, `jurisdictions[]`, dates, `revocation_uri`, `proof[]` (recorded verbal statement, signed document, platform attestation — hashed). A conforming reader SHOULD warn before synthesizing a voice or using a LoRA of a real person without a proof listed in the record, and MAY refuse. **Responsibility**: the format does not replace the law, which differs from one country to another, and does not try to: the author of a `.cof` is responsible for what it contains and how it is shared. Without a consent record a real person stays possible — personal use or satire of a public figure remain possible within the limits of local regulations — and validators **warn**; consent is required in principle for a private person, and strongly recommended before any public sharing, a fortiori any sale. Two rules are hard, whatever the author says: minors (§ 9.4) and **intimate content of a real person without their explicit consent** (scope `intimate`), which is a validation error. **Scopes follow the content**, per character: an `intimate` variant requires `intimate` (error); a variant marked `nudity` requires `nudity` or `intimate` (error); likeness images (face, body, character sheet, reference set, hair) and identity weights require `likeness-image`, a 3D likeness `likeness-3d`, voice samples or embeddings `voice-synthesis` (`allowVoiceCloning: true` without it is warned), a personality `conversational-persona` (memories, § 8), non-neutral motion clips or videos `motion-capture`, `allowTraining` other than `none` requires `training` — the other cases are warnings.

### 9.3 Provenance, signature, security
Append-only `source[]`, `created/modified`, `generator`, `digitalSourceType` per asset, C2PA per media asset + sidecar `rights/manifest.c2pa`, optional manifest signature (RFC 8785 + JWS). `container.executableContent` declared and verified — **executable content** = files with the extensions `.js .mjs .lua .py .wasm .exe .com .msi .scr .dll .so .dylib .jar .apk .sh .bash .bat .cmd .ps1 .vbs .applescript`, and SVG / HTML files that carry script (`<script>`, `on…=` handlers, `javascript:` URLs); validators inspect `.zip` archives, and the archives nested inside them (detected by extension or by content) up to three levels, with the same rules — deeper or unreadable nesting is warned (pickles refused, executables need the declaration, Daz scripts `.dsa` / `.dse` flagged); `.rar` / `.7z` are not inspected (warning); pickles (`.pkl`, `.pickle`, `.ckpt`, `.pt`, `.pth`, and `.bin` files that are pickles) are always refused; no executable serialization format (weights are in **safetensors**, never pickle); restricted names; anti-zip-bomb limits; prompt texts `untrusted`; external `uri`s in `https://`, verified by hash.

### 9.4 Age, minors and intimate content — per-preset rules
Age is carried by the representation (§ 2.2), so the rules apply **preset by preset**, which allows a file to contain an "adult" preset with intimate content and a "childhood" preset without.
1. An `intimate` variant MUST carry an age **≥ 18** (in years); otherwise the file is invalid, wherever the variant is used. Its files are its own (§ 4.5), and no file may represent both a person under 18 and an adult (§ 2.2).
2. In a preset where **at least one** element (morphological variant or `age_override`) is under 18: **no** `intimate` variant, **no variant marked `nudity`**, no `body.estimated`, and the **effective** `allowSexualUsage` (`rights.permissions` merged with `permissions_override`) MUST be `false`. A mixed file therefore sets `allowSexualUsage` to `false` at file level and MAY allow it through `permissions_override` on the adult preset only.
3. In a preset that applies or offers an `intimate` element, every representation of the body (`face`, `body`, `character-sheet`, `reference-set`, identity weights, 3D characters) MUST carry an age, **whatever the morphology class** — declaring a non-human class never removes the age requirement.
4. A preset without any age (text only) is not subject to any visual rule; the format cannot read an age in a text — that is the role of the coherence check.
5. **AI "age-legality" check** (`docs/coherence-api.md`): the checker estimates the apparent age of face and body images; if a preset contains an `intimate` or `nudity` variant and an image clearly looks like a minor while the declared age is adult, or if an image shows visible genitals outside an `intimate` variant, it returns an issue with severity **`illegal`**; an image showing nudity in a variant not marked `nudity` gets severity `major`, and the builder asks the author to confirm and mark it. The builder displays it in red as an illegal combination and **refuses to build** the file until it is resolved; an `illegal` severity is never a mere warning.
6. *Open question for the community*: reporting of a detected illegal combination (to whom, in what form, with what safeguards). The standard establishes from now on the principle that safety and legality are design constraints, not reader options; the reporting mechanism will be defined with the first adopters.

---

## 10. Dual-mode distribution
Monolithic `.cof` file, or OCI artifact (`artifactType: application/vnd.cof.character.manifest.v1+json`, config = manifest, one uncompressed layer per asset, `subject`/referrers for signatures). Identity weights are particularly well suited to registry mode.

---

## 11. Validation, builder, conformance

### 11.0 Sub-file schemas
Each JSON sub-file referenced by a variant has its schema in `spec/schemas/` (`card`, `psyche`, `weights`, `voice-profile`, `attitude`, `pose`, `skeleton`, `hair`, `body`, `consent`, `visemes` — see `spec/schemas/README.md`). The validator enforces them as **errors**: these files are produced by the builder or the CLI, so a deviation is a bug, not a freedom. `consent.schema.json` is the source of the manifest's `$defs/consent`.

### 11.1 Conformance levels
`COF-Core` (mimetype, manifest, rights, hashed assets, resolvable presets); `COF-Psyche`; `COF-Visual`; `COF-Voice`; `COF-3D`; `COF-Motion`; `COF-Weights` (base model + hash + license); `COF-Rights+` (C2PA + signature). The validator reports errors/warnings and recomputes completeness, `coverage` and `targets_ready` per preset.

**Requirements a program cannot check** (no recognition embedding, no memory of a real person without consent, a genuine consent proof, a truthful age): they bind the **author**; validators check what is checkable (scopes, presence of proofs, declared ages) and the coherence check (§ 11.4) reviews the rest.

### 11.2 The builder
Single web page (HTML/JS, offline, GitHub Pages + Hugging Face Space), everything local. Flow: **Identity → Elements** (for each type: add variants; import a PNG/CharX/SOUL.md card; drop images or a character sheet → slicing, classification, proposed style; WAV → measurements; VRM/GLB/BVH → rig; LoRA → weights sheet) → **Presets** (compose combinations; mark the default; save as / merge) → **Rights** → **Checks** → **Build**.

**Coherence checks** (toggleable, never blocking — except a finding of severity `illegal`, § 9.4): local heuristics (variant age vs images and voice, style per preset, language of the samples, perceived voice gender vs declared presentation, morphology vs images) **and** AI gateway: the builder sends to an API endpoint of the user's choice (OpenAI-compatible *chat/completions* format with vision, or a platform's native integration) a **preset bundle** (`cof coherence-bundle`: text summaries, thumbnails, voice descriptors, declared weights) and expects `{ "score": 0–100, "issues": [ { "severity", "elements": [...], "message" } ] }`; the result is stored in `presets.<p>.coherence` with `computed_by` and date. JSON contract in `docs/coherence-api.md`.

**Priorities**: dedicated screen, defaults from § 2.5, editable; exported into the manifest.

**Build**: size class, compression (cropping/JPEG quality, WebP; Opus for long audio; externalization of large assets; **video size/quality** displayed when videos are present, 20 MB cap that can be disabled with a warning), generation of derived files **on request only**, ancillary exports (PNG ccv3, `.charx`, SOUL/IDENTITY, `.vrm`), "save as" per preset, **import and merge** of other `.cof` files.

### 11.3 Merging and extraction (`cof merge`, `cof extract`)
- **Merge**: same `name` + `nickname` + `fictional` + `morphology.class` ⇒ same identity (elements and presets added to that identity); otherwise a new identity, which **keeps the rights of its source file** (`identities.<id>.rights`) and its consent. Variants and presets renamed on collision (prefix), `derives_from`/`extends` and the presets' `alternatives` / `primary_image` rewritten, assets deduplicated by `sha256`, `provenance.source` ← identifiers of the source files.
- **Preset extraction**: new file containing only the preset's identity, its variants — applied **and offered** (`alternatives`) — (and their `derives_from` parents), their assets and derived files, and the rights; new `id`, `provenance.source` ← `cof:<id>#preset=<p>`.

### 11.4 Authoring discipline: what every author must check — including AI agents
COF is deliberately permissive: almost everything is optional, unknown keys are preserved, and explicit escape hatches exist (`self_contained: false` for a 3D file without its textures, weights by link, `x-` categories). The price of that openness is **discipline in what goes in**. It rests on three layers.

1. **Validator, blocking** (`cof validate`, every file): age on the representations that require it; `intimate` ≥ 18 and flagged in `tags.content`; per-preset minor rules (no `intimate`, no estimated body, no effective `allowSexualUsage`); unresolved references (assets, variants, presets, tags); one variant per kind in a preset except the stackable kinds (unless the preset sets `rules.single_per_kind: false`, which the author then answers for); one file shown both under 18 and as an adult; an intimate variant's file used elsewhere; a preset with intimate content whose body representations lack an age; an `extends` cycle; no preset; undeclared executable content (also inside `.zip` archives) and any pickle; an invalid `.safetensors`; a missing thumbnail file; missing hash or size of an embedded asset; intimate content or nudity of a real person without consent scope `intimate` (or `nudity`); nudity in a preset under 18; a variant marked `nudity` without `tags.content` `nudity`; a non-self-contained 3D file without `self_contained: false`; a coherence finding of severity `illegal`.
2. **Validator, warnings** (accepted, shown): the same image embedded twice (e.g. a reduced copy and its original), weights or assets by link (with or without `sha256`), declared non-self-contained 3D, FBX, voice samples without transcript, a permanent prompt block above 2,500 tokens, a voice shared by presets far apart in age, `derives_from` across kinds, deprecated keys.
3. **Coherence review, judgment.** The builder runs it with local heuristics and an optional AI gateway (§ 11.2). **An author who does not use the builder — a script, another tool, an AI agent — MUST perform it before publishing** and report what could not be checked:
   - **Age** — the apparent age in every image matches the variant's `age`; text personalities, voices, outfits and poses suit the preset's age.
   - **Minors** — nothing sexualised, suggestive or intimate in any element of a preset under 18 (text, image, voice, pose); in doubt, the preset is treated as a minor preset. Such a finding is `illegal`: the file is not built.
   - **Identity** — the same person across the variants of one identity (face, hair, proportions), except deliberate transformations (age, style).
   - **Style** — the variants of a preset share its declared style (no photo-realistic face in a manga preset).
   - **Voice** — perceived age and gender presentation match the preset; the sample language equals `language`; transcripts match the audio.
   - **Language** — every text variant is written in its declared language; `language` tags match the content.
   - **Rights** — each licence is the real one of its asset (including the generator's plan terms); permissions are what the rights holder actually grants; a real person requires consent.
   - **Provenance** — AI-generated media carry `digitalSourceType: trainedAlgorithmicMedia` and their generator.
   - **Third parties and secrets** — environments, documents, skills and memories contain no identifiable third party without consent and no secret (keys, personal data).
   - **Weight** — the file stays within its target size class; heavy assets (LoRA, 3D scenes, videos) are justified.

---

## 12. Versioning and governance
Semver; public RFCs (14 days); vocabularies versioned separately (CC0); a `1.x` reader reads `1.y`: minor versions only **add** optional fields and enumeration values (never remove nor rename), and a reader or validator of an earlier minor treats an unknown field or enum value of a later-minor file as a warning — preserved, never a reason to refuse the file — **except** an unknown variant `kind`, which stays an error in every version (a kind may carry safety rules: new kinds are read by newer tools only); unknown keys preserved; transfer to neutral governance as soon as there are two independent adopters.

---

## Annex A — Migration v0.2 … v0.5 → 1.0
`cof migrate` chains v0.2 → v0.3 → v0.4 → v0.5 → 1.0. **v0.5 → 1.0**: the version number only (`cof: "1.0"`); `preset_groups` (builder 0.8.0) become `preset_tags`. Readers of 1.0 accept any `1.x` file: later minor versions only add optional fields, which are preserved. **v0.4 → v0.5**: the identity age is copied onto the morphological variants that lack one (reserved variant → age of its identity, otherwise of the default identity) and as `age_override` onto the presets that lack one; an `intimate` < 18 is not corrected (the file becomes invalid, by design). v0.3 → v0.4: v0.3 types (`face`, `hair`, `outfit`, `avatar`, `attitude`…) → categories + `kind` (`appearance/face`, `appearance/hair`, `appearance/clothing` (`garment: full-outfit`), `volume3d/mesh`, `posture/attitude`…), preset slots → lists, `humanoid` + human species → `human`.

## Annex B — Minimal valid example (COF-Core)
```
mimetype
manifest.json        (identity without age, tags, rights.permissions, provenance, elements.personality.variants.p1.card, presets.default + default_preset, assets: [])
elements/personality/p1/card.json
```

**Required root fields** (the schema is normative): `cof`, `id`, `name`, `fictional`, `morphology` (`class`), `tags` (`content` with at least one value, `ip.original`), `elements`, `assets`, `rights`, `provenance` (`created`, `modified`), `presets` (at least one) and `default_preset`. Everything else is optional; `tags`, `provenance`, `presets` are bookkeeping that tools write for the author.
