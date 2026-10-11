# Changelog

## 0.7.0 — 2026-10-11 — catégorie « fichiers », usage agent, fiche d'implémentation
- **Nouvelle catégorie `files`** (bibliothèque, version avancée uniquement) : `skill` (dossier `SKILL.md` + ressources), `memory` (`MEMORY.md`…), `document`, `other` ; champs `files[]`, `entry` (détecté automatiquement), `target` (`agent-skills`, `openclaw`, `hermes`, `claude`, `custom`) ; rôles d'asset `skill-file`, `memory`, `file` ; cible `agent-runtime` et tags `has-skills` / `has-memory`. Scripts de skills refusés sauf déclaration « contenu exécutable » à l'étape Build.
- **Spec § 7 bis — usage agent** : correspondance SOUL.md / IDENTITY.md / skills / MEMORY.md ↔ COF, vérifiée sur OpenClaw et Hermes Agent ; règles (bibliothèque ignorée des lecteurs non-agents, scripts déclarés, mémoire d'une personne réelle soumise au consentement).
- **`docs/IMPLEMENTING.md`** (anglais) : identification (type MIME, octets magiques à l'offset 38), classes de conformité, algorithme de lecture minimal + code Python, recettes par profil (chat, visuel, voix, 3D, agent), obligations droits et sécurité, écriture, versionnage, sécurité, tests de conformité, modèle d'enregistrement IANA (RFC 6838), check-list.
- Exemples **08-agent-skills** et **09-mixte-adulte-mineur** (9 exemples conformes) ; 20 tests.
- Builder 0.7.0 : logo redessiné d'après le brouillon (clair, sombre, monochrome, PNG 512, favicon), icône LoRA « réseau de neurones » adaptée au thème, pictogramme d'avertissement (triangle jaune) devant les messages de règles et de cohérence, catégorie Fichiers grisée en version facile.
- Feuille de route : v1.0 du conteneur annoncée le 17–18 octobre, gel de structure le 14, codes descriptifs en 1.1 / 1.2.

## 0.6.5 — 2026-10-11 — aperçus et lecture audio
- Tableaux de fichiers (facile, par déclinaison, Build) : **survol** d'une ligne image → aperçu flottant (≤ 320 px) ; survol d'une ligne audio → lecture automatique avec **forme d'onde** et curseur de progression ; quitter la ligne arrête et ferme.
- Version avancée : chaque échantillon audio a un **lecteur** ▶ ⏸ ⏹ avec forme d'onde cliquable (recherche) et temps ; les entrées de fichier natives (« Aucun fichier choisi », trompeuses après chargement) sont remplacées par un bouton « 📂 Choisir … » — la liste des fichiers chargés est dans le tableau dessous.

## 0.6.4 — 2026-10-11 — images porteuses de texte
- Builder : une image **sans carte** mais avec un texte descriptif embarqué (PNG iTXt/tEXt/zTXt `Description`/`Comment`, XMP `dc:description`, EXIF `ImageDescription`/`UserComment`/`XPComment` — y compris `Raw profile type APP1` —, JPEG COM/XMP/EXIF) crée une déclinaison de personnalité **texte libre** *et* une déclinaison d'apparence **photos en vrac** (version facile : coches Personnalité et Apparence ; version avancée : import de personnalité). Le tableau des fichiers indique la source du texte.
- CLI : `cof embed-text <png> <fiche.md>` (écrit un iTXt `Description` UTF-8, image inchangée) et `cof read-text <image>` ; spec §3.

## 0.6.3 — 2026-10-11 — builder : retirer un fichier, déclinaisons vides
- Bouton **✕ supprimer** à droite de chaque ligne des tableaux de fichiers (facile, par déclinaison, récapitulatif Build) : retire le fichier de l'état et de toutes les listes ; en version facile une déclinaison vidée disparaît, en version avancée une fiche importée redevient une déclinaison « import » vide.
- Version avancée : en quittant l'étape Éléments, chaque déclinaison **qui ne vaut que par un fichier** (apparence hors description, poses image, échantillons, clips/vidéo, 3D, poids) et qui n'en a pas déclenche « Votre déclinaison … ne contient pas de fichier. Souhaitez-vous la conserver ? » (non = suppression). Au build, une telle déclinaison est une **erreur bloquante**.
- Version facile : champ « Âge apparent » à droite, aligné sur la colonne des icônes.

## 0.6.2 — 2026-10-11 — builder : retour visuel et inventaire des fichiers
- Version facile : zone de dépôt réduite de moitié, icônes de média doublées (grille 2 colonnes) ; au chargement d'un média : **animation** de grossissement avec halo vert, coche verte qui apparaît ensuite, fond de la tuile légèrement vert, **son** discret (deux notes, WebAudio, aucun fichier) ; **tableau des fichiers chargés** sous la zone de dépôt (fichier, emplacement dans le .cof, format, média).
- Version avancée : tableau des fichiers de la déclinaison sous chaque zone de dépôt ; étape Build : **récapitulatif de tous les fichiers** (fichier, emplacement, format, taille, média, déclinaison, presets). Tables à filets fins gris clair.
- Images `.jfif` et autres variantes JPEG acceptées (0.6.1).

## 0.6.0 — 2026-10-11 — builder : version facile et interface multilingue
- **Version facile** (bouton en haut à droite ; la version avancée reste le défaut) : nom + grande zone de dépôt ; icônes des 7 médias sur le côté, coche verte quand un fichier est chargé (une carte PNG coche personnalité **et** apparence) ; seuls personnalité (fiche/texte), apparence (une image) et voix (un échantillon) sont acceptés, les autres sont grisés « version avancée » ; un seul fichier par média — un second propose de passer en version avancée (oui : bascule et ajoute le fichier) ; un seul preset ; champ « Âge apparent sur les photos » dès qu'une image est déposée (règle v0.5) ; message « Passez à la version avancée si… » ; ouvrir un `.cof` bascule automatiquement en version avancée.
- **Langue de l'interface** : FR (source), EN, DE, ES, ZH, JA — sélecteur dans l'en-tête, mémorisé localement. Portée : navigation, titres, libellés de champs, catégories, types de déclinaison, boutons, version facile. Non traduits à ce stade : textes d'aide longs, messages de contrôle, spécification (feuille de route, phase 1).

## 0.5.4 — 2026-10-10 — builder
- En-tête allégé : plus de bouton « Build » (doublon de l'étape 6) ni « Importer et fusionner » (doublon) ; l'import-fusion vit à l'étape Build sous un seul bouton « Importer et fusionner un .cof (preset, personnage)… ». L'en-tête garde « Ouvrir un .cof » (remplace le travail en cours) et le thème.

## 0.5.3 — 2026-10-10 — builder
- Logo (silhouette tête-épaules, monochrome + chevron accent) devant le titre ; bouton **clair / sombre** dans l'en-tête (mémorisé localement, suit le système par défaut) ; champs « Âge représenté » et « Base de l'âge » côte à côte, avant les tags de style.

## 0.5.2 — 2026-10-10 — étape 7 : schémas des sous-fichiers
- 11 schémas JSON 2020-12 dans `spec/schemas/` (`card`, `psyche`, `weights`, `voice-profile`, `attitude`, `pose`, `skeleton`, `hair`, `body`, `consent`, `visemes`) + `README.md` ; `consent.schema.json` devient la source de vérité du `$defs/consent` du manifeste (scope `intimate` ajouté, sha256 exigé seulement si une preuve est jointe).
- `cof validate` valide chaque sous-fichier référencé par une déclinaison contre son schéma (erreurs) ; test dédié.
- Builder 0.5.2 : `profile.json` n'écrit plus de langue vide sur les échantillons.
- `docs/design-notes-phase0.md` : notes de conception pour les étapes 6, 8, 9, 11, 12 (passation).

## 0.5.0 — 2026-10-10 (format v0.5)
- **L'âge quitte l'identité** (plus de `age` racine ni par identité) : il est porté par la **représentation** — `variant.age` sur les déclinaisons morphologiques (obligatoire sur `face` / `body` / `character-sheet` / `reference-set` pour les morphologies de forme humaine, obligatoire et ≥ 18 sur `intimate`, optionnel sur cheveux / pilosité / 3D / poids) et plancher par preset (`age_override`). Âge d'un preset = min(déclinaisons, plancher). Un âge mystérieux = `basis: apparent`.
- **Règles par preset** (§ 9.4) : aucun `intimate`, aucune `body.estimated`, aucun `allowSexualUsage` effectif dans un preset dont un élément a moins de 18 ans ; un fichier peut contenir un preset adulte avec intime et un preset mineur sans.
- **Contrôle IA `age-legality`** : sévérité `illegal` (corps d'apparence mineure + intime), affichée en rouge, bloque le build. Question du signalement laissée à la communauté (§ 9.4.5).
- `cof migrate` v0.4 → v0.5 (âge d'identité recopié sur déclinaisons et presets) ; exemples migrés ; builder ouvre encore les `.cof` v0.4 en les migrant à la volée.
- Builder 0.5.1 : plus de champ âge dans l'identité ; « Âge représenté » obligatoire/optionnel selon le type ; contrôles par preset ; « Particularités » au pluriel ; `cof import --age` place l'âge sur le visage et en plancher du preset.

## 0.4.3 — 2026-10-10
- Builder 0.4.3 : **personnalité harmonisée** avec les autres catégories — « + Ajouter une déclinaison » puis choix du type dans la carte (*texte structuré* / *texte libre* / *import d'un fichier*) ; le type « import » affiche une zone glisser-déposer identique aux autres et prend le type du fichier déposé (carte → structuré, .md/.txt → libre, image sans fiche → « Photos en vrac » et la déclinaison vide disparaît) ; une déclinaison « import » restée vide est ignorée au build et signalée.
- Build : « Exporter **un** preset » ; nouveau bouton « Importer un preset… » (même mécanisme que « Importer et fusionner » : un preset exporté est un `.cof` allégé, l'importer l'ajoute à ce fichier).

## 0.4.2 — 2026-10-10
- **Transcription des échantillons de voix facultative** (recommandée) : `assets[].transcript` optionnel dans le schéma ; validation → avertissement au lieu d'erreur (erreur seulement si déclarée et absente) ; KPI voix : échantillons 30 + 10 si tous transcrits. Motivation : ElevenLabs, XTTS, OpenVoice… clonent sans texte ; F5-TTS, CosyVoice, Fish en profitent.
- **`intimate` : « verrouillé » remplacé par « opt-in »** et défini techniquement (§4.5) : non-chargement par défaut sauf `allowSexualUsage` **et** demande explicite de l'hôte ; dossier isolé pour retrait d'un bloc ; `tags.content` doit contenir `nudity` ou `sexual` (nouvelle règle de validation, CLI + builder).
- Builder 0.4.2 : « + Ajouter une déclinaison » uniforme sur les 7 catégories — pour la personnalité il ouvre le choix texte structuré / texte libre / import ; transcription vide non écrite dans le fichier ; libellés mis à jour.

## 0.4.1 — 2026-10-10
- **Deux régimes de preset** explicités dans la spec : *combinaison* (personnalité, apparence, poids, 3D, voix — une déclinaison par type sauf cumulables, régions du corps exclusives) et **bibliothèque** (`posture`, `motion` — plusieurs déclinaisons de tout type, rien d'obligatoire à l'inférence, `defaults` optionnels par catégorie). Vêtements et accessoires = **garde-robe** (cumulables par région).
- `attitude.json` admis dans `motion` en plus de `posture` (lecteurs : chercher dans les deux) ; +30 au KPI motion.
- `character-sheet` : **une seule planche** par déclinaison par défaut, `allow_multiple_sheets: true` pour en admettre plusieurs (cohérence exigée) ; `reference-set` : multiple d'office, cohérence exigée.
- Builder 0.4.1 : icônes 👄 voix / 🏃 postures / 🎥 mouvements ; création d'une personnalité au choix **texte structuré / texte libre / import de fichier** (carte PNG/JSON, .md/.txt → texte libre, image sans fiche → proposée en « Photos en vrac », image conservée) ; planche unique par défaut avec option « plusieurs planches » et avertissement de cohérence ; bibliothèques en cases à cocher dans les presets avec « par défaut » optionnel ; conflits de type ignorés pour les bibliothèques.
- CLI : `LIBRARY_CATEGORIES` exemptées de la règle « une déclinaison par type » ; schéma : `preset.defaults`, `variant.allow_multiple_sheets`, `motion.kind = attitude` ; test dédié.

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
