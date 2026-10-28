# cof-cli

Outil de référence pour COF (Character Open File) : validation, empaquetage, extraction, fusion, conversions, et l'ajout d'un souvenir vécu (1.1). `pip install cof-cli` (PyPI) ou, depuis ce dossier, `pip install -e ".[dev]"`. Python ≥ 3.10.

```bash
cof validate spec/examples/10-clara-mercier        # dossier ou fichier .cof : erreurs, avertissements, complétude (--json pour la CI)
cof pack spec/examples/10-clara-mercier -o clara.cof   # recalcule hashes, complétude, langues ; écrit COF.md et la vignette
cof info clara.cof                                  # presets, déclinaisons, âges, tags — le point de départ pour un agent
cof unpack clara.cof -o clara/
cof tokens clara.cof
cof extract clara.cof --preset fr-65 -o clara-65/   # une tranche plus légère : un preset, un personnage (--identity) ou des tags (--tag fr --tag age-65)
cof extract clara.cof --identity clara-mercier --all-audiences -o clara-sfw/   # sans nudité ni intime, médias des souvenirs explicites retirés (gist conservé)
cof extract clara.cof --preset default --keep-personal -o clara-perso/         # garde les souvenirs `visibility: personal` (retirés par défaut)
cof merge clara.cof martien.cof -o duo/             # un casting : même nom + surnom + statut fictif + morphologie ⇒ même personnage, sinon plusieurs
cof memory add clara.cof --gist fr="Ce matin, relu avec Léo." --gist en="This morning, reread with Léo." --date 2026-10-25 --who "Léo" --tag travail --personal
cof memory add clara/ --kind period --gist en="The agency years." --age 24 --approx --fidelity faded   # sur un dossier ; `--help` liste tout (--where, --self-shown, --media, --preset…)
cof import carte.png -o perso/ --age 30 --lang fr --keep-png   # carte PNG CCv2/V3 → dossier COF
cof export clara.cof --format png -o clara.png      # → PNG avec chunks chara + ccv3
cof export clara.cof --format card -o clara.card.json
cof export clara.cof --format soul -o ./agent/      # → SOUL.md + IDENTITY.md
cof export clara.cof --format agent -o ./agent/     # → espace de travail d'agent : SOUL.md, IDENTITY.md, skills/, MEMORY.md + memories/ (--keep-personal, --preset)
cof embed-text clara.png fiche.md -o clara-fiche.png   # texte descriptif dans un PNG (iTXt), lisible par le builder
cof read-text clara-fiche.png
cof migrate dossier-v0.5/                           # v0.2 … v0.5 → 1.0
```

Ce que `validate` vérifie : la structure de l'archive (sentinelle `mimetype`, chemins sûrs, pas d'entrée en double ni chiffrée, taux de compression, taille), les hashes SHA-256 et tailles des assets, les schémas JSON du manifeste et des sous-fichiers (`card`, `psyche`, `weights`, `voice-profile`, `memory`…), la résolution des presets (slots, alternatives, `extends`, `derives_from`), les identifiants d'assets et de déclinaisons, les règles d'âge sur l'**âge le plus bas** d'un preset (déclinaisons appliquées et offertes, `age_override`, souvenirs qui montrent le personnage), l'interdiction de tout contenu nu ou intime sous 18 ans, le consentement d'une personne réelle, les règles des souvenirs (RFC 0002 : forme de `when`, liens, `media_from`, nœuds explicites — qui est montré, âges connus et adultes, âge vécu ≥ 18, drapeau `nudity`, `tags.content`), les relations entre personnages d'un casting (RFC 0003), les styles mélangés, les transcriptions des échantillons de voix, le contenu exécutable non déclaré, les doublons, les budgets de tokens ; puis recalcule la complétude et les cibles prêtes. Les chemins et noms lus dans un manifeste ne sortent jamais du dossier de sortie (`export`, `extract`, `merge`).

Tests : `pytest` (dossier `cli/`, 68 tests) ; le corpus négatif de `tests/invalid/` (63 cas, un par règle) est régénéré par `python tests/invalid/build.py`. Tokens : installer `tiktoken` pour un comptage exact (sinon heuristique par caractères).
