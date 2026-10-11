# Example 10 — Clara Mercier (flagship, bilingual)

One character, **twelve presets tagged by language and by age**, one file:

| Language tag | Presets |
|---|---|
| **English** | young adult (**default**), manga, at 12, at 65, near-future combatant, AI agent |
| **Français** | jeune adulte, manga, à 12 ans, à 65 ans, combattante du futur, agent IA |

Ten personality variants (5 FR, 5 EN — free text and Character Card V3), five appearance variants shared by both languages, ten voices (one per age group and language, all with transcripts), and an OpenPose posture library.

What it demonstrates:
- **Languages per variant** — the same images serve both languages; only personality and voice change.
- **Presets with inheritance** — English presets `extend` the default; French presets extend `fr`, which itself extends the default and only swaps personality and voice.
- **Preset tags** — container-level tags in three facets: *language* (`en`, `fr`), *age* (`age-12`, `age-29`, `age-65`) and *usage* (`agent`, on the two AI-agent presets). Export any slice: `cof extract clara.cof --tag fr -o clara-fr/`, or the intersection `--tag en --tag age-12`.
- **Age on the representation** — each appearance variant declares its depicted age (12, 29, 65); the two 12-year-old presets are minor presets and the § 9.4 rules apply to them alone.
- **Agent use** — the *AI agent* presets use a short Character Card V3 (FR and EN system prompts aligned, exportable to `SOUL.md`) plus a shared **skill** in the `files` category: `accessible-color-palette` — a multi-file Agent Skill (`SKILL.md`, exact colour maths, a worked palette with computed WCAG ratios) for building harmonious, accessible colour systems in OKLCH. Persona facts live in the card fields, expert know-how lives in the skill.
- **Built by an AI** — version 4 (English variants, voices wiring, presets and tags) was assembled programmatically by Claude from the French version, then validated with `cof validate`.

Provenance: texts and character sheets generated with Google Gemini, English versions translated with Claude; images with Google Gemini (Nano Banana 2); voices with ElevenLabs (model v4) and Typecast, free plans — *Voice generated with Typecast (https://typecast.ai)*. Fictional character; any resemblance to a real person is coincidental.

License: character, texts and images **CC BY 4.0** — Yann Souetre. Voice samples **CC BY-NC 4.0** (generated on free plans: non-commercial use only, with attribution to ElevenLabs and Typecast).
