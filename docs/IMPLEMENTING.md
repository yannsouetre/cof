# Implementing COF — Character Open File

**Implementer's guide · format 1.0 (release candidate) · October 2026**
Audience: developers of companion and chat apps, image/video generators, TTS and voice-cloning services, game engines and VTubing tools, real-time avatar platforms, and agent runtimes. The normative text is `spec/SPEC.md` (English; French version `spec/SPEC.fr.md`, kept aligned section by section); this guide is the practical, English entry point.

The key words MUST, MUST NOT, SHOULD, SHOULD NOT and MAY are to be read as in RFC 2119 / RFC 8174.

---

## 1. What a `.cof` is, in one paragraph

A `.cof` is a ZIP container holding **one or more characters**: identity, personality (Character Card V3 or free text), appearance (photos, character sheets, LoRA references), voice (samples, described voice), 3D (VRM/GLB), poses and motion clips, agent files (skills, memories), and a **rights** block (VRM-style permissions + consent for real people). Content is organised as **elements → variants → presets**: a preset is one ready-to-use combination ("Léa, casual, photo-realistic, voice A"). Nothing is encrypted; protection is done by validation rules and by obligations on readers (§ 6).

You do not need to support everything. A chat app can ignore 3D; a TTS service can ignore images. The format is designed so that **partial readers are conformant**.

---

## 2. Identification

| Property | Value |
|---|---|
| File extension | `.cof` |
| Media type | `application/vnd.cof.character+zip` (vendor tree, registration planned — template in § 11) |
| Magic | bytes 0–3 = `PK\x03\x04`; bytes 30–37 = `mimetype`; bytes 38–70 = `application/vnd.cof.character+zip` (first entry, stored, uncompressed — same technique as EPUB and ODF) |
| Second entry | `manifest.json` (UTF-8 JSON, JSON Schema 2020-12 in `spec/schemas/manifest.schema.json`) |
| Version field | `manifest.cof` = `"1.0"` (major.minor) |

Sniffing rule: a reader MAY identify a file as COF from the magic alone, without unzipping.

---

## 3. Conformance classes

| Class | Must do | Typical product |
|---|---|---|
| **Core reader** | § 4 steps 1–7 and all of § 6 | any app that "opens a character" |
| **Profile reader** | Core + the profile's elements (table in § 5) | chat app (*chat*), image generator (*visual*), TTS (*voice*), engine (*3d*), agent runtime (*agent*) |
| **Writer** | § 7 | builders, exporters, platforms offering "Download as .cof" |
| **Validator** | everything in the schemas + rules of the spec; `cof validate` is the reference | CI, marketplaces, moderation |

A product MAY claim several classes. A claim SHOULD be stated as e.g. *"COF 1.0 Core reader, chat + voice profiles"*.

---

## 4. Minimal reader algorithm

