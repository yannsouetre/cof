# Example 10 — Clara Mercier (flagship)

One character, **six presets**, one file: young adult (default), manga style, 12-year-old, 65-year-old, near-future combatant, and an AI-agent persona. Four voices (one per age group), three OpenPose poses, free-text and structured personalities.

What it demonstrates:
- **Presets with inheritance** — every preset `extends` the default and only replaces personality, appearance and voice.
- **Age on the representation** — each appearance variant declares its depicted age (12, 29, 65; `basis: apparent`); the 12-year-old preset is a minor preset and the validator applies the § 9.4 rules to it alone.
- **Libraries** — the OpenPose poses are a posture library shared by all presets.
- **Agent use** — the *Clara AI Agent* preset uses a Character Card V3 (structured text) exportable to `SOUL.md`.

Provenance: texts and character sheets generated with Google Gemini; images with Google Gemini (Nano Banana 2); voices with ElevenLabs and Typecast. Fictional character; any resemblance to a real person is coincidental.

License: character, texts and images **CC BY 4.0** — Yann Souetre. Voice samples: `LicenseRef-COF-pending-voice-terms` until the terms of the voice generation plans are confirmed.
