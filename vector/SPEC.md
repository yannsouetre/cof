# COF-Vector — un « SVG du visage, du corps et des vêtements »
## Note de conception v0.1 (9 octobre 2026) — projet frère de COF, dépôt dédié `cof-vector`

> **Idée en une phrase.** Décrire l'apparence d'un personnage par des **courbes normalisées** et des **paramètres de texture** plutôt que par des pixels : plus précis qu'un texte, 100 à 1 000 fois plus léger qu'une photo, éditable, indépendant de la résolution, et **rendable** en un dessin au trait que n'importe quel générateur d'images peut suivre.
> Analogie : JPEG → SVG ; maillage 3D → CSG/NURBS. Licence visée : spec CC-BY-4.0, code MIT, vocabulaires CC0.

---

## 1. Pourquoi ça n'existe pas déjà, et pourquoi c'est faisable maintenant

L'état de l'art (cf. `01_Etat_de_l_art.md` § 4) montre deux familles de codes du visage :
- les **modèles paramétriques 3D** (FLAME, BFM, MetaHuman DNA) — précis, mais opaques pour un humain (300 coefficients de PCA ne se lisent pas), et exigeant le modèle pour être rendus ;
- les **vocabulaires descriptifs** (FISWG/ASTM, prompts) — lisibles, mais imprécis et non géométriques.

Entre les deux, **rien** : aucun format ouvert ne stocke la géométrie *visible* d'un visage (ses contours, ses proportions) sous une forme à la fois exacte, compacte, éditable et lisible. C'est exactement ce que fait le SVG pour un logo. Ce qui rend la chose faisable en 2026 sans laboratoire :
- des détecteurs de points de repère gratuits et précis **dans le navigateur** (MediaPipe Face Landmarker : 478 points 3D + 52 blendshapes, Apache 2.0 ; Pose Landmarker : 33 points du corps) ;
- des générateurs d'images qui acceptent un **dessin au trait** comme contrainte de forme (ControlNet lineart/canny/scribble, IP-Adapter, et les équivalents intégrés aux outils vidéo) — le rendu d'un code vectoriel devient directement exploitable ;
- des modèles 3D ouverts (FLAME 2023 Open, Anny) vers lesquels on peut projeter ou depuis lesquels on peut extraire les mêmes courbes.

## 2. Principes

1. **Courbes, pas pixels.** Tout contour est une suite de **Bézier cubiques** (comme SVG `path`), ce qui donne édition, lissage et mise à l'échelle gratuits.
2. **Repère normalisé et anthropométrique.** Visage : origine au milieu des pupilles, unité = **distance inter-pupillaire (IPD)** ; corps : origine au sol entre les pieds, unité = **stature**. Deux visages se comparent donc directement, et le code ne dépend ni de la photo ni de la résolution.
3. **Deux vues canoniques** : face (`F`) et profil gauche (`P`), chacune avec ses contours ; le profil peut être absent (le rendu reste possible, les mesures de profondeur sont alors « inconnues », pas inventées).
4. **Texture procédurale, pas image.** La peau, les cheveux, les tissus sont des paramètres (couleur, sous-ton, rugosité, densités, motifs, zones) — ce qui est « la texture de la peau et tout le reste » en quelques dizaines d'octets.
5. **Trois sorties de rendu** depuis le même code : dessin au trait SVG (face/profil), carte de teintes plates SVG, phrase descriptive. Un lecteur qui ne sait rien faire d'autre peut au moins afficher le trait et lire la phrase.
6. **Niveaux de détail** : `coarse` (ovale, yeux, nez, bouche, sourcils : ~12 courbes, ~600 octets), `standard` (+ paupières, lèvres internes, oreilles, ligne de cheveux, mâchoire : ~30 courbes, ~2 Ko), `fine` (+ rides, grains de beauté, iris, cils, asymétries : ~5–8 Ko).
7. **Pas de biométrie cachée.** Le code décrit la *forme visible* ; il n'embarque aucun embedding de reconnaissance. Il est réversible en dessin, pas en identité — un code extrait d'une personne réelle reste toutefois une donnée personnelle et hérite des règles de consentement de COF.

## 3. Structure du fichier `face.vec.json` (v0.1)

