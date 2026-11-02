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
the 1.0 lists. Needs `python` with cof-cli importable from `cli/`.
