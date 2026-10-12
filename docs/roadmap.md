# Révision du 11 octobre 2026 — v1.0 du **conteneur**, annonce le week-end du 17–18 octobre

**Décision** : COF est d'abord un conteneur. Il est publiable maintenant : spec v0.5 (structure stabilisée), 12 schémas, CLI de référence (20 tests), builder hors ligne (facile + avancé, 6 langues d'interface), 9 exemples conformes, fiche d'implémentation (`docs/IMPLEMENTING.md`, en anglais). Les **codes descriptifs** (vocabulaires visage / cheveux / FACS / LMA / squelettes, mesures vocales, extraction de pose) passent en **1.1 / 1.2**, par PR, sans casser les lecteurs 1.0 (§ 8 de la fiche d'implémentation).

**Condition non négociable** : *gel de structure le mercredi 14 octobre au soir*. Depuis le 9, la structure a changé trois fois (catégories, âge, fichiers) ; une 1.0 qui casse dans le mois tue la confiance. Après le gel, seulement des ajouts optionnels.

| Jour | Claude | Yann |
|---|---|---|
| lun. 12 | numérotation `cof: "1.0"` + `cof migrate` 0.5 → 1.0 ; README anglais ; corpus de tests **négatifs** (`tests/invalid/`, une règle violée par fichier) | tester le builder, enrichir le `.cof` de test, lister les irritants |
| mar. 13 | `cof export --agent` (SOUL.md + IDENTITY.md + skills/ + MEMORY.md) ; dette connue : `tags.auto` recalculé par la CLI, `cof extract --no-intimate`, règle `allowVoiceCloning ⇒ consent.scope ∋ voice-synthesis` | relire la fiche d'implémentation comme un développeur extérieur |
| mer. 14 | **gel de structure** ; relecture croisée (grille des notes de passation) par un autre modèle | arbitrer les points ouverts de la relecture |
| jeu. 15 | builder en ligne (GitHub Pages) ; `SECURITY.md`, `CONTRIBUTING.md`, modèles d'issues ; notes de version | choisir le visuel d'annonce (logo validé) |
| ven. 16 | textes d'annonce FR + EN (LinkedIn, X/Bluesky, Reddit, Discord, Show HN), captures, script de vidéo de 2 min | enregistrer la vidéo (builder → `.cof` → carte PNG dans SillyTavern → SOUL.md pour un agent) |
| **sam. 17** | release GitHub **v1.0.0** (tag, binaires d'exemple) | **annonce douce** : LinkedIn FR/EN, r/SillyTavern, r/LocalLLaMA, Discords SillyTavern / OpenClaw / ComfyUI / VRM |
| mar. 20 | réponses aux retours, correctifs 1.0.x | **Show HN** (mardi matin heure US : meilleure visibilité qu'un week-end) |

**Ce qui tient lieu de « consommateur réel » dès le jour 1** (principe « une spec sans consommateur meurt ») : (1) la carte PNG exportée (`ccv3`) s'ouvre telle quelle dans SillyTavern, Chub, Risu — compatibilité native, sans attendre d'extension ; (2) `cof export --agent` produit un espace de travail OpenClaw / Hermes / Agent Skills ; (3) le builder rouvre et édite n'importe quel `.cof`. L'extension SillyTavern dédiée, le viewer web et le nœud ComfyUI restent en novembre (1.1).

**Ajouts au plan (11 oct., après le fichier Clara v3)** — à traiter avant le gel du 14 :
- *Exemple vitrine* : Clara Mercier (6 presets, 4 voix, poses OpenPose, persona agent) devient `spec/examples/10-clara-mercier` — sous réserve de l'accord de Yann sur la licence (CC-BY-4.0 proposé) et de la provenance déclarée des images et voix (outils de génération, `digitalSourceType: trainedAlgorithmicMedia`).
- *Identifiants des schémas* : les `$id` pointent vers `cof.dev`, domaine que le projet ne possède pas. Les remplacer par l'adresse GitHub Pages (`https://yannsouetre.github.io/cof/schemas/1.0/…`) au moment de la numérotation 1.0.
- *Langue normative* : spec en anglais pour l'annonce (le français devient la traduction) — décision de Yann.
- *Activation de GitHub Pages* sur le dépôt (réglage administrateur, côté Yann) pour publier le builder et les schémas.

**Ajouts au plan (11 oct. soir, retours de Yann)** — faits avant le gel :
- *Environnements* : type `appearance/environment` (cumulable, sans âge, `use: background | location`) pour les arrière-plans de discussion et les lieux liés au personnage ; type `volume3d/environment` (un lieu en GLB, USDZ ou splat). Pas de pack de décors : un autre conteneur, plus tard, si le besoin se confirme.
- *3D autonome* : toute déclinaison 3D est **un seul fichier** qui porte maillages, textures et rig (VRM, GLB, USDZ, 3MF, splats) ; OBJ et glTF à ressources externes refusés par le validateur, FBX déconseillé. Pas de « sous-conteneur » de fichiers en vrac : chemins relatifs fragiles, invérifiables, et les convertisseurs (Blender, gltf-transform, obj2gltf) existent.
- *Vignette système* : chemin réservé `Thumbnails/thumbnail.png` (≤ 256 px, 3e entrée, stockée), généré par la CLI et le builder.
- *Taille* : badge de taille totale dans l'en-tête du builder (détail par catégorie, orange au-delà de la classe visée).

**Après la 1.0** :
- *Miniatures dans les explorateurs* (un champ du fichier ne suffit pas : chaque OS exige un petit programme installé) — 1.1 : thumbnailer freedesktop pour Linux (un fichier `.thumbnailer` + un script de 20 lignes) ; 1.2 : extension Windows (fournisseur de miniatures COM, installeur signé) et extension Quick Look pour macOS (dans une appli) — bons candidats pour des contributeurs ; Android : aucune intégration système, seulement dans une future appli de visualisation.
- *Plafonds de taille* : tailles recommandées par usage / plateforme, plafond par défaut modifiable dans le builder, alerte au dépassement — à définir avec Yann. Pistes pour alléger : compression Draco / meshopt et textures KTX2 dans les GLB, LoRA référencés par URL + hash (`uri`) plutôt qu'embarqués, vidéos plafonnées.
- *Arrière-plans animés* : boucles vidéo courtes pour les avatars vidéo (`environment` + `videos`) si la demande apparaît.

**Indicateurs à J+14** : 10 `.cof` tiers, 1 contributeur externe, 1 outil tiers qui lit ou écrit le format, 300 étoiles.

---

# COF — Feuille de route et stratégie de communication (v2, calendrier resserré)

> Principe directeur tiré de l'état de l'art : **une spec sans consommateur meurt** (llms.txt, OMI_personality, elizaOS characterfile, rokoss21/soul.md). MCP, A2A, VRM, Character Cards et safetensors ont gagné avec : une implémentation de référence, un consommateur réel dès le jour 1, un second adoptant indépendant, une gouvernance neutre annoncée tôt.
> **Calendrier** : fenêtre d'opportunité courte → **Phase 0 bouclée le 31 octobre 2026**, **Phase 1 (lancement) entre fin novembre et mi-décembre 2026**. Les codes descriptifs (visage, corps, voix, attitude) sont dans le planning dès la phase 0, en version « structure + preuve de faisabilité ».

## Positionnement en une phrase

> **COF est le « MP4 des personnages » : un seul fichier ouvert qui transporte la personnalité, l'apparence, la voix, le corps 3D et le mouvement d'un personnage IA — avec ses droits et son consentement embarqués — et qu'on ouvre aussi bien dans un chat, un générateur d'images ou de vidéo, un moteur de jeu, Blender, ou comme âme d'un agent.**

Trois arguments, dans cet ordre :
1. **Fin de la jonglerie** : un dossier de PNG, WAV, VRM, LoRA et notes devient un fichier qu'on glisse-dépose — et le **builder** le fabrique en sept écrans, sans rien installer.
2. **Jamais prisonnier** : Ready Player Me a fermé le 31 janvier 2026 et les avatars non exportés ont disparu ; Sora cameos, Kling Elements, Soul ID ne s'exportent pas. COF est le format de *sortie* que ces plateformes ne proposent pas.
3. **Conforme par construction** : EU AI Act art. 50 applicable depuis le 2 août 2026, NO FAKES Act sorti de commission, Chine « une personne, un code » : consentement, marquage, tags de contenu et provenance sont dans le manifeste, pas dans un PDF à côté.

Et une **innovation à part** qui mérite sa propre visibilité : **COF-Vector**, le « SVG du visage et du corps » (cf. `04_COF-Vector_concept.md`) — un personnage transportable en quelques Ko, cohérent d'un outil à l'autre.

## Dépôts GitHub (sous `github.com/yannsouetre`)

| Dépôt | Rôle | Licence |
|---|---|---|
| `cof` | Spécification, schémas, vocabulaires, RFC, exemples, docs, site (GitHub Pages) | spec CC-BY-4.0, vocabulaires CC0 |
| `cof-cli` | Validateur / packer / convertisseurs en Python (+ mesures acoustiques, extraction vectorielle côté serveur) | MIT |
| `cof-builder` | La page web du builder (HTML/JS, hors ligne, GitHub Pages + Space Hugging Face statique) | MIT |
| `cof-vector` | Le code vectoriel visage/corps/vêtements : spec, schémas, JS + Python, démo photo → code → SVG | spec CC-BY-4.0, code MIT |
| `cof-examples` (optionnel) | Personnages d'exemple lourds (VRM, voix) en Git LFS / HF | CC-BY-4.0 |

## Suivi de la phase 0 (→ 31 octobre 2026) — 12 étapes

| # | Étape | État |
|---|---|---|
| 1 | Dépôt, licences, gouvernance, RFC 0001 | ✅ |
| 2 | Spécification + schémas + règles (complétude, tags) | ✅ (1.0 RC, schémas publiés sur GitHub Pages) |
| 3 | `cof-cli` : validate / pack / unpack / tokens / completeness / import-export PNG / SOUL / migrate / merge / extract | ✅ |
| 4 | Exemples 1–2 (texte seul ; apparence) | ✅ (7 exemples) |
| 5 | Découpage de planches + post-traitements (Python de référence) | ✅ (dérivés optionnels) |
| 6 | Vocabulaires : FDV (visage descriptif), HAIR, FACS↔ARKit, LMA, squelettes | → 1.1 (styles visuels fait) |
| 7 | Schémas des sous-fichiers : card, psyche, weights, voice profile, attitude, pose, skeleton, hair, body, consent, visemes — validés par la CLI | ✅ (11 schémas ; reste `outfit`, `voice.vec`, `face.mesh`) |
| 8 | `voice measure` (mesures acoustiques → code vocal) | → 1.1 |
| 9 | Pose depuis photo → OpenPose normalisé + rendu « bonhomme » | → 1.2 |
| 10 | Builder (identités, 7 catégories typées, presets multi-emplacements, fusion, export de preset, version facile, interface FR/EN/DE/ES/ZH/JA) | ✅ (0.9.0, entièrement traduit) |
| 11 | Exemples : agent avec skills ✅, mixte adulte/mineur ✅ ; VRM + clips, entreprise, consentement complet → 1.1 | ⏳ |
| 12 | Relecture croisée, **spec figée en 1.0** (gel de structure mer. 14 oct.), builder ⇄ CLI validés | ⏳ (numérotation 1.0 + corpus négatif faits le 12) |

## Phases

**Report phase 1** : traduction de la spécification et des messages de contrôle (EN d'abord, puis DE/ES/ZH/JA) ; l'interface du builder est déjà en six langues.

### Phase 0 — Fondations (→ 31 octobre 2026) · « rien n'est annoncé »

**Semaine 1 (9 → 17 oct.) — squelette et noyau**
- Création des dépôts `cof`, `cof-cli`, `cof-builder`, `cof-vector` ; `README`, `LICENSE`, `GOVERNANCE.md`, `CHANGELOG.md`, `rfcs/0001-container.md`.
- `cof/SPEC.md` = spécification v0.2 relue ; `schemas/manifest.schema.json` (fourni) + `psyche`, `consent`, `permissions` ; `docs/completeness-rules.md` (règles du KPI) ; `docs/tags-rules.md`.
- `cof-cli` : `validate`, `pack`, `unpack`, `tokens`, calcul de `completeness` et `targets_ready`, `import --png` / `export --png` (CCv3), `export --soul`.
- Exemple n° 1 : personnage texte seul (4 Ko) ; exemple n° 2 : + vues + 8 s de voix synthétique.

**Semaine 2 (18 → 24 oct.) — codes descriptifs v1 (structure + faisabilité)**
- `cof-vector` : `vocabularies/contours-face-1.0.json` (contours ← indices MediaPipe), `face.vec.schema.json`, `extract.js` (photo → 478 pts → Bézier → normalisation), `render.js` (→ SVG trait + flat), `measure.js`, `describe.js`. **Démo** : glisser une photo → code → SVG téléchargeable. Test de faisabilité sur 3 portraits synthétiques, regénération via ControlNet, comparaison côte à côte publiée dans `examples/`.
- `cof` : vocabulaires `fdv-1.0.json` (visage descriptif), `hair-1.0.json`, `facs-arkit-1.0.json`, `lma-effort-1.0.json`, **`skeletons-1.0.json`** (OpenPose BODY_25/COCO-18/WholeBody, MediaPipe 33, VRM, Mixamo/Unity, Unreal/MetaHuman, SMPL-X, Anny, MHR → squelette canonique) ; schémas `attitude.schema.json`, `pose.schema.json`, `skeleton.schema.json`.
- `cof-cli` / builder : extraction de pose depuis une photo (MediaPipe Pose 33 → BODY_25), rendu du « bonhomme OpenPose » PNG pour ControlNet.
- `cof-cli` : `voice measure` (F0, débit, pauses, HNR, jitter/shimmer via parselmouth/librosa) → `voice.vec.json` + `renderings` (phrase, SSML, Parler) ; `face.vec` en Python (mediapipe) pour l'automatisation.

**Semaine 3 (25 → 31 oct.) — builder v0 et exemples**
- `cof-builder` v0 : 7 écrans, import PNG/CharX/SOUL.md, glisser-déposer images/WAV/VRM, détection automatique (MediaPipe) → code vectoriel + tags `auto` + 52 blendshapes, mesures acoustiques, contrôles de cohérence (âge, doublons, budgets), options de **Build** (classe de taille, compression PNG→WebP/JPEG, substitution médias → code, Opus pour la voix longue), exports annexes. Déployé en GitHub Pages ; fichier HTML unique téléchargeable.
- Exemples n° 3 (VRM + clips, standard), n° 4 (« personnage d'entreprise » : avatar de formation, droits corporate, `targets: agent-persona, video-realtime`), n° 5 (flux de consentement complet, fictif).
- Relecture complète : spec, schémas, règles, exemples cohérents ; `cof validate` vert sur les 5 exemples ; `cof-builder` produit un `.cof` que `cof-cli` valide (et inversement).

**Jalon de sortie phase 0** : spec v0.3 figée pour le lancement ; builder v0 utilisable par un non-technicien ; démo COF-Vector qui tourne ; 5 exemples ; aucun composant annoncé publiquement (dépôts publics mais silencieux).

### Phase 1 — Consommateurs et lancement (1er nov. → 15 déc. 2026)

**Novembre — les consommateurs**
- **Viewer web** (`cof-builder` mode lecture ou page séparée) : glisser un `.cof` → fiche, vues, SVG vectoriel, avatar `three-vrm`, lecture des échantillons, chat via un petit modèle (WebLLM ou API au choix de l'utilisateur), voix via TTS navigateur ou Kyutai Unmute. Déployé en Space Hugging Face statique.
- **Intégration tueuse n° 1** : extension **SillyTavern** « Import/Export .cof » (carte + lorebook + voix via TTS local + galerie des vues + SOUL dérivé) — issue ouverte dès la 1re semaine de novembre avec prototype.
- **Intégration n° 2** (légère) : plugin/script **OpenClaw** : `.cof` → `SOUL.md` + `IDENTITY.md` + avatar ; et un gabarit « instructions système + avatar » pour agents OpenAI/Anthropic/xAI (`cof export --agent`).
- **Intégration n° 3** (si temps) : add-on Blender minimal « Import .cof » (extrait le VRM/GLB, applique nom/licence/vignette) — le format devient un *asset*.
- `cof-cli push/pull` OCI (ghcr.io) ; sidecar C2PA via `c2pa-python` pour les PNG/WAV ; signature Ed25519 du manifeste.
- Enregistrement IANA `application/vnd.cof.character+zip` (arbre vendor, procédure légère).

**Lancement (date cible : 1er → 15 décembre 2026, dès que viewer + extension SillyTavern + builder + 5 exemples sont alignés)**
- Même jour : Show HN (« COF – an open container for AI characters: personality, voice, 3D, motion and consent in one file »), r/SillyTavern, r/LocalLLaMA, r/StableDiffusion, r/VRchat, r/aivideo ; Discords SillyTavern / OpenClaw / VRM / ComfyUI ; X/Bluesky/LinkedIn ; billet long FR + EN ; vidéo de 4 minutes (builder → viewer → SillyTavern → ControlNet) ; soumissions aux *Awesome lists*.
- **Second temps (+1 semaine)** : billet dédié **COF-Vector** (« le SVG du visage ») avec la démo photo → code → SVG → regénération ; c'est le contenu le plus « viral » et il mérite sa propre vague.

**Indicateurs** : 10 personnages tiers en `.cof` ; 1 contributeur externe ; 1 outil tiers qui *lit* ou *écrit* `.cof` ; 500 étoiles cumulées.

### Phase 2 — Épaisseur, spécialistes, alliés (janvier → avril 2027)
- COF-Vector v1.0 avec spécialistes (anthropométrie, infographie, juridique) : profondeur depuis les 478 pts 3D et FLAME, `body.vec`/`garment.vec` complets, métrique publique de similarité, pont `face.vec ↔ FLAME ↔ VRM`.
- Moteurs : un TTS open source qui lit `voice/` directement (Chatterbox, Fish, Kokoro) ; viewer VRM (VSeeFace) ; mocap vidéo → `motion/` (SAM 3D Body / GVHMR) avec `rig` déclaré ; ControlNet/ComfyUI node « COF reference » qui charge le SVG + prompt.
- Normalisation par couche : *use case* « personnage multimodal portable » déposé au WG MSF Interoperable Characters/Avatars ; échanges VRM Consortium (`meta` étendu) ; Khronos CATSG si confirmé ; pont `cof ↔ ARF` à la publication ISO (début 2027).
- **Angle entreprise / AFCI** : pilote « personnages d'entreprise » (avatars de formation, agents internes) — COF comme **dossier de conformité portable** (art. 50, consentement, permissions corporate) ; atelier AFCI ; article newsletter IA & Conseil Interne ; Hub France IA / Cap Digital.
- Extension morphologique : premiers profils de contours non humains (`applies_to`), sans toucher au conteneur.

**Indicateurs** : 2 implémentations indépendantes en lecture/écriture ; 1 plateforme qui *exporte* en `.cof`.

### Phase 3 — v1.0 et gouvernance (S2 2027)
- Gel `cof 1.0` après deux implémentations indépendantes et suite de tests de conformité publique.
- Transfert de la gouvernance à un groupe neutre ; marque « COF-compatible » ; candidature comme format de *paquet* auprès des groupes qui normalisent les couches.

## Stratégie de communication (résumé)

| Axe | Contenu |
|---|---|
| **Nom & identité** | COF — Character Open File ; `.cof` ; logo simple (une silhouette dans un dossier qui se referme) ; badge « COF-compatible » ; COF-Vector a son propre visuel (un visage en traits) |
| **Message clé** | « Un personnage = un fichier. Ouvert, portable, consenti. » |
| **Preuve avant parole** | Jamais d'annonce sans builder + viewer + intégration réelle + 5 exemples |
| **Deux vagues** | 1) le conteneur (utilité, lock-in, conformité) ; 2) COF-Vector (innovation, démo visuelle) |
| **Cibles prioritaires** | 1) roleplay / LLM local (SillyTavern, Risu, Chub) ; 2) VTubing / VRM ; 3) créateurs image/vidéo IA (ComfyUI, Kling, Runway) frustrés par le lock-in ; 4) auteurs d'agents (OpenClaw, GPTs, Claude, Grok) ; 5) entreprises / consultants — conformité |
| **Canaux** | GitHub (source de vérité), Show HN, Reddit (6 subs), Discords ciblés, X/Bluesky/LinkedIn, billet FR + EN, vidéo 4 min, newsletter AFCI |
| **Rythme** | release toutes les deux semaines jusqu'au lancement puis mensuelle ; une RFC publique à la fois ; réponses aux issues sous 72 h les 3 premiers mois |
| **Alliances** | mainteneurs SillyTavern/Risu (ils ont porté CCv3), VRM Consortium, auteurs d'Anny (Naver Labs Europe, Grenoble), Kyutai (voix), ComfyUI (node), MSF WG avatars, Hub France IA |
| **Différenciation défendable** | bloc droits/consentement/tags/provenance (réglementaire) + COF-Vector (technique) |
| **Risques & parades** | *plateformes indifférentes* → open source d'abord, où l'import est un PR ; *Khronos publie `KHR_character*`* → référencé par `mapping_vocabularies`, pas de conflit ; *dérives NSFW/IP* → défauts restrictifs, âge obligatoire, slots `content`/`ip`, exemples « safe » uniquement ; *solo-maintainer* → gouvernance écrite dès le jour 1 ; *quelqu'un prend la fenêtre* → calendrier resserré, dépôts publics (horodatage) dès la semaine 1 |

