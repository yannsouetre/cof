# Personnalité ↔ psyché : le contrat de proposition — v0.1 (COF 1.2, RFC 0004 § 3 octies)

Peu d'auteurs construiront une psyché de trente nœuds à la main. Le builder et cof-cli **proposent** donc des nœuds à partir de ce que l'auteur a déjà écrit — la fiche de personnalité, les listes 1.0, les souvenirs — et l'auteur coche ce qui reste. La recette est **indépendante du modèle** : cette page est tout le contrat, le même pour une passerelle OpenAI-compatible, une fenêtre de chat où l'auteur colle le dossier, une plateforme qui embarque le builder, ou une règle (les listes 1.0, un signe du zodiaque). La seule règle qui ne bouge jamais : **une proposition n'est jamais écrite telle quelle**. Rien n'entre dans le fichier sans un accept explicite, nœud par nœud (`--accept` dans cof-cli, une case par ligne dans le builder).

Deux sens :
1. **Décomposition** (personnalité → nœuds) : un dossier en entrée, une liste de nœuds candidats en sortie (§ 1–3).
2. **Rendu** (nœuds → texte) : la section « Qui elle est » de `SOUL.md`, déterministe, sans modèle (§ 5).

## 1. Entrée : le dossier (bundle)

`cof psyche propose <src> --bundle-out bundle.json` l'écrit (avec le prompt du § 3) ; le builder construit le même objet depuis son état.

```jsonc
{ "cof": "1.2", "contract": "psyche-propose/0.1",
  "languages": ["fr", "en"],                       // les langues de l'auteur : chaque gist vient dans chacune (la langue du preset d'abord, puis celles du fichier)
  "character": { "id": "id1", "name": "Clara Mercier", "gender": "female", "age": 29, "language": "fr", "summary": "…" },
  "preset": "fr-agent",                            // le preset dont la personnalité et la langue ont été lues (null : le preset par défaut du personnage)
  "cast": [ { "id": "martien", "name": "le Martien", "gender": "male" } ],   // les autres personnages du fichier, pour les positions (`about: {"identity"}`)
  "personality": [                                 // la déclinaison de personnalité du preset d'abord, puis une par autre langue du personnage
    { "variant": "p2", "kind": "card", "language": "fr", "description": "…", "personality": "…", "scenario": "…", "first_mes": "…", "mes_example": "…", "system_prompt": "…" },
    { "variant": "p6", "kind": "description", "language": "en", "text": "…" } ],
  "lists": { "goals": ["…"], "fears": ["…"], "values": ["sobriété", "…"], "behavior": ["…"] },   // les listes 1.0 (psyche.json, extensions cof.* de la carte), fusionnées par texte
  "memories": [ { "id": "ev2", "kind": "moment", "gist": "…", "when": "age 28" }, { "id": "ep1", "kind": "period", "gist": "…", "when": "age 24–28" } ],   // les souvenirs du personnage, sans les copies
  "psyche":   [ { "id": "val1", "kind": "value", "gist": "…", "strength": 95 } ],   // les nœuds qui existent déjà : à ne pas reproposer, mais liables
  "max_nodes": 40 }
```

Les gists sont donnés dans la langue du preset (`character.language`). Aucune image n'est envoyée : une psyché est du texte.

## 2. Sortie : la proposition (JSON strict)

