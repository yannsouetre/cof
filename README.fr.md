# COF — Character Open File

**Un personnage = un fichier. Ouvert, portable, consenti.**

COF est un format de fichier ouvert (`.cof`, conteneur ZIP) qui réunit tout ce qui définit un personnage IA : personnalité, apparence (photos, code vectoriel, descriptif), voix, corps 3D, mouvement — **et** ses droits, son consentement et sa provenance. Un même fichier s'ouvre dans un chat, un générateur d'images ou de vidéo, un moteur de jeu, Blender, ou sert d'« âme » à un agent.

> Statut : **version candidate 1.0** — format 1.0 (structure gelée le 14 octobre 2026, publication v1.0.0 le 17 octobre), outil de référence `cof-cli` 1.0.0rc2, builder 0.11. Les retours sont bienvenus via les [issues](https://github.com/yannsouetre/cof/issues).

## Pourquoi
- Fin de la jonglerie entre PNG, WAV, VRM, LoRA et notes éparses.
- Jamais prisonnier d'une plateforme : COF est le format de *sortie* que les outils propriétaires ne proposent pas.
- Conforme par construction : permissions, tags de contenu, consentement, marquage « contenu synthétique » dans le manifeste.

## Contenu du dépôt
| Dossier | Contenu |
|---|---|
| `spec/` | La spécification (`SPEC.md`), les JSON Schemas, les exemples |
| `vector/` | COF-Vector : le « SVG du visage, du corps et des vêtements » |
| `vocabularies/` | Vocabulaires et tables de correspondance (CC0) |
| `rfcs/` | Propositions d'évolution |
| `docs/` | Guide d'implémentation, état de l'art, feuille de route |
| `cli/` | Outil en ligne de commande (validate, pack, import, export, extract, merge…) |
| `builder/` | Le builder web (une page HTML) — <https://yannsouetre.github.io/cof/builder/> |
| `skills/` | Skills d'agent pour manipuler des `.cof` (`cof-author`) |

## Écrit par une IA
COF est conçu pour être rédigé par des agents : donnez au vôtre la skill [`cof-author`](skills/cof-author/SKILL.md) (ou [`llms.txt`](llms.txt)) et l'outil `cof` ; il modifie un dossier décompressé, empaquette, valide et boucle jusqu'à ce que `cof validate` réponde OK. L'exemple phare Clara Mercier (12 presets, deux langues, tags, une skill d'agent) a été assemblé et mis à jour ainsi par Claude ; en test à l'aveugle, Codex et Google Antigravity ont ajouté deux presets avec la seule skill et produit un fichier valide. **Il faut un agent qui exécute des commandes** — un agent de code installé sur votre ordinateur (Claude Code, Codex, Antigravity, Cursor…) ou un agent cloud doté d'un terminal ; un assistant de chat sans exécution de code ne peut pas fabriquer un `.cof`. Comptez plusieurs minutes et, selon l'agent, de nombreuses validations de commandes : pour une petite modification, le [builder](https://yannsouetre.github.io/cof/builder/) est souvent plus rapide.

## Ouvert, avec discipline
COF est volontairement souple : presque tout est facultatif, les clés inconnues sont conservées, et il existe des portes de sortie explicites — un fichier 3D sans ses textures (`self_contained: false`), des poids LoRA par lien plutôt qu'intégrés, des catégories `x-` personnalisées. Cette ouverture ne tient qu'avec une **discipline sur ce qu'on y met** : le validateur bloque ce qui est dangereux ou cassé (mineurs et contenu intime, empreintes manquantes, références non résolues, exécutables non déclarés…), avertit sur ce qui est risqué (liens qui peuvent disparaître, 3D sans texture, transcriptions absentes…), et chaque auteur — humain, outil ou agent IA — fait la revue de cohérence du [§ 11.4 de la spec](spec/SPEC.fr.md) avant de publier : âges, identité, style, voix, langue, droits, provenance.

## Englober, pas remplacer
Un `.cof` contient une Character Card V3 valide et s'exporte en PNG `ccv3`, `.charx`, `SOUL.md`/`IDENTITY.md`, `.vrm`. Les outils existants n'ont rien à réécrire.

## Licences
Code MIT · Spécifications CC BY 4.0 · Vocabulaires CC0 — voir `LICENSES.md`.

---

*COF — Character Open File, by Yann Souetre. English version of the spec coming with the launch.*
