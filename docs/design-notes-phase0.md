# Notes de conception — suite de la phase 0 (passation)

Rédigé le 10 octobre 2026, après la v0.5 du format et l'étape 7 (schémas des sous-fichiers). Ces notes sont destinées à qui reprend les étapes 6, 8, 9, 11 et 12 : elles consignent les idées, les pièges connus et les décisions qu'il reste à prendre, avec une recommandation à chaque fois. Les décisions **déjà prises** sont dans `spec/SPEC.md` ; ce document ne les répète que quand une suite en dépend.

Principes qui ont guidé tout ce qui précède, à garder comme boussole :
1. **Rien de chiffré, rien de caché** ; les protections sont des règles de validation et des contrats de lecteur, jamais de l'obscurité.
2. **L'âge est une propriété de la représentation**, pas de l'identité ; les règles de protection s'appliquent par preset.
3. **Deux régimes de preset** : combinaison (ce que le preset *est*) et bibliothèque (ce qu'il *peut* utiliser).
4. **Le format structure ce qu'il peut vérifier, l'IA vérifie le reste** (cohérence, légalité d'âge) ; une sévérité `illegal` bloque, tout le reste informe.
5. **Codes compacts > média lourd > texte**, mais un code n'entre dans la norme que s'il est régénérable par un outil ouvert et lisible par un humain (la leçon du maillage vectoriel abandonné).

---

## Étape 6 — Vocabulaires formels

### 6.1 `skeletons-1.0.json` (priorité haute : conditionne les étapes 9 et 11)
- Une entrée par squelette, conforme à `skeleton.schema.json` : `openpose-body25`, `coco-18`, `coco-wholebody-133`, `mediapipe-pose-33`, `h36m-17` (2D) ; `VRMC_vrm-1.0` (humanoid bones), `unity-humanoid`, `mixamo`, `ue-mannequin`, `metahuman`, `smplx-1.1`, `anny-104`, `anny-163`, `mhr` (3D).
- **Squelette canonique COF** = le sous-ensemble commun à tout le monde : `hips, spine, chest, neck, head, l/r_shoulder, l/r_elbow, l/r_wrist, l/r_hip, l/r_knee, l/r_ankle, l/r_foot` (+ `nose, l/r_eye, l/r_ear` pour la 2D). Chaque joint de chaque squelette pointe vers un canonique ou `null`. Ne pas essayer de couvrir les doigts et le visage dans le canonique en v1 : ils vont dans `hands`/`face` du `pose.json`.
- Piège : MediaPipe 33 → BODY_25 n'est pas une bijection (`MidHip` et `Neck` sont **calculés** comme milieux). Le vocabulaire doit porter des règles `derived: { "from": ["l_hip","r_hip"], "op": "midpoint" }`, sinon l'étape 9 réinvente la conversion.
- Piège : conventions d'axes (Y-up vs Z-up, forward ±Z) et de pose de repos (T vs A) sont la première source de clips « cassés » entre VRM, Mixamo et SMPL-X. Elles sont dans le schéma ; les remplir **tous**, même quand ça paraît évident.

### 6.2 `lma-effort-1.0.json`
- Les 8 actions d'effort avec leur triplet (space, weight, time) : float (indirect, light, sustained), punch (direct, strong, sudden), glide (direct, light, sustained), slash (indirect, strong, sudden), dab (direct, light, sudden), wring (indirect, strong, sustained), flick (indirect, light, sudden), press (direct, strong, sustained). Le vocabulaire sert à **valider** la cohérence entre `effort.dominant_action` et les 4 axes (un `glide` avec `weight: +0.9` est une incohérence à signaler en `minor`).
- Fournir pour chaque action 2–3 **rendus texte** (fr, en) utilisables tels quels dans un prompt vidéo ou une instruction d'agent : c'est ce qui rend le code utile sans moteur dédié.
- Shape (rising/sinking/spreading/enclosing/advancing/retreating) : même structure.

### 6.3 `facs-arkit-1.0.json`
- Table FACS AU ↔ ARKit 52 ↔ Unified Expressions ↔ VRM presets (`happy, angry, sad, relaxed, surprised, aa, ih, ou, ee, oh, blink…`). Les visèmes y sont aussi (ARKit `jawOpen`… ↔ Oculus 15 ↔ Preston Blair).
- Ne pas prétendre à une correspondance exacte : porter un champ `fidelity: exact | approximate | none` par paire. Les moteurs s'en servent pour décider s'ils remappent ou ignorent.

### 6.4 `hair-1.0.json` et `fdv-1.0.json` (visage descriptif)
- HAIR : le schéma `hair.schema.json` fixe déjà les échelles 0–9. Le vocabulaire ajoute les **libellés** par cran (fr/en), les correspondances vers l'échelle Andre Walker (1a–4c) et vers des termes de prompt (`"curl 7" → "tight curls"`), plus une liste fermée de coiffures (`loose, bob, lob, pixie, braids, box-braids, locs, bun, ponytail, undercut, mohawk, afro, twists, cornrows, buzz…`).
- FDV (face descriptive vocabulary) : **rester descriptif et prompt-orienté**, pas anthropométrique. Axes proposés : forme du visage (oval, round, square, heart, long, diamond), yeux (forme, écartement, paupières), sourcils, nez (longueur, largeur, arête), bouche (épaisseur, largeur), menton/mâchoire, pommettes, signes (taches de rousseur, grains de beauté, cicatrices, rides par zone), lunettes exclues (accessoire). Chaque axe = valeurs fermées + rendu prompt fr/en. Le but est que `face.json` (non encore schématisé) puisse être **écrit à la main** et **relu par un humain**. Ne pas réintroduire de coordonnées.
- `face.json` à schématiser dans la foulée (il manque à la liste des 11) : `fdv` (valeurs du vocabulaire) + `renderings.prompt` + `age` (déjà sur la déclinaison, ne pas dupliquer).

### 6.5 Règle d'écriture commune aux vocabulaires
- Fichier JSON `{"id","version","license":"CC0-1.0","terms":[...]}`, chaque terme avec `id` (kebab), `label` `{fr,en}`, `prompt` `{fr,en}` optionnel, `maps` optionnel (vers d'autres vocabulaires avec `fidelity`). Un schéma `vocabulary.schema.json` générique vaudrait le coup pour les valider tous de la même façon.
- `vocabularies/README.md` les liste ; `docs/tags-rules.md` dit lesquels alimentent `tags.auto`.

---

## Étape 8 — `cof voice measure` (mesures acoustiques → `voice.vec.json`)

- Pile recommandée : **parselmouth** (Praat) pour F0, jitter, shimmer, HNR ; **librosa** pour débit/pauses (VAD par énergie + seuil) ; pas de modèle lourd en v1. Le tout optionnel (`pip install cof-cli[voice]`).
- Sortie `voice.vec.json` (à schématiser : `voice-vec.schema.json`) : `f0 {median_hz, p10, p90, range_semitones}`, `rate {syllables_per_s (approx. par pics d'énergie), words_per_min si transcription}`, `pauses {ratio, mean_s}`, `quality {hnr_db, jitter_pct, shimmer_pct}`, `loudness {lufs_integrated}`, `measured_on [asset ids]`, `tool`, `version`. Puis **projection** vers le profil canonique : `pitch.range` (very-low < 100 Hz … very-high > 250 Hz pour une voix adulte, à ajuster par `gender_presentation` déclaré, jamais inféré), `rate` (slow < 3 syl/s … fast > 5.5), `timbre` (breathy si HNR bas, etc.).
- **Règle de cohérence** à ajouter (CLI + builder, `minor`) : écart entre `canonical.pitch.range` déclaré et `voice.vec.f0` mesuré, et entre `age_perceived` et l'âge du preset.
- Piège : les échantillons synthétiques (TTS) ont un jitter/shimmer anormalement bas ; signaler `info: "échantillon probablement synthétique"` plutôt que de conclure.
- `renderings` : phrase descriptive, fragment SSML (`<prosody pitch="…" rate="…">`), description style Parler-TTS. Ce sont ces rendus qui servent aux moteurs sans clonage ; ils valent plus que les chiffres bruts.

---

## Étape 9 — Pose depuis photo → `pose.json` + rendu « bonhomme »

- MediaPipe Pose 33 (déjà installé dans le venv Python 3.11 `~/.venv-mp`, wheel 0.10.14 à modèles embarqués, parce que les téléchargements de modèles sont bloqués) → conversion vers `openpose-body25` **via** `skeletons-1.0.json` (étape 6.1) → `pose.json` normalisé → rendu PNG ControlNet (couleurs et épaisseurs standard OpenPose : 18 couleurs sur la roue, membres en traits de 4 px à 512, points de 4 px ; fond noir).
- Normalisation : coordonnées dans le cadre d'origine [0,1] + `aspect` ; ne pas recadrer sur la bounding box (on perd la position dans l'image, utile pour recomposer).
- Dans le builder (JS) : pas de MediaPipe à charger (dépendances lourdes, CDN) — le builder **consomme** un `pose.json` ou laisse la CLI le produire. Le rendu bonhomme en canvas, lui, est trivial à faire côté builder (quelques dizaines de lignes) : à faire, ça rend la bibliothèque de poses visible.
- Variante `posture/photo` avec `use: pose-only` : la CLI doit pouvoir extraire la pose **et** proposer de ne conserver que le `pose.json` + rendu (supprimer la photo) : c'est le cas d'usage « seule la pose compte » et ça allège le fichier.
- Piège : poses assises/partiellement hors cadre → joints à confiance 0 ; le rendu doit omettre les membres dont un joint a c < 0.3, pas les tracer vers (0,0).

---

## Étape 11 — Exemples manquants

- **VRM + clips** : prendre un VRM CC0 (ex. modèles d'exemple du consortium VRM) + 2 clips VRMA courts ; vérifie la chaîne `volume3d/mesh` (rig `VRMC_vrm-1.0`) + `motion/clips` + `visemes.json` + `targets_ready` contenant `game-3d`. Faire figurer un `attitude.json` dans `motion` pour montrer le double rattachement.
- **Personnage d'entreprise** : identité `fictional: true`, `tags.ip` franchise = l'entreprise, permissions `commercialUsage: corporation`, `allowTraining: none`, `aiDisclosure: true`, `creditNotation: required`, un preset « support client » (voix décrite, personnalité carte avec `system_prompt`) et un preset « vidéo » (visage + character sheet + style `3d-render`). C'est l'exemple qui parle aux adoptants B2B : le soigner.
- **Consentement complet** : `fictional: false`, identité avec `consent` (schéma v0.5 : `scope` dont `voice-synthesis`, `proof` signée + sha256), échantillon de voix avec `allowVoiceCloning: true` **et** `scope ∋ voice-synthesis` (règle à ajouter au validateur : clonage autorisé ⇒ scope doit l'inclure), `allowImpersonationOfRealPerson` à `false` par défaut. Utiliser une voix synthétique et préciser dans le README que la « personne réelle » est fictive pour l'exemple.
- **Mixte adulte / mineur** (nouveau, v0.5) : un fichier avec un preset adulte (visage 34, `intimate` 34, `permissions_override.allowSexualUsage: true`) et un preset « enfance » (visage 12, texte) avec `allowSexualUsage: false` au niveau fichier. Pas d'image intime réelle : une image neutre marquée `intimate` suffit pour l'exemple, avec `tags.content: ["nudity"]`. C'est l'exemple qui prouve la règle §9.4.

---

## Étape 12 — Gel de la spec pour le lancement

- Figer sous le numéro **v0.5** (pas v0.3 comme écrit dans la feuille de route initiale : trois refontes ont eu lieu depuis).
- Relecture croisée à faire par un **autre** modèle ou une autre personne, avec cette grille : (1) chaque champ du schéma est-il mentionné dans la spec et réciproquement ? (2) chaque règle du validateur a-t-elle une phrase dans la spec ? (3) chaque règle du builder a-t-elle son équivalent CLI (parité des scores de complétude) ? (4) la §9.4 est-elle lisible par un juriste non technicien ?
- Dette connue à solder avant le gel : `face.json`, `outfit.json`, `voice.vec.json`, `face.mesh` non schématisés ; `tags.auto` recalculé par le builder mais pas par la CLI (`cof validate --recompute` devrait le faire) ; la CLI ne vérifie pas encore `allowVoiceCloning ⇒ consent.scope ∋ voice-synthesis` ; `cof extract --no-intimate` (copie tout public) promis au §4.5 pas implémenté ; `migrate` v0.4→v0.5 ne gère pas les presets sans `identity` dans un fichier multi-identités (prend l'identité par défaut).

---

## Idées non planifiées, à garder sous la main

- **`cof lint`** séparé de `validate` : conformité (bloquante) vs qualité (conseils : images trop petites, transcription manquante, style non déclaré). Aujourd'hui tout est dans `validate` sous forme d'avertissements ; séparer rendra les sorties lisibles dans la CI des adoptants.
- **Signature du manifeste** (RFC 8785 + JWS) : prévue §9.3, non implémentée ; dès qu'un adoptant redistribue des `.cof`, c'est la première demande qui viendra. Ne pas la faire avant le lancement, mais garder la place.
- **Contrôle d'âge local, sans API** : un petit modèle d'estimation d'âge sur visage (ONNX, quelques Mo) dans la CLI rendrait le contrôle `age-legality` disponible hors ligne ; à évaluer après le lancement, avec un seuil très prudent (ne lever `illegal` qu'au-dessous de ~14 ans estimés, et `major` entre 14 et 18).
- **Signalement** (§9.4.5) : la seule piste qui tient juridiquement est un **hash perceptuel** des images intimes refusées, envoyé à un tiers de confiance choisi par la communauté ; ne rien promettre avant d'avoir un partenaire.
- **Profil de taille « stream »** : pour l'usage temps réel, un preset peut vouloir un sous-ensemble d'assets chargé en premier (`priorities.by_target.video-realtime`) ; une liste ordonnée d'assets « first paint » par preset serait un ajout léger et utile.
- **Vocabulaire de scènes** (contexte d'usage : bureau, extérieur, combat…) côté presets : demandé implicitement par les usages vidéo, hors périmètre v0.5 ; à discuter au lancement.
