#!/usr/bin/env node
/* Builder — Clara with thousands of memories opens in seconds (the 1.1.1 rule: index once, each step costs what it shows).
   Usage: node tests/builder/perf_test.js [repo-root] [work-dir] [N]   (N extra memories, default 1000; 5000 is the demonstration size)
   Needs: playwright (npm i playwright && npx playwright install chromium), python with cof-cli importable from <root>/cli.
   Builds a copy of example 10 (Clara: 12 presets with ages, 23 psyche nodes, memories with photos) plus N generated memories
   (tools/stress/gen_memories.py --base, 60 periods, objects on 30 %), each preset with an own list getting the memories up to its age,
   packs it, opens it in headless Chromium and checks two things:
   - call counts during the open, which do not depend on the machine: a preset is expanded (memHeld) a few times per preset, not once
     per element card × memory photo × preset (the bug: Clara + 5 000 memories never opened), and its age (presetAge) a few times per
     preset, not once per memory;
   - times, with a generous ceiling (COF_PERF_SLACK multiplies them, default 1): open < 5 s, Presets step < 500 ms, Memories and Psyché
     steps < 1 s, checks < 2 s.
   The generation takes about 10 s for 1 000 memories and a few minutes for 5 000 (the generator rewrites the manifest per memory).
   Exit code 1 on any failure. */
const fs = require("fs"), path = require("path"), http = require("http"), { spawnSync } = require("child_process");
const { chromium } = require("playwright");
const ROOT = path.resolve(process.argv[2] || path.join(__dirname, "..", ".."));
const WORK = path.resolve(process.argv[3] || fs.mkdtempSync(path.join(require("os").tmpdir(), "cof-perf-")));
const N = +(process.argv[4] || 1000), SLACK = +(process.env.COF_PERF_SLACK || 1);
fs.mkdirSync(WORK, { recursive: true });
let ok = true;
const check = (cond, msg) => { console.log((cond ? "ok   " : "FAIL ") + msg); ok = ok && !!cond; };
const py = (args, cwd) => spawnSync(process.env.PYTHON || "python", args, { encoding: "utf8", cwd, env: { ...process.env, PYTHONPATH: path.join(ROOT, "cli") } });
const EX = path.join(ROOT, "spec", "examples", "10-clara-mercier");

/* the file: example 10 + N memories, realistic preset lists (the 12-year-old presets list what came by 12, the 65-year-old ones everything) */
const src = path.join(WORK, `clara-${N}`), cof = path.join(WORK, `clara-${N}.cof`);
{
  const g = py([path.join(ROOT, "tools", "stress", "gen_memories.py"), String(N), "60", src, "--objects", "0.3", "--base", EX], ROOT);
  if (g.status !== 0) throw new Error("generation failed: " + g.stdout + g.stderr);
  const mf = path.join(src, "manifest.json"), m = JSON.parse(fs.readFileSync(mf, "utf8"));
  const base = JSON.parse(fs.readFileSync(path.join(EX, "manifest.json"), "utf8"));
  const ages = [];
  for (const [vid, v] of Object.entries(m.elements.memories.variants)) {
    if (base.elements.memories.variants[vid]) continue;
    const n = JSON.parse(fs.readFileSync(path.join(src, v.memory), "utf8")), w = n.when || {};
    ages.push([vid, ((w.from || w).age || {}).value]);
  }
  for (const [pid, p] of Object.entries(m.presets)) {   /* the generator adds every memory to every preset: back to example 10's lists, then by age */
    const own = base.presets[pid].slots.memories;
    if (!Array.isArray(own)) { if ("memories" in base.presets[pid].slots) p.slots.memories = own; else delete p.slots.memories; continue; }
    const age = (p.age_override || {}).value ?? 29;
    p.slots.memories = [...own, ...ages.filter(([, a]) => typeof a === "number" && a <= age).map(([v]) => v)];
  }
  fs.writeFileSync(mf, JSON.stringify(m, null, 2) + "\n");
  const r = py(["-m", "cof_cli.cli", "pack", src, "-o", cof], ROOT);
  if (r.status !== 0) throw new Error("pack failed: " + r.stdout + r.stderr);
  console.log(`file: Clara + ${N} memories, ${Object.keys(m.presets).length} presets`);
}

const server = http.createServer((q, s) => { let f = path.join(ROOT, decodeURIComponent(q.url.split("?")[0])); try { if (fs.statSync(f).isDirectory()) f = path.join(f, "index.html"); } catch (e) {} fs.readFile(f, (e, d) => { if (e) { s.writeHead(404); return s.end(); } s.writeHead(200, { "content-type": f.endsWith(".html") ? "text/html; charset=utf-8" : "application/octet-stream" }); s.end(d); }); });
(async () => {
  await new Promise(r => server.listen(0, r));
  const browser = await chromium.launch(); const page = await browser.newPage({ viewport: { width: 1400, height: 900 } });
  const errors = []; page.on("pageerror", e => errors.push(e.message)); page.on("dialog", d => d.accept().catch(() => {}));
  await page.goto(`http://localhost:${server.address().port}/builder/`); await page.evaluate(() => setMode("advanced"));
  /* call counters on two top-level functions (a function declaration is a global binding: the builder's own calls go through the wrapper) */
  await page.evaluate(() => { window.__calls = {}; for (const n of ["memHeld", "presetAge"]) { const f = window[n]; window.__calls[n] = 0; window[n] = function () { window.__calls[n]++; return f.apply(this, arguments); }; } });
  const t0 = Date.now(); await page.setInputFiles("#fileOpen", cof);
  await page.waitForFunction(() => S.loadedManifest && !document.getElementById("busy").classList.contains("on"), null, { timeout: 600000, polling: 100 });
  const open = Date.now() - t0;
  const calls = await page.evaluate(() => ({ ...window.__calls, presets: Object.keys(S.presets).length, memories: Object.keys(S.memories).length }));
  const step = s => page.evaluate(s => { const t = performance.now(); if (s === "runChecks") runChecks(); else go(s); return Math.round(performance.now() - t); }, s);
  const T = {}; for (const s of ["memories", "psyche", "presets", "build", "runChecks"]) T[s] = await step(s);
  console.log(`open ${open} ms · steps ${JSON.stringify(T)} · calls during the open ${JSON.stringify(calls)}`);
  check(calls.memories >= N, `${calls.memories} memories loaded`);
  check(calls.memHeld <= 4 * calls.presets, `each preset expanded a few times during the open, not per card × photo × preset (memHeld × ${calls.memHeld}, ${calls.presets} presets)`);
  check(calls.presetAge <= 40 * calls.presets, `each preset's age asked a few times, not per memory (presetAge × ${calls.presetAge})`);
  check(open < 5000 * SLACK, `opens in under ${5 * SLACK} s (${open} ms)`);
  check(T.presets < 500 * SLACK, `Presets step under ${500 * SLACK} ms (${T.presets})`);
  check(T.memories < 1000 * SLACK && T.psyche < 1000 * SLACK, `Memories and Psyché steps under ${SLACK} s (${T.memories}, ${T.psyche})`);
  check(T.runChecks < 2000 * SLACK, `checks under ${2 * SLACK} s (${T.runChecks} ms)`);
  check(T.build < 1000 * SLACK, `Build step under ${SLACK} s (${T.build} ms)`);
  check(!errors.length, "no page errors" + (errors.length ? ": " + errors.join(" | ") : ""));
  await browser.close(); server.close();
  console.log(ok ? "ALL OK" : "FAILURES"); process.exit(ok ? 0 : 1);
})().catch(e => { console.error(e); process.exit(1); });
