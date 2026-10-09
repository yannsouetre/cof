# COF-Vector — le « SVG du visage, du corps et des vêtements »

Spécification : `SPEC.md`. Code Python (v0.1, preuve de faisabilité) : `py/`.

| Script | Rôle | État |
|---|---|---|
| `py/sheet_split.py` | Planche de personnage → panneaux → vues canoniques (`body.front`, `head.right.closeup`…) + `sheet.regions.json` | Fonctionne sur les humains et humanoïdes ; robots/créatures sans visage → faible confiance, à confirmer dans le builder |
| `py/edges.py` | Vue → cartes de traits `canny` (1 bit), `lineart` (1 bit), `softedge` (4 bits, ½ résolution) + SVG potrace | Fonctionne sur les 5 typologies, robot compris ; 6–16 Ko par carte 1 bit |
| `py/_archive/face_vec_mesh_abandoned.py` | Ancienne approche maillage → Béziers (v0.1) | Abandonnée : visage générique |

## Installation (Python 3.11, roue MediaPipe « legacy » avec modèles embarqués)
```bash
uv venv -p 3.11 .venv && source .venv/bin/activate
pip install mediapipe==0.10.14 numpy "opencv-contrib-python-headless<4.11" pillow
python py/sheet_split.py planche.jpg out/            # → out/views/*.jpg, out/sheet.regions.json
python py/edges.py out/views/head.front.jpg out/lines/     # → head.front.{canny,lineart,softedge}.png + .svg  (Python 3.13 + opencv + potracer suffisent)
```
(Les versions récentes de `mediapipe` téléchargent les modèles à la volée ; la 0.10.14 les embarque, ce qui évite toute dépendance réseau.)

## Résultats sur les 5 exemples (spec/examples/02 → 06)
Les vues et les cartes de traits des exemples ont été produites par ces scripts sans retouche, sauf la confirmation manuelle des angles du robot et d'un profil du martien (ce que fera l'écran de confirmation du builder). Taille d'une carte `lineart` 1024² : 6–17 Ko, contre ~190 Ko pour la vue.
