# Règles du KPI de complétude (v0.3)

Calculé **par preset** (slots résolus, héritage `extends`/`derives_from` appliqué) ; KPI de fichier = preset par défaut ; `coverage` = types d'éléments présents, nombre de déclinaisons et de presets. Les **dérivés** ne comptent jamais.

| Couche (poids) | Points |
|---|---|
| identity (10 %) | name 20 · âge du preset connu (déclinaisons ou plancher) 20 · summary 20 · languages 10 · morphology 10 · tags.content 10 · tags.ip 10 |
| personality (20 %) | card 30 · description 10 · personality 10 · scenario 5 · first_mes 10 · mes_example 10 · story/lore 10 · psyche 15 |
| appearance (20 %) | head.front 25 · ≥ 2 vues de tête 10 · face params ou mesh 10 · mesh 5 · hair 5 · vues de corps 10 · ≥ 2 vues 5 · body params 5 · outfit 10 · identity_weights 15 |
| physique (5 %) | attitude 60 · poses 40 |
| voice (15 %) | échantillons 30 · tous transcrits +10 (transcription facultative) · durées 8 s et ≥ 25 s 10 · profile 25 · voice.vec 20 · engines 5 |
| volume (10 %) | avatar 60 · rig déclaré 10 · splat 15 · print 15 |
| motion (5 %) | clips ou vidéo 60 · visemes 25 · rig déclaré sur tous les clips 15 · `attitude` (signature de mouvement) 30 — plafonné à 100 |
| rights (15 %) | permissions 40 · licence sur tous les assets 15 · consentement si requis 20 · provenance.source 10 · C2PA ou signature 15 |

Niveaux : A ≥ 85, B ≥ 60, C ≥ 35, D < 35. Un texte seul parfait plafonne ~41 ; une apparence seule ~33 : voulu, le KPI mesure la **couverture**.

Cibles prêtes : `chat-text`/`agent-persona` si personality ≥ 50 ; `chat-voice` si + voice ≥ 40 ; `image-video-gen` si appearance ≥ 25 ; `video-realtime` si voice ≥ 40, appearance ≥ 40 et (face params/mesh ou avatar) ; `game-3d` si avatar ; `print-3d` si print ; `archive` si rights ≥ 60.
