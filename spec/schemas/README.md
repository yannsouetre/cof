# JSON Schemas (draft 2020-12) — COF v0.5

| Schema | File validated | Referenced by | Notes |
|---|---|---|---|
| `manifest.schema.json` | `manifest.json` | — | root; `$defs/consent` is a synchronized copy of `consent.schema.json` |
| `card.schema.json` | `elements/personality/<v>/card.json` | `variant.card` | checked subset of Character Card V3 (`extensions.cof`: behavior, goals, fears, language) |
| `psyche.schema.json` | `elements/personality/<v>/psyche.json` | `variant.psyche` | Big Five / HEXACO [0,1], custom traits with `evidence`, goals, fears, values, contradictions, baseline emotion (category + PAD), renderings |
| `weights.schema.json` | `elements/identity_weights/<v>/weights.json` | `variant.spec` | `base_model.name` required; `format` safetensors only; `covers` disjoint per preset |
| `voice-profile.schema.json` | `elements/voice/<v>/profile.json` | `variant.profile` | canonical profile, ordinal VPA, samples (transcription optional), perishable `engines[]`, "verification-only" fingerprint |
| `attitude.schema.json` | `elements/{posture,motion}/<v>/attitude.json` | `variant.spec` (kind `attitude`) | LMA Effort (4 axes −1…+1, 8 actions), Shape, tempo, BAP postures, BML gestures → `expresses: [trait:…]`, gaze, proxemics, gait, `poses[]` |
| `pose.schema.json` | `pose.json` | `attitude.poses[].path`, `variant.pose` | normalized 2D keypoints `[x,y,c]`, declared skeleton (`openpose-body25`, `coco-18`, `coco-wholebody-133`, `mediapipe-pose-33`, `h36m-17`), joint count enforced per skeleton, optional hands/face, `render` (PNG stick figure) |
| `skeleton.schema.json` | entries of `vocabularies/skeletons-1.0.json` | — | skeleton definition: joints + parent + mapping to the **COF canonical** skeleton; axes, units, rest pose |
| `hair.schema.json` | `elements/appearance/<v>/hair.json` | `variant.code` (kind `hair`) | COF-HAIR-1: length / curl / density 0–9, hex colors, gray %, hairstyle, part, bangs |
| `body.schema.json` | `elements/appearance/<v>/body.json` | `variant.params` (kind `body`) | height, build, ISO 7250 measurements, Anny phenotypes, SMPL-X β, skin tone (Monk / Fitzpatrick), `estimated` + `confidence` |
| `consent.schema.json` | `rights/consent.json`, `identities.<id>.consent` | — | real person: `scope[]` (including `intimate`), dates, jurisdictions, proofs (sha256 required if a file is attached), subject age ≥ 18 |
| `visemes.schema.json` | `elements/motion/<v>/visemes.json` | `variant.visemes` | viseme vocabulary of the clips (ARKit-52, Oculus-15, Preston Blair, Unified Expressions, custom + mapping) |

Rule: `cof validate` validates every sub-file referenced by a variant against its schema (error, not warning: these files are produced by the builder or the CLI). Sub-files not listed (e.g. `outfit.json`, `voice.vec.json`, `face.mesh`) are not schematized yet — see `docs/design-notes-phase0.md`.
