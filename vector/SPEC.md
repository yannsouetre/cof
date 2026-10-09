# COF-Vector — représentations légères de l'apparence
## Note de conception v0.2 (9 octobre 2026) — projet frère de COF

> **Idée en une phrase.** Entre la photo (lourde, figée) et le texte (léger, imprécis), stocker des **cartes de traits** de chaque vue — contours Canny, dessin au trait, contours doux — en PNG 1 ou 4 bits : **6 à 16 Ko** pour un visage en 1024² (contre ~190 Ko pour la photo), exactement ce que les générateurs d'images et de vidéo consomment comme contrainte (ControlNet canny / lineart / softedge), et vectorisable en SVG quand on veut éditer ou mettre à l'échelle.
> Licence visée : spec CC-BY-4.0, code MIT.

### Pourquoi ce pivot (v0.1 → v0.2)
La v0.1 reconstruisait le visage par un maillage de 478 points et des courbes de Bézier. Résultat : un visage *générique* (le maillage est un a priori humain lisse ; cheveux, lunettes, oreilles, créatures et robots disparaissent). La v0.2 part des pixels et les **simplifie algorithmiquement** : la ressemblance est conservée (tests sur cinq typologies : écolière, femme moderne, martien, robot, homme médiéval — y compris le robot sur lequel tout détecteur de visage échoue). L'ancien extracteur est archivé (`py/_archive/`), et ses points-clés ne servent plus qu'à des sous-produits optionnels (mesures, couleurs, phrase descriptive), jamais à un rendu.

## 1. Les trois cartes (famille des préprocesseurs ControlNet)

| Carte | Algorithme (v0.2, sans modèle neuronal) | Équivalent ControlNet | Stockage | Taille typique (tête 1024²) | Ce qu'elle apporte |
|---|---|---|---|---|---|
| `canny` | Canny, seuils automatiques (médiane ± 33 %) | Canny Edge Preprocessor | PNG **1 bit** | 6–16 Ko | contours géométriques nets, structure |
| `lineart` | `lineart_standard` (différence image − flou gaussien, seuil) | LineArt / LineartStandard Preprocessor | PNG **1 bit** | 6–17 Ko | dessin au trait, reconnaissable à l'œil |
| `softedge` | magnitude du gradient lissée, chute douce | HED Soft-Edge / PiDiNet | PNG **4 bits**, demi-résolution | 25–40 Ko (512²) | contours organiques, volume du visage, plis |

Règles :
- Chaque carte est **dérivée** d'une vue (`source_view`) et déclarée dans `assets[]` avec `role: "line-map"`, `method`, `bits`, `width/height`, `derived_from`. Elle ne remplace pas la vue : elle permet de **la retirer** (option « compresser » du builder) en gardant la contrainte de forme.
- Noms : `appearance/lines/<sujet>.<angle>.<method>.png` ; SVG vectorisé optionnel `…<method>.svg` (potrace ; 20–80 Ko, éditable, indépendant de la résolution).
- Les versions **neuronales** (HED, PiDiNet, TEED, Lineart Anime) sont acceptées avec le même schéma (`method: hed|pidinet|teed|lineart-anime`) — le builder web les proposera via ONNX quand les poids sont disponibles ; les versions algorithmiques restent le repli garanti, sans réseau ni modèle.
- Résolutions : 1024 pour `canny`/`lineart` (la géométrie compte), 512 pour `softedge` (la tonalité compte). Un `.cof` *lite* peut ne garder que `lineart` à 512 (~4 Ko).

## 2. Exploitabilité dans l'inférence (ce que fait un lecteur)
- **Génération d'image/vidéo** : la carte est passée telle quelle comme image de contrôle (ControlNet, et les équivalents intégrés des outils vidéo) ; `lineart` ou `canny` pour imposer la forme, `softedge` pour laisser la liberté de style ; le prompt vient de `renderings.sentence` et des descriptifs L0.
- **Vignette / aperçu** : `lineart` est lisible par un humain comme un croquis — affichage immédiat sans décodage.
- **Comparaison / recherche** : la distance entre cartes `canny` (chamfer / IoU après alignement) sert de métrique de « c'est bien lui » entre deux images.
- **Édition** : le SVG potrace s'ouvre dans Inkscape/Illustrator ; corriger une mèche ou un nez = déplacer des points.

## 3. Pipeline du builder
```
vue (photo ou planche découpée) ──► niveaux de gris ──► canny (1 bit) / lineart (1 bit) / softedge (4 bits, ½ résolution)
                                 └─► [optionnel] points-clés → mesures + couleurs → phrase descriptive (L0)
                                 └─► [optionnel] potrace → SVG
```
Côté navigateur : OpenCV.js (Canny, flou gaussien, Sobel) ou implémentations WebGL/WASM ; `potrace` existe en JS. Aucun téléchargement de modèle n'est nécessaire pour la v0.2.

## 4. Corps et vêtements
Les mêmes cartes s'appliquent aux vues `body.*` (silhouette et plis en `lineart`, structure en `canny`) et aux tenues (une carte par vue habillée). Les poses habituelles restent portées par les points-clés OpenPose (spec COF § 5.1) — carte « bonhomme » colorée, elle aussi de la famille ControlNet. Aucune vectorisation sémantique des vêtements n'est tentée en v0.2.

## 5. Limites et suite
- Les cartes dépendent de la vue (éclairage, résolution) ; elles ne sont pas une *géométrie* canonique — le validateur ne compare donc pas de mesures entre cartes, il vérifie seulement la présence de la vue source.
- Phase 2 : PiDiNet/TEED en ONNX dans le builder ; carte de **profondeur** (`depth`, Depth Anything) et **normales** pour la 3D ; segmentation (cheveux / peau / vêtements) pour le code L0 automatique.
- Dépôt : `vector/py/edges.py` (référence Python), `vector/py/sheet_split.py` (découpage des planches), `vector/js/` (à venir, pour le builder).
