# Example 11 — Léa & Martien (two characters, one file)

A **cast file**: two distinct characters travel together, each one a logical container with its own elements, presets, default preset and rights.

| Character | Presets | Rights |
|---|---|---|
| **Léa Marchand** (`lea-marchand`, default) | `default` (adult), `young` (14 — a minor preset) | root `rights`: personal non-profit, modification and redistribution allowed |
| **Martien** (`martien`) | `m1-default` | its own `identities.martien.rights`, which **replace** the root rights: no modification, no redistribution |

What it demonstrates:
- **Every element belongs to one character** (`identity` on each variant, required as soon as a file holds several characters); a preset only uses its own character's elements — Léa's face in a Martien preset is a blocking error.
- **Likeness never crosses characters**: a file carrying a face, a body, a voice, weights or a 3D character is used by one character only. **Neutral files may be stored once**: the studio background (`a-place-shared`) is one image used by two distinct environment elements, `env-lea` and `env-martien`; exporting either character copies it.
- **Per-character rights and default preset** (`identities.<id>.rights`, `identities.<id>.default_preset`); per-preset age rules still apply (`young`).
- **Built by `cof merge`** from examples 07 and 04 (Martien's rights made stricter first): the merge carried each source file's rights onto its character. Export one character back with `cof extract duo.cof --identity martien -o martien/` — its rights become the file's.

Images: see examples 07 and 04; the shared studio comes from example 10 (Google Gemini, CC BY 4.0).
