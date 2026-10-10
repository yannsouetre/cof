# COF — Character Open File
## Spécification v0.4 (brouillon de travail, 10 octobre 2026)

> **Statut** : brouillon d'auteur, RFC publique sur GitHub (`rfcs/`).
> **Licence** : spécification CC-BY-4.0 ; implémentation de référence MIT ; vocabulaires et schémas CC0.
> **Auteur** : Yann Souetre.
> **Nom** : *COF — Character Open File*, extension `.cof`, type MIME `application/vnd.cof.character+zip`.
> **v0.4** : éléments organisés en **7 catégories par nature de média**, chaque déclinaison déclarant son **type** (`kind`) ; presets à **emplacements multiples** avec règles de cumul par **région du corps** (vêtements, accessoires, pilosité, particularités, LoRA) ; **identités multiples** dans un fichier avec presets rattachés ; langues portées par les déclinaisons ; fusion et extraction de presets ; vidéos de mouvement plafonnées.
> v0.3 : architecture modulaire, poids d'identité, maillages, styles, dérivés optionnels, cohérence, priorités.
> Les choix s'appuient sur l'état de l'art (`docs/state-of-the-art.md`). Les parties « à inventer » sont marquées **[NOUVEAU]**.

---

## 0. En une page

Un fichier `.cof` est un **conteneur ZIP** qui réunit tout ce qui définit un ou plusieurs personnages synthétiques, sous une forme **modulaire** :

```
Fichier .cof
 ├─ Identité(s)        (nom, âge, morphologie ; plusieurs identités possibles = casting)
 ├─ Éléments, en 7 catégories par nature de média :
 │    personnalité (texte) · apparence (photos) · poids d'identité (LoRA) · 3D · voix · postures · mouvements
 │    └─ Déclinaisons, chacune avec un TYPE : visage f1, f2… ; vêtement « robe » o1, « bottes » o2 ; voix v1 « grave »…
 ├─ Presets             (une identité + une combinaison de déclinaisons ; un preset par défaut)
 └─ Droits, provenance, KPI (complétude, cohérence)
```

| Couche | Contenu | Brique réutilisée |
|---|---|---|
| Identité & manifeste | qui, quel âge, quels éléments/presets, quels assets, quels droits | JSON Schema 2020-12, SPDX, IPTC, JSON-LD |
| Personnalité | personnalité, buts, craintes, histoire, lore, traits typés | **Character Card V3** embarquée + `psyche.json` |
| Apparence | visage, cheveux, pilosité, corps, tenues — en images, maillages, paramètres, descriptif | JPEG/PNG, glTF/FLAME/Anny, Fashionpedia, GarmentCode, Monk |
| Poids d'identité **[NOUVEAU]** | LoRA / embeddings liés à un modèle de base | safetensors, Civitai/HF |
| Attitude physique | signature de mouvement, postures OpenPose | LMA, BAP, BML, OpenPose |
| Voix | échantillons + transcriptions, profil typé, code vocal | WAV, SSML, EmotionML, VPA |
| Volumétrie | avatar riggé, splat, version imprimable | VRM 1.0 / glTF, SPZ, 3MF |
| Mouvement | clips, mapping de visèmes | BVH, VRMA |
| Dérivés **[NOUVEAU]** | post-traitements optionnels (cartes Canny/lineart/softedge…) | préprocesseurs ControlNet |
| Droits | permissions, consentement, provenance, signature | `VRMC_vrm.meta` étendu, C2PA |

Six principes :
1. **Englober, ne pas remplacer** — CCv3 embarquée ; exports PNG `ccv3`, `.charx`, `SOUL.md`, `.vrm`.
2. **Tout est optionnel sauf l'identité et les droits** ; un personnage « texte seul », « apparence seule » ou « voix seule » est valide. La complétude est un indicateur, pas une contrainte (§ 2.5).
3. **Modularité** — chaque élément peut avoir plusieurs déclinaisons ; les presets les combinent ; un preset par défaut est chargé à l'ouverture (§ 2.3).
4. **Une vérité, des projections** — chaque information n'est écrite qu'une fois ; les autres y renvoient (§ 6.1).
5. **Lisible par un humain et par un LLM** — JSON + Markdown ; tout code compact a aussi une forme en phrases.
6. **Aucun code exécutable, rien de chiffré, le consentement d'abord.**

### 0.1 Usages cibles (`targets`)

| Cible | Ce que l'outil lit en priorité | Exemples |
|---|---|---|
| `chat-text` | personnalité, lore, profils de tokens | SillyTavern, Risu, tout LLM |
| `chat-voice` | + voix (échantillons, code vocal) | Unmute, OpenAI Realtime, Hume |
| `video-realtime` | + visage (images/maillage), visèmes, attitude | HeyGen, Tavus, LiveKit + Audio2Face |
| `image-video-gen` | poids d'identité, images, dérivés, prompts | Flux/SDXL + ControlNet, Kling, Veo, Runway, Sora |
| `game-3d` | avatar riggé, mouvement, visèmes, droits → `meta` VRM | Unity, Unreal, Godot, VRChat, Blender |
| `agent-persona` | SOUL/IDENTITY dérivés, psyche, `aiDisclosure` | OpenClaw, agents OpenAI/Anthropic/xAI |
| `print-3d` | 3MF, licence | slicers |
| `archive` | tout, hashes, C2PA, consentement | dépôts, registres, conformité |