```jsonc
{
  "cofvec": "0.1", "kind": "face", "lod": "standard",
  "frame": { "unit": "ipd", "origin": "mid-pupils", "ipd_mm": 63, "yaw_deg": 0, "pitch_deg": 0 },   // ipd_mm optionnel : rend l'échelle absolue
  "applies_to": ["humanoid"],

  "contours": {                                // chaque contour = liste de segments Bézier cubiques [x0,y0, c1x,c1y, c2x,c2y, x1,y1], coordonnées en IPD, 3 décimales
    "F.outline":      { "closed": true,  "pts": [[-1.52,0.35, -1.60,-0.40, -1.20,-1.60, -0.40,-2.10], "…"] },
    "F.jaw":          { "closed": false, "pts": ["…"] },
    "F.brow.L":       { "closed": true,  "pts": ["…"] }, "F.brow.R": { "mirror": "F.brow.L", "asym": [[0.02,-0.01], "…"] },
    "F.eye.L.upper":  { "pts": ["…"] }, "F.eye.L.lower": { "pts": ["…"] }, "F.eye.R.upper": { "mirror": "F.eye.L.upper" },
    "F.iris.L":       { "circle": [-0.5, 0.0, 0.19] },                        // primitives autorisées : circle, ellipse
    "F.nose.bridge":  { "pts": ["…"] }, "F.nose.wing.L": { "pts": ["…"] }, "F.nose.base": { "pts": ["…"] },
    "F.lip.upper.outer": { "pts": ["…"] }, "F.lip.lower.outer": { "pts": ["…"] }, "F.lip.inner": { "pts": ["…"] },
    "F.hairline":     { "pts": ["…"] }, "F.ear.L": { "pts": ["…"] },
    "P.outline":      { "pts": ["…"] }, "P.nose": { "pts": ["…"] }, "P.lips": { "pts": ["…"] }, "P.chin_neck": { "pts": ["…"] }, "P.ear": { "pts": ["…"] }
  },

  "landmarks": {                               // points nommés (sous-ensemble MPEG-4 FDP / MediaPipe), même repère ; redondants mais pratiques
    "pupil.L": [-0.5, 0.0], "pupil.R": [0.5, 0.0], "nose.tip": [0.0, -0.92], "mouth.center": [0.0, -1.55], "chin": [0.0, -2.35], "P.nose.tip": [0.62, -0.92]
  },

  "measures": {                                // dérivées (recalculables), en IPD — utiles aux LLM, aux comparaisons et au contrôle de cohérence
    "face_width": 3.05, "face_height": 3.40, "eye_width": 0.47, "eye_height": 0.17, "canthal_tilt_deg": 4,
    "nose_length": 0.95, "nose_width": 0.58, "mouth_width": 0.98, "lip_upper_h": 0.11, "lip_lower_h": 0.19,
    "chin_height": 0.55, "jaw_angle_deg": 118, "forehead_h": 1.05, "P.nose_projection": 0.60, "P.chin_projection": 0.05
  },

  "surface": {                                 // texture procédurale
    "skin":   { "monk": 4, "hex": "#D7A98A", "undertone": "warm", "roughness": 0.35, "sheen": 0.2, "translucency": 0.3,
                "freckles": { "density": 0.3, "zones": ["cheeks", "nose"] }, "moles": [ { "at": [0.72, -1.21], "r": 0.02 } ],
                "wrinkles": { "forehead": 1, "crow_feet": 2, "nasolabial": 1, "scale": "0-9" }, "dark_circles": 1, "blush": 0.2,
                "scars": [ { "contour": "F.brow.L", "t": 0.3, "len": 0.25, "angle_deg": 20 } ] },
    "eyes":   { "iris_hex": "#5B3A1E", "iris_pattern": "radial", "limbal_ring": 0.6, "sclera_hex": "#F2F0EC", "lashes": 0.6 },
    "brows":  { "hex": "#2B1B12", "density": 0.8, "texture": "straight" },
    "lips":   { "hex": "#B5696A", "gloss": 0.2 },
    "hair":   { "$ref": "appearance/hair.json", "strands_dir": "F.hairline:down-left" }
  },

  "expressions": {                             // offsets vectoriels par expression nommée (facultatif) : deltas de points de contrôle
    "amused": { "F.lip.upper.outer": [[0,0.02,"…"]], "F.eye.L.lower": ["…"] }
  },

  "provenance": { "extracted_from": "appearance/views/head.front.jpg", "method": "mediapipe-face-landmarker/0.10 + bezier-fit", "quality": 0.87, "manual_edits": 3 },
  "renderings": { "lineart_svg": "appearance/face.vec.F.svg", "lineart_profile_svg": "appearance/face.vec.P.svg", "flat_svg": "appearance/face.vec.flat.svg",
                  "sentence": "Oval face three IPD wide, high forehead, thick straight dark brows, wide-set almond eyes with a 4° upward tilt, straight narrow nose, wide mouth with thin upper and full lower lip, pointed chin, warm medium skin with light freckles on cheeks and nose." }
}
```

Taille : ~2–4 Ko en JSON lisible pour `standard` ; ~1 Ko en CBOR/float16 si besoin. Une photo 1024² pèse 200 Ko : facteur 50 à 200.

## 4. `body.vec.json` et `garment.vec.json`

