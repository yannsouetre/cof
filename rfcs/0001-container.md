# RFC 0001 — Conteneur ZIP, sentinelle `mimetype`, manifeste racine

- Statut : en commentaires (jusqu'au 2026-10-23)
- Auteur : Yann Souetre
- Date : 2026-10-09

## Motivation
Un personnage IA est aujourd'hui éclaté entre PNG (cartes), WAV, VRM, LoRA et notes ; aucun format ouvert ne les réunit avec les droits et le consentement (voir `docs/state-of-the-art.md`).

## Proposition
Voir `spec/SPEC.md` § 1 et § 2 : archive ZIP ; première entrée `mimetype` stockée sans compression contenant `application/vnd.cof.character+zip` ; deuxième entrée `manifest.json` validée par `spec/schemas/manifest.schema.json` ; chemins ASCII sans `..` ; binaires stockés sans compression ; aucun chiffrement ; aucun code exécutable ; identité (`id` ULID, `name`, `age`, `morphology`) et `rights.permissions` obligatoires, tout le reste optionnel.

## Impact
Format nouveau ; exports de compatibilité vers PNG `ccv3`, `.charx`, `SOUL.md`, `.vrm`.

## Alternatives envisagées
PNG à chunks (hérité, +33 % base64, limite 2^31) ; GLB (binaire minimal mais pensé pour la 3D) ; Matroska (tout-contenant mais sans outillage LLM/web) ; OCI (retenu comme second mode de distribution, pas comme fichier).

## Questions ouvertes
Nom définitif de l'extension (`.cof` retenu, cf. § 0 de la spec) ; alignement 64 octets optionnel ; limites anti zip-bomb.