### 0.2 Niveaux de représentation

| Niveau | Nature | Qui le produit |
|---|---|---|
| **L2 — Média** | images (JPEG/PNG/WebP), audio, vidéo, maillages, avatars, splats | l'auteur |
| **L1 — Paramétrique** | FLAME/Anny, mesures, blendshapes, code vocal mesuré, points-clés OpenPose | le builder depuis L2, ou un outil |
| **L0 — Descriptif** | vocabulaires fermés + phrases | l'auteur ou le builder |
| **Dérivés** (hors niveau) | cartes de traits, bonhommes OpenPose, profondeur… **optionnels**, régénérables à la volée par toute plateforme | le builder, sur demande |

Un JPEG à résolution modérée est déjà une représentation compacte et complète ; les dérivés n'existent que comme *images de contrôle* prêtes à l'emploi, jamais comme substitut imposé (§ 4.8).

### 0.3 Portée morphologique

Aucune contrainte sur la nature du personnage. `morphology.class` ∈ `humanoid | anthropomorphic-animal | quadruped | avian | aquatic | mechanical | amorphous | other`. Les codes et détecteurs sont conçus d'abord pour l'anthropomorphe ; ailleurs ils s'appliquent « sans garantie » (avertissement, pas erreur).

---

## 1. Conteneur physique

### 1.1 Archive
- **ZIP** ; zip64 accepté en lecture.
- 1re entrée : `mimetype`, stockée sans compression, = `application/vnd.cof.character+zip`.
- 2e entrée : `manifest.json`. Un lecteur doit pouvoir fonctionner après ces deux entrées.
- Chemins ASCII `[A-Za-z0-9._/-]`, pas de `..`, pas d'absolu, pas de lien symbolique.
- Binaires haute entropie stockés sans compression (`store`), JSON/texte en `deflate`.
- Alignement 64 octets optionnel (`container.aligned`), chiffrement interdit.

### 1.2 Arborescence normative (v0.4)

```
mimetype
manifest.json                              ← identités, éléments, presets, assets, droits (§ 2)
elements/
  personality/<v>/   card.json  psyche.json  story.md  lorebook.json  SOUL.md  IDENTITY.md
  appearance/<v>/    images (head.front.jpg…), face.json / body.json / hair.json / outfit.json selon le type
  identity_weights/<v>/  weights.json  [weights.safetensors]
  volume3d/<v>/      avatar.vrm | mesh.glb | face.glb | splat.spz | figurine.3mf  skeleton.json
  voice/<v>/         profile.json  voice.vec.json  samples/  engines/
  posture/<v>/       photos, pose.json (OpenPose), silhouette.png, attitude.json
  motion/<v>/        clips/ (BVH, VRMA)  videos/ (courtes, basse résolution)  visemes.json
derived/<cat>/<v>/   post-traitements optionnels (§ 4.8)
sheets/              planches d'origine + regions (§ 4.1)
rights/              consent.json (par identité : consent.<identité>.json)  licenses/  manifest.c2pa
extensions/<vendeur>/…
```
`<v>` = identifiant de déclinaison (`f1`, `robe-rouge`, …), `[a-z0-9.-]`. Toute clé JSON inconnue est conservée ; `extensions/` n'est jamais purgé.

### 1.3 Enveloppes de compatibilité (exports)
PNG `chara`+`ccv3` (texte + vignette), `.charx`, `SOUL.md`/`IDENTITY.md`, `.vrm`, artefact OCI (§ 10). Toujours calculées depuis le **preset par défaut** (ou un preset choisi).

---

## 2. `manifest.json`

### 2.1 Identité(s)

Champs **obligatoires** de l'identité : `name`, `age` (valeur + unité + base : déclaré / apparent / canonique), `fictional`, `morphology` (`class` ∈ `human` (défaut) | `humanoid` (non-humain de forme humaine : elfe, androïde, alien) | `anthropomorphic-animal` | `quadruped` | `avian` | `aquatic` | `mechanical` | `amorphous` | `other`, + `species` libre). Tout le reste (`nickname`, `summary`, tags) est optionnel. Les **langues** ne sont pas une propriété de l'identité : elles sont portées par les déclinaisons de personnalité (`language`) et par chaque échantillon de voix ; la racine `languages` en est l'**union calculée** (catalogues, filtres).

