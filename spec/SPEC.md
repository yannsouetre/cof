# COF — Character Open File
## Spécification v0.2 (brouillon de travail, 9 octobre 2026)

> **Statut** : brouillon d'auteur, destiné à devenir une RFC publique sur GitHub.
> **Licence visée** : spécification CC-BY-4.0 ; implémentation de référence MIT ; vocabulaires et codes CC0.
> **Auteur** : Yann Souetre.
> **Nom** : *COF — Character Open File*, extension `.cof`, type MIME `application/vnd.cof.character+zip`.
> Ce document s'appuie sur l'état de l'art joint (`01_Etat_de_l_art.md`). Chaque choix renvoie à une brique existante quand elle existe ; les parties « à inventer » sont marquées **[NOUVEAU]**.
> **v0.2** : ajoute les usages cibles (§ 0.1), les niveaux de représentation et le code vectoriel (§ 0.2, § 4.0, doc `04_COF-Vector_concept.md`), le KPI de complétude et les tags (§ 2.2), la portée morphologique (§ 0.3), le code vocal (§ 6.3), le builder et la compression (§ 11.1).

> **Sur l'extension `.cof`.** Elle n'est utilisée que par un fichier de debug de l'IDE Microchip MPLAB (format COFF) — usage de niche en électronique embarquée, sans association système grand public. Les extensions de fichiers ne sont pas réservées (des dizaines de formats partagent `.dat`, `.bin`, `.pak`) ; ce qui identifie un format est son **type MIME** et sa **signature** : ici l'en-tête ZIP `PK` + le fichier `mimetype` en première entrée. Le nom est donc tenable. Noms de repli si besoin : `.cofx`, `.charf`.

---

## 0. En une page

Un fichier `.cof` est **un conteneur ZIP** qui réunit, en un seul objet partageable, tout ce qui définit un personnage synthétique — et qui peut être consommé par des outils très différents (§ 0.1) :

| Couche | Contenu | Brique réutilisée | Statut |
|---|---|---|---|
| Identité & manifeste | qui, quel âge, quels profils, quels assets, quels droits | JSON Schema 2020-12, SPDX, IPTC, JSON-LD (façon `KHR_xmp_json_ld`) | Obligatoire |
| Personnalité | personnalité, buts, craintes, histoire, lore | **Character Card V3** embarquée + traits typés | Obligatoire (minimal) |
| Apparence | vues multiples, visage, corps, cheveux, tenues, expressions | FLAME 2023 Open, Anny, ARKit 52 / Unified Expressions, Monk, Fashionpedia, GarmentCode | Optionnelle |
| Attitude physique | signature de mouvement, posture, gestes habituels | LMA Effort, BAP, BML | Optionnelle |
| Voix | échantillons + transcriptions, profil typé, rendus par moteur | WAV, SSML, EmotionML, VPA | Optionnelle |
| Volumétrie | avatar riggé, splat, version imprimable | VRM 1.0 / glTF, SPZ, 3MF | Optionnelle |
| Mouvement | clips, mapping de visèmes | BVH, VRMA | Optionnelle |
| Droits | permissions, consentement, provenance, signature | `VRMC_vrm.meta` étendu, C2PA, canonicalisation JSON | Obligatoire (minimal) |

Six principes gouvernent le format :

1. **Englober, ne pas remplacer.** Un `.cof` contient une Character Card V3 valide, peut être exporté en PNG `ccv3`, en `.charx`, en `SOUL.md`, en `.vrm` : les applications existantes n'ont rien à réécrire.
2. **Tout est optionnel sauf l'identité et les droits.** Un `.cof` de 4 Ko (manifeste + carte) est valide ; un `.cof` de 90 Mo avec avatar, voix et clips aussi. Un personnage qui n'a *que* une voix, ou *que* une apparence, est valide. La **complétude** n'est pas une contrainte, c'est un **indicateur** (§ 2.2).
3. **Une vérité, des projections.** Chaque information n'est écrite qu'une fois (les traits de personnalité dans `psyche.json`) ; les autres sections y *renvoient* au lieu de la répéter (voir § 6).
4. **Lisible par un humain et par un LLM.** Le cœur est du JSON et du Markdown ; les codes compacts (visage, corps, cheveux, voix, mouvement) ont une forme numérique *et* une forme en phrases.
5. **Trois façons de dire la même chose, du plus lourd au plus léger.** Chaque facette d'apparence peut être portée par des **médias** (photos, planches, vidéos), par un **code vectoriel/paramétrique** (plus précis qu'un texte, 100 à 1 000 fois plus léger qu'une image — § 0.2) et par un **descriptif** (vocabulaire + phrase). Le builder permet de passer de l'un à l'autre (« compresser » un personnage = remplacer des médias par du code).
6. **Aucun code exécutable, rien de chiffré, et le consentement d'abord.** Rien dans un `.cof` ne s'exécute ; rien n'est chiffré (format ouvert, inspectable) ; toute voix ou tout visage d'une personne réelle exige un bloc de consentement.

### 0.1 Usages cibles (« consommateurs »)

Un même `.cof` doit pouvoir être ouvert par des outils de nature très différente. La spec nomme ces cibles pour que chaque section sache *pour qui* elle existe, et pour que le validateur puisse dire « ce fichier est prêt pour X » :

| Cible (`targets[]`) | Ce que l'outil lit en priorité | Exemples d'outils |
|---|---|---|
| `chat-text` | `card.json`, `psyche.json`, lore, profils de tokens | SillyTavern, Risu, Chub, Character.AI (import), tout LLM |
| `chat-voice` | + `voice/` (échantillons, code vocal, SSML), `emotion_range` | Kyutai Unmute, OpenAI Realtime, Hume, ElevenLabs Conversational |
| `video-realtime` | + `face.json` expressions, `visemes.json`, `attitude.json`, avatar 2D/3D | HeyGen interactive, Tavus, D-ID, LiveKit + Audio2Face |
| `image-video-gen` | `appearance/references/`, `views/`, codes vectoriels rendus en *lineart* (ControlNet), prompts de rendu | Flux/SDXL + ControlNet, Kling, Veo, Runway, Sora (cameos via références) |
| `game-3d` | `volume/avatar.vrm|glb`, `motion/`, `visemes.json`, `rights` → `meta` VRM | Unity, Unreal, Godot, VRChat, Blender (import VRM/glTF), three.js |
| `agent-persona` | `SOUL.md`/`IDENTITY.md` dérivés, `psyche.json`, `card.system_prompt`, droits/`aiDisclosure` | OpenClaw, agents OpenAI/Anthropic/xAI (instructions système + avatar), Copilot Studio, elizaOS |
| `print-3d` | `volume/print/*.3mf`, licence | Bambu Studio, PrusaSlicer, Cura |
| `archive` | tout, hashes, C2PA, consentement | dépôts, registres OCI, conformité |

Le manifeste déclare `targets_ready[]` (calculé par le validateur à partir des sections présentes) ; un fichier texte-seul est « prêt » pour `chat-text` et `agent-persona`, pas pour `game-3d`. Rien n'empêche l'auteur de ne viser qu'une cible.

### 0.2 Niveaux de représentation (apparence, voix, mouvement)

| Niveau | Nature | Poids typique | Précision | Qui le produit |
|---|---|---|---|---|
| **L0 — Descriptif** | vocabulaire fermé + phrase générée (FDV, HAIR-1, Fashionpedia, profil vocal canonique, LMA) | 0,2–2 Ko | faible à moyenne | l'utilisateur, ou le builder depuis les niveaux supérieurs |
| **L1 — Code vectoriel / paramétrique** **[NOUVEAU]** | courbes normalisées du visage et du corps (COF-Vector), paramètres FLAME/Anny, texture procédurale, code vocal acoustique | 1–20 Ko | élevée (géométrie, proportions, teintes) | le builder depuis une photo/un WAV (MediaPipe, DECA, analyse acoustique), ou un éditeur |
| **L2 — Média** | photos, planches multi-vues, WAV, vidéos, VRM, splats | 100 Ko – 100 Mo | maximale (mais figée, non éditable) | l'utilisateur |

Analogie : L2 est le JPEG, L1 est le SVG ; L2 est le maillage, L1 est la CSG/NURBS. Un `.cof` peut porter les trois ; un lecteur utilise le plus riche qu'il sait exploiter et **doit** pouvoir se rabattre sur L1 puis L0. Le code vectoriel (L1) a sa propre page de conception (`04_COF-Vector_concept.md`) et son propre dépôt (`cof-vector`), parce que c'est une innovation en soi, utilisable hors de COF.

### 0.3 Portée : quels personnages ?

**Aucune contrainte sur la nature du personnage** : humain, elfe, robot, animal, entité abstraite — seule l'imagination de l'auteur fait la limite. En revanche, les *codes* (visage, corps, mouvement) sont conçus d'abord pour l'**anthropomorphe**. Le manifeste déclare donc :

