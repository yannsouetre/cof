# Example 10 — Clara Mercier (flagship, bilingual)

One character, **twelve presets in two groups**, one file:

| Group | Presets |
|---|---|
| **English** | young adult (**default**), manga, at 12, at 65, near-future combatant, AI agent |
| **Français** | jeune adulte, manga, à 12 ans, à 65 ans, combattante du futur, agent IA |

Ten personality variants (5 FR, 5 EN — free text and Character Card V3), five appearance variants shared by both languages, ten voices (one per age group and language), and an OpenPose posture library.

What it demonstrates:
- **Languages per variant** — the same images serve both languages; only personality and voice change.
- **Presets with inheritance** — English presets `extend` the default; French presets extend `fr`, which itself extends the default and only swaps personality and voice.
- **Preset groups** — container-level folders (`preset_groups`), exportable one at a time: `cof extract clara.cof --group francais -o clara-fr/`.
- **Age on the representation** — each appearance variant declares its depicted age (12, 29, 65); the two 12-year-old presets are minor presets and the § 9.4 rules apply to them alone.
- **Agent use** — the *AI agent* presets use a Character Card V3 exportable to `SOUL.md`.
- **Built by an AI** — version 4 (English variants, voices wiring, presets and groups) was assembled programmatically by Claude from the French version, then validated with `cof validate`.

Provenance: texts and character sheets generated with Google Gemini, English versions translated with Claude; images with Google Gemini (Nano Banana 2); voices with ElevenLabs (model v4) and Typecast, free plans — *Voice generated with Typecast (https://typecast.ai)*. Fictional character; any resemblance to a real person is coincidental.

License: character, texts and images **CC BY 4.0** — Yann Souetre. Voice samples **CC BY-NC 4.0** (generated on free plans: non-commercial use only, with attribution to ElevenLabs and Typecast).