```jsonc
{ "contract": "psyche-propose/0.1",
  "nodes": [
    { "id": "c1",                                  // un identifiant court, propre à la proposition (c1, c2…) ; jamais un id du fichier
      "kind": "belief",                            // une des onze sortes de la RFC 0004 § 3
      "gist": { "fr": "…", "en": "…" },            // une phrase par langue, 100 à 300 caractères chacune
      "strength": 60, "stability": "shifting",     // facultatifs (50 et settled par défaut)
      "since": { "age": { "value": 24 } },         // facultatif : {age: {value}} et/ou {date: "AAAA[-MM[-JJ]]"}, approx
      "because": ["memories/ep1"],                 // facultatif : memories/<id> (de préférence), psyche/<id>, ou l'id d'un candidat de la proposition
      "supports": ["psyche/val1"],                 // facultatif : psyche/<id> ou un id de candidat
      "between": ["c3", "psyche/val1"],            // contradiction seulement, obligatoire : exactement deux côtés (ids de candidats ou psyche/<id>)
      "about": { "user": true },                   // position seulement : {user: true} | {identity: "<id du casting>"} | {node: "memories/<id>" | "psyche/<id>" | "<candidat>"} | {label: {langue: texte}}
      "false_but_held": true,                      // croyance seulement : le mensonge que le personnage se raconte
      "risk": { "value": "inappropriate", "why": "…" },   // none | inappropriate | dangerous, avec la raison
      "tags": ["work", "self"],
      "source": "card.description" } ],            // d'où il vient — voir ci-dessous
  "notes": "texte libre pour la relecture" }
```

`source` est obligatoire et nomme l'un de : `card.description`, `card.personality`, `card.scenario`, `card.first_mes`, `card.mes_example`, `card.system_prompt` (un champ de la carte, `@<déclinaison>` en option), `text` (la description libre), `memory <id>` (un souvenir du dossier), `list goals[n]` / `list fears[n]` / `list values[n]` / `list behavior[n]` (une entrée des listes 1.0), `inferred` (lu entre les lignes), `zodiac` (l'entrée horoscope, par règle, jamais d'un modèle).

**Validation** (`cof_cli/propose.py › validate`, les mêmes contrôles dans le builder). Refusé : une sorte hors des onze ; un gist vide ou de plus de 600 caractères ; une force hors de 0–100 ou une stabilité hors des quatre niveaux ; un `since` mal formé ; un `because` / `about` / `supports` / `between` qui nomme un souvenir ou un nœud que le dossier n'a pas (jamais inventer un souvenir) ; un candidat qui se vise lui-même ; une contradiction sans exactement deux côtés distincts, ou `between` hors d'une contradiction ; `about` hors d'une position, un sujet d'aucune des quatre formes, ou une identité absente du casting ; `false_but_held` hors d'une croyance ; un `risk` hors des trois valeurs ; des étiquettes qui ne sont pas des slugs ; une `source` absente ou inconnue, ou `memory <id>` nommant un souvenir que le personnage n'a pas ; des ids de candidats en double. Noté, pas refusé : un gist hors de 100–300 caractères ou sans l'une des langues de l'auteur ; une règle qui n'est pas `core` ; une position sans sujet ; un risque sans raison ; un champ hors contrat (ignoré) ; plus de 40 candidats. Formes tolérées, normalisées avant validation : une liste nue (prise pour `nodes`), un id manquant (`c<n>`), `risk` en simple chaîne, `because` / `supports` / `between` / `tags` en une chaîne à virgules, une force décimale.

**Doublons** : un candidat dont le gist dit ce qu'un nœud existant (ou un candidat précédent) dit déjà — même texte une fois normalisé, ou la plupart des mêmes mots — est signalé à la relecture (`≈ psyche/val1`), jamais retiré : l'auteur décide.

## 3. Règles pour le modèle (le prompt)

Message système : *You decompose a fictional character's personality into psyche nodes (COF 1.2, RFC 0004). Answer in strict JSON only.* Message utilisateur : le texte ci-dessous (en anglais, la langue des modèles ; les gists viennent dans les langues demandées), puis le dossier en JSON. Le texte exact vit dans `cli/cof_cli/propose.py` (`PROMPT`) et dans le builder ; `--bundle-out` écrit les deux avec le dossier. En substance :