- **Corps** : repère `unit: stature`, contours `F.silhouette` (fermé), `F.shoulders`, `F.waist`, `F.hips`, `P.silhouette`, `F.arm.L/R`, `F.leg.L/R` ; landmarks des 33 points de pose ; `measures` aux noms ISO 7250 (stature, shoulder_breadth, chest/waist/hip circumference estimées, leg_length, arm_length, head_height ratio) ; `surface.skin` partagé avec le visage ; `marks` (tatouages comme contours + hex, cicatrices). Un bloc `intimate` suit les mêmes règles que `body.json` (séparé, désactivé par défaut, interdit si mineur).
- **Vêtements** : un fichier par tenue ; contours de la silhouette habillée (`F.outline`, `P.outline`), lignes de coupe (`F.neckline`, `F.hem`, `F.sleeve.L`, `F.waistband`), **texture procédurale de tissu** (`hex`, `pattern: solid|stripes|check|print`, `pattern_scale`, `sheen`, `weave: knit|woven|leather|denim`, `drape: stiff|fluid`), accessoires comme primitives (`circle`, `rect`) ; lien vers le patron GarmentCode s'il existe. Les catégories/attributs Fashionpedia restent dans `outfits/<id>.json`.

## 5. Pipeline de référence (ce que fera le builder dès la v1)

```
photo(s) ──► détection 478 pts (MediaPipe) ──► estimation pose (yaw/pitch) ──► rejet si |yaw| > 15° (ou vue marquée "P")
         ──► extraction des contours à partir des indices MediaPipe connus (ovale, yeux, lèvres, sourcils, nez)
         ──► ajustement Bézier (Schneider / fit-curve, tolérance 0,01 IPD) ──► normalisation (IPD, origine, rotation du roll)
         ──► mesures dérivées ──► symétrisation optionnelle + stockage des asymétries
         ──► échantillonnage couleur par zones (peau joues/front, iris, lèvres, sourcils, cheveux) → surface.*
         ──► rendu SVG trait + flat ──► phrase descriptive (gabarit depuis measures/surface)
         ──► face.vec.json + SVG dans le .cof
```
Sens inverse (rendu) : `face.vec.json → SVG → image via ControlNet lineart + prompt (renderings.sentence + FDV)`, ou `→ FLAME` par ajustement des 300 coefficients aux contours projetés (phase 2), ou `→ VRM` via blendshapes de forme (phase 2).

**Preuve de faisabilité (phase 0/1)** : trois portraits synthétiques → extraction → rendu SVG → regénération par un modèle d'image avec le SVG en contrainte → comparaison visuelle côte à côte. Même imparfait, ce test démontre le concept « cohérence de personnage sans photo ».

## 6. Ce que ça permet, concrètement

| Besoin | Sans COF-Vector | Avec |
|---|---|---|
| Garder le même visage d'un générateur à l'autre | 3–5 photos + espoir | un SVG de contrainte + une phrase, identiques partout |
| Éditer « un nez un peu plus fin » | regénérer, relancer | déplacer deux points de contrôle, re-rendre |
| Fiche de personnage ultra-légère (chat, agents) | pas d'apparence | ~3 Ko : visage + corps + tenue, lisibles par un LLM via `measures` et `sentence` |
| Vérifier qu'une image « est bien lui » | jugement humain | distance entre contours extraits et contours du code (métrique publique) |
| Décrire un visage sans photo d'une personne réelle | impossible proprement | code sans embedding biométrique (toujours soumis au consentement) |

## 7. Limites assumées de la v1 et plan

- **Humain d'abord** : indices de contours et repère IPD supposent un visage humain de face/profil ; animaux et créatures viendront par des *profils de contours* supplémentaires (`applies_to`).
- **Profondeur** : la vue de profil est souvent absente ; la v1 n'invente rien (mesures `P.*` à `null`) ; la phase 2 estimera la profondeur depuis les 478 points 3D de MediaPipe et FLAME.
- **Texture** : procédurale = approximation ; les photos restent la référence quand elles existent. Le but est la *portabilité*, pas le photoréalisme du code seul.
- **Expressions** : les offsets par expression sont optionnels ; la voie principale reste les 52 blendshapes (déjà produits par MediaPipe).
- **Spécialistes attendus en phase 2** : morphologie/anthropométrie (choix des contours et mesures), infographie (rendu procédural de peau), accessibilité (descriptions), juridique (statut du code vis-à-vis des données biométriques).

## 8. Dépôt `cof-vector` (structure prévue)

```
SPEC.md                      ← cette note, formalisée
schemas/face.vec.schema.json  body.vec.schema.json  garment.vec.schema.json
vocabularies/contours-face-1.0.json  (nom → indices MediaPipe → ordre des points)
js/   extract.js (MediaPipe → contours → Bézier), render.js (→ SVG), measure.js, describe.js
py/   même pipeline (mediapipe, numpy, svgwrite) pour cof-cli
examples/  3 portraits synthétiques + leurs .vec.json + SVG + regénérations
demo/  page web : glisser une photo → code → SVG → télécharger
```