```jsonc
"morphology": { "class": "humanoid", "species": "human", "notes": "" }
// class ∈ humanoid | anthropomorphic-animal | quadruped | avian | aquatic | mechanical | amorphous | other
```
Règle : un code dont le vocabulaire déclare `applies_to: ["humanoid"]` n'est pas *interdit* pour une autre classe, il est *non garanti* : le validateur l'accepte avec avertissement. Les classes non humanoïdes utilisent L0 (descriptif libre) et L2 (médias, 3D) sans restriction ; des vocabulaires spécifiques pourront être ajoutés plus tard sous `vocabularies/` sans changer le format. **Priorité absolue de la v1 : l'avatar humain.**

---

## 1. Conteneur physique

### 1.1 Archive

- Format : **ZIP** (APPNOTE 6.3.x), zip64 **accepté en lecture**, requis seulement au-delà de 4 Gio ou 65 535 entrées.
- Première entrée : fichier **`mimetype`**, stocké **sans compression**, contenant exactement `application/vnd.cof.character+zip` (leçon EPUB : détection sans décompression par lecture des 70 premiers octets).
- Deuxième entrée : **`manifest.json`** (le manifeste racine, § 2). Un lecteur DOIT pouvoir fonctionner après lecture de ces deux seules entrées.
- Chemins : ASCII `[A-Za-z0-9._/-]`, pas de `..`, pas de chemin absolu, pas de lien symbolique, séparateur `/`. Un lecteur DOIT rejeter toute entrée qui viole ces règles (anti zip-slip).
- Compression : `deflate` recommandé pour JSON/Markdown/texte ; **`store` (0) obligatoire** pour les binaires à haute entropie (JPEG/WebP/AVIF, Opus/FLAC/MP3, GLB/VRM, SPZ, MP4) — ils ne gagnent rien et se lisent par simple décalage.
- Alignement optionnel : si le manifeste déclare `"container": {"aligned": 64}`, chaque entrée binaire stockée commence sur un multiple de 64 octets (padding dans le champ *extra* ZIP, méthode USDZ) pour permettre le `mmap`. Les puissances de 2 servent **ici**, et nulle part ailleurs (voir § 8).
- Chiffrement ZIP : **interdit** (comme CharX). La confidentialité se traite au-dessus du conteneur.

### 1.2 Arborescence normative

```
mimetype                          ← sentinelle, stockée, 1re entrée
manifest.json                     ← manifeste racine (§ 2)
character/
  card.json                       ← Character Card V3 complète (source de vérité du texte)
  psyche.json                     ← traits typés, buts, craintes, contradictions, émotion de base (§ 3.2)
  story.md                        ← histoire & contexte long (Markdown)
  lorebook.json                   ← lorebook_v3 autonome (optionnel, sinon dans card.json)
  SOUL.md  IDENTITY.md            ← projections Markdown (générées ou maintenues à la main)
appearance/
  face.json                       ← code visage : FLAME + vocabulaire descriptif + expressions-types (§ 4.1)
  face.vec.json                   ← code vectoriel visage COF-Vector : courbes + texture procédurale (§ 4.0)
  body.json                       ← code corps : Anny + β SMPL-X + mesures + teint (§ 4.2)
  body.vec.json                   ← code vectoriel corps : silhouette face/profil normalisée (§ 4.0)
  hair.json                       ← code cheveux / pilosité (§ 4.3)
  outfits/<id>.json               ← tenues : Fashionpedia + GarmentCode (§ 4.4)
  views/<sujet>.<angle>.<ext>     ← vues multiples : head.front.jpg, body.left34.png… (§ 4.5)
  expressions/<nom>.<ext>         ← images d'expressions nommées (joy, anger… ou nom libre)
  references/                     ← jeu de référence génératif + prompt.txt stable (§ 4.6)
physique/
  attitude.json                   ← signature de mouvement, posture, gestes, proxémie (§ 5)
  poses/<nom>.pose.json           ← postures habituelles en points-clés OpenPose normalisés + rendu PNG ControlNet (§ 5.1)
voice/
  profile.json                    ← profil vocal typé, VPA, rendus moteur, SSML (§ 6)
  voice.vec.json                  ← code vocal COF-Voice : mesures acoustiques + qualité + manière (§ 6.3)
  samples/<id>.wav + <id>.txt     ← échantillons canoniques + transcription obligatoire
  engines/<moteur>/…              ← artefacts dérivés (voice_id, .npz, .onnx…), versionnés
volume/
  avatar.vrm | avatar.glb         ← avatar riggé (pivot VRM 1.0)
  skeleton.json                   ← déclaration du rig et table vers le squelette canonique si rig non standard (§ 7)
  splat.spz + splat.json          ← nuage gaussien (externe recommandé, cf. § 8) + liaison à l'avatar riggé
  print/figurine.3mf              ← dérivé imprimable
motion/
  clips/<id>.bvh | <id>.vrma      ← clips de mouvement
  visemes.json                    ← mapping de visèmes déclaré
rights/
  consent.json                    ← consentement (§ 9.2)
  licenses/                       ← textes de licence si non-SPDX
  manifest.c2pa                   ← sidecar C2PA du conteneur (optionnel)
extensions/<vendeur>/…            ← tout le reste, namespacé
```

Règle d'extension : tout chemin non prévu DOIT se trouver sous `extensions/<vendeur>/` et toute clé JSON inconnue DOIT être **conservée** à la relecture-réécriture (règle `extensions` de CCv2 reprise).

### 1.3 Enveloppes de compatibilité (exports, pas formats maîtres)

| Cible | Mécanisme | Perte |
|---|---|---|
| PNG `chara` + `ccv3` | `card.json` en base64 dans deux chunks `tEXt` ; vignette = `appearance/views/head.front.*` | tout sauf le texte et l'icône |
| `.charx` (Risu) | copie de `card.json` à la racine + `assets/` réorganisés, URI `embeded://` | droits, codes, voix structurée |
| `SOUL.md` / `IDENTITY.md` | projection Markdown (§ 3.4) | tout le non-textuel |
| `.vrm` | extraction de `volume/avatar.vrm` ; `meta` VRM alimenté depuis `rights` | tout sauf la 3D |
| Artefact OCI | § 10 | aucune (mêmes digests) |

---

## 2. `manifest.json` — le manifeste racine

Validé par `schemas/manifest.schema.json` (JSON Schema 2020-12). Exemple complet dans `examples/manifest.example.json`.