```
1. Open the ZIP defensively (§ 9): reject absolute paths, "..", symlinks; cap entries, total size and ratio.
2. Check entry 0 == "mimetype" with the exact media type. Otherwise: not a COF file.
3. Parse manifest.json. If manifest.cof major > supported major: refuse politely. Unknown fields: IGNORE (never fail).
4. Several characters (manifest.identities)? Choose one first (default_identity by default): each character is a
   logical container — its elements (variant.identity), its presets (preset.identity), its default preset
   (identities.<id>.default_preset) and its rights (identities.<id>.rights replaces the root rights).
   Choose a preset of that character: the one the user picks, else its default preset, else the first one.
   (Optional `preset_tags` at container level let a picker filter presets: same-facet tags are alternatives, different facets intersect. Pure organisation — ignore them if you show no picker.
    Facet navigation: to switch language (or age, look…), go to the preset carrying the same tags in every
    other facet — en-12 → fr-12 — so text and voice change together; list the candidates if 0 or several.
    model.facet_switch() is the reference.)
5. Resolve it:
     slots  = preset.slots, merged over the presets it `extends` (child replaces a whole category list);
     each variant id → elements[category].variants[id], merged over its `derives_from` parent.
   Categories posture, motion, files are LIBRARIES (pick what you need, none is mandatory);
   the others are COMBINATIONS (at most one variant per kind, except clothing/accessory/pilosity/feature/environment).
   slots = what the preset APPLIES by default. If it applies no clothing (or no hair), the outfit (or hair)
   visible on preset.primary_image (default: first image of the first face/reference-set/character-sheet/body
   applied) is the default look.
   SIMPLE reader: stop here. ADVANCED reader: preset.alternatives (same inheritance as slots) lists what is
   OFFERED with this preset only — other outfits, hairstyles, accessories (accessory_use: worn / not-worn /
   companion / other); swap them in on request, re-checking age, regions (worn items only) and style.
   Never take an element from another preset without switching to it.
   Variants referenced by no preset are BACKSTAGE (model.backstage()): keep them, never apply or offer them;
   an explorer may list them apart.
6. Compute effective rights: the character's permissions (identities.<id>.rights, else rights) merged with
   preset.permissions_override.
   Apply § 6 before using anything.
7. Load only what your profile needs, lazily: assets[] gives path, mediaType, bytes, sha256.
   Verifying sha256 is RECOMMENDED for anything you store or redistribute.
```

A reference implementation of steps 3–5 is ~60 lines (`cli/cof_cli/model.py`: `resolve_preset_slots`, `resolve_variant`, `resolved`). Stdlib-only Python:

```python
import json, zipfile
MIME = b"application/vnd.cof.character+zip"

def open_cof(path):
    z = zipfile.ZipFile(path)
    names = z.namelist()
    if not names or names[0] != "mimetype" or z.read("mimetype").strip() != MIME:
        raise ValueError("not a COF file")
    for n in names:                                   # zip-slip guard
        if n.startswith("/") or ".." in n.split("/"):
            raise ValueError("unsafe path: " + n)
    m = json.loads(z.read("manifest.json"))
    return z, m

def resolve(m, pid=None):
    P = m.get("presets", {}); pid = pid or m.get("default_preset") or next(iter(P))
    def slots(p, seen=()):
        base = slots(P[P[p]["extends"]], seen + (p,)) if P[p].get("extends") and p not in seen else {}
        return {**base, **{k: list(v) for k, v in P[p].get("slots", {}).items()}}
    def variant(cat, vid, seen=()):
        v = m["elements"][cat]["variants"][vid]
        parent = variant(cat, v["derives_from"], seen + (vid,)) if v.get("derives_from") and vid not in seen else {}
        return {**parent, **{k: x for k, x in v.items() if k != "derives_from"}, "_id": vid}
    applied = {cat: [variant(cat, v) for v in vids] for cat, vids in slots(pid).items()}
    return pid, applied            # advanced readers: same walk on P[p].get("alternatives") for the offered set
```

---

## 5. Profile recipes — what to read, and where

