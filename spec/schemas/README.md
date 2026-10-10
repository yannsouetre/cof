# Schémas JSON (draft 2020-12) — COF v0.5

| Schéma | Fichier validé | Référencé par | Notes |
|---|---|---|---|
| `manifest.schema.json` | `manifest.json` | — | racine ; `$defs/consent` est une copie synchronisée de `consent.schema.json` |
| `card.schema.json` | `elements/personality/<v>/card.json` | `variant.card` | sous-ensemble vérifié de Character Card V3 (`extensions.cof` : behavior, goals, fears, language) |
| `psyche.schema.json` | `elements/personality/<v>/psyche.json` | `variant.psyche` | Big Five / HEXACO [0,1], traits custom avec `evidence`, buts, craintes, valeurs, contradictions, émotion de base (catégorie + PAD), rendus |
| `weights.schema.json` | `elements/identity_weights/<v>/weights.json` | `variant.spec` | `base_model.name` obligatoire ; `format` safetensors seulement ; `covers` disjoints par preset |
| `voice-profile.schema.json` | `elements/voice/<v>/profile.json` | `variant.profile` | profil canonique, VPA ordinal, échantillons (transcription facultative), `engines[]` périssables, empreinte « verification-only » |
| `attitude.schema.json` | `elements/{posture,motion}/<v>/attitude.json` | `variant.spec` (kind `attitude`) | LMA Effort (4 axes −1…+1, 8 actions), Shape, tempo, postures BAP, gestes BML → `expresses: [trait:…]`, regard, proxémie, démarche, `poses[]` |
| `pose.schema.json` | `pose.json` | `attitude.poses[].path`, `variant.pose` | points-clés 2D normalisés `[x,y,c]`, squelette déclaré (`openpose-body25`, `coco-18`, `coco-wholebody-133`, `mediapipe-pose-33`, `h36m-17`), nombre de joints imposé par squelette, mains/visage optionnels, `render` (bonhomme PNG) |
| `skeleton.schema.json` | entrées de `vocabularies/skeletons-1.0.json` | — | définition d'un squelette : joints + parent + correspondance vers le squelette **canonique COF** ; axes, unités, pose de repos |
| `hair.schema.json` | `elements/appearance/<v>/hair.json` | `variant.code` (kind `hair`) | COF-HAIR-1 : longueur / courbure / densité 0–9, couleurs hex, gris %, coiffure, raie, frange |
| `body.schema.json` | `elements/appearance/<v>/body.json` | `variant.params` (kind `body`) | taille, carrure, mesures ISO 7250, phénotypes Anny, β SMPL-X, teint (Monk / Fitzpatrick), `estimated` + `confidence` |
| `consent.schema.json` | `rights/consent.json`, `identities.<id>.consent` | — | personne réelle : `scope[]` (dont `intimate`), dates, juridictions, preuves (sha256 obligatoire si fichier joint), âge du sujet ≥ 18 |
| `visemes.schema.json` | `elements/motion/<v>/visemes.json` | `variant.visemes` | vocabulaire des visèmes des clips (ARKit-52, Oculus-15, Preston Blair, Unified Expressions, custom + mapping) |

Règle : `cof validate` valide chaque sous-fichier référencé par une déclinaison contre son schéma (erreur, pas avertissement : ces fichiers sont produits par le builder ou la CLI). Les sous-fichiers non listés (ex. `outfit.json`, `voice.vec.json`, `face.mesh`) ne sont pas encore schématisés — voir `docs/design-notes-phase0.md`.
