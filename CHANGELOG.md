# Changelog

## 0.4.0 — 2026-10-10
- **Éléments en 7 catégories par nature de média** (personnalité, apparence, poids d'identité, 3D, voix, postures, mouvements) ; chaque déclinaison déclare son **type** (`kind`) : visage, corps, cheveux, vêtement (+ type de vêtement), accessoire, intime, pilosité (zone), particularité, character sheet, photos en vrac, description… ; maillage / maillage facial / nuage de points / impression ; photo(s) de pose, OpenPose, silhouette, attitude ; clips / vidéo (plafond 20 Mo) / description.
- **Presets à emplacements multiples** avec règles : une déclinaison par type sauf cumulables ; conflits par **région du corps et couche** (vocabulaire `garments-1.0`), accessoires par région, une pilosité par zone, LoRA à `covers` disjoints ; règles désactivables par preset.
- **Identités multiples** dans un fichier (casting), presets rattachés à une identité, consentement par identité, racine = copie de l'identité par défaut ; `morphology.class` gagne `human` (défaut), `humanoid` = non-humain de forme humaine.
- Langues portées par les déclinaisons (personnalité, échantillons) ; racine = union calculée.
- `cof merge` (mêmes nom + surnom ⇒ même identité), `cof extract --preset`, `cof migrate` v0.2/v0.3 → v0.4.
- Builder v0.4 : identités multiples, 7 catégories avec icônes, type obligatoire par déclinaison, presets à cases multiples avec détection de conflits en direct, importer-fusionner, exporter un preset, plafond vidéo avec alerte.

## 0.3.0 — 2026-10-10
- Architecture modulaire : éléments → déclinaisons (`derives_from`) → presets (`extends`, `default_preset`, `age_override`) ; KPI par preset ; `coverage` ; fichiers multi-personnages ; `priorities` (générales et par cible).
- Nouveaux éléments : `identity_weights` (LoRA & co., modèle de base obligatoire), `hair`/`facial_hair`/`body_hair`/`intimate`/`outfit`/`accessories` séparés ; maillage spatial de visage (`face.mesh`, topologies FLAME / MediaPipe / ARKit / MetaHuman / custom).
- Styles visuels (`visual-styles-1.0`) sur images, déclinaisons et presets ; KPI de cohérence déclaré + contrat d'API (`docs/coherence-api.md`).
- Post-traitements (canny/lineart/softedge…) rétrogradés en **dérivés optionnels** (`derived/`), jamais comptés.
- `cof migrate` v0.2 → v0.3 ; `cof export --preset` ; exemple 07 modulaire (2 personnalités, LoRA fictif, 2 presets).

## 0.2.0 — 2026-10-09
- Spécification v0.2 : usages cibles, niveaux de représentation (médias / code vectoriel / descriptif), portée morphologique, KPI de complétude, slots de tags, code vocal COF-Voice, poses OpenPose, vocabulaire de squelettes, builder et compression.
- Note de conception COF-Vector (vector/SPEC.md).
- JSON Schema du manifeste et exemple validé.
- État de l'art (docs/state-of-the-art.md) et feuille de route (docs/roadmap.md).

## 0.1.0 — 2026-10-09
- Première rédaction de la spécification (brouillon interne).
