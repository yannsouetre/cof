# COF Builder (v0.3, builder v0)

Une seule page HTML, **sans dépendance ni réseau** : ouvrez `index.html` dans un navigateur récent (Chrome/Edge/Firefox/Safari 2023+) — en local par double-clic, ou hébergée (GitHub Pages, Space Hugging Face statique). Tout reste dans le navigateur ; seule la passerelle de cohérence (optionnelle) envoie des données au point d'API que **vous** configurez.

Parcours : **1 Identité → 2 Éléments** (déclinaisons par type ; import de carte PNG/JSON ; glisser-déposer d'images, d'échantillons de voix avec transcription, d'avatar VRM/GLB, de clips ; fiche LoRA) **→ 3 Presets** (combinaisons, preset par défaut, héritage, âge par preset, surcharge de permissions optionnelle) **→ 4 Droits** (permissions VRM-like, consentement avec preuve) **→ 5 Contrôles** (erreurs de structure bloquantes ; cohérence heuristique non bloquante ; passerelle IA OpenAI-compatible ; priorités) **→ 6 Build** (classe de taille, redimensionnement/compression des images, dérivé Canny optionnel, export `.cof`, carte PNG ccv3, SOUL.md/IDENTITY.md, aperçu du manifeste). « Ouvrir un .cof » recharge un fichier v0.3 pour l'éditer.

Technique : ZIP écrit à la main (`mimetype` stocké en première entrée, `manifest.json` en seconde, binaires stockés, JSON en deflate via `CompressionStream`), SHA-256 via WebCrypto, chunks PNG `chara`/`ccv3` lus et écrits en JS, KPI de complétude calculé avec les mêmes règles que `cof-cli` (vérifié : scores identiques).

Pas encore dans ce v0 (prévu) : découpage automatique des planches, détection des vues et des styles, mesures acoustiques, bonhomme OpenPose, PiDiNet/HED en ONNX, génération des SOUL/IDENTITY par preset autre que le défaut, « enregistrer sous » un preset, fusion de fichiers.