**Plusieurs identités** **[NOUVEAU]** : un fichier peut décrire un casting. `identities: { "<id>": { name, nickname, age, summary, fictional, morphology, consent } }` + `default_identity`. Chaque preset se rattache à une identité (`presets.<p>.identity`, défaut = `default_identity`) ; une déclinaison peut se réserver à une identité (`identity`), sinon elle est partageable. Le **consentement est par identité** (une personne réelle = une identité). Pour que les lecteurs simples restent simples, la **racine porte une copie** des champs de l'identité par défaut (`name`, `age`, `fictional`, `morphology`, …) — le validateur vérifie l'égalité. La fusion de fichiers (§ 11.3) considère que deux identités sont la même si `name` et `nickname` sont identiques.

```jsonc
{ "cof": "0.4", "id": "01J9…", "name": "Léa Marchand", "nickname": "Léa",
  "age": { "value": 34, "unit": "years", "basis": "declared" }, "fictional": true,
  "morphology": { "class": "human", "species": "human" }, "summary": "…", "languages": ["fr", "en"],   // calculé
  "identities": { "lea": { "name": "Léa Marchand", "nickname": "Léa", "age": {…}, "fictional": true, "morphology": {…} },
                  "marc": { "name": "Marc", "age": {…}, "fictional": true, "morphology": {…} } },
  "default_identity": "lea",
  "tags": {…}, "thumbnail": "elements/appearance/f1/head.front.jpg", … }
```

### 2.2 Éléments : 7 catégories, un type par déclinaison **[NOUVEAU]**