> 1. Une phrase par nœud, 100 à 300 caractères par langue, dans chaque langue de `languages` (le même sens dans chacune).
> 2. Les sortes : valeur (ce qui compte), croyance (tenue pour vraie sur le monde ou sur soi), désir (poursuivi consciemment), besoin (ce qui guérirait, non vu), peur, blessure (l'entaille fondatrice, presque toujours à cause d'un souvenir), position (envers une personne, l'utilisateur ou une chose : remplir `about`), goût, habitude (un comportement récurrent observable), contradiction (une tension assumée entre deux nœuds : `between` les nomme), règle (une limite tenue quelle que soit la pression ; stabilité core).
> 3. `source` dit d'où vient le nœud : le champ de la carte, le texte libre, le souvenir (`memory ev3`), l'entrée de liste (`list goals[2]`), ou `inferred` quand il est lu entre les lignes. Ne jamais inventer un souvenir : `because` et `about` ne nomment que des ids du dossier. Préférer `because` vers un souvenir à `because` vers un nœud.
> 4. `strength` : le poids dans les décisions (70 ou plus est dit en entier ; 50 par défaut). `stability` : core ne change jamais à l'usage, settled seulement par un nœud vécu qui le déclare, shifting avec des preuves, fragile au fil d'une conversation.
> 5. Une croyance fausse que le personnage tient pour vraie (le mensonge qu'il se raconte) est `false_but_held: true`. Proposer une contradiction dès qu'un désir et une peur, ou une valeur et une habitude, tirent en sens contraire.
> 6. Déclarer `risk` avec une raison : `inappropriate` (inadapté à certains publics, pas nuisible en soi : instabilité, sexualité déviante, traits autodestructeurs), `dangerous` (rendrait le personnage nuisible s'il agissait : agression, manipulation, mépris de la sécurité d'autrui). `none` sinon.
> 7. Ne pas répéter un nœud existant de `psyche` ; on peut s'y lier. Au plus 40 nœuds ; moins de nœuds bien sourcés valent mieux que beaucoup.
> 8. Rien de ce qui est proposé n'est écrit : l'auteur relit chaque nœud.

La passerelle est celle du contrôle de cohérence du builder (`docs/coherence-api.fr.md`) : `POST {base_url}/chat/completions`, `temperature: 0`, le premier bloc `{…}` de la réponse est la proposition. Un modèle qui ne sait pas répondre en JSON, ou qui répond avec un souvenir qui n'existe pas, produit une proposition refusée, pas un fichier à moitié écrit.

## 4. Les entrées par règle (sans modèle)

Deux sources passent par le même format, la même validation et la même relecture :

- **Les listes 1.0** (`cof psyche propose --rules` ; « Proposer des nœuds à partir des listes » du builder) : la conversion de la RFC 0004 § 3 quater — un objectif devient un `want` (force 70), une peur un `fear` (70), une valeur un mot devenu phrase (« Sobriété. »), un comportement un `habit` ; doublons fusionnés par texte et par id, une carte écrite une fois par langue donnant un candidat avec un gist par langue ; `source: "list goals[n]"`. `cof migrate --psyche` écrit les mêmes nœuds sans relecture (pour un fichier avec des listes et sans psyché) ; la proposition est le chemin relu.
- **Un signe du zodiaque** (`--zodiac vierge`, noms anglais ou français ; `cli/cof_cli/zodiac.py`) : beaucoup d'auteurs décrivent une personnalité par un signe solaire (Yann, 31 octobre 2026). Une petite table statique donne trois ou quatre candidats `value` / `taste` / `habit` typiques du signe, gists en anglais et en français, force 50, stabilité `shifting`, étiquette `zodiac:<signe>`, `source: "zodiac"` — **à relire par l'auteur**, comme tout candidat. Un signe est un raccourci d'auteur : ce n'est ni une sorte de nœud ni un champ du format, et les nœuds qu'il suggère sont des nœuds ordinaires une fois acceptés (l'étiquette garde la trace).

## 5. Ce qui est écrit à l'accept

Pour chaque candidat accepté : `elements/psyche/<id>/psyche-node.json` avec le gist, la force, la stabilité (`settled` par défaut ; `core` pour une règle), `since`, `false_but_held`, `about`, les liens (`because`, `supports`, les deux `conflicts` d'une contradiction) avec les ids de candidats remplacés par les ids qui viennent d'être écrits, la valeur de risque, les étiquettes, et `origin: authored`, `visibility: canon`, `disclosure: open` ; la déclinaison du manifeste (`kind`, `label` tiré du gist, `node`, `identity` dans un casting, la `strength` en miroir), ids par sorte (`val3`, `bel4`…) ; le candidat listé dans `slots.psyche` par chaque preset du personnage qui tient l'une des déclinaisons de personnalité lues par le dossier (sinon n'importe quelle déclinaison de personnalité, sinon les presets du personnage) ; `cof: "1.2"`, `has-psyche`, `tags.content` suivant le risque. Une contradiction n'est écrite que si ses deux côtés sont acceptés ou existent déjà ; une référence à un candidat non accepté est retirée avec une note. Le fichier est validé avant que rien n'atterrisse (cof-cli édite une copie) ; les contrôles du builder s'appliquent comme à tout nœud.

## 6. L'inverse : nœuds → texte

`cof psyche text <src> [--preset p] [--keep-personal] [--keep-dangerous] [--out qui.md | --into-card]` imprime la section « Qui elle est » que `cof export --format agent` met dans `SOUL.md` (RFC 0004 § 3 quinquies) : une ligne par nœud dans l'ordre fixe blessure → valeurs → croyances (mensonges marqués) → désirs et besoins → peurs → positions → goûts → habitudes → contradictions → règles, le gist entier à force ≥ 70 et une courte proposition en dessous, `réservé`, `vécu` et le sujet d'une position en marqueurs, les nœuds secrets omis avec une ligne qui le dit, dans la langue du preset. `--into-card` l'**ajoute à la suite** du champ `personality` de la carte du preset (jamais à la place : la fiche garde la voix, la psyché donne la substance). Le bouton « Texte depuis la psyché » du builder rend le même texte (mêmes règles, en JavaScript) dans une fenêtre avec un bouton copier et « ajouter au champ personnalité de la carte ». Aucun modèle n'intervient : le rendu est déterministe, et l'aller-retour psyché → texte → psyché n'est pas censé être sans perte — la prose est pour le lecteur, les nœuds pour les outils.

## 7. Ligne de commande et builder

```bash
cof psyche propose clara.cof --preset fr-agent --provider openai-compatible --base-url http://localhost:11434/v1 --model qwen2.5 --out proposition.json   # COF_AI_KEY dans l'environnement ; la table, rien d'écrit
cof psyche propose clara.cof --preset fr-agent --from-file proposition.json --apply --accept c2,c3,c4   # les candidats choisis, validés, écrits (--accept all pour tous)
cof psyche propose clara.cof --rules --zodiac vierge --out proposition.json                            # sans modèle : les listes 1.0 et les traits du signe
cof psyche propose clara.cof --bundle-out dossier.json                                                 # emporter le dossier et le prompt dans n'importe quel chat, garder la réponse, revenir avec --from-file
cof psyche text clara.cof --preset fr-agent --into-card                                                # l'inverse
```

Builder (étape Psyché, mode avancé) : « 🤖 Proposer une psyché depuis la personnalité » construit le dossier depuis l'état courant, appelle la passerelle réglée à l'étape Contrôles (URL de base, clé, modèle — les mêmes réglages que le contrôle de cohérence ; sans réglage, il le dit et propose de coller une proposition JSON produite ailleurs, `cof psyche propose --out`), valide la réponse et ouvre le panneau de relecture : une ligne par candidat (sorte, gist, force, stabilité, source, risque et sa raison, liens, avertissement de doublon), une case par ligne — **toutes décochées** —, « Ajouter les nœuds cochés » crée les cartes. Une contradiction a besoin de ses deux côtés cochés ou existants. La clé reste dans le navigateur ; le dossier n'en sort que vers la passerelle que l'auteur a saisie.
