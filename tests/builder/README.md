# Builder round-trip test

Checks that the builder writes back, unchanged, what it does not know: a category added by a later 1.x minor
(its variants with every field, its sub-files, its media assets, its preset slots) and the file's minor version.

```
pip install playwright pillow cof-cli && python -m playwright install chromium
python tests/builder/make_fixture.py /tmp/later.cof
python tests/builder/roundtrip.py builder/index.html /tmp/later.cof /tmp/out.cof
```

The script opens the builder in headless Chromium, loads the file, clicks Build and inspects the download.

## Psyché step (builder 0.14, RFC 0004)

```
npm i playwright && npx playwright install chromium
node tests/builder/psyche_test.js [repo-root] [work-dir]
```

Packs copies of examples 10 (Clara 1.2) and 01 (Clara text-only, 1.0 lists) into the work dir, serves the repository over
HTTP and drives the builder: the 22 nodes of Clara in step 4 (kind chips, filter), a gist and a strength edited, a rule, a
stance about the user and a contradiction added, a node derived and one deleted, a preset's Psyché subsection ticked, the
checks on a deliberately broken node, every purge choice built and re-validated with `cof validate`, the conversion of
the 1.0 lists. Needs `python` with cof-cli importable from `cli/`. Then, on a copy of example 10 with the people, places and objects of
RFC 0005 written in (and an older draft's link to `identities/id1`): the « Personnes, lieux, objets » fold of a psyche card (one line while
empty, pickers filled on first use: self, the environments, the accessories), the identity link converted to `who` with its information
line in the checks, a link picker without identities, the three lists written and valid against `spec/schemas`, their checks, the six languages. Last, on a copy of example 10 with the values of RFC 0004 § 3 nonies (bel3 `aware: no` and `until` 45,
need1 `partly`, valences on the two stances and the two tastes, contra1 `until` 45): « Jusqu'à » next to « Depuis », « Conscience de soi » on
every card, the valence slider on stances and tastes only; the untouched file written back unchanged; until, awareness (the default « yes »
not added, kept when read), a valence moved, cleared and dropped by a change of kind; the checks (valence off a stance or taste, until
before since, an unconscious secret, the 65-year-old presets holding nodes ended at 45); the six languages.

## Objects of a memory and the RFC 0005 round trip (builder 0.14, RFC 0005)

```
node tests/builder/objects_test.js [repo-root] [work-dir]
```

Packs a copy of example 10 with the entries of RFC 0005 § 3 (the notebook and the pendant by name, the folk guitar as `appearance/x1`; a
person, a place and two objects on psyche nodes) and example 11 (the duo, 1.1). The « 🧸 Objets » field of a memory card, its picker (one
option until used, then a free name and the character's accessories only — in a cast file, that character's); **the file built without any
edit carries every memory and psyche node unchanged**; objects added (a free name with « montré », an accessory), renamed (the other
languages kept), removed (`what` absent when empty); the checks (no reference nor name, unresolved item, not an accessory, another
character's element, a real person who is not a character); a 1.1 file is written as 1.2 once a memory has an object; the six languages.
Node files are checked against `spec/schemas` (needs `jsonschema`), and with `cof validate` when the repository's cli knows RFC 0005.

## Psyche converter (docs/psyche-propose.md)

```
node tests/builder/psyche_propose_test.js [repo-root] [work-dir]
```

No network: the fetch to the configured gateway (`<base>/chat/completions`) is intercepted with Playwright's `page.route` and
answered with `tests/fixtures/psyche-propose/clara-proposal.json`. On Clara 1.2: « Proposer une psyché depuis la personnalité »
without a gateway says so and offers the paste; with one, the request carries the bundle of the contract; the review panel shows
six rows, all unticked, the duplicate of `val1` flagged; nothing is added until rows are ticked; a contradiction without its side
is refused; the four ticked rows become `taste3`, `bel4`, `contra2`, `stance3` (links mapped, risk tag, the presets holding the
personality read list them, the others keep their list) and the built file validates; a pasted proposal that breaks the contract
is refused. The inverse: « Texte depuis la psyché » renders exactly the « Who she is » section of `cof export --format agent`
for `fr-agent`, `default` and `en-12`, and « append » appends it to the card's personality. Also: the date inputs of a psyche
and a memory card sit on one line; the buttons and dialogs in the six languages.
