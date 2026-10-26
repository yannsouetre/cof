# Guide du builder — version avancée

*Le même guide s'ouvre avec le bouton **📖 Guide** du builder en version avancée. Source : `builder/guide_src.py` (elle alimente aussi la fenêtre du builder, en six langues).*

English: [builder-guide.md](builder-guide.md)

## 1. La version avancée en bref

Sept étapes, dans l'ordre de la colonne de gauche :

- **1 · Personnage(s)** — qui c'est : nom, fictif ou réel, morphologie.
- **2 · Éléments** — tout ce qui le décrit : textes, photos, voix, LoRA, 3D, poses, mouvements, fichiers.
- **3 · Souvenirs** — son passé : des moments et des périodes, avec ce qu'il a ressenti, ce qu'il tait, et quelques traces (une photo, un son).
- **4 · Presets** — les combinaisons prêtes à l'emploi : un look, un âge, un style, une langue.
- **5 · Droits** — ce que les autres ont le droit d'en faire.
- **6 · Contrôles** — ce qui manque ou ne colle pas.
- **7 · Build** — le fichier .cof final.

Seuls le nom, fictif ou réel, la morphologie et les droits sont obligatoires. La version facile ne gère qu'un personnage simple (une fiche, des photos, une voix) : un fichier plus riche reste en version avancée.

## 2. Catégories et déclinaisons

Les éléments sont rangés en 8 catégories : Personnalité, Apparence, Poids d'identité (LoRA), 3D, Voix, Postures, Mouvements, Fichiers. Dans chaque catégorie, vous ajoutez des **déclinaisons**, chacune d'un type : visage, corps, coiffure, vêtement, lieu…

**Règle d'or : une déclinaison = un ensemble cohérent d'une seule chose.** Plusieurs photos servent uniquement à montrer différents angles. Un autre visage, une autre coiffure, un autre vêtement, un autre lieu = une autre déclinaison.

- **Photos en vrac** : la seule exception, assumée. Visage, corps et tenue mélangés, mais toujours la même personne, au même âge, dans le même style.
- **Character sheet** : une planche qui montre le personnage entier (visage, corps, coiffure, tenue) sur une seule image.

## 3. L'âge

- L'âge appartient à chaque **représentation** (visage, corps, planche, photos en vrac, LoRA, 3D), pas au personnage : Clara peut avoir un visage à 12 ans et un autre à 29 ans.
- Vêtements, accessoires, lieux et descriptions n'ont pas d'âge.
- Un preset prend l'âge le plus bas de ses déclinaisons.
- Une même image ne peut pas servir à la fois à un âge de moins de 18 ans et à un âge adulte.

## 4. Souvenirs

Le passé du personnage, nœud par nœud. Un **moment** (● vert, code `ev`) est un point dans le temps, une **période** (■ violet, code `ep`) un intervalle ; un moment peut faire partie d'une période (lien « fait partie de »).

- **Le gist** : quelques phrases à la première personne, dans la langue maîtresse du personnage ; les autres langues sont facultatives (un agent anglais lit le gist anglais).
- **Quand, où, avec qui** : un âge ou une date, un lieu en texte ou un lieu du personnage, les personnes présentes — et qui est **montré** sur les médias.
- **Ressenti alors / aujourd'hui, clarté, importance** : ce qui rend un souvenir vivant plutôt qu'une fiche.
- **Origine, visibilité, confidence** : écrit par l'auteur ou vécu à l'usage ; canon ou personnel (les données d'un utilisateur, jamais partagées sans demande) ; ouvert, réservé ou secret (ce que le personnage ne dit pas).
- **Médias** : une à trois traces — image, son, courte vidéo, quelques lignes — ou les mêmes médias qu'un autre souvenir (deux personnages, une soirée, une photo).
- **Explicite** (nudité, intime) : seulement si le souvenir est vécu à 18 ans ou plus, si quelqu'un est déclaré montré, et si toute personne montrée est un adulte d'âge connu. Sinon les cases sont grisées, avec la raison.
- Les **presets** choisissent leurs souvenirs comme une bibliothèque : une période cochée emporte ses moments. Au build, deux purges : tout public (les médias explicites partent, les textes restent) et sans souvenirs personnels.

## 5. Presets

Un preset = un personnage + une combinaison de déclinaisons. Par exemple : « Clara 29 ans, photo », « Clara manga », « Clara 65 ans ».

- **Un seul** visage, corps, coiffure par preset.
- **Se cumulent** : vêtements et accessoires (s'ils ne couvrent pas la même partie du corps), pilosité, particularités, lieux, plusieurs LoRA.
- **Proposé** = disponible dans ce preset, jamais appliqué d'office (une tenue de rechange, par exemple).
- Le **preset par défaut** s'ouvre en premier ; son visage de face devient la vignette du fichier.

## 6. Plusieurs personnages

Un fichier peut regrouper plusieurs personnages : un duo, une équipe. Chaque déclinaison et chaque preset appartient à un seul personnage, choisi dans le menu « Personnage » en haut de l'écran.

- Un visage, une voix ou un LoRA ne se partage jamais entre deux personnages.
- Un lieu, une pose ou un fichier neutre peut servir à plusieurs.
- Pour reprendre un preset d'un autre fichier : étape Presets, « Importer un preset (.cof) ».

## 7. Droits et contenus sensibles

- Les droits sont **fermés par défaut** : vous ouvrez ce que vous autorisez (usage commercial, redistribution, clonage de voix, entraînement…), au besoin preset par preset.
- **Personne réelle** : le consentement est recommandé, et obligatoire pour la nudité ou le contenu intime.
- **Moins de 18 ans** : jamais de nudité ni de contenu intime dans le preset.
- Le contenu intime va uniquement dans sa déclinaison « intime », isolée et ignorée par défaut par les lecteurs.

## 8. Contrôles et build

- **Contrôles** : la complétude (ce qui manque à chaque preset) et la cohérence (ce qui ne colle pas). Les avertissements ne bloquent jamais ; seules les erreurs empêchent le build.
- **Contrôle IA** (facultatif) : vous choisissez l'IA (adresse, clé, modèle). Elle vérifie que le preset décrit un seul personnage cohérent et que chaque déclinaison montre une seule chose. Les images partent vers cette IA ; la clé n'est pas enregistrée.
- **Build** : choisissez la taille et la compression des images, puis téléchargez le .cof. Ouvrez-le dans l'explorateur COF pour vérifier le résultat.
