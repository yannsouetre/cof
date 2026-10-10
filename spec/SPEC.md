# COF — Character Open File
## Spécification v0.3 (brouillon de travail, 10 octobre 2026)

> **Statut** : brouillon d'auteur, RFC publique sur GitHub (`rfcs/`).
> **Licence** : spécification CC-BY-4.0 ; implémentation de référence MIT ; vocabulaires et schémas CC0.
> **Auteur** : Yann Souetre.
> **Nom** : *COF — Character Open File*, extension `.cof`, type MIME `application/vnd.cof.character+zip`.
> **v0.3** : architecture **modulaire** (éléments → déclinaisons → presets), fichiers multi-personnages, poids d'identité (LoRA), maillages de visage, styles visuels, subdivision des éléments visuels, post-traitements dérivés optionnels, KPI de cohérence et règles de priorité.
> Les choix s'appuient sur l'état de l'art (`docs/state-of-the-art.md`). Les parties « à inventer » sont marquées **[NOUVEAU]**.

---

## 0. En une page

Un fichier `.cof` est un **conteneur ZIP** qui réunit tout ce qui définit un ou plusieurs personnages synthétiques, sous une forme **modulaire** :

```
Fichier .cof
 └─ Personnage(s)
     ├─ Éléments        (personnalité, visage, cheveux, corps, tenue, voix, avatar 3D, mouvement, attitude, poids d'identité…)
     │    └─ Déclinaisons   (visage f1, f2… ; tenue o1 « casual », o2 « médiévale » ; voix v1 « grave », v2…)
     ├─ Presets         (combinaisons de déclinaisons : preset « défaut », preset « manga », preset « soirée »…)
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

### 1.2 Arborescence normative (v0.3)

```
mimetype
manifest.json                              ← identité, éléments, presets, assets, droits (§ 2)
elements/
  personality/<v>/card.json                ← Character Card V3 (source de vérité du texte)
  personality/<v>/psyche.json  story.md  lorebook.json  SOUL.md  IDENTITY.md
  face/<v>/        head.front.jpg  head.left.jpg …  face.json (FLAME/descriptif)  mesh.glb (§ 4.2)
  hair/<v>/        hair.json  views…        facial_hair/<v>/   body_hair/<v>/
  body/<v>/        body.json  body.front.jpg …
  intimate/<v>/    (optionnel, verrouillé — § 4.5)
  outfit/<v>/      outfit.json  views…      accessories/<v>/
  identity_weights/<v>/  weights.json  [lora.safetensors]   (§ 4.6)
  voice/<v>/       profile.json  voice.vec.json  samples/  engines/
  attitude/<v>/    attitude.json  poses/
  avatar/<v>/      avatar.vrm | avatar.glb  skeleton.json  splat.json
  motion/<v>/      clips/  visemes.json
