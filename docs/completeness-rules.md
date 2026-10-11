# Completeness KPI rules (v0.3)

Computed **per preset** (resolved slots, `extends`/`derives_from` inheritance applied); file KPI = default preset; `coverage` = element types present, number of variants and presets. **Derivatives** never count.

| Layer (weight) | Points |
|---|---|
| identity (10%) | name 20 · preset age known (variants or floor) 20 · summary 20 · languages 10 · morphology 10 · tags.content 10 · tags.ip 10 |
| personality (20%) | card 30 · description 10 · personality 10 · scenario 5 · first_mes 10 · mes_example 10 · story/lore 10 · psyche 15 |
| appearance (20%) | head.front 25 · ≥ 2 head views 10 · face params or mesh 10 · mesh 5 · hair 5 · body views 10 · ≥ 2 views 5 · body params 5 · outfit 10 · identity_weights 15 |
| physique (5%) | attitude 60 · poses 40 |
| voice (15%) | samples 30 · all transcribed +10 (transcription optional) · durations 8 s and ≥ 25 s 10 · profile 25 · voice.vec 20 · engines 5 |
| volume (10%) | avatar 60 · rig declared 10 · splat 15 · print 15 |
| motion (5%) | clips or video 60 · visemes 25 · rig declared on all clips 15 · `attitude` (motion signature) 30 — capped at 100 |
| rights (15%) | permissions 40 · license on all assets 15 · consent if required 20 · provenance.source 10 · C2PA or signature 15 |

Grades: A ≥ 85, B ≥ 60, C ≥ 35, D < 35. Perfect text alone caps at ~41; appearance alone at ~33: by design, the KPI measures **coverage**.

Ready targets: `chat-text`/`agent-persona` if personality ≥ 50; `chat-voice` if also voice ≥ 40; `image-video-gen` if appearance ≥ 25; `video-realtime` if voice ≥ 40, appearance ≥ 40 and (face params/mesh or avatar); `game-3d` if avatar; `print-3d` if print; `archive` if rights ≥ 60.
