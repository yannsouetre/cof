# COF — Character Open File

**Un personnage = un fichier. Ouvert, portable, consenti.**

COF est un format de fichier ouvert (`.cof`, conteneur ZIP) qui réunit tout ce qui définit un personnage IA : personnalité, apparence (photos, code vectoriel, descriptif), voix, corps 3D, mouvement — **et** ses droits, son consentement et sa provenance. Un même fichier s'ouvre dans un chat, un générateur d'images ou de vidéo, un moteur de jeu, Blender, ou sert d'« âme » à un agent.

> Statut : **brouillon v0.2** (octobre 2026). Rien n'est encore figé ; les retours sont bienvenus via les RFC.

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
| `docs/` | État de l'art, feuille de route |
| `cli/` | Outil en ligne de commande (validate, pack, convert) — à venir |
| `builder/` | Le builder web — à venir |

## Englober, pas remplacer
Un `.cof` contient une Character Card V3 valide et s'exporte en PNG `ccv3`, `.charx`, `SOUL.md`/`IDENTITY.md`, `.vrm`. Les outils existants n'ont rien à réécrire.

## Licences
Code MIT · Spécifications CC BY 4.0 · Vocabulaires CC0 — voir `LICENSES.md`.

---

*COF — Character Open File, by Yann Souetre. English version of the spec coming with the launch.*
