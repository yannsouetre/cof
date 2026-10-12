# Changelog

## 1.0.0rc1 — 2026-10-12 — format 1.0 release candidate
- **Format 1.0**: `cof: "1.0"`; readers accept any `1.x` (later minors only add optional fields, preserved). `cof migrate` takes v0.2 … v0.5 to 1.0 (0.5 → 1.0 is the number only, plus `preset_groups` → `preset_tags`); the validator refuses 0.x with a pointer to `cof migrate` and warns on a newer minor. All examples migrated. Builder writes 1.0 and reads 0.4 / 0.5 / 1.x.
- **Schemas published** at `https://yannsouetre.github.io/cof/schemas/1.0/` (the `$id`s, formerly on the unowned `cof.dev`); `schemas/1.0/` mirrors `spec/schemas/` (tested).
- **Negative conformance corpus** `tests/invalid/`: 22 files, one rule broken each (version, required fields, references, ages, intimate / minor rules, consent, base model, pickles, scripts, self-contained 3D, tags, `illegal` coherence finding, mimetype position / compression / value, path traversal, hash mismatch, missing asset), `cases.json` with rule and spec section, generator `build.py`; checked in CI tests.
- Found by the corpus: the `illegal` coherence severity was in the spec but not in the schema nor enforced — now both; `validate_cof` reported a path-traversal archive as a crash instead of an error — fixed.
- **CLI messages in English** (≈ 165 messages, report labels `ERROR` / `WARN`).
- **Example 10 — motion library**: 19 BVH clips from the Bandai Namco Research Motion Dataset 1 (CC BY-NC 4.0, credited per asset with `attribution` and `source_url`, in `provenance.source`, `metadata.credits` and the README): feminine-style walk / explain / respond / wave / bow / dance for the young adult, childish walk / run / wave at 12, elderly walk / explain / bow at 65, dash and fight moves for the combatant, happy style for the manga look. File 8.9 MB.
- Builder: unknown `metadata` keys and `extensions` are now preserved on rebuild (were dropped).
- **Builder 0.9.0 fully localised**: ~250 more interface strings made translatable (intros, hints, option lists, check and build messages) and translated in the six languages; missing translations fall back to English instead of French.
- Daz: `.zip` by default; a `.rar` asks first (not inspectable, may hide scripts). `cof-author` skill: security sweep (scripts, executables, pickles inside archives, optional malware scan, no secrets).

## 0.8.7 — 2026-10-12 — foldable blocks, safe deletes, voice embedding kind, Daz archives
- Builder 0.8.7: identities, variants and presets are **foldable** (± button before the title; folded = first line only: title, type, delete); folded by default from two items, unfolded when alone, new items open; *Collapse all / Expand all*.
- **Delete and remove ask for confirmation**, and say the original `.cof` is unchanged until the next build; removing the last file of a variant warns that it will be empty.
- **Voice embeddings are a voice kind** (`embedding`, next to `samples` and `described`), linked to their samples with `derives_from`, instead of a panel under every voice.
- **No visual style in 3D**: style and style tags removed from `volume3d` variants (rendering decides the look, not the file); spec § 4.7 says so.
- **Daz**: content kept as the product / export **archive** (`.zip` / `.rar`, new asset role `archive`); other formats accepted after a warning recommending an archive; category list in the interface language only; *base figure* hidden for environments and props; validator lists scripts found in zip archives (`.dsa`…), warns that RAR is not inspected and that a store-licensed archive must not be shared.
- Example 10: the four photo reference sets carry `style: photo-realistic` (manga ones: `manga`).

## 0.8.6 — 2026-10-12 — voice embeddings, Daz Studio, Clara's environments
- **Voice embeddings** (advanced mode): `profile.json` `engines[]` now documents `{engine, version, model, kind, files, voice_id}` — speaker embeddings, fine-tuned weights, RVC indexes or cloud voice IDs, each tied to the exact model that reads it, so a voice moves to another machine or platform without retraining. Builder panel per voice variant; validator checks references, formats and `allowVoiceCloning`.
- **Pickles always refused** (`.pt`, `.pth`, `.ckpt`, `.pkl`), even when executable content is declared; ambiguous `.bin` is sniffed (raw glTF buffers pass); object `.npy` / `.npz` refused. The builder explains why and shows the one-off conversion to safetensors. (The spec previously cited OpenVoice `se.pth` as an example — corrected.)
- **Daz Studio** (`volume3d/daz`): `.duf` / `.dsf` + own textures, `daz_category` (Daz store taxonomy), `figure`, `requires[]` (products, not embedded), age required for characters; licence warning (standard licence = renders only).
- **Example 10**: five environments (studio facing the park, tactical hangar, cosy living room, school atrium, manga study), each with a 16:9 desktop and a 9:16 mobile background, slotted next to the matching look; file 7 MB (lite).
- Builder 0.8.6: the top “+ Add a variant” button scrolls to the new variant and focuses its label; 3D flag and Daz fields survive reopening.

