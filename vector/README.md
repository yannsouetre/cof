# COF-Vector — le « SVG du visage, du corps et des vêtements »

Spécification : `SPEC.md`. Code Python (v0.1, preuve de faisabilité) : `py/`.

| Script | Rôle | État |
|---|---|---|
| `py/sheet_split.py` | Planche de personnage → panneaux → vues canoniques (`body.front`, `head.right.closeup`…) + `sheet.regions.json` | Fonctionne sur les humains et humanoïdes ; robots/créatures sans visage → faible confiance, à confirmer dans le builder |
| `py/face_vec.py` | Photo de face → maillage 478 pts → contours en Béziers normalisés (unité = distance inter-pupillaire) → mesures → couleurs → `face.vec.json` + SVG trait + SVG aplat + phrase | Fonctionne ; a priori humain (crâne/oreilles non vectorisés) ; pas de ligne de cheveux (phase 2) |

## Installation (Python 3.11, roue MediaPipe « legacy » avec modèles embarqués)
```bash
uv venv -p 3.11 .venv && source .venv/bin/activate
pip install mediapipe==0.10.14 numpy "opencv-contrib-python-headless<4.11" pillow
python py/sheet_split.py planche.jpg out/            # → out/views/*.jpg, out/sheet.regions.json
python py/face_vec.py out/views/head.front.jpg out/vec/   # → face.vec.json, face.vec.F.svg, face.vec.flat.svg, overlay
```
(Les versions récentes de `mediapipe` téléchargent les modèles à la volée ; la 0.10.14 les embarque, ce qui évite toute dépendance réseau.)

## Résultats sur les 5 exemples (spec/examples/02 → 06)
Les vues et les codes vectoriels des exemples ont été produits par ces deux scripts sans retouche, sauf la confirmation manuelle des angles du robot et d'un profil du martien (ce que fera l'écran de confirmation du builder). Taille d'un `face.vec.json` : ~8 Ko (lod `standard`), contre ~190 Ko pour la vue 1024².
