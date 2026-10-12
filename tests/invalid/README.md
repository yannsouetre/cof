# Negative conformance corpus

Every `.cof` in this folder violates **one** rule of the specification and MUST be rejected by a conformant
validator. `_base.cof` is the valid file they are derived from (a shrunk copy of
`spec/examples/09-mixte-adulte-mineur`: an adult preset with intimate content and a minor preset).

`cases.json` lists, for each file, the rule broken, the spec section and a substring of the reference
validator's error (`expect`) — other implementations only need to reject the file; their wording is free.

| File | Rule broken |
|---|---|
| `version-0.5.cof` | format version must be 1.x (older files are migrated) |
| `missing-id.cof` | `id` is required |
| `unknown-variant-in-preset.cof` | a preset slot references an existing variant |
| `face-without-age.cof` | a human-form face carries an age |
| `intimate-under-18.cof` | intimate content requires age ≥ 18 |
| `minor-preset-offers-intimate.cof` | a preset under 18 never offers intimate content either (rules cover `slots` ∪ `alternatives`) |
| `primary-image-not-applied.cof` | a preset's `primary_image` belongs to a variant it applies |
| `alternative-in-library.cof` | no `alternatives` on the libraries (posture, motion, files) |
| `intimate-without-content-tag.cof` | intimate content is flagged in `tags.content` |
| `minor-preset-with-intimate.cof` | a preset under 18 never contains intimate content |
| `minor-preset-sexual-usage.cof` | a preset under 18 never has an effective `allowSexualUsage` |
| `two-faces-in-preset.cof` | one variant per kind in a preset (except stackable kinds) |
| `real-person-without-consent.cof` | a non-fictional character requires consent |
| `weights-without-base-model.cof` | identity weights declare their base model |
| `pickle-file.cof` | pickles are always refused |
| `undeclared-script.cof` | scripts require `container.executableContent` |
| `obj-not-self-contained.cof` | 3D variants are self-contained (unless `self_contained: false`) |
| `tag-unknown-preset.cof` | a preset tag lists existing presets |
| `illegal-coherence-finding.cof` | a coherence finding of severity `illegal` invalidates the file |
| `mimetype-not-first.cof` | `mimetype` is the first entry |
| `mimetype-compressed.cof` | `mimetype` is stored uncompressed |
| `wrong-mimetype.cof` | `mimetype` = `application/vnd.cof.character+zip` |
| `path-traversal.cof` | no `..` or absolute paths |
| `hash-mismatch.cof` | assets match their declared `sha256` |
| `asset-missing.cof` | declared assets are present |

Regenerate with `python tests/invalid/build.py` (it also checks every case against the reference validator).
