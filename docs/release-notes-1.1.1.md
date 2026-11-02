# COF 1.1.1 — release notes (2 November 2026)

**The memory graph holds a whole life.** A tooling release: no change to the format — a 1.1.1 tool reads and writes exactly the files a 1.1.0 tool does, `cof: "1.1"` stays what a file declares.

▶ [Explore Clara's memories](https://yannsouetre.github.io/cof/viewer/#clara/memories:graph) · [Build one](https://yannsouetre.github.io/cof/builder/) · [Changelog](https://github.com/yannsouetre/cof/blob/main/CHANGELOG.md)

Three days after 1.1.0 we put the memory graph in front of files it had never seen: 100, 500 and 5 000 memories (the order of magnitude of [How much could a life weigh?](https://yannsouetre.github.io/cof/memories/how-much.html)). The one-row time axis became a 17 000-pixel strip, the builder took 53 s to open 500 memories and froze on 5 000. This release is what came out of that week-end.

## Explorer

- **Columns under the periods**: the moments of a period stand under its bubble, oldest first, *k* per column (automatic, or 1 to 30); the moments with no period are grouped by **life stage** when the file dates by age (early childhood, childhood, adolescence, studies and first steps, young adult, adult, later years — seven dashed pills), else by year or decade; an « undated » group last. The graph grows downwards, not sideways.
- **Two views**: the **Network view** draws people and places as nodes with their lines, up to 80 lines (beyond, it is not readable); the **Tags view** shows people and places as tags under the graph — hover a tag, a bubble or a period to reveal its neighbourhood, click tags to keep a selection (several tags: the memories they share), a filter box per row. A **time window** on a density strip (drag, or type from / to; a quick double-click shows the whole life) decides what is drawn; above a rendering budget the tab opens on the list and the graph on the most recent years.
- **A full-screen graph that behaves**: 1:1 by default, the zoom changes only when you ask (one wheel notch = one step of ×1.25 whatever the browser reports — Edge animates a notch as twenty small events), scroll bars, a draggable bar between the graph and the tags, a « ? Commands » dialog with every gesture, a three-second notice when the view switches by itself.
- **Pictures in the bubbles** drawn from 128 px copies, after the graph, eight at a time: 300 moments with a phone photo each open in under a second.
- **Memory card**: one link per line, and a folded « n memories link here » section — the links other memories declare towards this one (the graph draws them; the file keeps a link only where it is declared).
- **Pages** of 5 to 50 cards in every list (remembered), the memories list opens folded, **six languages** like the builder (German, Spanish, Chinese, Japanese join English and French), header in the builder's order.

## Builder 0.13.1

- **Pages of 50 cards** in Elements, Presets and Memories (filter first, page kept across in-place edits, a new card opens on its page); subsections of a preset card paged by 20 with a filter box.
- **A preset's memories by period**: « Periods only » (on by default) lists the periods and the life-stage groups of the loose moments — one click ticks or unticks a period with all its moments (✓ all, ◐ some, ○ none); turn it off to choose moment by moment. The file is written as before (a ticked period stands for its `part-of` moments).
- **Large files open in seconds**: 500 memories went from 53 s to 3 s, 5 000 from 25 s to 3 s; the Memories step no longer builds half a million `<option>` per visit (the two per-card selects that listed every memory are filled on first use); the checks index children once instead of rescanning 5 000 memories for each of them.
- Green « Open a .cof », a salience note under every memory's slider, pages of 5–50 by a slider.

## `cof-cli` 1.1.1

- `cof validate`: **tool limits, not format limits** — an INFO line from 5 000 memories (the reference tools are tuned for that order of magnitude), a WARN line from 20 000; INFO lines are printed (`info.notes` in `--json`).
- `tools/stress/gen_memories.py` (N moments, P periods, `--photos` for a realistic phone photo on every moment) and `tools/stress/gen_catalog.py` (N appearance variants, P presets) generate the files we tested with; the three memory files (100, 500, 5 000) are attached to this release for anyone who wants to try.

## Measured (Chromium, a laptop)

5 000 memories: explorer from tab click to graph 1.1 s (was 32 s), a zoom notch 65 ms (was 5–10 s); builder open 3 s (was 25 s), Memories step 0.6 s (was 6.5 s and a dead tab after three visits). 300 moments with photos: graph in 0.6 s, every picture in 2 s.

## Next

1.2 — the psyche as a graph (RFC 0004); the memory graph gets semantic zoom levels and folding periods; a date axis for characters without an age, with coherence checks between ages and dates. The roadmap is in `docs/roadmap.md`.

ComfyUI-COF stays at 0.6.0 (unchanged by this release).
