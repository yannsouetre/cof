# COF — Character Open File

**One character = one file. Open, portable, consented.**

COF is an open file format (`.cof`, a ZIP container) that bundles everything that defines an AI character: personality, appearance (photos, vector code, description), voice, 3D body, motion — **and** its rights, consent and provenance. The same file opens in a chat app, an image or video generator, a game engine, Blender, or serves as the "soul" of an agent.

> Status: **working draft** — specification v0.5, reference tooling 0.7.2 (October 2026). Nothing is frozen yet; feedback is welcome through the RFCs.

## Why
- No more juggling PNGs, WAVs, VRMs, LoRAs and scattered notes.
- Never locked into a platform: COF is the *export* format that proprietary tools don't offer.
- Compliant by construction: permissions, content tags, consent and "synthetic content" labeling live in the manifest.

## What's in a `.cof`
A `.cof` is a ZIP archive with a `mimetype` entry first and a `manifest.json` second, followed by the character's elements and rights:

| Part | Content |
|---|---|
| `manifest.json` | Identities, element variants, presets, tags, permissions, provenance, completeness KPI |
| `elements/` | 7 media categories — personality (Character Card V3, psyche, free text), appearance (face/body views, character sheets, loose photos, hair/body codes), identity weights (LoRA), 3D, voice (samples + profile), postures, motion — plus a `files` library (agent skills, memories) |
| `rights/` | Consent record and proofs when a real person is depicted |
| Presets | Named combinations of variants (e.g. adult / young, realistic / anime), each with its own depicted age and coherence report |

See [`spec/SPEC.md`](spec/SPEC.md) for the full definition.

## Quick start
**Build a file in the browser** — no install, nothing leaves your machine:
<https://yannsouetre.github.io/cof/builder/>

**Validate with the CLI** (Python):
```bash
pip install -e cli
cof validate file.cof                          # a .cof file or an unpacked folder
cof validate spec/examples/01-lea-text-only
cof pack spec/examples/01-lea-text-only -o lea.cof
cof export lea.cof --format png -o lea.png     # → PNG card (chara + ccv3 chunks)
```
More commands (import, export to SOUL.md/IDENTITY.md, migrate, tokens…) in [`cli/README.md`](cli/README.md).

**Let an AI agent write it** — COF is designed to be authored by agents: give yours the [`cof-author`](skills/cof-author/SKILL.md) skill (or point it to [`llms.txt`](llms.txt)) and the CLI; it edits an unpacked folder, packs, validates and loops until `cof validate` says OK. The flagship example, Clara Mercier v4 (12 presets, two languages, tags, an agent skill), was assembled and updated this way by Claude.

## Open, with discipline
COF is deliberately flexible: almost everything is optional, unknown keys survive round-trips, and there are explicit escape hatches — a 3D file without its textures (`self_contained: false`), LoRA weights by link instead of embedded, custom `x-` categories. That openness only works with **discipline in what goes in**: the validator blocks what is unsafe or broken (minors and intimate content, missing hashes, unresolved references, undeclared executables…), warns about what is risky (links that can rot, untextured 3D, missing transcripts…), and every author — human, tool or AI agent — runs the coherence review of [spec § 11.4](spec/SPEC.md) before publishing: ages, identity, style, voice, language, rights, provenance.

## Repository layout
| Folder | Content |
|---|---|
| `spec/` | The specification (`SPEC.md`, French original `SPEC.fr.md`), JSON Schemas, examples |
| `vector/` | COF-Vector: the "SVG of the face, body and clothing" |
| `vocabularies/` | Vocabularies and mapping tables (CC0) |
| `rfcs/` | Change proposals |
| `docs/` | Implementer guide, state of the art, roadmap, completeness/tags/coherence rules |
| `cli/` | Command-line tool (`validate`, `pack`, `import`, `export`, `migrate`…) |
| `builder/` | The web builder (single HTML page) |
| `skills/` | Agent Skills for working with `.cof` files (`cof-author`) |

## Key documents
- [`spec/SPEC.md`](spec/SPEC.md) — the specification
- [`docs/IMPLEMENTING.md`](docs/IMPLEMENTING.md) — how to read and write `.cof` files in your tool
- [`spec/examples/`](spec/examples/) — 10 conformant example characters
- [`skills/cof-author/SKILL.md`](skills/cof-author/SKILL.md) — the skill that teaches an AI agent to create and update `.cof` files
- [`spec/schemas/`](spec/schemas/) — JSON Schemas (draft 2020-12)
- [`CHANGELOG.md`](CHANGELOG.md), [`CONTRIBUTING.md`](CONTRIBUTING.md), [`GOVERNANCE.md`](GOVERNANCE.md)

## Embrace, don't replace
A `.cof` contains a valid Character Card V3 and exports to `ccv3` PNG, `.charx`, `SOUL.md`/`IDENTITY.md`, `.vrm`. Existing tools have nothing to rewrite.

## License
| Part | License |
|---|---|
| Code (`cli/`, `builder/`, `vector/py`, scripts) | MIT — see [`LICENSE`](LICENSE) |
| Specifications (`spec/SPEC.md`, `vector/SPEC.md`, `rfcs/`, `docs/`) and examples (`spec/examples/`) | CC BY 4.0 |
| Vocabularies, mapping tables and schemas (`vocabularies/`, `spec/schemas/`) | CC0 1.0 |

Details in [`LICENSES.md`](LICENSES.md). Requested attribution for the specifications: "COF — Character Open File, Yann Souetre, https://github.com/yannsouetre/cof".

---

*COF — Character Open File, by Yann Souetre. French version of this page: [`README.fr.md`](README.fr.md).*