| Catégorie | Nature | Types (`kind`) d'une déclinaison |
|---|---|---|
| `personality` | texte | `card` (Character Card V3 + psyche, story, lore), `description` (texte libre) |
| `appearance` | photos | `reference-set` (photos en vrac, l'IA se débrouille), `character-sheet` (plusieurs angles sur une image), `face`, `body`, `hair`, `clothing` (+ `garment`), `accessory` (+ `accessory`), `intimate`, `pilosity` (+ `area` face/corps), `feature` (particularité : cornes, queue, prothèse… + `region`), `description` |
| `identity_weights` | poids | `lora`, `lycoris`, `dora`, `textual-inversion`, `ip-adapter-embedding`, `dreambooth`, `other` (+ `covers`) |
| `volume3d` | 3D | `mesh` (avatar riggé / maillage complet), `face-mesh`, `point-cloud` (splat), `print` (3MF), `other` |
| `voice` | audio | `samples` (échantillons + transcriptions), `described` (profil sans audio) |
| `posture` | pose | `photo` (une pose), `photos` (plusieurs vues d'une même pose), `openpose`, `silhouette`, `attitude` (signature de mouvement), `description` — avec `use: pose-only` (l'inférence ne retient que la pose) |
| `motion` | mouvement | `clips` (BVH / VRMA), `video` (très court, basse résolution, plafond 20 Mo sauf `max_bytes_ack`), `description` |

Règles :
- Chaque déclinaison déclare `kind` (obligatoire), `label`, `style` / `style_tags` (visuel), `language` (texte/voix), `derives_from` (héritage de champs ; seule « hiérarchie »), `identity` (réservation optionnelle), et ses représentations (`images[]`, `samples[]`, `clips[]`, `videos[]` = identifiants d'assets ; `card`, `psyche`, `params`, `code`, `spec`, `profile`, `path`, `mesh`…).
- Une déclinaison `face` / `body` / `hair` / `clothing` / `accessory` / `pilosity` / `feature` décrit **un seul** visage / corps / coupe / vêtement / accessoire cohérent — pour un autre, on crée une autre déclinaison. La subdivision est **possible, jamais imposée** : avec une seule planche, on renseigne `character-sheet` et c'est valide.
- Les images sont référencées par identifiant d'asset et peuvent être partagées entre déclinaisons.

```jsonc
"elements": {
  "personality": { "variants": { "p1": { "kind": "card", "label": "Léa", "language": "fr", "card": "elements/personality/p1/card.json", "psyche": "…" },
                                 "p2": { "kind": "card", "label": "Léa en anglais", "language": "en", "derives_from": "p1", "card": "…" } } },
  "appearance":  { "variants": { "f1": { "kind": "face", "style": "photo-realistic", "images": ["a-f1-front", "a-f1-left"], "params": "…/face.json" },
                                 "b1": { "kind": "body", "images": ["a-b1-front"] },
                                 "h1": { "kind": "hair", "code": "…/hair.json" }, "h2": { "kind": "hair", "label": "Court blond" },
                                 "o1": { "kind": "clothing", "garment": "dress", "label": "Robe verte", "images": [...] },
                                 "o2": { "kind": "clothing", "garment": "shoes", "label": "Bottes" },
                                 "a1": { "kind": "accessory", "accessory": "glasses" },
                                 "pi1": { "kind": "pilosity", "area": "face", "label": "Barbe de trois jours" },
                                 "x1": { "kind": "feature", "region": "head", "label": "Cornes", "images": [...] },
                                 "s1": { "kind": "character-sheet", "images": ["a-sheet-1"] } } },
  "identity_weights": { "variants": { "l1": { "kind": "lora", "spec": "…/weights.json", "covers": ["face", "hair"] } } },
  "volume3d": { "variants": { "m1": { "kind": "mesh", "path": "…/avatar.vrm", "rig": "VRMC_vrm-1.0" }, "fm1": { "kind": "face-mesh", "mesh": { "path": "…", "topology": "FLAME-2023" } } } },
  "voice":    { "variants": { "v1": { "kind": "samples", "label": "Grave, posée", "profile": "…", "samples": ["a-v1-30s"] } } },
  "posture":  { "variants": { "ps1": { "kind": "photo", "use": "pose-only", "images": ["a-pose-1"] }, "at1": { "kind": "attitude", "spec": "…/attitude.json" } } },
  "motion":   { "variants": { "mo1": { "kind": "clips", "clips": ["a-clip-idle"], "visemes": "…" }, "vd1": { "kind": "video", "videos": ["a-vid-1"] } } }
}
```

### 2.3 Presets : emplacements multiples et règles de cumul **[NOUVEAU]**

```jsonc
"presets": {
  "default": { "label": "Léa aujourd'hui", "identity": "lea", "style": "photo-realistic",
               "slots": { "personality": ["p1"], "appearance": ["f1", "b1", "h1", "o1", "o2", "a1"], "voice": ["v1"], "posture": ["at1"], "volume3d": ["m1"], "identity_weights": ["l1"] },
               "rules": { "single_per_kind": true, "exclusive_regions": true } },
  "soiree":  { "label": "Soirée", "extends": "default", "slots": { "appearance": ["f1", "b1", "h2", "o3", "o2", "a2"] } },
  "en":      { "label": "Léa in English", "extends": "default", "slots": { "personality": ["p2"], "voice": ["v2"] } }
},
"default_preset": "default"
```
- Les emplacements sont des **listes par catégorie**. Règle `single_per_kind` (défaut vrai) : **au plus une déclinaison par type**, sauf les types cumulables `clothing`, `accessory`, `pilosity`, `feature` (et plusieurs `identity_weights` si leurs `covers` sont disjoints).
- Règle `exclusive_regions` (défaut vrai, désactivable par preset) : deux vêtements sont en conflit s'ils couvrent la **même région du corps sur la même couche** (vocabulaire `garments-1.0` : `full-outfit` exclusif ; `top`/`bottom`/`dress`/`jumpsuit` en couche de base ; `outerwear`/`shoes`/`headwear`/`gloves`/`scarf`/`belt`/`armor` en couche extérieure ; sous-vêtements et chaussettes en couche inférieure ; `cape`/`other` cumulables) ; deux accessoires sont en conflit sur la même région sauf cumulables (`necklace`, `bracelet`, `ring`, `bag`) ; une pilosité par zone (`face`, `body`) ; les particularités se cumulent librement. Les conflits sont des **avertissements** (le format n'interdit pas), les doublons de type des **erreurs**.
- `extends` hérite des listes du parent et **remplace** une catégorie entière quand elle est redéclarée. `identity` rattache le preset à une identité ; une déclinaison réservée à une autre identité est une erreur.
- `default_preset` obligatoire dès qu'il y a ≥ 1 preset ; sans preset, preset implicite = première déclinaison de chaque catégorie. Vignette = `head.front` du `face` du preset par défaut.
- KPI par preset (complétude, cohérence) ; KPI de fichier = preset par défaut.
- `age_override` par preset ; règles d'âge sur l'âge le plus bas du fichier (toutes identités et presets). `permissions_override` optionnel (jamais plus permissif que l'âge du preset).
- **Enregistrer sous / fusionner** : § 11.3.

### 2.4 Fichiers multi-personnages

Traités par les **identités multiples** (§ 2.1) : un seul pool d'éléments, des presets rattachés à des identités, des consentements par identité. Un outil extrait une identité (tous ses presets) ou un preset en `.cof` autonome ; la fusion de plusieurs `.cof` conserve les liens identité ↔ presets, renomme les déclinaisons en collision et dédoublonne les assets par `sha256`.

### 2.5 Complétude, cohérence, priorités

**Complétude** (calculée, 0–100, niveaux A ≥ 85 / B ≥ 60 / C ≥ 35 / D) : par preset, en résolvant ses slots ; pondération des couches identity 10 %, personality 20 %, appearance 20 %, physique 5 %, voice 15 %, volume 10 %, motion 5 %, rights 15 % ; règles publiques dans `docs/completeness-rules.md`. Les dérivés ne comptent pas. Au niveau fichier : KPI du preset par défaut + `coverage` (liste des types d'éléments présents, nombre de déclinaisons et de presets).

**Cohérence [NOUVEAU]** (déclarée, 0–100, optionnelle) : mesure si les déclinaisons d'un preset racontent le *même* personnage — genre/âge/espèce entre texte, images et voix ; style visuel homogène ; langue des échantillons vs `languages` ; âge du manifeste vs apparence. Elle est produite au build (contrôles activables, § 11.2) par des heuristiques locales **ou par une IA au choix de l'utilisateur** via une passerelle API ; stockée avec `computed_by`, `method`, `issues[]`. Un fichier incohérent reste **valide** : le format n'interdit rien, il rend visible. Une plateforme peut filtrer sur ce KPI.

**Priorités [NOUVEAU]** : quand plusieurs représentations décrivent la même chose, qui gagne ? Déclaré dans le manifeste, ajustable au build et au chargement :
```jsonc
"priorities": {
  "visual": ["identity_weights", "images", "avatar", "descriptive"],   // défaut général (LoRA > images > 3D > texte)
  "voice":  ["samples", "described"],                                   // WAV > voix décrite
  "by_target": {                                                        // défauts par usage cible, surchargeables
    "game-3d":        { "visual": ["avatar", "images", "identity_weights", "descriptive"] },
    "chat-text":      { "visual": ["descriptive", "images"] },
    "video-realtime": { "visual": ["avatar", "images", "identity_weights", "descriptive"] }
  }
}
```
Les priorités sont aussi le moyen de **mitiger** une incohérence connue (« l'image prime sur le texte »).

### 2.6 Assets

Index exhaustif de tout fichier non-JSON, chacun avec un **`id`** (référencé par les déclinaisons), `path` (ou `uri` externe + hash), `role` (`view`, `expression`, `reference`, `sheet`, `voice-sample`, `voice-consent`, `engine-artifact`, `weights`, `avatar`, `splat`, `print`, `motion-clip`, `motion-reference`, `mesh`, `derived`, `document`, `other`), `mediaType`, `bytes`, `sha256`, `license` (SPDX), `digitalSourceType` (IPTC), et selon le rôle : `subject`/`angle`/`framing`/`style` (images), `duration_s`/`transcript`/`emotion` (audio), `rig`/`fps` (clips), `method`/`source` (dérivés), `regions[]` (planches), `base_model` (poids), `derived_from`, `estimated`.

---

## 3. Élément `personality`

Déclinaison = une **Character Card V3** complète (`card`), optionnellement `psyche.json` (traits typés OCEAN/HEXACO, buts, craintes, valeurs, contradictions, émotion de base EmotionML, rendus en phrase et en curseurs), `story.md` (long), `lorebook.json` (`lorebook_v3`), projections `SOUL.md`/`IDENTITY.md` (OpenClaw, troncature 20 000 caractères). Conventions inchangées depuis v0.2 : `creator_notes` jamais dans le prompt, clés COF sous `data.extensions.cof`, `behavior` = manifestations observables (distinctes des dispositions de `psyche`), identifiants `trait:`/`goal:`/`fear:` pour les renvois. Profils de tokens (`summary` ≤ 512, `standard` 1–2 k, `full` ~4 k, `lore` ≤ 32 k par entrée) déclarés par déclinaison.

---

## 4. Éléments visuels

### 4.1 Images : vues séparées, planches, cadrages
- Nommage normatif des vues : `<sujet>.<angle>.<ext>` avec sujet ∈ `head | body | hands | detail-*`, angle ∈ `front | left34 | left | leftback34 | back | rightback34 | right | right34 | top | low34` ; `head.front` canonique = cadrage `head` (sommet des cheveux → menton, carré 1024², centré sur les pupilles) ; zooms serrés acceptés en `framing: closeup`.
- **Vues séparées = forme canonique** (dénominateur commun des générateurs : 1 à N images de référence ; vignette et applis de dialogue chargent `head.front` directement). **Planche conservée en option** (`role: sheet`, `regions[]` normalisées, `confidence`, `human_confirmed`) ; le builder découpe, retire titres/séparateurs, classe et cadre, dérive `head.front` de la vue de corps si le zoom est coupé.
- Chaque image porte un **`style`** (§ 4.7).

### 4.2 `face` — images, paramètres, **maillage spatial [NOUVEAU]**
Une déclinaison de visage peut porter jusqu'à quatre représentations cohérentes :
- `images[]` (vues de tête, expressions nommées) ;
- `params` : `face.json` — FLAME 2023 Open (300 forme + 100 expression), vocabulaire descriptif ouvert COF-FDV, teint (Monk + hex), expressions-types (nom VRM/Ekman + intensité + vecteur ARKit-52) ;
- `mesh` : **maillage 3D de la tête** — `path` (glTF/GLB recommandé ; OBJ/PLY acceptés), `topology` (`FLAME-2023 | MediaPipe-468 | ARKit | ICT-FaceKit | MetaHuman | custom`), `blendshapes` (`ARKit-52 | UnifiedExpressions-1.0 | VRM-presets | none`), `textures` (albedo/normal/roughness en assets), `units`, `landmarks` (jeu de points nommés si connu) ; un maillage scanné (photogrammétrie, Gaussian avatar figé) est accepté avec `topology: custom` et `watertight` ;
- `derived[]` (optionnel, § 4.8).
Le validateur vérifie la cohérence des mesures entre `params` et `mesh` quand les deux existent (avertissement). Aucun **embedding biométrique** (ArcFace…) n'est admis.

### 4.3 `hair`, `facial_hair`, `body_hair`
`hair.json` = code COF-HAIR-1 (longueur, courbure, densité, épaisseur, couleurs, style, raie, implantation, ~200 octets) + images dédiées optionnelles (fond neutre ou masque). `facial_hair` et `body_hair` : mêmes champs restreints. Si l'auteur n'isole pas les cheveux, ils restent implicites dans les images de `face`/`body` — c'est permis.

### 4.4 `body`
`body.json` : Anny (phénotypes [0,1]), β SMPL-X pour interop, mesures ISO 7250, teint, descriptif, `renderings.prompt` ; vues `body.*`. **Morphologie estimée sous les vêtements** (`body.estimated`, optionnelle, marquée `estimated` + `confidence`) : pose + silhouette corrigée d'un offset vestimentaire + a priori anthropométriques ; **interdite si `age < 18`**, non appliquée aux classes `mechanical`/`amorphous`, jamais sur une personne réelle sans `consent.scope` ∋ `likeness-3d`.

### 4.5 `intimate` (optionnel, verrouillé)
Élément séparé, même schéma descriptif, **ignoré par défaut** par les lecteurs tant que `permissions.allowSexualUsage` n'est pas vrai ; sa présence rend le fichier **invalide** si l'âge le plus bas (manifeste ou `age_override` d'un preset) est < 18.

### 4.6 `identity_weights` — LoRA et embeddings **[NOUVEAU]**
```jsonc
// elements/identity_weights/l1/weights.json
{ "kind": "lora",                                 // lora | lycoris | dora | textual-inversion | ip-adapter-embedding | dreambooth | other
  "base_model": { "name": "FLUX.1-dev", "family": "flux", "version": "1.0", "hash": "sha256:…" },   // le modèle de base est OBLIGATOIRE : un LoRA sans base est inutilisable
  "file": "a-lora-l1",                            // asset (safetensors) — externalisé par défaut (uri + sha256), vu les tailles
  "format": "safetensors", "rank": 16, "bytes": 171000000,
  "trigger_words": ["leamarchand", "woman"], "recommended_weight": 0.8, "weight_range": [0.6, 1.0],
  "covers": ["face", "hair", "body"],             // ce que le LoRA encode (pour la cohérence et les priorités)
  "pages": [ { "label": "Civitai", "url": "https://civitai.com/models/…" } ],
  "notes": "Entraîné sur 40 images, 1500 pas ; éviter > 1.0 ; fonctionne mieux avec le mot déclencheur en tête de prompt.",
  "training": { "images": 40, "steps": 1500, "resolution": 1024, "consent": "rights/consent.json" },
  "style": "photo-realistic", "license": "CC-BY-NC-4.0" }
```
Règles : `base_model.name` obligatoire ; `trigger_words` et `recommended_weight` recommandés ; le fichier de poids est un asset `role: weights` (hash obligatoire même s'il est externe) ; `allowTraining` et `consent` s'appliquent ; un LoRA d'une personne réelle sans consentement est invalide. Les embeddings IP-Adapter / « face ID » sont acceptés *seulement* s'ils ne sont pas des embeddings de reconnaissance (§ 4.2).

### 4.7 Styles visuels **[NOUVEAU]**
Vocabulaire `visual-styles-1.0` (CC0, extensible) : `photo-realistic`, `cinematic`, `3d-render`, `anime`, `manga`, `comic`, `cartoon`, `pixel-art`, `lego`, `clay`, `watercolor`, `oil-painting`, `ink-sketch`, `lineart`, `low-poly`, `voxel`, `chibi`, `other:<libre>`. Porté par **chaque image** (`assets[].style`), par **chaque déclinaison visuelle**, et attendu par **chaque preset** (`presets.<p>.style`). La liste de base reste **courte** ; les précisions passent par des **tags complémentaires** `style_tags[]` (ex. `anime-90s`, `ghibli-like`, `ukiyo-e`) plutôt que par l'allongement de la liste. Le builder le propose automatiquement (classifieur léger ou IA externe) ; l'auteur confirme. Le contrôle de cohérence signale un preset qui mélange des styles sans le déclarer.

### 4.8 Dérivés : post-traitements optionnels **[NOUVEAU]**
`derived/<type>/<v>/<vue>.<method>.png` (+ SVG), `assets[].role: "derived"`, `method` ∈ `canny | lineart | lineart-anime | softedge | hed | pidinet | teed | depth | normal | openpose | segmentation`, `source` = id de l'asset d'origine. **Facultatifs** ; générés par le builder sur demande ; **jamais comptés** comme images de base ni dans la complétude ; isolés dans leur bloc ; l'auteur peut choisir de ne livrer *que* des dérivés pour une vue (choix de l'auteur, pas du format). Les plateformes les régénèrent à la volée à partir des images quand elles sont absentes.

### 4.9 `outfit`, `accessories`
`outfit.json` : catégories/attributs Fashionpedia, couleurs, patron GarmentCode optionnel, `default: true` sur une seule tenue ; images dédiées optionnelles. Plusieurs tenues = plusieurs déclinaisons, combinées par les presets.

---

## 5. Élément `attitude` (physique)
`attitude.json` : signature de mouvement LMA Effort (4 axes −1…+1, action dominante, Shape), tempo, postures (BAP), lexèmes de gestes BML avec `expresses: ["trait:…"]`, regard, proxémie, démarche, labels 100STYLE/BABEL ; **postures en points-clés OpenPose** normalisés (`poses/<nom>.pose.json`, squelettes `openpose-body25 | coco-18 | coco-wholebody-133 | mediapipe-pose-33`) avec rendu « bonhomme » pour ControlNet.

---

## 6. Élément `voice`

### 6.1 Règle « une vérité, des projections »
| Question | Où ça vit |
|---|---|
| *Pourquoi* il agit ainsi | `personality` (psyche, card) |
| *Comment le corps* le montre | `attitude` |
| *Comment la voix* le montre | `voice` (acoustique, prosodie, registre) |
| *Ce qui est dit* | `card.mes_example` |
Les sections se renvoient par identifiants ; le validateur signale les doublons textuels > 80 %.

### 6.2 Contenu d'une déclinaison de voix
`profile.json` (profil canonique typé : genre perçu, âge, accent, hauteur, débit, volume, timbre, expressivité ; VPA ordinal ; `speech_style` ; `emotion_range` EmotionML ; échantillons en durées canoniques ≈ 8 s / 30 s / 2 min **chacun avec transcription** ; `engines[]` = artefacts dérivés nommés, versionnés, périssables — latents XTTS, `se.pth` OpenVoice, `spk2info` CosyVoice, packs Kokoro, `voice_id` cloud ; `prompt_renderings` ; `ssml_template` ; `fingerprint` ECAPA pour vérification seulement) et `voice.vec.json` (code vocal COF-Voice : mesures acoustiques calculées F0/débit/pauses/HNR/jitter/shimmer, qualité ordinale, manière de s'exprimer, rendus phrase/SSML/Parler). Consentement obligatoire si personne réelle.

---

## 7. Éléments `avatar` et `motion`
- `avatar` : VRM 1.0 pivot (`meta` **dérivé** de `rights` à l'export), GLB accepté avec `rig` déclaré ; `skeleton.json` pour un rig non standard ; vocabulaire `skeletons-1.0` (VRM humanoïde canonique ; Unity/Mixamo, Unreal/MetaHuman, SMPL-X, Anny, MHR ; squelettes 2D OpenPose/MediaPipe) avec tables de correspondance ; splat (SPZ, externe par défaut) lié à l'avatar par `splat.json` (pas d'ossature native) ; `print/*.3mf` dérivé imprimable.
- `motion` : clips BVH (pivot) / VRMA (humanoïde + expressions + regard), `rig`, `fps`, labels BABEL, `derived_from_video` ; `visemes.json` = vocabulaire déclaré (ARKit-52 / Oculus-15 / A–X).
- Point d'accroche Khronos : `mapping_vocabularies` pourra nommer `KHR_character*` si ces extensions paraissent au registre (existence non confirmée).

---

## 8. Tailles

**Profils de tokens** par déclinaison de personnalité : `summary` ≤ 512, `standard` 1–2 k, `full` ~4 k, `lore` ≤ 32 k activé par entrée ; aucun bloc permanent > 2 500 tokens sans justification ; ordre d'injection `identity → rules → lore → history → identity_recap`.

**Classes de taille** (par canal, pas par puissance de 2) : `lite` ≤ 20 Mo, `standard` ≤ 100 Mo, `full` illimité avec externalisation (`uri` + `sha256`) — poids d'identité et splats **externes par défaut**. Binaires stockés sans compression. Un fichier modulaire peut être gros (dizaines de déclinaisons) : l'option « enregistrer sous » un preset produit une version légère.

---

## 9. Droits

### 9.1 Permissions (calquées sur `VRMC_vrm.meta`, défauts restrictifs)
`avatarPermission`, `commercialUsage`, `modification`, `allowRedistribution`, `creditNotation`, `allowExcessivelyViolentUsage`, `allowSexualUsage`, `allowPoliticalOrReligiousUsage`, `allowAntisocialOrHateUsage`, **+** `allowVoiceCloning`, `allowTraining` (`none | finetune-private | finetune-public | any`), `allowImpersonationOfRealPerson`, `ageRating`, `minUserAge`, `aiDisclosure` (défaut `true`). Règles d'âge sur l'âge **le plus bas** du fichier (manifeste et `age_override` des presets) : < 18 ⇒ `allowSexualUsage` forcé à `false`, élément `intimate` et `body.estimated` interdits.

### 9.2 Consentement
`rights/consent.json` obligatoire dès que `fictional: false`, qu'un asset provient d'une personne réelle, ou qu'un poids d'identité a été entraîné sur une personne réelle : `subject_is_real_person`, `scope[]` (`voice-synthesis | likeness-image | likeness-3d | conversational-persona | motion-capture | training`), `excluded[]`, `jurisdictions[]`, dates, `revocation_uri`, `proof[]` (déclaration verbale enregistrée, document signé, attestation de plateforme — hachés). Un lecteur conforme refuse de synthétiser une voix ou d'utiliser un LoRA d'une personne réelle sans preuve valide.

### 9.3 Provenance, signature, sécurité
`source[]` append-only, `created/modified`, `generator`, `digitalSourceType` par asset, C2PA par asset média + sidecar `rights/manifest.c2pa`, signature optionnelle du manifeste (RFC 8785 + JWS). `container.executableContent` déclaré et vérifié ; aucun format sérialisé exécutable (les poids sont en **safetensors**, jamais pickle) ; noms restreints ; bornes anti zip-bomb ; textes de prompt `untrusted` ; `uri` externes en `https://` vérifiées par hash.

---

## 10. Distribution double mode
Fichier `.cof` monolithique, ou artefact OCI (`artifactType: application/vnd.cof.character.manifest.v1+json`, config = manifeste, une couche par asset non compressée, `subject`/referrers pour signatures). Les poids d'identité se prêtent particulièrement au mode registre.

---

## 11. Validation, builder, conformité

### 11.1 Niveaux de conformité
`COF-Core` (mimetype, manifeste, âge, droits, assets hashés, presets résolubles) ; `COF-Psyche` ; `COF-Visual` ; `COF-Voice` ; `COF-3D` ; `COF-Motion` ; `COF-Weights` (base model + hash + licence) ; `COF-Rights+` (C2PA + signature). Le validateur rend erreurs/avertissements, recalcule complétude, `coverage` et `targets_ready` par preset.

### 11.2 Le builder
Page web unique (HTML/JS, hors ligne, GitHub Pages + Space Hugging Face), tout en local. Parcours : **Identité → Éléments** (chaque type : ajouter des déclinaisons ; import de carte PNG/CharX/SOUL.md ; glisser des images ou une planche → découpage, classification, style proposé ; WAV → mesures ; VRM/GLB/BVH → rig ; LoRA → fiche de poids) → **Presets** (composer des combinaisons ; marquer le défaut ; enregistrer sous / fusionner) → **Droits** → **Contrôles** → **Build**.

**Contrôles de cohérence** (activables, jamais bloquants) : heuristiques locales (âge manifeste vs corps, style par preset, langue des échantillons, genre perçu voix vs présentation déclarée, morphologie vs images) **et** passerelle IA : le builder envoie à un point d'API au choix de l'utilisateur (format OpenAI-compatible *chat/completions* avec vision, ou intégration native d'une plateforme) un **dossier de preset** (`cof coherence-bundle` : résumés texte, vignettes, descripteurs de voix, poids déclarés) et attend `{ "score": 0–100, "issues": [ { "severity", "elements": [...], "message" } ] }` ; résultat stocké dans `presets.<p>.coherence` avec `computed_by` et date. Contrat JSON dans `docs/coherence-api.md`.

**Priorités** : écran dédié, défauts du § 2.5, modifiables ; exportées dans le manifeste.

**Build** : classe de taille, compression (recadrage/qualité JPEG, WebP ; Opus pour l'audio long ; externalisation des gros assets ; **taille/qualité vidéo** affichées quand des vidéos sont présentes, plafond 20 Mo désactivable avec alerte), génération de dérivés **sur demande seulement**, exports annexes (PNG ccv3, `.charx`, SOUL/IDENTITY, `.vrm`), « enregistrer sous » par preset, **importer et fusionner** d'autres `.cof`.

### 11.3 Fusion et extraction (`cof merge`, `cof extract`)
- **Fusion** : mêmes `name` + `nickname` ⇒ même identité (éléments et presets ajoutés à cette identité) ; sinon nouvelle identité. Déclinaisons et presets renommés en cas de collision (préfixe), `derives_from`/`extends` réécrits, assets dédoublonnés par `sha256`, `provenance.source` ← identifiants des fichiers d'origine.
- **Extraction d'un preset** : nouveau fichier contenant la seule identité du preset, ses déclinaisons (et leurs parents `derives_from`), leurs assets et dérivés, les droits ; nouvel `id`, `provenance.source` ← `cof:<id>#preset=<p>`.

---

## 12. Versionnage et gouvernance
Semver ; RFC publiques (14 jours) ; vocabulaires versionnés séparément (CC0) ; lecteur `1.x` lit `1.y` ; clés inconnues conservées ; transfert à une gouvernance neutre dès deux adoptants indépendants.

---

## Annexe A — Migration v0.2 / v0.3 → v0.4
`cof migrate` enchaîne v0.2 → v0.3 → v0.4 : types v0.3 (`face`, `hair`, `outfit`, `avatar`, `attitude`…) → catégories + `kind` (`appearance/face`, `appearance/hair`, `appearance/clothing` (`garment: full-outfit`), `volume3d/mesh`, `posture/attitude`…), emplacements de presets → listes, `humanoid` + espèce humaine → `human`.

## Annexe B — Exemple minimal valide (COF-Core)
```
mimetype
manifest.json        (identité, rights.permissions, elements.personality.variants.p1.card, presets.default, assets: [])
elements/personality/p1/card.json
```
