# Negative conformance corpus

Every `.cof` in this folder violates **one** rule of the specification and MUST be rejected by a conformant
validator. `_base.cof` is the valid file they are derived from (a shrunk copy of
`tests/fixtures/mixed-age`: an adult preset with intimate content and a minor preset).

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
| `cross-character-element.cof` | a preset only uses its own character's elements |
| `likeness-shared-between-characters.cof` | a file carrying a likeness or a voice belongs to one character |
| `face-marked-neutral.cof` | a face, body, voice… is never neutral |
| `element-without-character.cof` | with several characters, every element names its character |
| `intimate-without-content-tag.cof` | intimate content is flagged in `tags.content` |
| `minor-preset-with-intimate.cof` | a preset under 18 never contains intimate content |
| `minor-preset-sexual-usage.cof` | a preset under 18 never has an effective `allowSexualUsage` |
| `two-faces-in-preset.cof` | one variant per kind in a preset (except stackable kinds) |
| `real-person-intimate-without-consent.cof` | intimate content of a real person requires their explicit consent (scope `intimate`) |
| `weights-without-base-model.cof` | identity weights declare their base model |
| `pickle-file.cof` | pickles are always refused |
| `invalid-safetensors.cof` | a `.safetensors` must have a readable header that fits the file (a renamed pickle is refused) |
| `age-in-months.cof` | ages are compared in years — 100 months is 8 years |
| `intimate-file-shared.cof` | an intimate variant's files are its own |
| `same-file-minor-and-adult.cof` | one file never represents both a person under 18 and an adult |
| `intimate-age-any-morphology.cof` | with an intimate element, every body representation of the preset carries an age, whatever the morphology class |
| `extends-cycle.cof` | preset inheritance has no cycle |
| `thumbnail-missing.cof` | `manifest.thumbnail` names an existing file |
| `age-unknown-unit.cof` | an age whose unit is not understood never counts as adult |
| `nested-archive-pickle.cof` | archives are inspected with their nested archives |
| `nudity-in-minor-preset.cof` | no nudity of any kind in a preset under 18 |
| `nudity-without-content-flag.cof` | a variant marked `nudity` requires `tags.content` `nudity` |
| `nude-file-reused-unmarked.cof` | a file showing nudity is used only by variants marked `nudity` (or intimate) |
| `real-person-nudity-without-consent.cof` | nudity of a real person requires their explicit consent (scope `nudity` or `intimate`) |
| `cast-nudity-borrowed-consent.cof` | in a cast, each real person's consent is their own |
| `nudity-without-age.cof` | a preset applying a nude element has a known age (18 or over) |
| `nude-thumbnail.cof` | the file thumbnail never shows nudity or intimate content |
| `cast-root-consent-mismatch.cof` | in a cast, `rights.consent` is a copy of the default character's record |
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
| `memory-in-a-1.0-file.cof` | a file declares the lowest minor that defines what it uses: memories need cof 1.1 |
| `memory-without-node-file.cof` | a memory variant names its node file |
| `memory-without-gist.cof` | the gist is the only required field of a node |
| `memory-link-unresolved.cof` | a link points to an existing node, qualified <category>/<id> |
| `memory-period-with-point-when.cof` | a period's when has from / to, a moment's is a point |
| `memory-explicit-without-nudity-flag.cof` | an explicit node also carries the 1.0 flag nudity: true and the file tags.content |
| `memory-explicit-shows-minor.cof` | every person shown in an explicit node has a known age of 18 or more |
| `memory-explicit-shown-unknown-age.cof` | an unknown age never counts as adult: an explicit node needs every shown person's age |
| `memory-explicit-real-third-party.cof` | a real person shown nude must be a consenting identity of the file |
| `memory-shows-self-without-age.cof` | a node whose media show the character carries the character's age at the time |
| `memory-media-and-media-from.cof` | media and media_from are exclusive |
| `memory-showing-minor-with-intimate-preset.cof` | a memory showing the character under 18 makes the preset a minor preset: no intimate content there |
| `memory-explicit-nobody-shown.cof` | an explicit media shows someone: an explicit node declares at least one person shown |
| `memory-borrows-explicit-media.cof` | a node borrowing the media of an explicit node is explicit itself, same value (nothing else is inherited) |
| `memory-explicit-age-mismatch.cof` | on an explicit node the variant age (read by the minor rules) equals when.age |
| `memory-explicit-lived-as-minor.cof` | a memory lived as a minor is never explicit, whoever is shown (here only an adult third party) |
| `relation-to-oneself.cof` | a relation names another character of the same file (RFC 0003) |
| `psyche-node-missing.cof` | a psyche variant names its node file (RFC 0004) |
| `psyche-link-dangling.cof` | a psyche link points to an existing memory or psyche node |
| `psyche-supports-not-psyche.cof` | `supports` and `conflicts` link psyche nodes only |
| `psyche-contradiction-links.cof` | a contradiction carries exactly two `conflicts` links |
| `psyche-false-but-held-kind.cof` | `false_but_held` (the lie) is on a belief only |
| `psyche-about-kind.cof` | the `about` field is on a stance only |
| `psyche-because-cycle.cof` | `because` links between psyche nodes have no cycle |
| `psyche-strength-mirror.cof` | the variant's `strength` mirrors the node's |
| `psyche-risk-tag-missing.cof` | a `dangerous` node makes the file carry `tags.content` `psyche-dangerous` |
| `psyche-cof-version.cof` | a file using the psyche category declares cof 1.2 |
| `psyche-link-to-identity.cof` | a psyche link targets a memory or a psyche node — people go in `who` (RFC 0005) |
| `psyche-who-unknown-identity.cof` | a person entry's `identity` exists (a file without an `identities` table knows only `"self"`) |
| `psyche-object-unresolved.cof` | an object entry's `item` names an element of the character |
| `psyche-entry-without-reference-or-label.cof` | a person, place or object entry carries its reference or a `label` |
| `memory-object-unresolved.cof` | a memory's object (`what[].item`) names an existing element |
| `memory-objects-in-a-1.1-file.cof` | a file using objects on a memory declares cof 1.2 |
| `object-of-another-character.cof` | in a cast file, a node's places and objects are its own character's elements |
| `psyche-valence-on-a-belief.cof` | `valence` is on a stance or a taste only (RFC 0004 § 3 nonies) |
| `psyche-until-before-since.cof` | a node's `until` is not before its `since` (RFC 0004 § 3 nonies) |
| `psyche-image-not-an-image.cof` | a psyche node is illustrated by images only (RFC 0004 § 3 decies) |
| `psyche-image-unknown-asset.cof` | an image of a psyche node is an asset of the file |
| `psyche-image-shows-character-without-age.cof` | an image that shows the character makes the variant carry an `age` |
| `psyche-image-of-a-minor-in-an-adult-preset.cof` | the age of an image enters the preset's lowest age: a minor image makes a minor preset |
| `psyche-image-nudity-without-adult.cof` | an image with nudity shows an adult whose age is known |

Regenerate with `python tests/invalid/build.py` (it also checks every case against the reference validator).
