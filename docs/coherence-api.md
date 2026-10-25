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
  "checks_requested": ["gender", "age", "species", "style", "language", "weights-vs-images", "clothing", "element-consistency", "age-legality", "nudity"]
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

### `element-consistency` check
Each image is sent preceded by a short text naming its variant (id, type, label). The images of **one variant must show the same thing**: the same place for `environment` (different framings, angles or times of day are fine), the same garment or accessory for `clothing` and `accessory`, the same person for `face`, `body`, `reference-set` and `character-sheet`. Otherwise → severity `minor`, naming the variant and advising one variant per place, garment or person. A preset may hold several `environment`, `clothing`, `accessory`, `pilosity` and `feature` variants (SPEC § presets, `single_per_kind`): several places go in several variants, not in one.

### `nudity` check
The checker looks at every image of the preset. **Visible genitals or a sexual act in a variant that is not `intimate`** → severity `illegal` (misclassification: such images belong only in `intimate`; the builder refuses to build). **Nudity without genitals in a variant not marked `nudity`** → severity `major`: the builder asks the author to confirm and mark the variant (`nudity: true`, `tags.content` `nudity`). **Any nudity on an image that looks underage**, or in a preset under 18 → severity `illegal`. What counts as nudity differs between countries; the checker reports, the author decides within the rules above.

### `memory-timeline` check (COF 1.1, RFC 0002 § 6.2)
When the bundle carries memories (gists in timeline order, the thumbnails of memory media labelled by node), the checker also returns, as `info` or `minor`: a preset younger than a memory it lists; a `part-of` moment whose dates fall outside its period; a moment linked `after` a period whose dates contain it (information: the link wins); ages and dates of one character implying different birth years; a memory placed somewhere the character never declared (a place, a person) when the gists make it plain. The `age-legality` and `nudity` checks run on memory media as on the others; the media of an `explicit` node are in the bundle only when the host allows adult content.

The builder writes the result to `presets.<p>.coherence` with `method: "ai-api" | "platform-native"`, `computed_by` (model name), `computed_at`. **Local heuristic** checks (no AI) produce the same format with `method: "heuristic"`. A low score never invalidates the file; only an `illegal` issue blocks.