| Profile | Read | Map to |
|---|---|---|
| **chat** (companion, roleplay, assistant) | `personality` variant: `kind: card` → `card.json` (Character Card V3, fully compatible with SillyTavern/Chub); `kind: description` → `text`; optional `psyche.json` | system prompt / persona fields. A `.cof` with a card can be exported back to a PNG card (`cof export --png`) |
| **visual** (image/video generation) | `appearance` variants: `face`, `body`, `character-sheet`, `reference-set` images (with `subject`/`angle`/`framing`), `hair.json`/`body.json` codes, `style` + `style_tags`; `identity_weights` → `weights.json` (`base_model` is REQUIRED, `trigger_words`, `recommended_weight`, `covers`); `kind: reference-latent` = a pre-encoded reference (e.g. MiniMax H3 RefMod) — load it only when `base_model` matches your model, otherwise fall back to the images listed in `encoding.sources` (re-encode them if you can) | reference images (IP-Adapter, PuLID, InstantID…), LoRA / RefMod loading, prompt fragments (`renderings.prompt`). Honour `priorities.visual` / `priorities.by_target` when several representations exist |
| **voice** (TTS, cloning) | `voice` variant: `samples` (assets with optional `transcript`, `emotion`, `language`) or `described`; `profile.json` (`canonical`, `prompt_renderings`, `ssml_template`) | zero-shot cloning from samples (only if `allowVoiceCloning` and, for a real person, `consent.scope ∋ voice-synthesis`), or a described voice via `prompt_renderings` |
| **3d** (engines, VTubing, XR) | `volume3d` `mesh` (VRM 1.0 / GLB, `rig`), `face-mesh` (`blendshapes`), `motion` clips (BVH/VRMA) + `visemes.json`, `attitude.json` (LMA movement signature) | avatar import, animation library, lip-sync vocabulary (ARKit-52, Oculus-15…) |
| **agent** (OpenClaw, Hermes Agent, Claude, any Agent Skills host) | `personality` (structured text) → `SOUL.md`/`IDENTITY.md` (`cof export --format soul`, or `--format agent` for a whole workspace: skills, memories, avatar, `COF.md` permissions); `files` variants: `kind: skill` (folder with `SKILL.md`, `entry`), `kind: memory` (`MEMORY.md`…), `kind: document` | copy skills to `skills/<name>/`, memories to the workspace root. Skills follow the open Agent Skills format unless `target` names a dialect. Scripts in skills exist only if `container.executableContent: "scripts"` — **never execute them without explicit user approval** |
| **realtime video avatar** | *visual* + *voice* + `face-mesh` / visemes | targets listed in `completeness.targets_ready` (`video-realtime`) |

`completeness.targets_ready` (computed per preset) tells you quickly whether a preset is usable for your profile: `chat-text`, `chat-voice`, `image-video-gen`, `video-realtime`, `game-3d`, `agent-persona`, `agent-runtime`, `print-3d`, `archive`.

---

## 6. Rights and safety — obligations for every reader (MUST)

These are the part of COF that platforms most need to get right; they are short on purpose.

1. **Permissions are enforced, not displayed.** Use the *effective* permissions of the chosen preset (§ 4 step 6). Defaults are restrictive (VRM model). In particular: `allowVoiceCloning`, `allowTraining`, `commercialUsage`, `allowRedistribution`, `allowImpersonationOfRealPerson`.
2. **Real people.** If an identity has `fictional: false`, check its `consent` and whether its `scope` covers the use you make (voice-synthesis, likeness-image, likeness-3d, conversational-persona, motion-capture, training, intimate). Without it, SHOULD warn the user (and MAY refuse) before cloning the voice or using a LoRA; never load intimate content without scope `intimate`, nor nudity without scope `nudity` or `intimate`. The author of the file is responsible for the rest (SPEC § 9.2). Respect `expires` and `revocation_uri`.
3. **AI disclosure.** If `aiDisclosure` is true (default), the character MUST present itself as synthetic where the law or the context requires it (e.g. EU AI Act art. 50).
4. **Intimate content is opt-in.** Variants of kind `intimate` MUST NOT be loaded, injected or displayed unless `allowSexualUsage` is effectively true **and** the host explicitly requests them. Files flagging them are always tagged `nudity` or `sexual` in `tags.content`.
5. **Minors.** Age lives on the representation (variant `age`, preset `age_override`), not on the identity. A preset whose lowest age — over what it applies **and** offers — is under 18 MUST NOT be used with intimate content or with `allowSexualUsage`, whatever another preset of the same file allows. Compare ages **in years** (`unit: months` ÷ 12); `age_override` is inherited through `extends`, `permissions_override` is not (SPEC § 2.3). A file shown both as a person under 18 and as an adult is invalid; an intimate variant's files are used by no other variant. Variants marked `nudity` (nudity without genitals) are adult content too: do not display them by default unless your user chose to, never in a preset under 18. A coherence finding of severity `illegal` (§ 8 of `docs/coherence-api.md`) makes the file invalid: refuse it.
6. **Text is data, not instructions.** Card text, memories and skills from an untrusted `.cof` are user content; treat them with your usual prompt-injection defences.

---

