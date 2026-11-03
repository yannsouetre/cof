# Stress files

Generators for the files we test the explorer and the builder with. They are inputs for tests, not examples of good files: labels and gists are random words.

```
python3 tools/stress/gen_memories.py 500 30 out-dir            # 500 moments, 30 periods
python3 tools/stress/gen_memories.py 300 20 out-dir --photos   # a realistic 0.7 MP phone photo on every moment (≈ 340 KB each)
python3 tools/stress/gen_memories.py 5000 60 out-dir --objects 0.3   # objects (RFC 0005 `what`) on about 30 % of the moments
python3 tools/stress/gen_memories.py 5000 60 out-dir --objects 0.3 --base spec/examples/10-clara-mercier   # … some of them Clara's accessories (`item`)
python3 tools/stress/gen_catalog.py 300 200 out-dir            # 300 clothing / accessory variants with a picture, 200 presets
python3 tools/stress/gen_psyche.py 500 stress-500.cof stress-psyche-500.cof   # 500 psyche nodes on top of a memories file (.cof or folder, in and out)
cof pack out-dir -o stress-500.cof
```

Both start from `spec/examples/01-clara-text-only` and write a `cof: "1.1"` manifest; a preset younger than the last memory (the base's are 34) gets the age just after it (`age_override`), since a preset with an age shows nothing after it (`gen_memories.py --base DIR` starts from another folder). Moments get people and places from small pools (a few frequent names, many rare ones), ages with one decimal, and periods that stay valid above 60; link targets are drawn among the earlier moments, so the first ones accumulate incoming links (useful to test the « n memories link here » section of a card).

The three memory files used for the 1.1.1 measurements (100, 500 and 5 000 moments) are attached to the [v1.1.1 release](https://github.com/yannsouetre/cof/releases/tag/v1.1.1); the photo files (18–28 MB) are regenerated on demand.

`--objects SHARE` (0–1) gives that share of the moments one or two objects, the third axis of RFC 0005 beside people and places: names drawn from a pool of ten (« le carnet », « la guitare »… a few frequent, most rare, like people and places) and, when the base file has `accessory` variants, an `item` naming one of them about one time in three (example 01 has none: names only; example 10 brings the guitar, the drone and the bike). The file then declares `cof: "1.2"`. It is the input for the Objects row of the explorer and the builder at 5 000 memories.

`gen_psyche.py N SRC OUT [--life A] [--seed S]` adds N psyche nodes (RFC 0004) to a character — a memories stress file or any other — over a life of A years (default 50); SRC and OUT may each be a `.cof` (unpacked, then packed with `cof pack`) or a folder, and the source must not hold psyche nodes yet. Proportions, rounded to N: values 4 %, beliefs 15 %, wants 10 %, needs 5 %, fears 8 %, wounds 3 %, stances 20 %, tastes 15 %, habits 12 %, contradictions 4 %, rules 4 % (`core`). `since` is spread over the life by kind (values and wounds early, habits later; about 8 % without); about 25 % of the nodes end (`until`), half of those with a successor of the same kind (`derives_from`, starting the year the first one was let go); `aware` partly / no on about 15 %; `valence` on every stance and taste; `because` to a memory not later than the node on about 40 % (every wound), to an earlier node on about 15 % (never a cycle), a few `supports`; `who` / `where` / `what` on about 20 %, drawn from the memories' people, places and objects; stances toward the memories' people (the frequent ones most), a few free subjects and one toward the user; contradictions last, each with exactly two `conflicts` to nodes held together at some age; one or two nodes of risk `inappropriate` (and `tags.content`); labels « FR / EN » and gists in fr and en from templates. A preset `psyche` — the file's default — shows the character at A (`age_override`) with the nodes held at A (since ≤ A < until, a contradiction only with both sides held) and the memories up to A; the nodes that ended before A are in no preset (`cof validate` warns « backstage »: the explorer's time cursor shows them). The output passes `cof validate` without errors.

The three psyche files of the 1.2 measurements: `gen_psyche.py 150` on the 100-memory file (a well-written character: 50–150 nodes), `gen_psyche.py 500` and `gen_psyche.py 1000` on the 500-memory file (an exhaustive life model: 300–600; 1 000 as an upper bound).