## Qui fait quoi — répartition de travail Yann / Claude

| Claude (dans la session, directement dans les dépôts si accès donné) | Yann (étapes guidées une à une) |
|---|---|
| Rédaction spec/schémas/vocabulaires/règles, code `cof-cli`, `cof-builder`, `cof-vector`, exemples, tests, docs, billets FR/EN | Création des dépôts (ou accès), choix et arbitrages (noms, périmètres, défauts), tests utilisateur du builder « sans lire la doc », génération des portraits/voix synthétiques d'exemple avec ses outils, prise de contact (SillyTavern, AFCI, Kyutai), publication des posts, vidéo |

## Les 10 premières actions (à faire maintenant)

1. **Yann** : créer les dépôts publics vides `cof`, `cof-cli`, `cof-builder`, `cof-vector` sur GitHub (ou un seul `cof` monorepo si tu préfères — recommandé pour démarrer : *un seul dépôt `cof` avec dossiers `spec/`, `cli/`, `builder/`, `vector/`*, découpé plus tard), et donner l'accès à Claude via le connecteur GitHub de la session.
2. **Claude** : déposer spec v0.2, schémas, exemple, `GOVERNANCE.md`, `CHANGELOG.md`, `rfcs/0001`.
3. **Claude** : coder `cof validate` / `pack` / `unpack` / `tokens` / `completeness` (Python).
4. **Claude** : coder `import --png` / `export --png` (CCv3) et `export --soul` ; tests.
5. **Claude** : `cof-vector` : `contours-face-1.0.json`, `extract.js`, `render.js`, démo photo → SVG.
6. **Yann** : produire 3 portraits synthétiques (face, et si possible profil) + 2 courtes voix synthétiques pour les exemples ; tester la démo COF-Vector et dire ce qui « ne ressemble pas ».
7. **Claude** : vocabulaires FDV-1.0, HAIR-1.0, FACS↔ARKit-1.0, LMA-Effort-1.0 ; `voice measure`.
8. **Claude** : builder v0 (7 écrans, Build, compression) ; **Yann** : test « sans lire la doc », retours.
9. **Claude** : exemples n° 3–5 ; relecture de cohérence globale ; spec v0.3 figée.
10. **Ensemble** : préparer novembre — issue SillyTavern avec prototype, viewer web, billets, vidéo ; fixer la date de lancement entre le 1er et le 15 décembre.