```jsonc
{
  "cof": "0.1",                                  // version du format (semver majeur.mineur)
  "id": "01J9ZK5Y7Q4W8R2M3N6P0T1V9X",            // ULID stable sur toute la vie du personnage
  "name": "Léa Marchand",
  "nickname": "Léa",
  "age": { "value": 34, "unit": "years", "basis": "declared" },   // OBLIGATOIRE et non ambigu (§ 9.1)
  "languages": ["fr", "en"],                     // ISO 639-1
  "summary": "Ingénieure acoustique devenue archiviste sonore ; sceptique, drôle, loyale.",
  "fictional": true,                             // false ⇒ rights.consent OBLIGATOIRE
  "morphology": { "class": "humanoid", "species": "human" },   // § 0.3

  "completeness": {                              // KPI en en-tête, calculé par le builder/validateur (§ 2.2)
    "score": 62, "level": "B",
    "layers": { "identity": 100, "personality": 90, "appearance": 70, "physique": 40, "voice": 55, "volume": 60, "motion": 20, "rights": 80 },
    "targets_ready": ["chat-text", "chat-voice", "agent-persona", "image-video-gen"],
    "computed_by": "cof-cli/0.2.0", "computed_at": "2026-10-09T09:12:00Z"
  },

  "tags": {                                      // slots de tags : automatiques + manuels (§ 2.2)
    "auto":    ["humanoid", "adult", "female-presenting", "contemporary", "has-voice", "has-3d", "fr", "en"],
    "manual":  ["fiction", "mentor", "archiviste", "sound-design"],
    "content": ["none"],                         // vocabulaire fermé : none | nudity | sexual | violence | gore | drugs | profanity | horror | political | religious
    "ip":      { "original": true, "franchise": null, "based_on": null }   // ex. { "original": false, "franchise": "Mickey Mouse", "based_on": "Disney" }
  },

  "sections": {                                  // présence et chemins ; absence = section vide
    "character": "character/card.json",
    "psyche": "character/psyche.json",
    "appearance": { "face": "appearance/face.json", "body": "appearance/body.json",
                    "hair": "appearance/hair.json", "outfits": ["appearance/outfits/daily.json"] },
    "physique": "physique/attitude.json",
    "voice": "voice/profile.json",
    "volume": { "avatar": "volume/avatar.vrm" },
    "motion": { "visemes": "motion/visemes.json" }
  },

  "profiles": {                                  // budgets en tokens déclarés (§ 8.1)
    "summary":  { "tokens": 380,  "blocks": ["name", "summary", "psyche.core"] },
    "standard": { "tokens": 1650, "blocks": ["card.description", "card.personality", "card.scenario", "psyche"] },
    "full":     { "tokens": 3900, "blocks": ["standard", "story.md", "physique.summary", "voice.summary"] },
    "lore":     { "tokens": 21000, "activation": "per-entry" }
  },
  "injection_order": ["identity", "rules", "lore", "history", "identity_recap"],

  "mapping_vocabularies": {                      // points d'accroche vers les normes (§ 7)
    "skeleton": "VRMC_vrm-1.0/humanoid",         // ou "KHR_character_skeleton_mapping" le jour venu
    "expressions": "ARKit-52",                   // ou "UnifiedExpressions-1.0"
    "visemes": "ARKit-52",                       // ou "Oculus-15", "PrestonBlair-AX"
    "face_model": "FLAME-2023-Open",
    "body_model": "Anny-1.0",
    "movement_notation": "LMA-Effort-1.0"
  },

  "assets": [                                    // index exhaustif de tout fichier non-JSON (§ 2.1)
    { "path": "appearance/views/head.front.jpg", "role": "view", "mediaType": "image/jpeg",
      "bytes": 184322, "sha256": "…", "license": "CC-BY-4.0",
      "digitalSourceType": "http://cv.iptc.org/newscodes/digitalsourcetype/trainedAlgorithmicMedia",
      "generator": "FLUX.1-dev", "width": 1024, "height": 1024 },
    { "path": "voice/samples/calm-30s.wav", "role": "voice-sample", "mediaType": "audio/wav",
      "bytes": 1440044, "sha256": "…", "license": "LicenseRef-COF-Internal", "duration_s": 30.0,
      "transcript": "voice/samples/calm-30s.txt" },
    { "path": "volume/splat.spz", "role": "splat", "mediaType": "application/octet-stream",
      "bytes": 48213990, "sha256": "…", "uri": "https://example.org/lea/splat.spz" }   // externe + hash
  ],

  "size_class": "standard",                      // lite ≤ 20 Mo | standard ≤ 100 Mo | full (§ 8.2)
  "container": { "aligned": 0, "executableContent": "none" },   // § 9.4

  "rights": { "$ref": "rights/consent.json#/rights" },          // ou inline (§ 9)
  "provenance": {
    "created": "2026-10-09T09:12:00Z", "modified": "2026-10-09T09:12:00Z",
    "generator": "cof-cli/0.1.0",
    "source": ["https://github.com/yannsouetre/…"],              // append-only (CCv3)
    "c2pa": "rights/manifest.c2pa",
    "signatures": []                                             // § 9.3
  },

  "metadata": {                                  // JSON-LD restreint, façon KHR_xmp_json_ld
    "@context": { "dc": "http://purl.org/dc/elements/1.1/", "schema": "https://schema.org/" },
    "dc:creator": ["Yann Souetre"], "dc:rights": "CC-BY-4.0", "schema:version": "1.2.0"
  },
  "extensions": {}
}
```

### 2.1 Entrée d'asset (`assets[]`)

| Champ | Obligatoire | Note |
|---|---|---|
| `path` | oui | chemin interne (URI relative valide — pas de `embeded://`) |
| `role` | oui | `view`, `expression`, `reference`, `voice-sample`, `voice-consent`, `engine-artifact`, `avatar`, `splat`, `print`, `motion-clip`, `document`, `other` |
| `mediaType` | oui | type MIME IANA |
| `bytes`, `sha256` | oui | intégrité et dédoublonnage |
| `license` | oui | identifiant ou expression **SPDX** ; `LicenseRef-…` pour une licence privée dont le texte est dans `rights/licenses/` |
| `digitalSourceType` | recommandé | URI IPTC (`digitalCapture`, `trainedAlgorithmicMedia`, `compositeWithTrainedAlgorithmicMedia`…) — c'est la base du marquage « contenu synthétique » |
| `uri` | optionnel | localisation externe `https://` ; si présent, `path` PEUT être absent du ZIP (asset externalisé) ; le `sha256` reste obligatoire |
| champs spécifiques | — | `width/height`, `duration_s`, `transcript`, `angle`, `subject`, `emotion`, `generator`, `model_base` |

### 2.2 Complétude et tags **[NOUVEAU]**

**Complétude.** Le format n'impose rien au-delà de l'identité et des droits ; en échange, chaque fichier porte en en-tête un **KPI de complétude** qui permet de trier, filtrer et comparer des personnages par « qualité » dans un catalogue, un dépôt ou une plateforme.

