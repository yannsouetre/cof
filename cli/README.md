# cof-cli

Outil de référence pour COF (Character Open File) : validation, empaquetage, extraction, fusion, conversions, l'ajout d'un souvenir vécu (1.1) et d'un nœud de psyché vécu (1.2). `pip install cof-cli` (PyPI) ou, depuis ce dossier, `pip install -e ".[dev]"`. Python ≥ 3.10.

```bash
cof validate spec/examples/10-clara-mercier        # dossier ou fichier .cof : erreurs, avertissements, complétude (--json pour la CI)
cof pack spec/examples/10-clara-mercier -o clara.cof   # recalcule hashes, complétude, langues ; écrit COF.md et la vignette
cof info clara.cof                                  # presets, déclinaisons, âges, tags — le point de départ pour un agent
cof unpack clara.cof -o clara/
cof tokens clara.cof
cof extract clara.cof --preset fr-65 -o clara-65/   # une tranche plus légère : un preset, un personnage (--identity) ou des tags (--tag fr --tag age-65) ; les lieux et objets que nomment ses souvenirs et nœuds suivent
cof extract clara.cof --identity clara-mercier --all-audiences -o clara-sfw/   # sans nudité ni intime, médias des souvenirs explicites retirés (gist conservé)
cof extract clara.cof --preset default --keep-personal -o clara-perso/         # garde les souvenirs et nœuds de psyché `visibility: personal` (retirés par défaut)
cof extract clara.cof --preset default --no-risk -o clara-sans-risque/         # purge de risque (RFC 0004) : retire les nœuds `inappropriate` et `dangerous` (et les contradictions amputées), tags.content corrigés ; --all-audiences les retire aussi
cof merge clara.cof martien.cof -o duo/             # un casting : même nom + surnom + statut fictif + morphologie ⇒ même personnage, sinon plusieurs
cof memory add clara.cof --gist fr="Ce matin, relu avec Léo." --gist en="This morning, reread with Léo." --date 2026-10-25 --who "Léo" --what "le carnet" --what "item=appearance/x1" --tag travail --personal   # --what : un objet (1.2, RFC 0005), un nom et/ou item=<élément>, |shown s'il est dans un média
cof memory add clara/ --kind period --gist en="The agency years." --age 24 --approx --fidelity faded   # sur un dossier ; `--help` liste tout (--where, --self-shown, --media, --preset…)
cof psyche add clara.cof --kind stance --gist fr="Envers l'utilisateur : une collègue." --about user --strength 60 --stability shifting --link because=memories/ev3 --since-date 2026-10-25   # nœud vécu, `visibility: personal` (--canon sinon), première révision ; `--help` liste tout (--lie, --risk, --tag, --preset…)
cof psyche add clara.cof --kind habit --gist fr="Garde la guitare près du bureau." --who "ma grand-mère" --where "environment=appearance/e1" --what "ma guitare|item=appearance/x1" --canon   # personnes, lieux, objets du nœud (RFC 0005) ; une personne du casting : --who identity=<id> (les liens --link ne visent que souvenirs et nœuds)
cof psyche add clara.cof --kind stance --gist fr="Envers l'utilisateur : de la chaleur." --about user --valence 60 --aware partly --canon   # RFC 0004 § 3 nonies : --valence −100…+100 (position ou goût seulement), --aware yes|partly|no, --until-age / --until-date (quand le nœud a cessé d'être tenu)
cof psyche propose clara.cof --preset fr-agent --from-file proposition.json   # personnalité → psyché : une proposition validée (docs/psyche-propose.md), affichée en table, rien d'écrit
cof psyche propose clara.cof --from-file proposition.json --apply --accept c2,c3   # n'écrit que les candidats acceptés ; --rules (listes 1.0), --zodiac vierge, --bundle-out, --provider openai-compatible (clé : COF_AI_KEY)
cof psyche text clara.cof --preset fr-agent        # l'inverse : le texte « Qui elle est » ; --into-card l'ajoute à la suite du champ personnalité de la carte
cof import carte.png -o perso/ --age 30 --lang fr --keep-png   # carte PNG CCv2/V3 → dossier COF
cof export clara.cof --format png -o clara.png      # → PNG avec chunks chara + ccv3
cof export clara.cof --format card -o clara.card.json
cof export clara.cof --format soul -o ./agent/      # → SOUL.md + IDENTITY.md
cof export clara.cof --format agent -o ./agent/     # → espace de travail d'agent : SOUL.md (avec « Qui elle est » rendu depuis la psyché), IDENTITY.md, skills/, MEMORY.md + memories/ (--keep-personal, --keep-dangerous, --preset)
cof embed-text clara.png fiche.md -o clara-fiche.png   # texte descriptif dans un PNG (iTXt), lisible par le builder
cof read-text clara-fiche.png
cof migrate dossier-v0.5/                           # v0.2 … v0.5 → 1.0
cof migrate clara/ --psyche                         # 1.2 : les listes goals / fears / values / behavior deviennent des nœuds de psyché (les listes restent ; idempotent)
```

Ce que `validate` vérifie : la structure de l'archive (sentinelle `mimetype`, chemins sûrs, pas d'entrée en double ni chiffrée, taux de compression, taille), les hashes SHA-256 et tailles des assets, les schémas JSON du manifeste et des sous-fichiers (`card`, `psyche`, `weights`, `voice-profile`, `memory`…), la résolution des presets (slots, alternatives, `extends`, `derives_from`), les identifiants d'assets et de déclinaisons, les règles d'âge sur l'**âge le plus bas** d'un preset (déclinaisons appliquées et offertes, `age_override`, souvenirs qui montrent le personnage), l'interdiction de tout contenu nu ou intime sous 18 ans, le consentement d'une personne réelle, les règles des souvenirs (RFC 0002 : forme de `when`, liens, `media_from`, nœuds explicites — qui est montré, âges connus et adultes, âge vécu ≥ 18, drapeau `nudity`, `tags.content`), les relations entre personnages d'un casting (RFC 0003), les styles mélangés, les transcriptions des échantillons de voix, le contenu exécutable non déclaré, les doublons, les budgets de tokens ; puis recalcule la complétude et les cibles prêtes. En 1.2, il vérifie aussi la psyché (RFC 0004) : fichier `psyche-node.json` de chaque nœud, cibles des liens et de `about`, `supports` / `conflicts` entre nœuds seulement, une `contradiction` à exactement deux `conflicts`, `false_but_held` sur une `belief` et `about` sur une `stance` seulement, pas de cycle de `because`, miroir de `strength`, un nœud ne s'appuie que sur les souvenirs de son personnage, cohérence `risk` ↔ `tags.content` (`psyche-inappropriate`, `psyche-dangerous`) et `cof: "1.2"` déclaré ; les personnes, lieux et objets (RFC 0005) : `what` des souvenirs, `who` / `where` / `what` des nœuds — identité, environnement ou objet (`item`) résolus et du même personnage dans un casting, un nœud sans lien vers `identities/…` (les personnes vont dans `who`), `cof: "1.2"` déclaré ; un `item` qui n'est pas un accessoire ou un lieu qui n'est pas un environnement est un avertissement ; les informations non bloquantes s'affichent en lignes `INFO`. Les chemins et noms lus dans un manifeste ne sortent jamais du dossier de sortie (`export`, `extract`, `merge`).

Tests : `pytest` (dossier `cli/`, 88 tests) ; le corpus négatif de `tests/invalid/` (80 cas, un par règle) est régénéré par `python tests/invalid/build.py`. Tokens : installer `tiktoken` pour un comptage exact (sinon heuristique par caractères).