## 0.8.5 — 2026-10-12 — escape hatches, discipline, thumbnail choice
- **3D escape hatch**: OBJ / glTF with external resources are accepted when the variant declares `self_contained: false` (e.g. an untextured posing mesh); the builder explains why in a dialog and asks first; the validator then warns instead of refusing.
- **LoRA storage**: embedded by default (warning on size) or **by link** — an asset with `uri` and no `path`; `sha256` pins the version, without it the link follows the latest one (warning on link rot). Schema: `sha256` / `bytes` required only for embedded assets.
- **Thumbnail choice**: `manifest.thumbnail_source` (asset id) picks the image of `Thumbnails/thumbnail.png`; builder selector in Build with preview; default = first view of the default (or exported) preset.
- **Spec § 11.4 — authoring discipline**: what the validator blocks, what it warns about, and the coherence review every author MUST do without the builder (AI agents included). README section *Open, with discipline* (EN/FR); `cof-author` skill § 4.
- Example 10: tag family *style* (`photo-realistic`, `manga`).
- Builder 0.8.5: “file loaded” shown in the loading pop-up (✓, closes after 1 s) instead of a browser alert, same after a build; completeness badge readable in forced dark mode; warning / error colours readable in dark mode (were below 3:1).

## 0.8.4 — 2026-10-12 — environments, self-contained 3D, OS thumbnail, size badge
- **Environments**: `appearance/environment` (stackable, ageless, images with `role: environment`, `use: background | location | other`) for chat / video-avatar backgrounds and places tied to the character; `volume3d/environment` (a place as one GLB, USDZ or splat). Schema, model, spec (EN/FR), builder.
- **3D must be self-contained**: one file per variant carrying meshes, textures and rig; the validator refuses OBJ and glTF with external resources, warns on FBX; the builder only offers VRM / GLB / USDZ (+ splats, 3MF/STL for print).
- **OS thumbnail**: reserved path `Thumbnails/thumbnail.png` (≤ 256 px PNG, stored, third ZIP entry, `role: derived`, `method: thumbnail`), generated by `cof pack` and by the builder, referenced by `manifest.thumbnail`. OS thumbnailers come after 1.0 (Linux 1.1, Windows / macOS 1.2).
- Builder 0.8.4: **size badge** in the header (total of loaded files, per-category breakdown on hover, orange beyond the target size class); environment kinds; header no longer wraps.

## 0.8.3 — 2026-10-11 — skills visible, AI authoring
- Builder 0.8.3: text files of a `files` variant (skills, memories, documents) are **shown and editable** in a frame, with one chip per file (entry file first); edits go into the next build. Hover preview now also shows text files; the zoom cursor only appears where a preview exists.
- Example 10: tag `agent` (facet *usage*) on the two AI-agent presets.
- **AI authoring**: new Agent Skill [`skills/cof-author`](skills/cof-author/SKILL.md) (format in one page, validator loop, rules, recipes), `llms.txt` at the site root, implementer's guide § 7.1, README sections (EN/FR).
- **Blind-tested** with fresh agents given only the skill and the CLI: first run valid after 3 iterations, second run (after fixes) valid on the first try.
- CLI fixes found by that test: enum errors now list **every** allowed value (were truncated); `cof pack` fills asset hashes *before* recomputing, so completeness / coverage / languages are no longer left stale when new assets lack `sha256`; warning for a `description` personality with empty `text`, error for a `card` personality without `card`.

## 0.8.2 — 2026-10-11 — build feedback
- Builder 0.8.2: a **progress pop-up** (spinning ring around the logo, elapsed seconds, "keep this page open") while building, exporting a preset or a tag, opening a `.cof` or importing one — the page no longer looks frozen during long builds. Translated in the six interface languages.
- Example 10: French manga voice transcript added — every voice sample now has one.
- Example 10: the generic `eco-ux-audit` skill is replaced by a real expert skill, **`accessible-color-palette`** (multi-file: `SKILL.md`, `reference/color-math.md` with the exact WCAG and OKLab formulas, `examples/eco-green-palette.md` with a palette whose contrast ratios were computed and checked).