- `score` 0–100 = moyenne pondérée des couches : identity 10 %, personality 20 %, appearance 20 %, physique 5 %, voice 15 %, volume 10 %, motion 5 %, rights 15 %.
- Chaque couche est notée 0–100 selon des règles publiques (`docs/completeness-rules.md`) : présence des blocs, niveaux de représentation disponibles (L0/L1/L2 — un visage avec médias *et* code vectoriel vaut plus qu'un visage avec médias seuls), échantillons de voix avec transcription, cohérence (âge du manifeste = âge du corps, renvois `expresses` résolus, pas de doublons textuels), hashes vérifiés.
- `level` : **A** ≥ 85 (prêt pour toutes les cibles), **B** 60–84, **C** 35–59, **D** < 35 (ébauche). Un fichier texte-seul parfait plafonne autour de 45 : c'est voulu, le KPI mesure la *couverture*, pas la *qualité littéraire*.
- Le KPI est **recalculé** par tout outil conforme à l'écriture ; une valeur déclarée non conforme au calcul est un avertissement, pas une erreur. Rien n'est chiffré ni signé obligatoirement : le score est une aide au tri, pas une preuve.

**Tags.** Quatre slots :
- `auto` : générés par le builder depuis le contenu, selon des règles publiques — morphologie, tranche d'âge (`child`/`teen`/`adult`/`elder` depuis `age`), présentation de genre si déclarée, époque/univers, langues, couches présentes (`has-voice`, `has-3d`, `has-motion`), niveaux disponibles (`vector-face`). Un lecteur peut les regénérer.
- `manual` : libres, saisis par l'auteur, ≤ 30, minuscules, sans espaces.
- `content` : **vocabulaire fermé** de signalement (`nudity`, `sexual`, `violence`, `gore`, `drugs`, `profanity`, `horror`, `political`, `religious`, ou `none`). Le créateur est libre de créer ce qu'il veut ; ce slot permet aux plateformes de **filtrer** sans analyser le contenu. Le builder le propose à partir des `permissions` et des descriptifs ; l'auteur confirme. Un `content` faux n'est pas vérifiable par le format — il est en revanche opposable (provenance, signature).
- `ip` : déclaration de propriété intellectuelle — `original: true`, ou `franchise`/`based_on` nommés (ex. « Mickey Mouse », « Disney »). Permet à une plateforme de refuser un personnage sous droits tiers ; le builder peut alerter par simple correspondance avec une liste publique de franchises (`vocabularies/franchises.txt`, contributive), sans prétendre à l'exhaustivité.

---

## 3. Couche Personnalité (`character/`)

### 3.1 `card.json` — Character Card V3 embarquée (source de vérité du texte)

Une **CCv3 complète et valide** (`spec: "chara_card_v3"`, `spec_version: "3.0"`). Les champs remplissent les rubriques demandées :

| Rubrique voulue | Champ CCv3 | Convention COF |
|---|---|---|
| Personnalité | `data.personality` | texte libre, 1re personne ou 3e personne, ≤ 600 tokens recommandé |
| Comportement / idiosyncrasies | `data.extensions.cof.behavior` | liste de **manifestations observables** (tics de langage, rituels, habitudes) — distinct des dispositions (§ 3.2) |
| Buts et aspirations | `data.extensions.cof.goals` *et* phrase dans `personality` | voir `psyche.json` |
| Craintes | `data.extensions.cof.fears` | idem |
| Histoire et contexte | `data.description` (court) + `character/story.md` (long) + `character_book` (lore activable) | `story.md` ≤ 4 k tokens recommandé ; au-delà, découper en entrées de lorebook |
| Façons habituelles de s'exprimer | `data.mes_example` (dialogues Ali:Chat) + `voice/profile.json#speech_style` | le *contenu* verbal ici, le *son* dans Voix |

Règles : `creator_notes` n'entre jamais dans le prompt (CCv3) ; `extensions` est conservé intégralement ; les clés COF vivent sous `data.extensions.cof` pour rester importables **sans perte** dans SillyTavern/Risu/Chub.

### 3.2 `psyche.json` — traits typés **[NOUVEAU]**

Comble le vide constaté : aucun format ouvert ne porte à la fois le texte libre et les curseurs psychométriques.

```jsonc
{
  "model": "cof-psyche/0.1",
  "traits": {
    "big5":   { "openness": 0.72, "conscientiousness": 0.55, "extraversion": 0.31, "agreeableness": 0.64, "neuroticism": 0.40 },
    "hexaco": { "honesty_humility": 0.80 },          // facultatif, mêmes échelles [0,1]
    "custom": [ { "id": "trait:skepticism", "label": "Scepticisme méthodique", "value": 0.85, "evidence": "card.personality" } ]
  },
  "goals":  [ { "id": "goal:archive", "text": "Sauver les archives sonores de l'INA avant leur dégradation.", "horizon": "long", "priority": 1 } ],
  "fears":  [ { "id": "fear:silence", "text": "Le silence total — le signe que la mémoire s'efface.", "intensity": 0.7 } ],
  "values": [ "loyauté", "exactitude", "humour comme politesse" ],
  "contradictions": [ "Prêche la rigueur mais improvise constamment." ],
  "baseline_emotion": {                              // vocabulaires W3C EmotionML
    "category": { "set": "everyday", "value": "contentment" },
    "pad": { "pleasure": 0.3, "arousal": -0.2, "dominance": 0.4 }
  },
  "renderings": {                                    // projections dérivables automatiquement
    "sentence": "You are a character who is open, moderately conscientious, introverted, agreeable and emotionally steady.",
    "convai_sliders": { "openness": 3, "meticulousness": 2, "extraversion": 1, "agreeableness": 3, "sensitivity": 2 }
  }
}
```

Chaque trait, but et crainte porte un **identifiant** (`trait:…`, `goal:…`, `fear:…`) : c'est ce que les sections Attitude physique et Voix référencent au lieu de redécrire (§ 6 — dédoublonnage).

### 3.3 Lore

`character_book` CCv3 (ou `lorebook.json` autonome `spec: "lorebook_v3"`). Les decorators V3 (`@@depth`, `@@position`, `@@ignore_on_max_context`) sont conservés tels quels. COF ajoute dans `extensions.cof` un `tokens_estimated` par entrée pour alimenter `profiles.lore`.

### 3.4 Projections Markdown

`SOUL.md` = « voix, posture, limites » (règle OpenClaw : pas une biographie), généré depuis `personality` + `psyche.values` + `behavior` ; `IDENTITY.md` = `- Name:`, `- Creature:`, `- Vibe:`, `- Emoji:`, `- Avatar: appearance/views/head.front.jpg`. Troncature de sécurité : 20 000 caractères par fichier (limite OpenClaw). Table de mapping complète CCv3 ↔ SOUL/IDENTITY ↔ elizaOS publiée dans `docs/mappings.md` du dépôt.

---

## 4. Couche Apparence (`appearance/`)

Principe : les trois niveaux de représentation du § 0.2 — L0 descriptif, L1 code vectoriel/paramétrique, L2 médias — chacun optionnel et cohérent avec les autres. Un lecteur qui n'a que L0 ou L1 doit pouvoir régénérer une apparence plausible et **stable d'un outil à l'autre** ; c'est la raison d'être de L1.

### 4.0 Code vectoriel COF-Vector (L1) **[NOUVEAU — page dédiée `04_COF-Vector_concept.md`]**

Fichiers `appearance/face.vec.json`, `body.vec.json`, `garment.vec.json`. Résumé :

- **Géométrie en courbes** : les contours du visage (ovale, mâchoire, sourcils, paupières, nez, lèvres, oreilles, ligne de cheveux) sont des **courbes de Bézier cubiques** en coordonnées **normalisées** (origine entre les yeux, unité = distance inter-pupillaire), en vue de face *et* de profil ; idem pour la silhouette du corps (unité = stature) et les contours de vêtements. C'est le « SVG du visage » : ~2–6 Ko, éditable, indépendant de la résolution.
- **Texture en procédural** : la peau n'est pas une image mais des paramètres (teinte Monk + hex, sous-ton, rugosité, densité/zone de taches, rides par région 0–9, grain, brillance, cernes, pilosité) ; idem cheveux (HAIR-1 + direction des mèches) et tissus (couleur, motif, maille, brillance).
- **Rendu** : le code se *rend* en un **dessin au trait SVG** (face/profil) + une **carte de teintes** ; ces deux sorties alimentent directement les générateurs d'images (ControlNet lineart/canny, IP-Adapter), ce qui donne de la **cohérence de personnage entre outils** sans transporter de photo.
- **Extraction** : depuis une photo via détection de 478 points de repère (MediaPipe Face Landmarker, Apache 2.0, dans le navigateur) → ajustement de Bézier → normalisation ; depuis un VRM/FLAME via projection des sommets. Le builder le fait automatiquement.
- **Cohérence** : `face.vec.json` et `face.json` (FLAME) décrivent le même visage ; le validateur compare quelques mesures (largeur du nez, écart des yeux, hauteur des lèvres) et avertit au-delà d'un seuil.

### 4.1 `face.json`

```jsonc
{
  "model": "FLAME-2023-Open",                        // CC-BY-4.0 — redistribuable
  "shape":      { "dtype": "float16", "n": 300, "data_b64": "…" },      // identité de la tête (~600 o)
  "expression_neutral": { "dtype": "float16", "n": 100, "data_b64": "…" },
  "landmarks_hint": "MPEG-4-FDP",                    // facultatif : jeu de points de repère si fourni
  "descriptive": {                                   // [NOUVEAU] vocabulaire ouvert COF-FDV (§ 4.1.1)
    "face_shape": "oval", "forehead": { "height": "high", "width": "medium" },
    "eyebrows": { "thickness": "thick", "arch": "soft", "spacing": "close" },
    "eyes": { "shape": "almond", "size": "medium", "spacing": "wide", "color_hex": "#5B3A1E", "tilt": "upturned" },
    "nose": { "length": "medium", "bridge": "straight", "tip": "rounded", "width": "narrow" },
    "mouth": { "width": "wide", "lips_upper": "thin", "lips_lower": "full", "corners": "neutral" },
    "cheeks": "high", "chin": "pointed", "jaw": "soft", "ears": { "size": "small", "protrusion": "flat" },
    "marks": [ { "type": "freckles", "area": "cheeks", "density": "light" }, { "type": "scar", "area": "left_eyebrow", "length_cm": 1.5 } ]
  },
  "skin": { "monk": 4, "hex": "#D7A98A", "undertone": "warm" },        // Monk Skin Tone (CC BY 4.0) + sRGB
  "expressions": {                                   // expressions-types du personnage
    "vocabulary": "ARKit-52",
    "presets": [
      { "name": "amused", "vrm_preset": "happy", "facs": "6B+12C+14A", "arkit_u8_b64": "…52 octets…",
        "description": "Sourire asymétrique, œil gauche plissé.", "frequency": "frequent", "image": "appearance/expressions/amused.jpg" },
      { "name": "skeptical", "vrm_preset": null, "facs": "1A+2A+4B+14B", "arkit_u8_b64": "…" }
    ]
  },
  "renderings": { "prompt": "oval face, high forehead, thick soft-arched close-set brows, wide-set almond upturned dark-brown eyes, straight narrow nose, wide mouth with thin upper lip, pointed chin, light freckles, warm medium skin (Monk 4)" }
}
```

**4.1.1 COF-FDV (Face Descriptive Vocabulary) [NOUVEAU].** Vocabulaire ouvert, licence CC0, structuré *composant → caractéristique → descripteur*, inspiré du *principe* FISWG/ASTM E3149 mais réécrit de zéro (le texte ASTM est payant et interdit l'usage IA). Finalité déclarée : **génération et description**, pas identification biométrique. Les descripteurs sont des énumérations fermées, traduites (fr/en/ja…), chacune avec une glose en phrase. Les enumérations initiales sont publiées dans `vocabularies/fdv-1.0.json` du dépôt.

**4.1.2 Table AU ↔ ARKit [NOUVEAU].** Aucune table officielle n'existe ; COF publie `vocabularies/facs-arkit-1.0.json` (CC0) : chaque AU → combinaison pondérée de blendshapes ARKit 52, et les prototypes d'Ekman (joie 6+12, tristesse 1+4+15, surprise 1+2+5+26, colère 4+5+7+23, peur 1+2+4+5+7+20+26, dégoût 9+15+16) → vecteurs ARKit de référence.

**Interdit** : tout embedding de reconnaissance faciale (ArcFace…) — reconstructible à > 99 %, donc biométrique.

### 4.2 `body.json`

```jsonc
{
  "model": "Anny-1.0",                               // Apache-2.0 + CC0 — pivot libre, tous âges
  "age_years": 34,                                   // DOIT être égal à manifest.age
  "height_cm": 171, "mass_kg": 63,
  "phenotypes": { "gender": 0.08, "age": 0.42, "muscle": 0.45, "weight": 0.40, "proportions": 0.55 },   // [0,1], uint8 à l'encodage
  "measurements": {                                  // noms ISO 7250-1 (libres d'usage), valeurs en mm
    "stature": 1710, "chest_circumference": 880, "waist_circumference": 720, "hip_circumference": 960, "shoulder_breadth": 390
  },
  "interop": { "smplx_betas": { "dtype": "float16", "n": 10, "data_b64": "…" }, "smplx_version": "1.1" },  // pour échange, non reconstructible sans licence MPI
  "skin": { "$ref": "appearance/face.json#/skin" },
  "descriptive": { "build": "slender-athletic", "posture_default": "upright", "hands": "long fingers, short nails", "distinctive": ["tattoo: sound wave, left forearm"] },
  "intimate": null,                                  // bloc optionnel, séparé ; INTERDIT si age < 18 ; soumis à rights.permissions.allowSexualUsage (§ 9.1)
  "renderings": { "prompt": "slender athletic woman, 171 cm, upright posture, long-fingered hands, sound-wave tattoo on left forearm" }
}
```

Le bloc `intimate`, s'il est présent, suit le même schéma *composant → caractéristique → descripteur* que FDV et est **ignoré par défaut** par les lecteurs tant que `permissions.allowSexualUsage` n'est pas vrai ; sa simple présence quand `age < 18` rend le fichier **invalide**.

### 4.3 `hair.json` — COF-HAIR-1 **[NOUVEAU]**

Aucun standard ouvert n'existe (Walker 1A–4C est commercial et contesté). Code compact, licence CC0 :

| Champ | Type | Sémantique |
|---|---|---|
| `length` | uint8 0–9 ou `cm` | 0 chauve, 1 rasé, 3 oreilles, 5 épaules, 7 mi-dos, 9 taille |
| `curl` | uint8 0–9 | 0 raide, 3 ondulé, 6 bouclé, 9 crépu (continu, sans lettres de « type ») |
| `density`, `thickness` | uint8 0–9 | densité des follicules ; épaisseur du brin |
| `color_base_hex`, `color_tips_hex`, `grey_pct` | hex, hex, 0–100 | couleur naturelle/teinte, pointes, pourcentage de gris |
| `style` | enum ouverte | `loose`, `bob`, `pixie`, `braids`, `locs`, `ponytail`, `bun`, `undercut`, `afro`, `mohawk`… + `custom:` |
| `parting`, `hairline` | enum | `left`, `center`, `right`, `none` ; `straight`, `widow_peak`, `receding_m`, `rounded` |
| `facial_hair` | objet | `type` (`none`, `stubble`, `goatee`, `full_beard`…), `length`, `color_hex` |
| `body_hair` | uint8 0–9 | pilosité générale |
| `renderings.prompt` | texte | phrase générée automatiquement |

≈ 16 octets en binaire, ~200 octets en JSON. Tout champ peut être absent.

### 4.4 `outfits/<id>.json`

```jsonc
{ "id": "daily", "label": "Tenue de travail", "default": true,
  "items": [
    { "fashionpedia_category": "jacket", "attributes": ["cropped", "wool", "navy"], "color_hex": "#1F2A44",
      "garmentcode": "appearance/outfits/daily.jacket.garmentcode.json" },          // patron paramétrique MIT, optionnel
    { "fashionpedia_category": "pants", "attributes": ["straight", "high-waist", "charcoal"] }
  ],
  "accessories": [ { "type": "over-ear headphones", "worn": "around neck" } ],
  "renderings": { "prompt": "cropped navy wool jacket, high-waist straight charcoal trousers, over-ear headphones around the neck" } }
```
Plusieurs presets possibles (`daily`, `formal`, `combat`…) ; `default: true` sur un seul.

### 4.5 Vues multiples (`views/`)

Nommage normatif `<sujet>.<angle>.<ext>` :
- `sujet` ∈ `head`, `body`, `outfit-<id>`, `hands`, `detail-<libre>` ;
- `angle` ∈ `front`, `left34`, `left`, `leftback34`, `back`, `rightback34`, `right`, `right34`, `top`, `low34` ;
- fond neutre recommandé, 1024² (tête) ou 1024×2048 (corps) ; carré 1024² obligatoire pour `head.front` (vignette VRM/PNG) ;
- `ext` : `jpg`, `png`, `webp`, `avif`.

Un *character sheet* (planche) est accepté en complément sous `views/sheet.<n>.<ext>` avec, dans `assets[]`, une liste `regions` (boîtes englobantes nommées) si l'on veut l'exploiter automatiquement.

### 4.6 Jeu de référence génératif (`references/`)

3 à 5 images cohérentes + `prompt.txt` (prompt descriptif stable, ≤ 120 mots) + `negative.txt` optionnel. C'est exactement ce que Sora 2 cameos, Kling Elements, Veo Ingredients et Midjourney Omni-reference consomment sans jamais l'exporter. Un LoRA ou autre poids d'identité PEUT être joint sous `references/weights/` avec `model_base` et `version` déclarés — il est par nature non portable et doit être marqué `role: "engine-artifact"`.

### 4.7 Compatibilités demandées (Human / Poser)

Il n'existe pas de « format Human » NVIDIA : NVIDIA ACE/Audio2Face consomment des GLB/USD et des blendshapes ARKit, couverts par `volume/` et `mapping_vocabularies.expressions`. Poser (`.pz3`) et Daz (`.duf`) sont propriétaires ; l'équivalent ouvert est Anny/MakeHuman, d'où le pivot `body.json`. Un convertisseur `body.json → MPFB2 (Blender)` est la voie réaliste vers ces écosystèmes.

---

## 5. Couche Attitude physique (`physique/attitude.json`) **[NOUVEAU — assemblage de notations existantes]**

Aucun format ne décrit le *style* de mouvement d'un personnage. COF assemble trois codifications éprouvées :

```jsonc
{
  "notation": "LMA-Effort-1.0",
  "effort": { "space": -0.4, "weight": 0.2, "time": -0.6, "flow": 0.3,       // −1…+1 : indirect↔direct, léger↔fort, soutenu↔soudain, libre↔lié
              "dominant_action": "glide", "secondary_action": "dab" },        // 8 actions de base Laban
  "shape": ["enclosing", "retreating"],                                      // qualités Shape
  "tempo": { "walk_speed": "slow", "gesture_rate": "sparse", "stillness": "high" },
  "posture": {                                                               // inspiré BAP (niveau forme)
    "default": "upright, weight slightly back, arms crossed low",
    "seated": "leans back, one ankle on knee",
    "listening": "head tilted left, chin on hand"
  },
  "gestures": [                                                              // lexèmes BML propres au personnage
    { "lexeme": "cof:touch_earcup", "type": "adaptor", "bml": "<gesture lexeme='touch_earcup' hand='left'/>", "trigger": "thinking", "frequency": 0.6, "expresses": ["trait:skepticism"] },
    { "lexeme": "cof:index_tap", "type": "beat", "trigger": "making a point", "frequency": 0.8 }
  ],
  "gaze": { "contact": "intermittent", "aversion_direction": "down-left" },
  "proxemics": { "preferred_distance_m": 1.2, "touch": "rare" },
  "gait": { "descriptor": "long strides, heel-first, slight left shoulder lead" },
  "style_labels": ["100STYLE:Calm", "BABEL:walk", "BABEL:sit"],
  "expresses": ["trait:skepticism", "trait:big5.extraversion"],              // renvois vers psyche.json (§ 6)
  "reference_clips": ["motion/clips/idle-think.bvh"],
  "renderings": { "sentence": "Moves slowly and economically; gestures are rare and precise; often still, arms crossed low, head tilted when listening." }
}
```

Reconstructible par un *realizer* BML ; descriptible en phrases pour un LLM ; comparable entre personnages via les quatre axes Effort.

### 5.1 Postures habituelles en points-clés — compatibilité OpenPose **[NOUVEAU]**

Les postures et attitudes typiques (`posture.default`, `posture.seated`, gestes clés) sont aussi stockées en **points-clés 2D normalisés** dans `physique/poses/<nom>.pose.json`, au format du vocabulaire OpenPose — c'est ce que consomment ControlNet OpenPose, DWPose et la plupart des outils image/vidéo pour imposer une pose :

```jsonc
{ "cofpose": "0.1", "name": "default-standing", "skeleton": "openpose-body25",     // ou coco-18, coco-wholebody-133 (DWPose), mediapipe-pose-33
  "frame": { "unit": "stature", "origin": "mid-ankles", "view": "front" },
  "keypoints": [[0.00,0.93,0.98], [0.00,0.84,0.99], "…25 triplets [x, y, confiance]…"],
  "hands":  { "left": ["…21 pts…"], "right": null }, "face": null,                  // optionnels (OpenPose hand-21 / face-70)
  "mirror_ok": true, "expresses": ["trait:big5.extraversion"],
  "derived_from": "appearance/views/body.front.jpg",
  "renderings": { "openpose_png": "physique/poses/default-standing.openpose.png", "sentence": "Standing upright, weight slightly back, arms crossed low, head tilted left." } }
```
Règles : coordonnées normalisées (unité = stature, origine entre les chevilles) pour être indépendantes de l'image ; le builder extrait les points depuis une photo (MediaPipe Pose 33 → table de conversion vers BODY_25/COCO-18 publiée dans `vocabularies/skeletons-1.0.json`) et **rend** l'image « bonhomme OpenPose » en couleurs standard pour ControlNet ; une séquence de poses (`poses/<nom>.seq.json`, liste horodatée) couvre les gestes courts sans passer par un BVH. Les clips 3D complets restent dans `motion/` (§ 7).

---

## 6. Couche Voix (`voice/`) et règle de dédoublonnage

### 6.1 Règle « une vérité, des projections »

| Question | Où ça vit | Les autres sections… |
|---|---|---|
| *Pourquoi* le personnage agit ainsi (dispositions, buts, peurs) | `character/psyche.json` + `card.json` | renvoient par `expresses: ["trait:…"]` |
| *Comment le corps* le montre | `physique/attitude.json` | ne décrit que le moteur/postural |
| *Comment la voix* le montre | `voice/profile.json` | ne décrit que l'acoustique et la prosodie |
| *Ce qui est dit* (tics verbaux, registre, exemples) | `card.json#mes_example` + `voice/profile.json#speech_style` | `speech_style` ne contient que le *registre* (vocabulaire, longueur de phrases, interjections), pas le contenu |

Un validateur signale tout texte dupliqué à > 80 % entre sections (avertissement, pas erreur).

### 6.2 `profile.json`

```jsonc
{
  "canonical": {                                     // noyau convergent Parler-TTS / ElevenLabs / Hume / Gemini
    "gender_presentation": "feminine", "age_perceived": "30s", "accent": "fr-FR, légère pointe du Sud-Ouest",
    "pitch": { "f0_mean_hz": 190, "range": "narrow" }, "rate": "slow-medium", "loudness": "soft",
    "timbre": ["warm", "slightly breathy", "low resonance"], "expressiveness": "controlled", "audio_quality": "studio"
  },
  "vpa": { "scheme": "Laver-VPA", "settings": { "larynx_height": -1, "lip_rounding": 0, "nasality": 1, "breathiness": 2, "tension": -1 } },   // ordinal −3…+3, optionnel
  "speech_style": { "register": "familier-précis", "sentence_length": "short", "fillers": ["bon", "mmh"], "humor": "dry", "expresses": ["trait:skepticism"] },
  "emotion_range": [ { "emotionml": "contentment", "sample": "voice/samples/calm-30s.wav" }, { "emotionml": "irritation", "sample": "voice/samples/irritated-8s.wav" } ],
  "samples": [                                       // durées canoniques ≈ 8 s / 30 s / 2 min ; WAV mono 16 bit ≥ 16 kHz (24 kHz recommandé)
    { "id": "calm-8s",  "path": "voice/samples/calm-8s.wav",  "duration_s": 8.2,  "transcript": "voice/samples/calm-8s.txt",  "emotion": "contentment", "use": ["xtts", "cosyvoice", "chatterbox"] },
    { "id": "calm-30s", "path": "voice/samples/calm-30s.wav", "duration_s": 30.0, "transcript": "voice/samples/calm-30s.txt", "emotion": "contentment", "use": ["fish", "f5"] },
    { "id": "calm-2m",  "path": "voice/samples/calm-2m.wav",  "duration_s": 118,  "transcript": "voice/samples/calm-2m.txt",  "use": ["elevenlabs-ivc"] }
  ],
  "engines": [                                       // dérivés nommés, versionnés, périssables
    { "engine": "elevenlabs", "version": "v3", "voice_id": "…", "settings": { "stability": 0.5, "similarity_boost": 0.8 }, "expires": "2027-10-09" },
    { "engine": "kokoro", "version": "1.0", "path": "voice/engines/kokoro/lea.pt" },
    { "engine": "piper", "version": "1.2", "path": "voice/engines/piper/lea.onnx", "config": "voice/engines/piper/lea.onnx.json" }
  ],
  "prompt_renderings": { "elevenlabs_voice_design": "…", "hume": "…", "parler": "…" },
  "ssml_template": "<speak><prosody rate='slow' pitch='-5%'>{text}</prosody></speak>",
  "fingerprint": { "scheme": "ECAPA-TDNN-192", "data_b64": "…" },   // vérification/dédoublonnage SEULEMENT, jamais synthèse
  "consent": { "$ref": "rights/consent.json#/voice" }               // OBLIGATOIRE si la voix provient d'une personne réelle
}
```

### 6.3 Code vocal COF-Voice (L1) **[NOUVEAU]**

**Constat vérifié** : les moteurs TTS produisent bien des « fichiers de profil » en plus des WAV — latents de conditionnement XTTS (`gpt_cond_latent` + `speaker_embedding`, sauvegardables en `.pt`/`.json`), *tone color embedding* OpenVoice (`se.pth`), `spk2info.pt` / « save speaker » CosyVoice, packs de voix Kokoro (`.pt`, vecteurs de style 256-d), `.npz` Bark, `.onnx` Piper, `voice_id` cloud — mais **chacun n'est lisible que par son moteur** et dépend de sa version. Ils sont donc stockés dans `voice/engines/` comme dérivés, et le format ajoute un **code vocal descriptif et mesurable**, portable, qui permet de *piloter* la synthèse quand le moteur ne peut pas consommer l'échantillon tel quel :

```jsonc
// voice/voice.vec.json
{
  "model": "COF-Voice-1.0",
  "acoustic": {                                  // mesuré automatiquement sur les échantillons (praat-parselmouth / librosa)
    "f0_mean_hz": 190, "f0_sd_hz": 22, "f0_range_semitones": 9,
    "speech_rate_sps": 4.6, "articulation_rate_sps": 5.4, "pause_ratio": 0.18, "mean_pause_ms": 420,
    "hnr_db": 18.5, "jitter_pct": 0.9, "shimmer_pct": 3.1, "spectral_tilt_db": -9,
    "formant_shift": 0.98, "loudness_lufs": -20
  },
  "quality": {                                   // ordinal −3…+3, grille inspirée VPA (Laver)
    "breathiness": 2, "nasality": 1, "creak": 0, "tension": -1, "larynx_height": -1, "lip_rounding": 0, "pharyngeal": 0, "whisperiness": 0
  },
  "manner": {                                    // façon de s'exprimer — ce qui n'est PAS le contenu (celui-ci vit dans card.mes_example)
    "rhythm": "legato", "stress_pattern": "end-of-phrase", "intonation": "falling", "pitch_dynamics": "narrow",
    "pauses": "frequent-short", "laugh": "short-nasal", "hesitations": "mmh", "emphasis_style": "slower-not-louder",
    "emotion_shift": { "irritation": { "f0_mean_hz": 215, "speech_rate_sps": 5.6, "tension": 1 } }
  },
  "renderings": {                                // projections automatiques
    "sentence": "Warm, slightly breathy feminine voice in her thirties, low-medium pitch with a narrow range, slow legato delivery, frequent short pauses, dry humour delivered slower rather than louder.",
    "ssml": "<prosody pitch='-6%' rate='88%' volume='soft'>{text}</prosody>",
    "parler": "A woman speaks slowly with a warm, slightly breathy voice at a low pitch in a very clear recording.",
    "elevenlabs_voice_design": "…"
  }
}
```
Le bloc `acoustic` est **calculé** par le builder depuis `samples/` (mesures standard de phonétique) ; `quality` et `manner` sont saisis ou pré-remplis ; `renderings` sont générés. Résultat : une voix transportable en ~1 Ko qui pilote n'importe quel moteur (SSML, description textuelle, ou choix automatique de la voix préréglée la plus proche), et que l'échantillon WAV vient affiner quand le moteur accepte le clonage.

---

## 7. Couches Volumétrie (`volume/`) et Mouvement (`motion/`)

- **Avatar riggé** : `avatar.vrm` (VRM 1.0, `VRMC_vrm`) pivot ; `avatar.glb` accepté si le manifeste déclare `mapping_vocabularies.skeleton`. Le `meta` VRM est **dérivé** de `rights` à l'export (§ 9.1) : il n'y a qu'une seule source de permissions.
- **Point d'accroche Khronos** : si une extension `KHR_character*` apparaît au registre Khronos, `mapping_vocabularies.skeleton/expressions` pourront la nommer sans changer le format. On ne dépend pas de ces noms aujourd'hui (existence non confirmée, cf. état de l'art § 3).
- **Squelettes et structures d'os** **[NOUVEAU]** : chaque modèle 3D et chaque clip déclare son **rig** par un identifiant du vocabulaire `vocabularies/skeletons-1.0.json`, qui publie pour chacun la liste des os et sa **table de correspondance** vers le squelette canonique COF (= les noms humanoïdes VRM 1.0 : `hips`, `spine`, `chest`, `upperChest`, `neck`, `head`, `leftUpperArm`… 55 os) :

  | Identifiant | Os / points | Usage |
  |---|---|---|
  | `vrm-humanoid-1.0` (canonique) | 15 requis + ~40 optionnels (doigts, yeux, mâchoire) | VRM, three-vrm, VRChat, Blender add-on VRM |
  | `unity-humanoid` / `mixamo` | ~54 / 65 (`mixamorig:Hips`…) | Unity, Mixamo, retargeting générique |
  | `ue-mannequin` / `metahuman` | 68 / ~300 (visage inclus) | Unreal Engine |
  | `smplx-1.1` / `smplh` | 55 / 52 joints | recherche, AMASS, Motion-X |
  | `anny-104` / `anny-163` | 104 / 163 os | modèle corps libre pivot (Anny) |
  | `mhr` (Meta) | rig de SAM 3D Body | export BVH/GLB de SAM 3D Body |
  | `openpose-body25` / `coco-18` / `coco-wholebody-133` / `mediapipe-pose-33` | points-clés 2D | ControlNet, DWPose, extraction photo/vidéo (§ 5.1) |

  Un fichier `volume/skeleton.json` peut en plus décrire un rig **non standard** (liste des os, parent, repos) avec sa propre table vers le canonique ; un lecteur qui ne connaît pas le rig retargète via le canonique. Les blendshapes faciaux suivent la même logique via `mapping_vocabularies.expressions` (ARKit-52 / Unified Expressions / VRM presets).
- **Splat** : `splat.spz` (SPZ v4, ~10× plus compact que PLY) ou `KHR_gaussian_splatting` dans le GLB ; **externalisé par défaut** (`uri` + `sha256`) vu les tailles. Aucun format d'avatar splatté *animable* n'existe : le splat est une référence visuelle statique, **sans ossature native**. `volume/splat.json` déclare `bound_to: "volume/avatar.vrm"` (l'avatar riggé dont il est le rendu) et `alignment` (transformation vers le repère de l'avatar) ; un futur bloc de poids os-par-gaussienne est réservé (`weights: null`) pour le jour où un format d'avatar splatté riggé se stabilisera.
- **Impression 3D** : `print/figurine.3mf` (3MF Core 1.4, métadonnées `Title/Designer/Copyright/LicenseTerms` recopiées depuis `rights`), maillage manifold, échelle déclarée (`scale_mm_per_unit`, hauteur cible). C'est un **dérivé** généré depuis l'avatar, jamais la source.
- **Clips** : `clips/<id>.bvh` (pivot universel) et/ou `clips/<id>.vrma` (humanoïde + expressions + regard, retargetable). Chaque clip déclare dans `assets[]` : `rig` (`VRMC_vrm-1.0`, `SMPL-X-1.1`, `MHR`, `Mixamo`), `fps`, `duration_s`, `labels` (BABEL), `derived_from_video` (sha256 de la vidéo source, si extraite par WHAM/GVHMR/SAM 3D Body…).
- **Visèmes** : `motion/visemes.json` déclare le vocabulaire (`ARKit-52`, `Oculus-15`, `PrestonBlair-AX`) et une table de correspondance optionnelle — on stocke le *mapping*, pas les courbes.
- **Vidéos d'exemple** : acceptées sous `motion/reference/*.mp4` (H.264/AV1, ≤ 20 s recommandé) avec `role: "motion-reference"` ; les clips BVH/VRMA qui en dérivent le référencent.

---

## 8. Tailles : budgets en tokens et classes par canal

### 8.1 Profils de tokens (déclarés dans `manifest.profiles`)

| Profil | Budget | Usage | Justification |
|---|---|---|---|
| `summary` | ≤ 512 tokens | modèles locaux 8 k, prompt caching minimal, fiches de groupe | passe les minima de cache les plus bas ; tient dans tout contexte |
| `standard` | 1 000 – 2 000 tokens | usage courant (zone des cartes CCv2 ; repère JanitorAI « < 2 k, 2,5 k max ») | efficacité/fidélité maximale observée |
| `full` | ~4 000 tokens | histoire, attitude, voix résumées | plafond au-delà duquel le *context rot* se paie |
| `lore` | ≤ 32 000 tokens au total | activé **par entrée** (mots-clés), jamais injecté en bloc | équivalent des 32 000 caractères Character.AI |

Règles : aucun bloc *permanent* > 2 500 tokens sans justification dans `creator_notes` ; chaque bloc porte `tokens_estimated` (tokenizer déclaré, ex. `cl100k_base`) ; ordre d'injection recommandé `identity → rules → lore → history → identity_recap` (courbe en U : le début et la fin du contexte sont les mieux retenus). Les fenêtres 2026 (200 k–1 M) ne changent pas ces budgets : elles déplacent la contrainte vers le coût et la fiabilité.

### 8.2 Classes de taille (par canal de diffusion, pas par puissance de 2)

| Classe | Plafond | Contenu type | Canal visé |
|---|---|---|---|
| `lite` | ≤ 20 Mo | texte + codes + `head.front` + 3 vues + 8 s de voix | Discord gratuit (20 Mo), e-mail (~25 Mo) |
| `standard` | ≤ 100 Mo | + VRM, + échantillons 30 s/2 min, + clips, + références | GitHub (100 Mio bloquant, 50 Mio avertissement) |
| `full` | illimité | + splat, + poids d'identité, + vidéos — **externalisés** par `uri` + `sha256` | Hugging Face, S3, OCI |

**Les multiples de 2 en Mo n'ont aucune propriété utile** ; 64 Mio n'est pas plus « mémoire » que 60 Mo. Les puissances de 2 s'appliquent là où elles ont un sens physique : alignement interne (4/32/64 octets), résolution des vignettes (256², 1024²), résolution des codes (uint8, 52 blendshapes, codebook 512).

---

## 9. Couche Droits (`rights/`) — la valeur différenciante

### 9.1 `permissions` (calqué sur `VRMC_vrm.meta`, défauts restrictifs)

```jsonc
"permissions": {
  "avatarPermission": "onlyAuthor",                 // onlyAuthor | onlySeparatelyLicensedPerson | everyone
  "commercialUsage": "personalNonProfit",           // personalNonProfit | personalProfit | corporation
  "modification": "prohibited",                     // prohibited | allowModification | allowModificationRedistribution
  "allowRedistribution": false, "creditNotation": "required",
  "allowExcessivelyViolentUsage": false, "allowSexualUsage": false, "allowPoliticalOrReligiousUsage": false, "allowAntisocialOrHateUsage": false,
  "allowVoiceCloning": false,                       // [NOUVEAU] spécifiques aux personnages IA
  "allowTraining": "none",                          // none | finetune-private | finetune-public | any  (aligné plus tard sur CAWG / CC Signals)
  "allowImpersonationOfRealPerson": false,
  "ageRating": "PEGI-12", "minUserAge": 13,
  "aiDisclosure": true                              // le personnage se déclare synthétique (EU AI Act art. 50) — défaut true, désactivable seulement si fictional=false ET consent présent
}
```
`manifest.age` est **obligatoire** et non ambigu (`value` numérique + `basis`: `declared` | `apparent` | `canonical`). Si `age.value < 18` : `allowSexualUsage` est forcé à `false`, `body.intimate` interdit, et les assets `role: voice-sample` d'une personne réelle exigent un consentement de titulaire légal.

### 9.2 `consent.json` (obligatoire dès que `fictional: false` ou qu'un asset provient d'une personne réelle)

```jsonc
{ "subject_is_real_person": true,
  "subject": { "name": "…", "contact_hash": "sha256:…" },
  "scope": ["voice-synthesis", "likeness-image", "conversational-persona"],
  "excluded": ["political", "sexual", "advertising"],
  "jurisdictions": ["FR", "EU"],
  "granted": "2026-10-01", "expires": "2029-10-01", "revocation_uri": "https://…",
  "proof": [ { "type": "verbal-statement-audio", "path": "voice/samples/consent.wav", "sha256": "…", "transcript": "voice/samples/consent.txt" },
             { "type": "signed-document", "sha256": "…" } ],
  "voice": { "$ref": "#/" } }
```
Modèle de preuve calqué sur ce qu'Azure et Gemini exigent déjà (déclaration verbale enregistrée). Un lecteur conforme **refuse de synthétiser** une voix `subject_is_real_person: true` sans `proof` valide.

### 9.3 Provenance et signature

- `provenance.source[]` append-only ; `created/modified` ; `generator`.
- `digitalSourceType` IPTC **par asset** → base du marquage machine-readable (art. 50).
- **C2PA** : manifestes embarqués dans chaque asset média où le SDK le permet (PNG, JPEG, WAV, MP4) + sidecar `rights/manifest.c2pa` couvrant le ZIP (hard binding `c2pa.hash.collection.data`), en attendant un support ZIP natif.
- **Signature du manifeste** (optionnelle) : JSON canonicalisé (RFC 8785), signature Ed25519/ES256 en JWS détaché dans `provenance.signatures[]` (modèle *Signed Agent Card* A2A). L'`id` ULID + la signature donnent une identité stable vérifiable.

### 9.4 Sécurité

- `container.executableContent` ∈ `none` (défaut) | `sandboxed-wasm` | `scripts`. Un lecteur DOIT vérifier la déclaration : la présence de `.js/.lua/.py/.wasm` non déclarés rend le fichier invalide. **Aucun format sérialisé exécutable** (pas de pickle, pas de code dans les cartes).
- Noms de fichiers et `name` restreints ; `..`, chemins absolus et liens symboliques interdits ; bornes anti zip-bomb : ratio de décompression ≤ 100:1, taille décompressée déclarée.
- Tout texte destiné au prompt (`description`, `personality`, `mes_example`, `system_prompt`, `post_history_instructions`, lore `constant`) est **`untrusted`** : un importateur DOIT afficher `system_prompt`, `post_history_instructions` et les entrées `constant` avant activation.
- Les `uri` externes sont `https://` uniquement et vérifiées par `sha256` avant usage.

---

## 10. Distribution double mode

1. **Fichier** `.cof` monolithique (ZIP) — le mode partage.
2. **Artefact OCI** — le mode registre : manifeste OCI avec `artifactType: application/vnd.cof.character.manifest.v1+json`, `config` = `manifest.json` (lisible sans télécharger), une couche par asset **non compressée** (`mediaType` propre, digest = `sha256` déclaré), `subject`/referrers pour signatures (cosign) et attestations. Un outil `cof push`/`cof pull` convertit sans perte dans les deux sens (même digests).

---

## 11. Niveaux de conformité et validation

| Niveau | Exige |
|---|---|
| **COF-Core** | `mimetype`, `manifest.json` valide, `age`, `rights.permissions`, `character/card.json` CCv3 valide, `assets[]` exhaustif et hashes vérifiés |
| **COF-Psyche** | + `psyche.json` valide, renvois `expresses` résolus |
| **COF-Visual** | + au moins `head.front` 1024² ; `face.json`/`body.json`/`hair.json` valides s'ils existent ; prompt de rendu présent |
| **COF-Voice** | + ≥ 1 échantillon avec transcription, `canonical` rempli, consentement si personne réelle |
| **COF-3D** | + avatar VRM/GLB chargeable, `meta` VRM cohérent avec `rights` |
| **COF-Motion** | + ≥ 1 clip avec `rig` déclaré, `visemes.json` |
| **COF-Rights+** | + C2PA par asset média, signature du manifeste |

Le validateur de référence (`cof validate fichier.cof`) rend un rapport par niveau, des *erreurs* (non conforme) et des *avertissements* (doublons textuels, budgets dépassés, assets externes injoignables), recalcule `completeness` et `targets_ready`.

L'aller-retour **PNG ccv3 → COF → PNG sans perte** est un *test* du convertisseur, pas une exigence du format : un `.cof` peut légitimement contenir moins (ou autre chose) que la carte dont il est issu, par exemple après compression.

### 11.1 Le builder **[NOUVEAU]**

Le builder est l'outil grand public du format : une **page web unique** (HTML + JavaScript, aucune installation, fonctionne hors ligne une fois chargée, téléchargeable gratuitement, hébergeable sur GitHub Pages et en Space Hugging Face statique). Tout se passe dans le navigateur : rien n'est envoyé à un serveur.

Parcours : **1 Identité** (nom, âge, fictif/réel, morphologie, langues) → **2 Personnalité** (texte libre *ou* import d'une carte PNG/CharX/SOUL.md ; curseurs psyche optionnels) → **3 Apparence** (glisser des photos/planches ; le builder détecte les points de repère, propose le code vectoriel, le vocabulaire descriptif et les tags ; presets de tenues) → **4 Voix** (glisser des WAV ; transcription saisie ou dictée ; mesures acoustiques automatiques ; code vocal pré-rempli) → **5 Corps 3D & mouvement** (glisser VRM/GLB/BVH/VRMA ; vérification du rig) → **6 Droits** (permissions par défaut restrictives, consentement si personne réelle, licence SPDX) → **7 Contrôles** (cohérence âge/corps, doublons, budgets de tokens, tags `content`/`ip`, complétude) → **Build**.

Options du **Build** :
- *Classe de taille* visée (lite / standard / full) avec estimation en temps réel ;
- **Compression** : PNG → JPEG/WebP à qualité choisie ; redimensionnement des vues ; **substitution** des médias par leur code L1 (garder ou non les photos source) ; voix : WAV → Opus/FLAC pour les échantillons longs, WAV conservé pour l'échantillon de 8 s ; externalisation des assets lourds (URL + hash) ;
- Exports annexes : PNG ccv3, `.charx`, `SOUL.md`/`IDENTITY.md`, `.vrm` seul, JSON du manifeste.

Pile technique visée (tout open source, côté client) : `fflate` (ZIP), WebCrypto (SHA-256), `ajv` (JSON Schema), MediaPipe Tasks Vision (points de repère + 52 blendshapes), Web Audio + un petit module de mesures acoustiques (F0, débit, pauses), `three-vrm` (aperçu de l'avatar), `fitting-curves` ou équivalent (Bézier). Une version Python du même pipeline existe dans `cof-cli` pour l'automatisation.

---

## 12. Versionnage et gouvernance

- `cof` suit **semver** : `0.x` = brouillon RFC ; `1.0` quand deux implémentations indépendantes lisent/écrivent le format.
- Toute évolution passe par une **RFC publique** (dossier `rfcs/`, numérotée) avec période de commentaires de 14 jours.
- Les vocabulaires (FDV, HAIR, FACS↔ARKit, LMA-Effort) sont versionnés **séparément** sous `vocabularies/` en CC0 ; un fichier déclare la version qu'il utilise.
- Engagement : transfert à une fondation ou un groupe neutre (MSF, Linux Foundation / AAIF, VRM Consortium) dès **deux adoptants indépendants**.
- Compatibilité : un lecteur `1.x` lit tout `1.y` ; clés inconnues conservées ; `extensions/` jamais purgé.

---

## Annexe A — Ce qui est réutilisé / ce qui est inventé

| Réutilisé tel quel | Réutilisé adapté | Inventé par COF (CC0) |
|---|---|---|
| Character Card V3, lorebook_v3 | `VRMC_vrm.meta` → `permissions` (+5 champs IA) | **COF-Psyche** (traits typés + renvois) |
| VRM 1.0, glTF/GLB, BVH, VRMA, 3MF, SPZ | `KHR_xmp_json_ld` → `metadata` JSON-LD | **COF-FDV** vocabulaire descriptif du visage |
| FLAME 2023 Open, Anny, SMPL-X (interop) | Modèle de preuve de consentement Azure/Gemini → `consent.json` | **COF-HAIR-1** code cheveux/pilosité |
| ARKit 52, Unified Expressions, FACS (nomenclature), EmotionML, SSML | Signed Agent Card A2A → signature du manifeste | **Table FACS ↔ ARKit** |
| Fashionpedia (noms), GarmentCode, Monk Skin Tone, ISO 7250 (noms) | OCI Artifacts (Docker Model Runner) → mode registre | **Signature de mouvement** (LMA + BAP + BML assemblés) |
| SPDX, IPTC digitalSourceType, C2PA, JSON Schema, ULID, RFC 8785 | EPUB `mimetype`, USDZ alignement 64 → conteneur | **Profils de tokens** et **classes de taille** déclarés |
| MediaPipe Face Landmarker (478 pts + 52 blendshapes), Bézier cubiques (SVG) | Mesures phonétiques standard (F0, débit, HNR…) → `acoustic` | **COF-Vector** (visage/corps/vêtements en courbes + texture procédurale) et **COF-Voice** (code vocal) |
| — | — | **KPI de complétude**, **slots de tags** (`auto`/`manual`/`content`/`ip`), **cibles** `targets_ready` |
| OpenPose BODY_25 / COCO-18 / COCO-WholeBody (DWPose), MediaPipe Pose 33 ; squelettes VRM, Unity/Mixamo, Unreal/MetaHuman, SMPL-X, Anny, MHR | squelette canonique COF = noms humanoïdes VRM 1.0 | **`skeletons-1.0.json`** (tables de correspondance), **poses OpenPose normalisées**, liaison splat ↔ avatar riggé |

## Annexe B — Exemple minimal valide (COF-Core, ~4 Ko)

```
mimetype
manifest.json        (id, name, age, fictional:true, sections.character, rights.permissions, assets:[])
character/card.json  (CCv3 : name, description, personality, scenario, first_mes, mes_example)
```
C'est un `.cof` complet. Tout le reste s'ajoute sans jamais casser ce noyau.
