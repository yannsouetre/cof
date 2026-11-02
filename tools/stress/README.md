# Stress files

Generators for the files we test the explorer and the builder with. They are inputs for tests, not examples of good files: labels and gists are random words.

```
python3 tools/stress/gen_memories.py 500 30 out-dir            # 500 moments, 30 periods
python3 tools/stress/gen_memories.py 300 20 out-dir --photos   # a realistic 0.7 MP phone photo on every moment (≈ 340 KB each)
python3 tools/stress/gen_catalog.py 300 200 out-dir            # 300 clothing / accessory variants with a picture, 200 presets
cof pack out-dir -o stress-500.cof
```

Both start from `spec/examples/01-clara-text-only` and write a `cof: "1.1"` manifest. Moments get people and places from small pools (a few frequent names, many rare ones), ages with one decimal, and periods that stay valid above 60; link targets are drawn among the earlier moments, so the first ones accumulate incoming links (useful to test the « n memories link here » section of a card).

The three memory files used for the 1.1.1 measurements (100, 500 and 5 000 moments) are attached to the [v1.1.1 release](https://github.com/yannsouetre/cof/releases/tag/v1.1.1); the photo files (18–28 MB) are regenerated on demand.
