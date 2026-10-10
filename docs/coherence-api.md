# Passerelle de contrôle de cohérence (builder → IA au choix) — contrat v0.1

Le builder peut déléguer le **contrôle de cohérence** d'un preset à une IA choisie par l'utilisateur. Deux modes :
1. **API OpenAI-compatible** (`POST {base_url}/chat/completions`, modèle avec vision) : le builder construit un message système + un message utilisateur contenant le *dossier de preset* ci-dessous (texte + vignettes en `image_url` base64) et demande une réponse JSON stricte.
2. **Intégration native** : une plateforme qui embarque le builder appelle sa propre IA avec le même dossier et renvoie le même résultat.

## Dossier de preset (`cof coherence-bundle <dir> --preset <p>`)
```jsonc
{
  "cof": "0.3", "character": { "name": "…", "age": { "value": 34 }, "fictional": true, "morphology": { "class": "humanoid", "species": "human" }, "languages": ["fr"] },
  "preset": { "id": "default", "label": "…", "style": "photo-realistic", "age_override": null },
  "elements": {
    "personality": { "summary": "…", "gender_presentation_declared": "feminine", "age_in_text": 34 },
    "face":  { "style": "photo-realistic", "thumbnails": ["data:image/jpeg;base64,…"] },
    "body":  { "style": "photo-realistic", "thumbnails": ["…"] },
    "hair":  { "code": { "length": 5, "color_base_hex": "#4d2f27" } },
    "outfit":{ "prompt": "khaki cotton utility jacket…" },
    "voice": { "canonical": { "gender_presentation": "feminine", "age_perceived": "30s", "accent": "fr-FR" }, "sample_languages": ["fr"] },
    "identity_weights": { "base_model": "FLUX.1-dev", "covers": ["face", "hair", "body"], "trigger_words": ["…"] }
  },
  "checks_requested": ["gender", "age", "species", "style", "language", "weights-vs-images"]
}
```

## Réponse attendue (JSON strict)
```jsonc
{ "score": 92,
  "issues": [
    { "severity": "major", "elements": ["voice", "face"], "check": "gender", "message": "La voix est perçue masculine, le visage et le texte sont féminins." },
    { "severity": "minor", "elements": ["outfit"], "check": "style", "message": "Tenue décrite en style manga dans un preset photo-réaliste." } ] }
```
Le builder écrit le résultat dans `presets.<p>.coherence` avec `method: "ai-api" | "platform-native"`, `computed_by` (nom du modèle), `computed_at`. Les contrôles **heuristiques locaux** (sans IA) produisent le même format avec `method: "heuristic"`. Un score bas n'invalide jamais le fichier.