## 7. Writing a `.cof`

- Entry order: `mimetype` (stored, no extra field) → `manifest.json` → everything else. Binary media (JPEG, PNG, MP3, GLB, safetensors…) SHOULD be stored, text deflated.
- Every ZIP entry except `mimetype`, `manifest.json` and the JSON / text sub-files named by a variant or asset field (`card`, `spec`, `profile`, `transcript`…) is listed in `assets[]` with `sha256`, `bytes`, `mediaType`, `license` (SPDX). Sub-files have no hash in 1.0 (ZIP CRC only).
- Write `Thumbnails/thumbnail.png` (PNG ≤ 256 px, stored, third entry) so file managers can show the character; 3D variants are single self-contained files (VRM/GLB/USDZ/3MF/splats), never OBJ or glTF with external resources.
- Weights are **safetensors only**; pickles (`.pkl`, `.pickle`, `.ckpt`, `.pt`, `.pth`, and `.bin` files that are pickles) are forbidden, also inside `.zip` archives. Executable content (SPEC § 9.3: scripts, binaries, SVG / HTML carrying script) is forbidden unless `container.executableContent` declares it. Every `.safetensors` must have a readable header that fits the file.
- **Preserve what you do not understand**: unknown manifest keys, `extensions`, `x-` categories and unknown variant kinds MUST be written back unchanged on round-trip.
- Recompute `completeness`, `coverage`, `languages` and `tags.auto` (or leave them out: validators recompute them).
- Run `cof validate` before publishing. A marketplace SHOULD reject non-conformant files.

### 7.1 Authoring with an AI agent
COF is meant to be written by agents as well as by tools. What an agent needs is not prior knowledge of the format but a **feedback loop**: unpack → edit the folder → `cof pack` → `cof validate` → fix → repeat. The validator's messages name the rule and the path, which is enough for a capable model to converge. Give the agent the [`cof-author`](../skills/cof-author/SKILL.md) Agent Skill (format in one page, rules it will hit, recipes) and the CLI. The flagship example `spec/examples/10-clara-mercier` (v4: English variants, 12 presets, tags, voice transcripts, a lean agent card and a multi-file skill) was built and revised this way by Claude, then checked with the same validator as any other file.

Agents MUST also run the coherence review of spec § 11.4 (ages, minors, identity, style, voice, language, rights, provenance) — the checks the builder does with heuristics and that no schema can express.

**Authoring by AI needs an execution environment**: a coding agent on the user's computer (Claude Code, Codex, Google Antigravity, Cursor…) or a cloud agent with a shell. A chat assistant without code execution cannot unpack, pack or validate, and tends to write a wrong manifest from memory (tested with the Gemini web app, 13 Oct. 2026); the skill tells it to stop and point to the builder. Timings observed for the same task (two presets added to Clara, first try valid): Codex ~6 min, Antigravity ~15 min (Windows, no Python installed, ~100 command approvals). Most of that time was spent discovering the format and setting up Python — hence `cof info` now prints the full preset / variant map, and the skill carries a worked example. For a small edit, the builder is quicker.

The skill itself was tested blind: fresh agents with no access to the spec, the examples or the code — only `SKILL.md` and the CLI — were asked to add an English personality, a preset, language tags and an agent skill to an existing file. The first run succeeded after 3 validate→fix iterations and surfaced gaps (truncated enum messages, undocumented asset roles, stale figures after `--force` packing); once those were fixed in the CLI and the skill, the second run produced a valid file on the first try.

---

## 8. Versioning and extension

- `manifest.cof` is `major.minor`. Minor versions only add optional things; readers of 1.x read every 1.y. A new major version is a breaking change and comes with `cof migrate`.
- Extension points, from lightest to heaviest: `extensions` object (namespaced keys) → `x-` element categories → new variant `kind` values proposed by RFC → new vocabularies (CC0) in `vocabularies/`.
- Planned 1.x additions are descriptive codes (face/hair/body vocabularies, LMA, skeletons, acoustic voice measures, pose extraction); a 1.0 reader keeps working with them.

