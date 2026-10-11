# Coherence check gateway (builder → AI of your choice) — contract v0.1

The builder can delegate the **coherence check** of a preset to an AI chosen by the user. Two modes:
1. **OpenAI-compatible API** (`POST {base_url}/chat/completions`, vision-capable model): the builder builds a system message + a user message containing the *preset bundle* below (text + thumbnails as base64 `image_url`) and requests a strict JSON response.
2. **Native integration**: a platform that embeds the builder calls its own AI with the same bundle and returns the same result.

## Preset bundle (`cof coherence-bundle <dir> --preset <p>`)
```jsonc
{
  "cof": "0.5",
  "character": { "name": "…", "age": { "value": 34 },   // preset age (lowest of its variants), null if unknown
                 "fictional": true, "morphology": { "class": "humanoid", "species": "human" }, "languages": ["fr"] },
  "preset": { "id": "default", "label": "…", "style": "photo-realistic", "age_override": null },
  "elements": {
    "personality": { "summary": "…", "gender_presentation_declared": "feminine", "age_in_text": 34 },
    "face":  { "style": "photo-realistic", "age_declared": 34, "age_basis": "apparent", "thumbnails": ["data:image/jpeg;base64,…"] },
    "intimate": { "age_declared": 34 },                         // present ⇒ age-legality check mandatory
    "body":  { "style": "photo-realistic", "thumbnails": ["…"] },
    "hair":  { "code": { "length": 5, "color_base_hex": "#4d2f27" } },
    "outfit":{ "prompt": "khaki cotton utility jacket…" },
    "voice": { "canonical": { "gender_presentation": "feminine", "age_perceived": "30s", "accent": "fr-FR" }, "sample_languages": ["fr"] },
    "identity_weights": { "base_model": "FLUX.1-dev", "covers": ["face", "hair", "body"], "trigger_words": ["…"] }
  },
  "checks_requested": ["gender", "age", "species", "style", "language", "weights-vs-images", "clothing", "age-legality"]
}
```

## Expected response (strict JSON)
```jsonc
{ "score": 92,
  "issues": [
    { "severity": "major", "elements": ["voice", "face"], "check": "gender", "message": "The voice is perceived as masculine; the face and text are feminine." },
    { "severity": "minor", "elements": ["outfit"], "check": "style", "message": "Outfit described in manga style in a photo-realistic preset." } ] }
```
### `age-legality` check (severity `illegal`)
If the bundle contains an `intimate` variant, the checker **must** estimate the apparent age of every face and body image. If an image clearly looks underage (< 18, with a margin) while the declared age is adult, it returns `{ "severity": "illegal", "check": "age-legality", "elements": [...], "message": "..." }`. The builder displays this issue in red as an **illegal combination** and refuses to build the file as long as it remains; a reader that receives a file carrying such an issue in `presets.<p>.coherence` must treat it as invalid. Severities `info | minor | major` remain non-blocking.

The builder writes the result to `presets.<p>.coherence` with `method: "ai-api" | "platform-native"`, `computed_by` (model name), `computed_at`. **Local heuristic** checks (no AI) produce the same format with `method: "heuristic"`. A low score never invalidates the file; only an `illegal` issue blocks.
