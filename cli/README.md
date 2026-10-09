# cof-cli

Outil de référence pour COF (Character Open File) : validation, empaquetage, conversions.

```bash
pip install -e ".[dev]"          # depuis le dossier cli/
cof validate spec/examples/01-lea-text-only      # dossier ou fichier .cof
cof pack spec/examples/01-lea-text-only -o lea.cof   # recalcule hashes + complétude
cof info lea.cof
cof unpack lea.cof -o lea/
cof tokens lea.cof
cof import carte.png -o perso/ --age 30 --lang fr --keep-png   # carte PNG CCv2/V3 → dossier COF
cof export lea.cof --format png -o lea.png                     # → PNG avec chunks chara + ccv3
cof export lea.cof --format soul -o ./agent/                   # → SOUL.md + IDENTITY.md (OpenClaw)
cof export lea.cof --format card -o lea.card.json
```

Ce que `validate` vérifie : schéma du manifeste, sentinelle `mimetype`, chemins sûrs (pas de `..`, pas de symlink), absence de chiffrement, taux de compression, hashes SHA-256 et tailles des assets, cohérence âge ↔ corps, bloc intime interdit si mineur, consentement si personne réelle, transcriptions des échantillons de voix, contenu exécutable non déclaré, renvois `expresses` vers `psyche.json`, doublons textuels, budgets de tokens ; puis recalcule le KPI de complétude et les cibles prêtes.

Tests : `pytest` (dossier `cli/`). Tokens : installer `tiktoken` pour un comptage exact (sinon heuristique par caractères).
