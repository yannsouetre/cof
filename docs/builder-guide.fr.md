# Guide du builder — version avancée

*Le même guide s'ouvre avec le bouton **📖 Guide** du builder en version avancée. Source : `builder/guide_src.py` (elle alimente aussi la fenêtre du builder, en six langues).*

English: [builder-guide.md](builder-guide.md)

## 1. La version avancée en bref

Huit étapes, dans l'ordre de la colonne de gauche :

- **1 · Personnage(s)** — qui c'est : nom, fictif ou réel, morphologie.
- **2 · Éléments** — tout ce qui le décrit : textes, photos, voix, LoRA, 3D, poses, mouvements, fichiers.
- **3 · Souvenirs** — son passé : des moments et des périodes, avec ce qu'il a ressenti, ce qu'il tait, et quelques traces (une photo, un son).
- **4 · Psyché** — sa vie intérieure en graphe : valeurs, croyances, désirs, besoins, peurs, blessures, positions, goûts, habitudes, contradictions, règles — reliés aux souvenirs.
- **5 · Presets** — les combinaisons prêtes à l'emploi : un look, un âge, un style, une langue.
- **6 · Droits** — ce que les autres ont le droit d'en faire.
- **7 · Contrôles** — ce qui manque ou ne colle pas.
- **8 · Build** — le fichier .cof final.

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
- **Objets** : ce que le souvenir garde — un accessoire du personnage (choisi dans la liste) ou un nom libre (« le carnet ») ; cochez « montré » si l'objet apparaît sur un média. Écrit en `what` (COF 1.2, RFC 0005) ; un souvenir avec des objets fait passer le fichier en 1.2.
- **Ressenti alors / aujourd'hui, clarté, importance** : ce qui rend un souvenir vivant plutôt qu'une fiche.
- **Origine, visibilité, confidence** : écrit par l'auteur ou vécu à l'usage ; canon ou personnel (les données d'un utilisateur, jamais partagées sans demande) ; ouvert, réservé ou secret (ce que le personnage ne dit pas).
- **Médias** : une à trois traces — image, son, courte vidéo, quelques lignes — ou les mêmes médias qu'un autre souvenir (deux personnages, une soirée, une photo).
- **Explicite** (nudité, intime) : seulement si le souvenir est vécu à 18 ans ou plus, si quelqu'un est déclaré montré, et si toute personne montrée est un adulte d'âge connu. Sinon les cases sont grisées, avec la raison.
- Les **presets** choisissent leurs souvenirs comme une bibliothèque : une période cochée emporte ses moments. Au build, deux purges : tout public (les médias explicites partent, les textes restent) et sans souvenirs personnels.

## 5. Psyché

La vie intérieure du personnage, en graphe (COF 1.2). Onze sortes de nœuds : blessure, valeur, croyance, désir, besoin, peur, position, goût, habitude, contradiction, règle. Chaque nœud tient en une ou deux phrases par langue.

- **Force** (0–100, à régler nœud par nœud), **stabilité** (noyau, établi, mouvant, fragile : ce qu'un hôte peut changer à l'usage), **depuis** (l'âge d'apparition), origine, visibilité, confidence.
- **Liens** : « à cause de » et « à propos de » vers un souvenir ou un nœud ; « soutient » et « contredit » entre nœuds. Une contradiction porte exactement deux « contredit » ; une blessure vient presque toujours d'un souvenir.
- **Personnes, lieux, objets** : ce à quoi le nœud tient sans passer par un souvenir (RFC 0005) — soi-même ou un personnage du fichier, un environnement, un accessoire, ou un nom libre (« ma grand-mère », « Lyon », « le carnet »), avec « personne réelle » pour quelqu'un de réel qui n'est pas un personnage. Repliés sur une ligne tant qu'ils sont vides. Un lien vers un personnage écrit par un ancien brouillon devient une personne à l'ouverture du fichier (les contrôles disent combien).
- **Conscience de soi, valence, jusqu'à** (RFC 0004 § 3 nonies) : « Conscience de soi » (oui, en partie, non ; oui par défaut, non écrit) dit ce que le personnage sait de lui-même — pas ce qu'il dit aux autres, qui est la confidence : un nœud inconscient est agi, jamais dit. Une position ou un goût a un curseur de **valence** de −100 (hostile / déteste) à +100 (chaleureux / adore), centré sur 0, « non définie » et absente du fichier tant qu'il n'a pas bougé (✕ l'efface ; changer la sorte pour autre chose qu'une position ou un goût la retire, et la carte le dit). « Jusqu'à (âge) » / « Jusqu'à (date) », sous « Depuis », dit quand le personnage a cessé de tenir le nœud. Contrôles : erreurs pour une valence hors position ou goût et pour un « jusqu'à » avant le « depuis » (âges avec âges, dates avec dates) ; avertissements pour « conscience de soi : non » sur un nœud secret et pour un preset plus âgé que le « jusqu'à » d'un nœud qu'il tient.
- **Risque déclaré** : aucun, inapproprié, dangereux. Un hôte qui donne des outils au personnage ne charge jamais un nœud dangereux ; la fiction peut tout charger. Au build, la purge « sans risque » les retire.
- Une croyance peut être **fausse mais tenue** (le mensonge que le personnage se raconte) ; une position a un **sujet** (un personnage, l'utilisateur, un souvenir, un libellé).
- **Proposer une psyché** (bouton 🤖) : depuis la personnalité par une passerelle IA ou une proposition collée, ou **hors ligne depuis un signe solaire** (« ♈ Depuis un signe astrologique » : une liste des douze signes, noms dans les six langues) — trois ou quatre candidats `value` / `taste` / `habit` de la même table que `cof psyche propose --zodiac`, tous décochés dans le panneau de relecture (les phrases n'existent qu'en anglais et en français : une autre langue reçoit le texte anglais, à traduire à la relecture) ; rien n'est écrit sans cocher. La même fenêtre offre trois autres entrées hors ligne, chacune avec son bouton « Proposer » : **« Depuis un type Myers-Briggs (quatre lettres) »** (une liste des seize types ; les quatre lettres sont employées à titre descriptif, sans affiliation), **« Depuis un type de l'ennéagramme »** (une liste des neuf types : la peur et le désir fondamentaux, une valeur, une habitude) et **« Depuis des scores Big Five (OCEAN) »** (cinq champs 0–100, préremplis depuis les traits typés de la personnalité quand elle en a ; 70 ou plus propose le pôle haut, 30 ou moins le pôle bas, entre les deux rien) — les tables de `cof psyche propose --mbti / --enneagram / --big-five`, noms des traits dans les six langues, texte anglais dans les quatre langues autres que l'anglais et le français.
- Les **presets** choisissent leurs nœuds comme une bibliothèque ; un nœud qui change avec l'âge est un second nœud, dérivé du premier. « Visualisation graphe » montre la constellation dans l'explorateur.

## 6. Presets

Un preset = un personnage + une combinaison de déclinaisons. Par exemple : « Clara 29 ans, photo », « Clara manga », « Clara 65 ans ».

- **Un seul** visage, corps, coiffure par preset.
- **Se cumulent** : vêtements et accessoires (s'ils ne couvrent pas la même partie du corps), pilosité, particularités, lieux, plusieurs LoRA.
- **Proposé** = disponible dans ce preset, jamais appliqué d'office (une tenue de rechange, par exemple).
- Le **preset par défaut** s'ouvre en premier ; son visage de face devient la vignette du fichier.
- **L'âge arrête les souvenirs et la psyché** : quand le preset a un âge (celui qu'il déclare s'il en déclare un, sinon le plus bas que montrent ses déclinaisons — une femme de 40 ans montrée à 25 ans garde sa vie jusqu'à 40, avec un avertissement de cohérence), ses Souvenirs ne proposent que ce qui a commencé à cet âge (l'âge d'un moment, le début d'une période ; une date seule, par l'année de naissance que donnent les souvenirs datés) et sa Psyché que les nœuds tenus à cet âge (apparus, pas encore quittés). Une ligne compte le reste ; « afficher quand même » le montre grisé, sans pouvoir le cocher. Une période cochée n'emporte que ses moments vécus à cet âge. Un élément hérité que l'âge exclut est barré, avec « retirer pour ce preset ». Changer l'âge après coup ouvre une fenêtre : désélectionner ce qui vient après, ou le garder pour corriger l'âge (les contrôles le signalent).

## 7. Plusieurs personnages

Un fichier peut regrouper plusieurs personnages : un duo, une équipe. Chaque déclinaison et chaque preset appartient à un seul personnage, choisi dans le menu « Personnage » en haut de l'écran.

- Un visage, une voix ou un LoRA ne se partage jamais entre deux personnages.
- Un lieu, une pose ou un fichier neutre peut servir à plusieurs.
- Pour reprendre un preset d'un autre fichier : étape Presets, « Importer un preset (.cof) ».

## 8. Droits et contenus sensibles

- Les droits sont **fermés par défaut** : vous ouvrez ce que vous autorisez (usage commercial, redistribution, clonage de voix, entraînement…), au besoin preset par preset.
- **Personne réelle** : le consentement est recommandé, et obligatoire pour la nudité ou le contenu intime.
- **Moins de 18 ans** : jamais de nudité ni de contenu intime dans le preset.
- Le contenu intime va uniquement dans sa déclinaison « intime », isolée et ignorée par défaut par les lecteurs.

## 9. Contrôles et build

- **Contrôles** : la complétude (ce qui manque à chaque preset) et la cohérence (ce qui ne colle pas). Les avertissements ne bloquent jamais ; seules les erreurs empêchent le build.
- **Contrôle IA** (facultatif) : vous choisissez l'IA (adresse, clé, modèle). Elle vérifie que le preset décrit un seul personnage cohérent et que chaque déclinaison montre une seule chose. Les images partent vers cette IA ; la clé n'est pas enregistrée.
- **Build** : choisissez la taille et la compression des images, puis téléchargez le .cof. Ouvrez-le dans l'explorateur COF pour vérifier le résultat.