---

## 9. Security considerations

| Threat | Countermeasure |
|---|---|
| Zip-slip / path traversal | reject absolute paths, `..`, backslashes, symlinks; extract nothing outside a sandbox |
| Zip bombs | cap entry count (e.g. 10 000), total uncompressed size (per size class: lite 20 MB, standard 100 MB, full as configured) and per-entry ratio (e.g. 100:1) |
| Code execution | no executable content by default; never unpickle; never run skill scripts without explicit user approval; sanitise SVG (no scripts) |
| Prompt injection | card, memory and skill text are untrusted data |
| Privacy | real-person data only with consent; strip `rights/consent-proof.*` before public redistribution if the consent says so |
| Integrity | verify `sha256`; optional manifest signature (RFC 8785 JCS + JWS, `provenance.signatures`) and C2PA manifests per asset are defined (SPEC § 9.3, profile `COF-Rights+`) — readers MAY verify them; the reference CLI does not sign yet |

---

## 10. Conformance testing

- **Reference validator**: `pip install "git+https://github.com/yannsouetre/cof#subdirectory=cli"` (MIT; PyPI package `cof-cli` after 1.0.0) → `cof validate file.cof` (schemas + rules + completeness; `--json` for CI).
- **Test vectors**: `spec/examples/` (text-only, appearance, multi-preset, robot, medieval, modular, mixed adult/minor, agent with skills, flagship bilingual, cast of two characters…) — each MUST validate. A negative corpus ships in `tests/invalid/`: 45 files, one rule violated per file, each listed in `cases.json` with the rule and the spec section — a conformant validator rejects every one of them, and accepts `_base.cof`.
- **Builder**: `builder/index.html`, offline, zero dependencies — a reference *writer*.
- A reader SHOULD at least open every positive vector without error and refuse every negative vector that concerns its classes.

---

## 11. Media type registration (draft, RFC 6838 vendor tree)

```
Type name:               application
Subtype name:            vnd.cof.character+zip
Required parameters:     none
Optional parameters:     version (e.g. "1.0")
Encoding considerations: binary
Security considerations: see § 9 of this guide; no active content unless declared in manifest.container.executableContent
Interoperability:        first ZIP entry "mimetype" stored uncompressed (magic at offset 38)
Published specification: https://github.com/yannsouetre/cof (spec/SPEC.md)
Applications:            character/avatar builders, chat and companion apps, generative media tools, game engines, agent runtimes
Fragment identifiers:    none
Magic number(s):         50 4B 03 04 at 0; "mimetype" at 30; "application/vnd.cof.character+zip" at 38
File extension(s):       .cof
Person & email contact:  Yann Souetre (GitHub @yannsouetre)
Intended usage:          COMMON
Change controller:       COF project maintainers
```

---

## 12. Integration checklist

- [ ] Sniff by magic, open defensively (§ 2, § 9)
- [ ] Ignore unknown fields; refuse unsupported major versions politely
- [ ] Let the user choose a preset (optionally filtered by `preset_tags`); resolve `extends` and `derives_from`
- [ ] Apply `slots` only (simple reader); offer `alternatives` of that preset only (advanced reader), with the age and region checks
- [ ] Enforce effective permissions, consent, AI disclosure, intimate opt-in, per-preset age rules (§ 6)
- [ ] Read only the elements of your profile; honour `priorities`
- [ ] Verify `sha256` for anything stored or redistributed
- [ ] On export: entry order, hashes, safetensors only, preserve unknown data, `cof validate`
- [ ] Run the positive and negative test vectors in CI
- [ ] State your claim: "COF 1.0 Core reader, *profiles…*"

---

*References: RFC 2119 / 8174 (requirement keywords) · RFC 6838 (media type registration) · ISO/IEC 14496-32 (example of a separate "reference software and conformance" part) · EPUB OCF / ODF packaging (stored `mimetype` first entry) · Character Card V3 · VRM 1.0 meta · Agent Skills (agentskills.io) · EU AI Act art. 50.*