derived/<type>/<v>/   head.front.canny.png …  (§ 4.8, optionnel)
sheets/            planches d'origine + regions (§ 4.1)
rights/            consent.json  licenses/  manifest.c2pa
characters/<id>/…  (fichiers multi-personnages : un sous-arbre complet par personnage — § 2.4)
extensions/<vendeur>/…
```
`<v>` = identifiant de déclinaison (`f1`, `outfit-medieval`, …), `[a-z0-9-]`. Toute clé JSON inconnue est conservée ; `extensions/` n'est jamais purgé.

### 1.3 Enveloppes de compatibilité (exports)
PNG `chara`+`ccv3` (texte + vignette), `.charx`, `SOUL.md`/`IDENTITY.md`, `.vrm`, artefact OCI (§ 10). Toujours calculées depuis le **preset par défaut** (ou un preset choisi).

---

## 2. `manifest.json`

### 2.1 Identité

```jsonc
{
  "cof": "0.3",
  "id": "01J9ZK5Y7Q4W8R2M3N6P0T1V9X",         // ULID stable
  "name": "Léa Marchand", "nickname": "Léa",
  "age": { "value": 34, "unit": "years", "basis": "declared" },   // obligatoire, non ambigu
  "languages": ["fr", "en"], "summary": "…", "fictional": true,
  "morphology": { "class": "humanoid", "species": "human" },
  "tags": { "auto": [...], "manual": [...], "content": ["none"], "ip": { "original": true } },
  "thumbnail": "elements/face/f1/head.front.jpg",   // = visage de face du preset par défaut (calculé)
  ...
}
```

### 2.2 Éléments et déclinaisons **[NOUVEAU]**

```jsonc
"elements": {
  "personality": { "variants": {
      "p1": { "label": "Léa, archiviste", "card": "elements/personality/p1/card.json", "psyche": "elements/personality/p1/psyche.json", "story": "elements/personality/p1/story.md" },
      "p2": { "label": "Léa, 20 ans plus tôt", "derives_from": "p1", "card": "elements/personality/p2/card.json" } } },
  "face":   { "variants": {
      "f1": { "label": "Visage photo", "style": "photo-realistic", "images": ["a-face-f1-front", "a-face-f1-left"], "params": "elements/face/f1/face.json", "mesh": { "path": "elements/face/f1/mesh.glb", "topology": "FLAME-2023", "blendshapes": "ARKit-52" } },
      "f2": { "label": "Visage manga", "style": "manga", "derives_from": "f1", "images": ["a-face-f2-front"] } } },
  "hair":   { "variants": { "h1": { "label": "Long châtain", "code": "elements/hair/h1/hair.json", "images": ["a-hair-h1"] }, "h2": { "label": "Court blond", "code": "elements/hair/h2/hair.json" } } },
  "facial_hair": { "variants": {} }, "body": { "variants": { "b1": { "params": "elements/body/b1/body.json", "images": ["a-body-b1-front", "a-body-b1-back"] } } },
  "body_hair": { "variants": {} }, "intimate": { "variants": {} },
  "outfit": { "variants": { "o1": { "label": "Casual", "spec": "elements/outfit/o1/outfit.json", "images": ["a-body-b1-front"] }, "o2": { "label": "Médiéval", "spec": "elements/outfit/o2/outfit.json" } } },
  "identity_weights": { "variants": { "l1": { "label": "LoRA Flux", "spec": "elements/identity_weights/l1/weights.json" } } },
  "voice":    { "variants": { "v1": { "label": "Grave, posée", "profile": "elements/voice/v1/profile.json", "samples": ["a-voice-v1-30s"] }, "v2": { "label": "Enjouée" } } },
  "attitude": { "variants": { "m1": { "spec": "elements/attitude/m1/attitude.json" } } },
  "avatar":   { "variants": { "av1": { "path": "elements/avatar/av1/avatar.vrm", "rig": "VRMC_vrm-1.0" } } },
  "motion":   { "variants": { "mo1": { "clips": ["a-clip-idle"], "visemes": "elements/motion/mo1/visemes.json" } } }
}
```
Règles :
- **Types d'éléments** (vocabulaire fermé, extensible par `x-<vendeur>-…`) : `personality`, `face`, `hair`, `facial_hair`, `body`, `body_hair`, `intimate`, `outfit`, `accessories`, `identity_weights`, `voice`, `attitude`, `avatar`, `motion`. La subdivision visuelle (visage / cheveux / pilosité / corps / tenue) est **possible, jamais imposée** : un auteur qui n'a qu'une planche ne renseigne que `face` et `body` ; une plateforme qui sait exploiter `hair` séparément y gagne quand il est présent.
- Une **déclinaison** porte : `label`, `style` (vocabulaire `visual-styles`, § 4.7), `tags`, `derives_from` (héritage : les champs absents sont pris dans le parent — c'est la seule « hiérarchie » ; « 1.1 / 1.2 » n'est qu'une convention de nommage), ses représentations (`images[]` = identifiants d'assets, `params`, `mesh`, `code`, `spec`, `samples[]`, `clips[]`…), et `derived[]` (identifiants d'assets de post-traitement, § 4.8).
- Les **images sont référencées par identifiant d'asset**, pas par chemin : une même vue de corps habillé peut servir à `body/b1` et à `outfit/o1`.
- Une déclinaison hors de tout preset est autorisée (avertissement du validateur, pas erreur).

### 2.3 Presets **[NOUVEAU]**

```jsonc
"presets": {
  "default": { "label": "Léa aujourd'hui", "style": "photo-realistic",
               "slots": { "personality": "p1", "face": "f1", "hair": "h1", "body": "b1", "outfit": "o1", "voice": "v1", "attitude": "m1", "avatar": "av1", "motion": "mo1", "identity_weights": "l1" },
               "completeness": { "score": 78, "level": "B", "layers": {…} }, "coherence": { "score": 92, "computed_by": "…" } },
  "manga":   { "label": "Version manga", "extends": "default", "style": "manga", "slots": { "face": "f2", "hair": "h2" } },
  "young":   { "label": "Léa à 14 ans", "extends": "default", "slots": { "personality": "p2", "voice": "v2" }, "age_override": { "value": 14, "unit": "years", "basis": "canonical" } }
},
"default_preset": "default"
```
Règles :
- Un preset = une **combinaison** `slot → déclinaison` ; au plus une déclinaison par type d'élément ; `extends` hérite des slots d'un autre preset puis surcharge.
- `default_preset` est obligatoire dès qu'il y a ≥ 1 preset ; s'il n'y a aucun preset, le lecteur construit un preset implicite avec la première déclinaison de chaque élément. La **vignette** du fichier = `head.front` du visage du preset par défaut.
- Chaque preset a ses **KPI** (complétude, cohérence) ; les KPI de fichier = ceux du preset par défaut (identiques s'il n'y a qu'un preset).
- `age_override` : un preset peut représenter le personnage à un autre âge ; toutes les règles d'âge (§ 9.1) s'appliquent à l'âge **le plus bas** parmi le manifeste et les presets.
- À l'usage, l'application charge le preset par défaut, laisse choisir un autre preset, ou — niveau fin — composer les déclinaisons une à une.
- **Enregistrer sous / fusionner** : un outil peut extraire un ou plusieurs presets (avec les seules déclinaisons et assets qu'ils référencent) en un nouveau `.cof` (nouvel `id`, `provenance.source` ← ancien `id`), ou fusionner plusieurs `.cof` d'un même personnage (déclinaisons renommées en cas de collision, assets dédoublonnés par `sha256`).

### 2.4 Fichiers multi-personnages **[NOUVEAU]**

Un `.cof` peut contenir **plusieurs personnages** (un casting, une famille, un jeu) : `manifest.json` racine déclare `"characters": [ { "id": "…", "name": "…", "path": "characters/lea/manifest.json" }, … ]` et `"default_character"` ; chaque sous-arbre `characters/<id>/` est un personnage **complet** (son propre manifeste, ses éléments, ses droits). Un fichier mono-personnage garde tout à la racine. Un outil « extrait » un personnage en un `.cof` autonome sans perte. Les droits et consentements sont **par personnage**, jamais mutualisés.

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
Vocabulaire `visual-styles-1.0` (CC0, extensible) : `photo-realistic`, `cinematic`, `3d-render`, `anime`, `manga`, `comic`, `cartoon`, `pixel-art`, `lego`, `clay`, `watercolor`, `oil-painting`, `ink-sketch`, `lineart`, `low-poly`, `voxel`, `chibi`, `other:<libre>`. Porté par **chaque image** (`assets[].style`), par **chaque déclinaison visuelle**, et attendu par **chaque preset** (`presets.<p>.style`). Le builder le propose automatiquement (classifieur léger ou IA externe) ; l'auteur confirme. Le contrôle de cohérence signale un preset qui mélange des styles sans le déclarer.

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

**Build** : classe de taille, compression (recadrage/qualité JPEG, WebP ; Opus pour l'audio long ; externalisation des gros assets), génération de dérivés **sur demande seulement**, exports annexes (PNG ccv3, `.charx`, SOUL/IDENTITY, `.vrm`), « enregistrer sous » par preset.

---

## 12. Versionnage et gouvernance
Semver ; RFC publiques (14 jours) ; vocabulaires versionnés séparément (CC0) ; lecteur `1.x` lit `1.y` ; clés inconnues conservées ; transfert à une gouvernance neutre dès deux adoptants indépendants.

---

## Annexe A — Migration v0.2 → v0.3
Un fichier v0.2 (`sections` + `appearance/`, `character/`, `voice/`…) se lit comme un v0.3 à **une déclinaison par élément** et **un preset implicite** ; `cof migrate` déplace les fichiers sous `elements/<type>/<v1>/`, crée `elements`/`presets`/`default_preset`, attribue des `id` aux assets et déplace les cartes de traits sous `derived/`.

## Annexe B — Exemple minimal valide (COF-Core)
```
mimetype
manifest.json        (identité, rights.permissions, elements.personality.variants.p1.card, presets.default, assets: [])
elements/personality/p1/card.json
```
