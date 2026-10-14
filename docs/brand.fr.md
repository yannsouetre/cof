# Identité visuelle de COF

Une seule apparence pour le format, ses outils et sa communication. Elle vient du clip de lancement (`clip/`) et l'explorateur l'utilise déjà. La [version anglaise](brand.md) porte les mêmes règles.

## Couleurs

La palette principale est sombre : un fond vert-noir profond, un texte clair et un seul accent, le turquoise.

| Jeton | Sombre (principal) | Clair | Usage |
|---|---|---|---|
| `--bg` | `#0d1312` | `#f3f4f2` | fond de page |
| `--panel` | `#18201f` | `#ffffff` | cartes, panneaux, étiquettes |
| `--line` | `#2a3533` | `#dde1de` | bordures, séparateurs |
| `--ink` | `#eef3f1` | `#1a1e1d` | texte |
| `--muted` | `#93a39e` | `#5f6764` | texte secondaire, légendes |
| `--accent` (turquoise) | `#4cc2a8` | `#0f6b5c` | liens, boutons, le choix actif, « autorisé » |
| `--accent-deep` | `#0f6b5c` | `#0f6b5c` | fin du dégradé de l'icône de fichier, boutons pleins sur fond clair |
| `--mint` | `#bfeee2` | `#d9ece7` | coin plié du fichier, surlignages doux |
| `--offer` (violet) | `#a98ae8` | `#6a45b8` | ce qu'un preset propose sans l'appliquer ; LoRA et poids |
| `--no` (corail) | `#f07a72` | `#a8231d` | « non autorisé », erreurs |
| `--warn` (ambre) | `#e0a54a` | `#9a5b00` | avertissements |

Règles :
- Un seul accent par écran : le turquoise. Le violet et le corail portent un sens (proposé, refusé) ; ils ne servent jamais de décoration.
- Le texte sur turquoise est `#05201b`, jamais blanc.
- Les grandes surfaces restent neutres ; la couleur va aux petits éléments (un bouton, une pastille, une coche).

## Polices

Les trois sont libres (SIL Open Font License) et accompagnent le clip dans `clip/fonts/`.

| Rôle | Police | Graisses |
|---|---|---|
| Titres, le mot « COF », grands chiffres | **Bricolage Grotesque** | 700, 500 |
| Texte, libellés, boutons | **IBM Plex Sans** | 400, 500 |
| Noms de fichiers, formats, code, valeurs | **IBM Plex Mono** | 500 |

- Les titres sont serrés : interlettrage −0,02 em, interligne d'environ 1,0.
- Les noms de fichiers et les formats sont toujours en chasse fixe : `photos (.jpeg)`, `LoRA (.safetensors)`.

## Formes

- Coins arrondis : 14 px pour les étiquettes et les vignettes, 22 à 28 px pour les cartes et l'icône de fichier.
- **L'icône de fichier** : un document turquoise (dégradé `#4cc2a8` → `#0f6b5c`), coin supérieur droit plié en menthe, le mot `.cof` en Bricolage 700, `character` au-dessus en Plex Mono. Elle représente le format dans les schémas et dans le clip.
- **Le buste** (`builder/icon/`) : l'icône d'application du builder et de l'explorateur.
- Pastilles pour les choix (langue, âge, style) : entièrement arrondies, contour seul quand elles sont inactives, remplies de turquoise quand elles sont actives.

## Images

- Les personnages des exemples (Clara Mercier, Martien…) sur fond blanc, dans des cartes arrondies, avec une ombre douce.
- Schémas : peu de boîtes, des libellés courts, des liaisons turquoise fines, l'icône de fichier au centre.
- Toute image publiée pour COF ne montre que des personnages fictifs et indique que ses images sont générées par IA.

## Fichiers

- Figures du README : `docs/img/` (générées depuis `tools/readme-figures/`).
- Clip : `clip/index.html` (source), `docs/media/cof-clip.mp4` (avec musique).
- Polices : `clip/fonts/` (avec leurs licences).
