# The memories graph at scale — measurement campaign (31 October 2026)

**What was measured**: the explorer's memories graph (`viewer/index.html`) before and after the 1.1.1 layout (columns under periods, virtual periods by year, time window on a density strip, complete / optimized view under a rendering budget, reveal on hover). Design: the note « graphe des souvenirs à grande échelle » of 31 October, §§ 1, 2, 4, 5, 7.

**Method**: stress files from `tools/stress/gen_memories.py N P` (N moments, P periods, 0–3 links per moment, people and places drawn from small pools with a few frequent names and many rare ones, no media), packed with `cof pack`. The explorer is served by `python -m http.server` and driven by Playwright 1.63 (headless Chromium 153, Linux container, **software rendering, no GPU**), viewport 1300 × 900, English, light theme. Times are wall-clock from the test script; layout and DOM times come from the explorer's own `window.__cofGraph` (layout = JavaScript passes; DOM = `innerHTML`, style, SVG layout up to `getBBox()`). A **zoom step** is one wheel notch in full screen, timed from the event to the second animation frame after it (the floor of this measure is about 60 ms, two frames of the headless compositor); the sweep tables give the median of seven alternating in / out notches at the fitted zoom. Heap = `JSHeapUsedSize` from the DevTools protocol. A headless software renderer is slower than a laptop with a GPU: read the times as an upper bound, the ratios as the result. The stress files are not committed (`*.cof` is ignored outside the examples and samples); regenerate them with the script.

## 1. Before (one row on the time axis, every link and person drawn)

| File (moments + periods) | Tab → graph | SVG elements | Width | Zoom step (median of 5) |
|---|---:|---:|---:|---:|
| 100 + 10 | 0.6 s | 1 147 | 17 100 px | 174 ms |
| 500 + 30 | 0.7 s | 5 289 | 85 100 px | 530 ms |
| 2 000 + 100 | 4.8 s | 23 102 | 340 100 px | 3.2 s |
| 5 000 + 250 | 31.8 s | 57 930 | 850 100 px | 6.8 s |