## 0.8.1 — 2026-10-11 — preset tags replace groups
- **Preset tags** (`preset_tags`, optional, container level) replace the same-day `preset_groups`: `[{id, label, facet?, description?, presets}]`, **many-to-many** (a preset can be `en` *and* `age-12`). Optional `facet` (language, age, style…): same-facet tags are alternatives in a filter, different facets intersect. Spec § 2.3 (EN/FR), schema, validation (duplicate id, unknown preset), merge carries tags, `cof extract --tag X [--tag Y]` (intersection; parents outside the selection are flattened, kept tags restricted). Legacy `preset_groups` → warning; `cof migrate` converts them; the builder reads them as tags.
- Builder 0.8.1: presets page gets a **filter bar grouped by facet** (chips with counts, *All*, *Untagged*, "n / N presets shown"), each preset shown once; **+ Create a tag** (name, facet with suggestions, presets checklist; ✎ to edit or delete); per-preset tag toggles on each card; a new preset inherits the active filter tags; **Export a tag** in Build.
- Example 10 (Clara v4): tags `en`/`fr` (facet language) and `age-12`/`age-29`/`age-65` (facet age); EN and FR presets share the same images and poses.
- Example 10: English voice transcripts (v6–v10); the French agent card's system prompt cut from ~9,400 to ~1,600 characters and aligned with the English one (it embedded a whole persona sheet duplicating the card fields, plus a pseudo-JSON card). Backstory and INFJ/1w9 moved into the card's `description`/`personality`; the audit method and its worked example became a shared **skill** (`files` → `eco-ux-audit`, slotted in both agent presets, target `agent-runtime`). Redundant, unclosed JSON block removed from the p1/p6 sheets.
- Builder fix: *Export a preset / a tag* no longer embeds the assets of excluded variants (a French export carried the English audio).

## 0.8.0 — 2026-10-11 — preset groups, bilingual flagship
- **Preset groups** (`preset_groups`, optional, container level): folders of presets, a preset in at most one group, never inherited. Schema, validation (unknown preset, preset in two groups, duplicate ids), merge carries groups, `cof extract --group`. Spec § 2.3 (EN/FR). Fully backward compatible: files without groups are unchanged and valid.
- Builder 0.8.0: presets page shows groups as collapsible folders (rename, choose presets by name, delete), an "Ungrouped" folder, "+ Add a group"; **Export a group** next to *Export a preset* in Build (presets whose parent is outside the group are flattened).
- **Example 10 — Clara Mercier v4, bilingual**: 12 presets in two groups (English with the English young adult as default, Français), 10 personalities (EN translated by Claude), 10 voices incl. manga; built programmatically by Claude and validated. Voice samples CC BY-NC 4.0 (free plans, attribution to ElevenLabs and Typecast).

## 0.7.3 — 2026-10-11 — English becomes normative
- `spec/SPEC.md` is now the **English normative text**; `spec/SPEC.fr.md` is the French translation. README, coherence API, completeness and tags rules, schemas README, vocabularies and builder READMEs translated (French originals kept as `*.fr.md`); schema descriptions in English.
- Spec fixes found during translation: identity no longer lists `age` in the overview and in the `identities` pattern; 8 categories (incl. `files`); coherence checks "never blocking — except `illegal`"; intimate opt-in and real-person refusal stated with MUST / MUST NOT.
- **Example 10 — Clara Mercier** (flagship): 6 presets, 4 voices, OpenPose library, agent preset; provenance per asset (`digitalSourceType: trainedAlgorithmicMedia`, generator), CC BY 4.0 for character, texts and images; voice samples pending confirmation of the voice tools' plan terms.
- Root `index.html` landing page and `.nojekyll` for GitHub Pages (builder at `/builder/`).

## 0.7.2 — 2026-10-11
- Les étiquettes de langue sont acceptées dans toutes les casses (`FR`, `fr-FR`, `fr`) — BCP 47 est insensible à la casse (RFC 5646 § 2.1.1) ; le builder les normalise en minuscules.
- Correctif builder : `profile.json` reprenait la langue d'échantillon saisie au moment du dépôt, pas celle de la déclinaison (fichier v3 de test rendu non conforme). Rouvrir et reconstruire un fichier corrige.

## 0.7.1 — 2026-10-11 — retours sur le premier fichier multi-presets réel
- Builder : bouton « + Ajouter une déclinaison » aussi **en bas** de chaque catégorie (dès qu'une déclinaison existe), et « + Ajouter un preset » en bas des presets ; la nouvelle carte défile à l'écran.
- Complétude (CLI + builder) : une personnalité **texte libre** riche compte enfin pour le chat (35 → +15 au-delà de 400 caractères, +10 au-delà de 1 500) ; avant, une fiche de 4 Ko n'était jamais « prête pour le chat ».
- Vignette (`thumbnail`) : repli sur la première image visage → planche → photos en vrac → corps du preset par défaut (avant : visage de face uniquement).
- Tags automatiques : tranche d'âge de **chaque** preset (`child`, `teen`, `adult`, `elder`) + `has-minor-preset` ; avant, seule celle du preset par défaut.
- Nouveaux contrôles (avertissements, CLI + builder) : voix partagée par des presets d'âges éloignés de plus de 15 ans ; `derives_from` entre types différents (le builder ne propose plus que des parents de même type).

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
