# Pipeline d'amorçage — personnages de la galerie COF

Ce script fabrique les personnages d'exemple de la galerie. Pour chaque fiche JSON, il génère les images de référence avec l'API Gemini, assemble le dossier COF, puis lance `cof pack` et `cof validate`. Il écrit ensuite un fichier `REVIEW.md` à cocher par un humain.

Il tourne **sur ton PC**. Il ne publie, n'envoie et ne partage **rien**.

## Règles de la galerie d'amorçage (vérifiées par le script)

- Personnages **fictifs et originaux** uniquement : pas de personne réelle, pas de franchise, pas de « à la manière de » un artiste vivant.
- **Adultes** (18 ans ou plus) ou **non-humains** uniquement. Aucun contenu intime : `tags.content` vaut `["none"]`.
- Une fiche qui enfreint une de ces règles est refusée avant tout appel à l'API.

## Installation (une fois)

```powershell
# Python 3.10+ (ou : winget install astral-sh.uv, puis uv venv && .venv\Scripts\activate)
pip install -U google-genai pillow
pip install -e ..\..\cli              # cof-cli, depuis un clone du dépôt
# sans clone : pip install "git+https://github.com/yannsouetre/cof#subdirectory=cli"
```

## La clé de l'API

Dans une variable d'environnement, **jamais** dans un fichier, une fiche ou une conversation :

```powershell
setx GEMINI_API_KEY "ta-clé"          # puis ouvrir un NOUVEAU terminal
```

Le nom du modèle d'images change souvent. Vérifie le nom actuel dans la documentation de Google (page « Nano Banana »), puis passe-le avec `--model`, ou une fois pour toutes avec `setx COF_GEMINI_MODEL "nom-du-modèle"`. Par défaut, les scripts utilisent `gemini-nano-banana-2.1` (octobre 2026 ; `gemini-3-pro-image` pour les scènes complexes, `gemini-2.5-flash-image` est l'ancien modèle). Le palier **payant** de l'API est recommandé pour des images publiées sous CC-BY-4.0 (au palier gratuit, Google peut utiliser les données envoyées).

## Utilisation

```powershell
cd tools\seed
python seed.py sheets\example-aiko.json --prompts-only     # 1. relire les prompts
python seed.py sheets\example-aiko.json --dry-run          # 2. tester toute la chaîne, sans API (images factices)
python seed.py sheets\*.json --out out                     # 3. pour de vrai (6 images par personnage)
```

Sorties dans `out\` :
- `<nom>.cof`, le fichier validé ;
- `<nom>\`, le dossier source ;
- `<nom>.REVIEW.md`, la liste à cocher avant toute publication.

La première vue générée (le visage de face) sert de référence à toutes les suivantes, pour garder le même personnage. Si une vue est ratée, supprime le dossier et relance la fiche. Une fiche coûte 6 appels.

## La fiche

Exemple complet : `sheets/example-aiko.json`.

- **Champs obligatoires** : `name`, `summary`, `morphology.class`, `style` (vocabulaire `visual-styles-1.0`), `appearance` (une description physique et vestimentaire **précise**, en anglais), `card` (`description`, `personality`, `scenario`, `first_mes`, `mes_example`).
- **Âge** : `age` est obligatoire, et doit être d'au moins 18, pour les classes `human`, `humanoid` et `anthropomorphic-animal`.
- **Optionnels** : `nickname`, `language` (`en` par défaut), `tags`, `license` (`CC-BY-4.0` par défaut), `creator`.

## Avant de publier (`REVIEW.md`)

1. Les 6 images montrent le même personnage.
2. Il paraît l'âge déclaré, sans ambiguïté.
3. Il ne ressemble à personne de réel (recherche d'image inversée sur les vues de face).
4. Il est entièrement habillé, sans rien de suggestif, de texte ou de filigrane.
5. Le texte de la carte correspond aux images.
6. Les conditions de l'API d'images permettent de publier ces images sous la licence déclarée.

C'est **Yann** qui valide et publie.

## Souvenirs (`memories.py`, format 1.1 — RFC 0002)

Le second script ajoute des **souvenirs** à un `.cof` existant (ou à un dossier COF) : une fiche de souvenirs → une image par souvenir (même API, même clé) → `elements/memories/` → `cof pack` → `cof validate` → `REVIEW.md`. Le fichier source n'est jamais modifié : le résultat est écrit dans `out\<nom>-memories.cof`.

```powershell
python memories.py sheets\clara.memories.json --prompts-only      # 1. relire les prompts
python memories.py sheets\clara.memories.json --dry-run --out out  # 2. toute la chaîne sans API (images factices)
python memories.py sheets\clara.memories.json --out out            # 3. pour de vrai (une image par souvenir illustré)
```

La fiche (`sheets/clara.memories.json`, exemple complet) : `source` (le `.cof` ou le dossier à étendre), `identity`, `language` (langue maîtresse écrite sur l'identité), `reference` (l'asset de ressemblance envoyé à l'API quand le personnage apparaît), `presets` (quels presets listent quels souvenirs ; les presets qui héritent d'un autre héritent aussi de ses souvenirs), et `memories[]` : `id`, `kind` (`moment` / `period`), `label`, `node` (le contenu de `memory.json` : `gist` obligatoire, en une ou plusieurs langues), `image` (facultatif : `prompt`, `shows_character`, `aspect`, `style`) et `age` (l'âge du personnage s'il est montré).

Règles vérifiées avant tout appel : aucun souvenir `explicit`, aucune personne réelle, et une image qui montre le personnage exige un âge ≥ 18 — la galerie ne représente jamais de mineur ; un souvenir d'enfance montre un lieu ou un objet, pas l'enfant.

Les deux scripts partagent `gen.py` (client, génération avec image de référence, images factices du mode `--dry-run`).