Of the 31.8 s at 5 000, about 18 s were not drawing at all: `gistLang` resolved every slot of the preset once per memory (quadratic). Fixed in 1.1.1, with the other whole-list rescans (timeline sort, parents' sort, periods of the list, nudity set).

## 2. After (1.1.1 defaults: budget 1 500, k auto, default window)

| File | Opens on | Tab → graph¹ | View drawn | Window | Drawn / total | SVG elements (est.) | Width | Layout + DOM | Zoom step² | Heap |
|---|---|---:|---|---|---:|---:|---:|---:|---:|---:|
| Clara at 65 (9) | graph | — | complete | whole life | 9 / 9 | 152 (110³) | 1 434 px | 2 + 10 ms | — | — |
| 100 + 10 | graph | 0.26 s | complete | whole life | 110 / 110 | 1 028 (999) | 5 382 px | 11 + 45 ms | 92 ms | 4.3 MB |
| 100 + 10, optimized | — | — | optimized | whole life | 110 / 110 | 621 (580) | 5 382 px | 5 + 20 ms | 70 ms | 4.8 MB |
| 500 + 30 | list | 0.28 s | optimized (forced) | ages 35–62 | 259 / 530 | 1 413 (1 337) | 9 524 px | 25 + 57 ms | 81 ms | 4.2 MB |
| 2 000 + 100 | list | 0.59 s | optimized (forced) | ages 55–62 | 269 / 2 100 | 1 393 (1 387) | 7 866 px | 59 + 53 ms | 64 ms | 9.5 MB |
| 5 000 + 250 | list | 1.1 s | optimized (forced) | ages 60–62 | 269 / 5 250 | 1 390 (1 384) | 7 694 px | 107 + 61 ms | 65 ms | 20 MB |
| 5 000 + 250, « Whole life » | — | +1.1 s | optimized (forced) | whole life | 5 250 / 5 250 | 27 006 (27 000) | 129 758 px | 181 + 451 ms | 574 ms | 25.5 MB |

¹ From the click on the Memories tab with the graph chosen (opening the file itself: 0.14–0.25 s; node files read in batches of 256). Above the budget the tab opens on the **list** by default, which costs 0.5 s at 500, 1.1 s at 2 000 and **3.9 s at 5 000** (5 250 cards rendered — see § 5).
² Median of seven alternating notches at the fitted zoom (sweep method); the five-notches-in method of § 1 gives 130–190 ms for the complete 100 file (the zoomed-in SVG paints more area).
³ Clara's estimate leaves out the thumbnails' clip paths of the linked elements and the frames; it only has to be right where the budget bites.

The page stayed free of errors in every run (`pageerror` listened to). The 5 000 file opens in optimized view with a time window in about 1.4 s from the file input (0.24 s to read the archive, 1.1 s to the drawn graph) and stays responsive (zoom notch 55–75 ms).

## 3. Sweeps — zoom cost against what is drawn

Complete view, 500 + 30 file, windows of 2 to 60 years starting at age 3 (`?budget=1000000` so the complete view is never forced):

| Window | Drawn | Elements | Est. | Layout + DOM | Zoom step (median / max) |
|---|---:|---:|---:|---:|---:|
| 2 y | 23 | 272 | 264 | 5 + 9 ms | 65 / 81 ms |
| 6 y | 53 | 547 | 531 | 3 + 13 ms | 64 / 70 ms |
| 10 y | 84 | 818 | 794 | 4 + 12 ms | 67 / 78 ms |
| 15 y | 125 | 1 206 | 1 175 | 4 + 19 ms | 80 / 82 ms |
| 20 y | 165 | 1 596 | 1 552 | 16 + 36 ms | 98 / 111 ms |
| 30 y | 252 | 2 402 | 2 338 | 14 + 36 ms | 131 / 145 ms |
| 60 y | 530 | 4 937 | 4 813 | 11 + 66 ms | 203 / 241 ms |

Optimized view, same file, and 5 000 + 250 file:

| File, window | Drawn | Elements | Layout + DOM | Zoom step (median / max) |
|---|---:|---:|---:|---:|
| 500, 10 y | 84 | 466 | 5 + 17 ms | 64 / 65 ms |
| 500, 30 y | 252 | 1 386 | 9 + 39 ms | 65 / 81 ms |
| 500, 60 y | 530 | 2 896 | 24 + 78 ms | 80 / 92 ms |
| 5 000, 3 y | 249 | 1 290 | 184 + 55 ms | 86 / 98 ms |
| 5 000, 6 y | 498 | 2 571 | 274 + 76 ms | 114 / 144 ms |
| 5 000, 12 y | 1 052 | 5 416 | 116 + 144 ms | 147 / 369 ms |
| 5 000, 24 y | 2 116 | 10 886 | 207 + 316 ms | 259 / 537 ms |
| 5 000, 60 y | 5 250 | 27 006 | 320 + 1 899 ms | 574 / 1 093 ms |

The estimate the explorer uses (5 per bubble, +2 with a thumbnail, 2 per link, 4–5 per person or element plus one line per memory) is within 3 % of the elements counted after drawing. At 5 000 memories, about 100–270 ms of « layout » are passes over the whole file (budget estimate, default window, hubs), not drawing: they do not grow with the window.

## 4. Thresholds derived

| Threshold | Value | Why |
|---|---|---|
| Rendering budget (complete view allowed, default window size) | **1 500 SVG elements** (kept) | Complete view: zoom notch < 100 ms up to ≈ 1 600 elements, 131 ms at 2 400, 203 ms at 4 900. Optimized view (no long hub lines): < 100 ms up to ≈ 2 900 elements on the 500 file, ≈ 1 300–2 500 on the 5 000 file (a larger page: its chip row lists 118 people). 1 500 is the largest round value under the complete-view knee. |
| Slow device | first drawing > **150 ms** → budget halved to **750** | Drawing time (markup + DOM + SVG layout) of the first graph of the session; measured here: 6–75 ms on budget-sized drawings, so a device three times slower than this headless renderer still keeps 1 500. The passes over the whole file are left out of the timing (they measure the file, not the device: 95–107 ms on the 5 000 file, which halved the budget on this machine in a first version of the timing). |
| In memories (stress files, links and people as generated) | complete view up to **≈ 150 memories**; optimized view's default window ≈ **250–270 memories** | ≈ 9.5 elements per memory in complete view, ≈ 5.2 in optimized view. Clara (16 memories, 5–9 per preset) is far below. |
| Default window at 5 000 memories over 60 years | **the last 3 years** (269 memories, 1 390 elements) | The most recent years whose optimized drawing fits the budget, grown backwards from the last memory. |
| List by default | when the **whole file**'s complete view exceeds the budget | 500 + 30 is above (4 813), 100 + 10 below (999). |
| « Whole life » at 5 000 | allowed, not responsive (27 006 elements, zoom 0.6–1.1 s) | Left to the reader's choice; the virtualized rendering of 1.1.2 (design note § 2 B) is what makes it fluid. |

**For Yann to decide — readability is a stricter criterion than responsiveness.** The 100 + 10 stress file fits the budget (999 elements) and opens in complete view, which responds well but is a tangle: about 140 links and six people linked to 13–44 memories each, across 5 400 px. The design note's hypothesis (« ≈ 60 memories in complete view ») matches a budget of about 600–800 elements, not 1 500. Two ways: lower the default budget to ≈ 700 (the 100 file would open optimized, Clara is unaffected — 152 elements at most), or keep 1 500 for responsiveness and accept that a dense hundred-memory file opens complete with its toggle one click away. This branch keeps 1 500 as specified; the value is one constant (`GBUDGET`).

## 5. Not covered here

- **The list at 5 000** (3.9 s, 5 250 cards) is now the default view above the budget; its pagination (50 per page, note § 7.8) is a separate 1.1.1 item. Until it lands, a very large file opens slower on the list than on the graph.
- **Firefox** and a real GPU: not available in this environment. The design note asks for both; the same scripts run unchanged with `firefox.launch()` where it is installed.
- **Thumbnails**: the stress files have no media. A bubble with a thumbnail costs two more elements and an image decode; the budget counts the elements, not the decode.
- **Builder embed**: tested by posting the file's entries to the explorer the way the builder does (`cof-embed-open` → `cof-embed-shown`, preset selector, Escape → `cof-embed-close`), not through the builder's own button.

## 6. Screenshots (not committed)

Taken with the same scripts at 1300 × 900: Clara at 65 and Clara's « future » preset before and after (same viewport), Clara in French and dark theme with a reveal, the 100 + 10 file in complete view and in optimized view with a reveal on a person and on a memory, the 5 000 + 250 file with its density strip and default window, a brushed window and a reveal, a date-based file (axis in years, « undated » bin) and a file with no period (virtual years and decades).
