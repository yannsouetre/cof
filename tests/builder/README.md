# Builder round-trip test

Checks that the builder writes back, unchanged, what it does not know: a category added by a later 1.x minor
(its variants with every field, its sub-files, its media assets, its preset slots) and the file's minor version.

```
pip install playwright pillow cof-cli && python -m playwright install chromium
python tests/builder/make_fixture.py /tmp/later.cof
python tests/builder/roundtrip.py builder/index.html /tmp/later.cof /tmp/out.cof
```

The script opens the builder in headless Chromium, loads the file, clicks Build and inspects the download.
