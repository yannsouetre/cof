#!/usr/bin/env node
/* Builder — a preset's age stops its memories and its psyche (Yann, 3 November), end to end in headless Chromium.
   Usage: node tests/builder/age_test.js [repo-root] [work-dir]
   Needs: playwright (npm i playwright && npx playwright install chromium), python with cof-cli importable from <root>/cli.
   On example 10 (Clara: presets at 12, 29 and 65; bel4 since ~45, bel3 and contra1 until ~45): what the Memories and Psyché
   subsections of a preset card offer at 12, 29 and 65 (moment by moment and periods only), the count line and « afficher quand même »;
   the pop-up when the age field changes (« Garder » keeps everything and the checks report it; « Désélectionner » removes the items);
   an inherited list struck through with « retirer pour ce preset »; the file built without edits keeps every preset's lists. Then on a
   copy with a moment after its period's end (ev5 part-of ep2, listed by en-futur, not by fr-futur) and two date-only moments: the
   loaded lists are written back unchanged (a ticked period no longer drags a later moment into a younger preset), a period ticked at
   29 brings only its moments lived by 29, a date-only memory is placed through the implied birth year. The six languages.
   Exit code 1 on any failure. */
const fs = require("fs"), path = require("path"), http = require("http"), { spawnSync } = require("child_process");
const { chromium } = require("playwright");
const ROOT = path.resolve(process.argv[2] || path.join(__dirname, "..", ".."));
const WORK = path.resolve(process.argv[3] || fs.mkdtempSync(path.join(require("os").tmpdir(), "cof-age-")));
fs.mkdirSync(WORK, { recursive: true });
let ok = true;
const check = (cond, msg) => { console.log((cond ? "ok   " : "FAIL ") + msg); ok = ok && !!cond; };
const py = (args, cwd) => spawnSync(process.env.PYTHON || "python", args, { encoding: "utf8", cwd });
const CLI = path.join(ROOT, "cli");
/* a copy of example 10, patched by `patch(src, manifest)`, packed into `out` */
function pack(out, patch) {
  const src = path.join(WORK, "src-" + path.basename(out, ".cof"));
  fs.rmSync(src, { recursive: true, force: true });
  fs.cpSync(path.join(ROOT, "spec", "examples", "10-clara-mercier"), src, { recursive: true });   /* cof pack rewrites the manifest it packs: never the repo's copy */
  if (patch) { const mf = path.join(src, "manifest.json"); const m = JSON.parse(fs.readFileSync(mf, "utf8")); patch(src, m); fs.writeFileSync(mf, JSON.stringify(m, null, 2) + "\n"); }
  const r = py(["-m", "cof_cli.cli", "pack", src, "-o", out, "--force"], CLI);
  if (r.status !== 0) throw new Error("pack failed: " + r.stdout + r.stderr);
}
const readMan = file => { const r = py(["-c", "import json,sys,zipfile;print(json.dumps(json.loads(zipfile.ZipFile(sys.argv[1]).read('manifest.json'))))", file]); if (r.status !== 0) throw new Error(r.stderr); return JSON.parse(r.stdout); };
/* a preset's effective list: its own, else its nearest ancestor's (the builder writes a list equal to its parent's as inherited) */
const lists = (m, slot) => Object.fromEntries(Object.keys(m.presets).map(p => { let q = p; const seen = new Set(); while (q && m.presets[q] && !seen.has(q)) { seen.add(q); const l = m.presets[q].slots?.[slot]; if (l) return [p, JSON.stringify(l)]; q = m.presets[q].extends; } return [p, "null"]; }));
const sameLists = (a, b) => Object.keys(a).every(p => a[p] === b[p]) && Object.keys(a).length === Object.keys(b).length;
const diffLists = (a, b) => Object.keys({ ...a, ...b }).filter(p => a[p] !== b[p]).map(p => `${p}: ${a[p]} → ${b[p]}`).join("; ");
/* RFC 0002 memories added to the copy: a moment after its period (ev5 part-of ep2 at 31 — the « moment hors de la période » finding),
   two moments with a date only (Clara is 29 in March 2026: born 1997) */
function patchLate(src, m) {
  const V = m.elements.memories.variants;
  const node = f => path.join(src, f);
  const ev5 = JSON.parse(fs.readFileSync(node(V.ev5.memory), "utf8")); ev5.links = [...(ev5.links || []), { to: "memories/ep2", type: "part-of" }]; fs.writeFileSync(node(V.ev5.memory), JSON.stringify(ev5, null, 2) + "\n");
  for (const [vid, date, fr] of [["ev15", "2027-06", "un été à Marseille"], ["ev16", "2036-04", "le déménagement"]]) {
    fs.mkdirSync(node(`elements/memories/${vid}`), { recursive: true });
    fs.writeFileSync(node(`elements/memories/${vid}/memory.json`), JSON.stringify({ gist: { fr: fr + ".", en: fr + "." }, nature: ["experienced"], when: { date }, fidelity: "clear", origin: "authored", visibility: "canon", disclosure: "open" }, null, 2) + "\n");
    V[vid] = { kind: "moment", label: fr, memory: `elements/memories/${vid}/memory.json` };
  }
  m.presets["en-futur" in m.presets ? "en-futur" : "en-future"].slots.memories.push("ev5");
}
const mime = { ".html": "text/html; charset=utf-8", ".js": "text/javascript", ".json": "application/json", ".css": "text/css", ".svg": "image/svg+xml", ".png": "image/png" };
const server = http.createServer((q, s) => { let f = path.join(ROOT, decodeURIComponent(q.url.split("?")[0])); if (!f.startsWith(ROOT)) { s.writeHead(403); return s.end(); } try { if (fs.statSync(f).isDirectory()) f = path.join(f, "index.html"); } catch (e) {} fs.readFile(f, (e, d) => { if (e) { s.writeHead(404); return s.end(); } s.writeHead(200, { "content-type": mime[path.extname(f)] || "application/octet-stream" }); s.end(d); }); });

(async () => {
  const clara = path.join(WORK, "clara.cof"), late = path.join(WORK, "clara-late.cof");
  pack(clara); pack(late, patchLate);
  const srcMan = readMan(clara), lateMan = readMan(late);
  await new Promise(r => server.listen(0, r)); const URL = `http://localhost:${server.address().port}/builder/`;
  const browser = await chromium.launch();
  const ctx = await browser.newContext({ viewport: { width: 1400, height: 900 }, acceptDownloads: true });
  const page = await ctx.newPage(); const errors = [];
  page.on("pageerror", e => errors.push(e.message)); page.on("dialog", d => d.accept().catch(() => {}));
  await page.addInitScript(() => { window.__dl = []; const oc = URL.createObjectURL.bind(URL); URL.createObjectURL = b => { window.__dl.push(b); return oc(b); }; HTMLAnchorElement.prototype.click = function () {}; });
  const open = async file => { await page.evaluate(() => { window.__prev = S.loadedManifest; }); await page.setInputFiles("#fileOpen", file); await page.waitForFunction(() => S.loadedManifest !== window.__prev && !document.getElementById("busy").classList.contains("on"), null, { timeout: 120000 }); await page.waitForTimeout(400); };
  const build = async out => { await page.evaluate(() => { window.__dl.length = 0; go("build"); }); await page.click("#btnBuild"); await page.waitForFunction(() => window.__dl.some(b => b.type === "application/vnd.cof.character+zip"), null, { timeout: 90000 }); const b64 = await page.evaluate(async () => { const b = window.__dl.filter(x => x.type === "application/vnd.cof.character+zip").pop(); const u = new Uint8Array(await b.arrayBuffer()); let s = ""; for (let i = 0; i < u.length; i += 32768) s += String.fromCharCode.apply(null, u.subarray(i, i + 32768)); return btoa(s); }); fs.writeFileSync(out, Buffer.from(b64, "base64")); return readMan(out); };
  const checks = async re => { await page.evaluate(() => go("checks")); await page.click("#btnRunChecks"); await page.waitForTimeout(300); return (await page.evaluate(() => document.querySelector("#issueList").innerText)).split("\n").filter(l => re.test(l)); };
  const presets = async (perOnly = false, show = false) => { await page.evaluate(([p, s]) => { S._memPerOnly = p; S._ageShow = s; go("presets"); }, [perOnly, show]); await page.waitForTimeout(150); };
  const card = pid => `#presetList .variant[data-pid="${pid}"]`;
  /* the chips of a card's subsection: id (a moment or a period; a group « ~gid »), state, late, greyed, the tag after it */
  const chips = (pid, fs) => page.evaluate(([c, fs]) => [...document.querySelectorAll(`${c} [${fs}] ${fs === "data-memfs" ? "[data-mrow]" : "[data-prow]"}`)].map(b => ({ id: b.dataset.mslot || b.dataset.prow, kind: b.dataset.mrow ? b.dataset.mrow[0] : "n", st: b.dataset.state, late: b.classList.contains("late"), off: b.disabled, tag: b.nextElementSibling?.classList.contains("latetag") ? b.nextElementSibling.textContent : "" })), [card(pid), fs]);
  const ids = (L, f = () => true) => [...new Set(L.filter(f).map(x => x.id))].sort();
  /* what a subsection offers, from its lines (all pages): memories « m:ev1:… » / « p:ep1 » / « g:s1 », psyche node ids */
  const offered = (pid, cat) => page.evaluate(([p, c]) => subLines(p, c).map(([k]) => { const [a, b] = k.split(":"); return c === "psyche" ? { id: k, kind: "n" } : { id: a === "g" ? "~" + b : b, kind: a }; }), [pid, cat]);
  /* the chips of one page, narrowed by the subsection's filter box */
  const narrow = async (pid, cat, q) => { await page.evaluate(([p, c, q]) => { S._q[subKey(p, c)] = q; renderPresets(); }, [pid, cat, q]); await page.waitForTimeout(100); };
  const line = (pid, fs) => page.evaluate(([c, fs]) => document.querySelector(`${c} [${fs}] .agecut`)?.firstChild?.textContent.trim() || "", [card(pid), fs]);
  const setAge = async (pid, v) => { await page.evaluate(([c, v]) => { const el = document.querySelector(c + ' [data-pk="age_override"]'); el.value = v; el.dispatchEvent(new Event("input", { bubbles: true })); el.dispatchEvent(new Event("change", { bubbles: true })); }, [card(pid), String(v)]); await page.waitForTimeout(200); };
  const popup = () => page.evaluate(() => { const D = document.querySelector("#dlg"); if (!D.classList.contains("on") || !D.querySelector("[data-agepop]")) return null; return { head: D.querySelector("[data-agepop] p").textContent, lines: [...D.querySelectorAll(".agelist li")].map(l => l.textContent), btns: [...D.querySelectorAll(".dbtns button")].map(b => b.textContent), title: D.querySelector("h3").textContent }; });
  const press = label => page.evaluate(l => [...document.querySelectorAll("#dlg .dbtns button")].find(b => b.textContent === l).click(), label).then(() => page.waitForTimeout(250));
  const memList = pid => page.evaluate(p => ({ ...memPresetList(p), held: memHeld(p) }), pid);
  const psyList = pid => page.evaluate(p => psyPresetList(p), pid);

  await page.goto(URL, { waitUntil: "load" }); await page.evaluate(() => setMode("advanced"));
  await open(clara);

  /* ---- what is offered at 29, 12 and 65 (moment by moment) ---- */
  await presets(false);
  let M = await offered("default", "memories"), N = await offered("default", "psyche");
  check(JSON.stringify(ids(M, x => x.kind === "m")) === JSON.stringify(["ev1", "ev10", "ev11", "ev12", "ev13", "ev14", "ev2", "ev3", "ev4", "ev9"]) && !M.some(x => x.late), "default (29): the moments up to 29 are offered, ev5–ev8 (31–63) are not: " + ids(M, x => x.kind === "m").join(","));
  check(ids(M, x => x.kind === "p").join() === "ep1,ep2", "default (29): both periods offered (begun at 24 and 27)");
  check(await line("default", "data-memfs") === "4 souvenir(s) après 29 ans non proposé(s)", "default: « 4 souvenir(s) après 29 ans non proposé(s) »");
  check(!ids(N).includes("bel4") && ids(N).includes("bel3") && ids(N).includes("contra1") && ids(N).length === 22, "default (29): bel4 (since ~45) not offered; bel3, contra1 (until ~45) offered; 22 of 23 nodes");
  check(await line("default", "data-psyfs") === "1 nœud(s) non tenu(s) à 29 ans non proposé(s)", "default: « 1 nœud(s) non tenu(s) à 29 ans non proposé(s) »");
  for (const pid of ["en-12", "fr-12"]) {
    M = await offered(pid, "memories"); N = await offered(pid, "psyche");
    check(ids(M, x => x.kind !== "g").join() === "ev1,ev11" && (await chips(pid, "data-memfs")).find(x => x.id === "ev1").st === "def", `${pid} (12): only ev1 and ev11 (8) offered, ev1 ticked: ${ids(M).join()}`);
    check(await line(pid, "data-memfs") === "14 souvenir(s) après 12 ans non proposé(s)", `${pid}: « 14 souvenir(s) après 12 ans non proposé(s) »`);
    check(ids(N).join() === "bel2,fear2,fear3,hab1,hab2,need1,taste1,taste2,val2,val3,val4,want3" && ids(await chips(pid, "data-psyfs"), x => x.st === "def").join() === "hab2,taste1,val4", `${pid} (12): the 12 nodes held at 12 offered (contra1 holds from 28 since 3 Nov. evening), its three ticked`);
  }
  for (const pid of ["en-65", "fr-65"]) {
    M = await offered(pid, "memories"); N = await offered(pid, "psyche");
    check(ids(M, x => x.kind !== "g").length === 16 && !(await line(pid, "data-memfs")), `${pid} (65): all 16 memories offered, no line`);
    check(!ids(N).includes("bel3") && !ids(N).includes("contra1") && ids(N).includes("bel4") && ids(N).length === 21, `${pid} (65): bel3, contra1 (until ~45) not offered, bel4 offered`);
    check(await line(pid, "data-psyfs") === "2 nœud(s) non tenu(s) à 65 ans non proposé(s)", `${pid}: « 2 nœud(s) non tenu(s) à 65 ans non proposé(s) »`);
  }
  /* periods only: at 12 neither period nor a group of later moments */
  await presets(true);
  M = await chips("en-12", "data-memfs");
  check(!M.some(x => x.kind === "p") && M.every(x => x.kind === "g") && M.length >= 1 && !M.some(x => x.late) && ids(await offered("en-12", "memories")).join() === ids(M).join(), "en-12, periods only: no period (24, 27), only the groups that hold moments lived by 12: " + ids(M).join());
  M = await offered("default", "memories");
  check(ids(M, x => x.kind === "p").join() === "ep1,ep2" && !(await chips("default", "data-memfs")).some(x => x.late), "default, periods only: ep1, ep2 and the groups, none late");
  /* « afficher quand même »: greyed, not tickable */
  await presets(false, true); await narrow("default", "memories", "ev");
  M = await chips("default", "data-memfs");
  const ev5 = M.find(x => x.id === "ev5");
  check(ev5 && ev5.late && ev5.off && ["ev5", "ev6", "ev7", "ev8"].every(v => M.find(x => x.id === v)?.off), "« afficher quand même »: ev5–ev8 shown greyed and disabled");
  check(await page.evaluate(c => document.querySelector(c + " [data-memfs] [data-ageshow]").getAttribute("aria-pressed"), card("default")) === "true", "the toggle reads pressed");
  await page.evaluate(c => document.querySelector(c + ' [data-memfs] [data-mslot="ev5"]').click(), card("default")); await page.waitForTimeout(100);
  check(!(await memList("default")).held.includes("ev5"), "a click on a greyed chip ticks nothing");
  await narrow("default", "psyche", "bel");
  N = await chips("default", "data-psyfs");
  check(N.find(x => x.id === "bel4")?.off === true, "« afficher quand même »: bel4 greyed in the Psyché subsection");
  await page.evaluate(c => document.querySelector(c + " [data-memfs] [data-ageshow]").click(), card("default")); await page.waitForTimeout(150);
  check(!(await offered("default", "memories")).some(x => x.id === "ev5") && !(await chips("default", "data-memfs")).some(x => x.id === "ev5"), "toggled off: ev5 hidden again");
  await narrow("default", "memories", ""); await narrow("default", "psyche", "");

  /* ---- the pop-up on an age change: « Garder » ---- */
  await presets(false);
  const before = { m: await memList("default"), p: await psyList("default") };
  await setAge("default", 12);
  let pop = await popup();
  check(pop && pop.head === "Ce preset a 12 ans, mais il retient 4 souvenirs et 10 nœuds incompatibles avec cet âge :", "age 12 on default: « Ce preset a 12 ans, mais il retient 4 souvenirs et 10 nœuds incompatibles avec cet âge : » — " + (pop && pop.head));
  check(pop && pop.lines.length === 9 && pop.lines[8] === "et 6 autres" && /^🕰️ .*ep1 · 24 ans$/.test(pop.lines[0]) && pop.lines.some(l => /^🧠 .*wound1 · depuis 24 ans$/.test(l)), "eight lines then « et 6 autres »; « ep1 · 24 ans », « wound1 · depuis 24 ans »");
  check(pop && pop.btns.join("|") === "Garder — je corrige l'âge|Désélectionner ces éléments", "two buttons: « Garder — je corrige l'âge », « Désélectionner ces éléments »");
  await press("Garder — je corrige l'âge");
  const afterKeep = { m: await memList("default"), p: await psyList("default") };
  check(JSON.stringify(afterKeep.m.list) === JSON.stringify(before.m.list) && JSON.stringify(afterKeep.p.list) === JSON.stringify(before.p.list) && await page.evaluate(() => S.presets.default.age_override) === 12, "« Garder »: the lists are unchanged, the age stays 12");
  await narrow("default", "memories", "ev4");
  M = await chips("default", "data-memfs"); await narrow("default", "memories", "");
  check(M.find(x => x.id === "ev4")?.late && !M.find(x => x.id === "ev4")?.off && M.find(x => x.id === "ev4")?.tag === "après l'âge", "the kept items are struck through, « après l'âge », still clickable");
  let iss = await checks(/default/);
  check(iss.some(l => /memories\.ev4 : souvenir plus vieux que l'âge du preset default \(29 > 12\)/.test(l)) && iss.some(l => /psyche\.wound1 apparu à 24 ans, après l'âge que montre ce preset \(12\)/.test(l)), "the Checks step reports them (ev4 29 > 12, wound1 since 24)");
  await presets(false);
  await setAge("default", 29);
  check(!(await popup()), "back to 29: no pop-up (nothing incoherent)");

  /* ---- « Désélectionner » ---- */
  await setAge("en-65", 40);
  pop = await popup();
  check(pop && pop.head === "Ce preset a 40 ans, mais il retient 3 souvenirs et 1 nœud incompatibles avec cet âge :" && pop.lines.length === 4 && /bel4 · depuis 45 ans$/.test(pop.lines[3]), "en-65 at 40: « … 3 souvenirs et 1 nœud incompatibles avec cet âge : » (ev6, ev7, ev8; bel4)");
  await press("Désélectionner ces éléments");
  let ml = await memList("en-65"), pl = await psyList("en-65");
  check(!["ev6", "ev7", "ev8"].some(v => ml.held.includes(v)) && ml.held.includes("ev5") && !pl.list.includes("bel4") && pl.list.length === 20, "« Désélectionner »: ev6–ev8 and bel4 leave en-65, ev5 (31) and the 20 other nodes stay");
  await setAge("en-65", 65); check(!(await popup()), "en-65 back to 65: no pop-up");
  await setAge("en-65", 64); check(!(await popup()), "a change that keeps everything coherent opens nothing");
  await setAge("en-65", 65);

  /* ---- an inherited list (fr extends default, no list of its own) ---- */
  await setAge("fr", 25);
  pop = await popup();
  check(pop && pop.head === "Ce preset a 25 ans, mais il retient 3 souvenirs et 8 nœuds incompatibles avec cet âge :" && pop.lines.length === 9 && pop.lines.slice(0, 8).every(l => / · hérité$/.test(l)) && pop.lines[8] === "et 3 autres", "fr at 25: 3 memories and 8 nodes (contra1 since 28), the inherited items marked « hérité », « et 3 autres »");
  await press("Garder — je corrige l'âge");
  await narrow("fr", "memories", "ev"); await narrow("fr", "psyche", "stance");
  M = await chips("fr", "data-memfs"); N = await chips("fr", "data-psyfs");
  const ev4 = M.find(x => x.id === "ev4"), st1 = N.find(x => x.id === "stance1");
  check(ev4 && ev4.late && !ev4.off && /^hérité, après l'âge retirer pour ce preset$/.test(ev4.tag), "inherited ev4 (29) struck through « hérité, après l'âge » with « retirer pour ce preset »");
  check(st1 && st1.late && /^hérité, non tenu à cet âge retirer pour ce preset$/.test(st1.tag), "inherited stance1 (since 29) struck through « hérité, non tenu à cet âge »");
  await page.evaluate(c => document.querySelector(c + ' [data-memfs] [data-mdrop="ev4"]').click(), card("fr")); await page.waitForTimeout(150);
  ml = await memList("fr"); const dm = await memList("default");
  check(!ml.inherited && JSON.stringify(ml.held) === JSON.stringify(dm.held.filter(v => v !== "ev4")) && dm.held.includes("ev4"), "« retirer pour ce preset »: fr gets its own list without ev4, default keeps it");
  await page.evaluate(c => document.querySelector(c + ' [data-psyfs] [data-pdrop="stance1"]').click(), card("fr")); await page.waitForTimeout(150);
  pl = await psyList("fr"); const dp = await psyList("default");
  check(!pl.inherited && JSON.stringify(pl.list) === JSON.stringify(dp.list.filter(v => v !== "stance1")), "and for a node: fr's own psyche list without stance1");
  M = await chips("fr", "data-memfs");
  check(M.find(x => x.id === "ev3")?.tag === "après l'âge" && !(await offered("fr", "memories")).some(x => x.id === "ev4"), "now its own list: ev3 « après l'âge » (no button), ev4 no longer offered");
  await page.evaluate(c => document.querySelector(c + ' [data-memfs] [data-mslot="ev3"]').click(), card("fr")); await page.waitForTimeout(150);
  check(!(await memList("fr")).held.includes("ev3"), "a click on an own struck chip removes it");
  await narrow("fr", "memories", ""); await narrow("fr", "psyche", "");

  /* ---- the file built without edits: every preset's lists unchanged ---- */
  await open(clara);
  let outMan = await build(path.join(WORK, "clara-out.cof"));
  check(sameLists(lists(srcMan, "memories"), lists(outMan, "memories")) && sameLists(lists(srcMan, "psyche"), lists(outMan, "psyche")), "Clara built without edits: the memories and psyche lists of the 12 presets unchanged (own or inherited) " + diffLists(lists(srcMan, "memories"), lists(outMan, "memories")) + diffLists(lists(srcMan, "psyche"), lists(outMan, "psyche")));
  check(JSON.stringify(Object.fromEntries(Object.entries(outMan.presets).map(([p, v]) => [p, v.age_override]))) === JSON.stringify(Object.fromEntries(Object.entries(srcMan.presets).map(([p, v]) => [p, v.age_override]))), "and the ages");

  /* ---- a later moment of a period, date-only moments ---- */
  await open(late);
  const EF = "en-futur" in lateMan.presets ? "en-futur" : "en-future";
  outMan = await build(path.join(WORK, "late-out.cof"));
  check(sameLists(lists(lateMan, "memories"), lists(outMan, "memories")), "loaded with ev5 (31) part-of ep2: every list written back unchanged (fr-futur ticks ep2 without ev5) " + diffLists(lists(lateMan, "memories"), lists(outMan, "memories")));
  ml = await memList("fr-futur");
  check(ml.list.includes("ep2") && !ml.held.includes("ev5") && (await memList(EF)).held.includes("ev5"), "fr-futur (29) holds ep2 without ev5; " + EF + " lists ev5 on its own and keeps it");
  await presets(false); await narrow(EF, "memories", "ev5");
  M = await chips(EF, "data-memfs"); await narrow(EF, "memories", "");
  check(M.find(x => x.id === "ev5")?.late && M.find(x => x.id === "ev5")?.tag === "après l'âge", EF + ": ev5 shown struck through « après l'âge »");
  M = await offered("default", "memories");
  check(ids(M).includes("ev15") && !ids(M).includes("ev16"), "date-only: ev15 (2027-06, born 1997 → 30, one year of slack) offered at 29, ev16 (2036) not");
  check(ids(await offered("en-65", "memories")).includes("ev16"), "ev16 offered at 65");
  /* tick ep2 at 29 (periods only): ep2 with ev9, ev10, never ev5 */
  await presets(true);
  await page.evaluate(c => document.querySelector(c + ' [data-memfs] [data-mslot="ep2"]').click(), card("default")); await page.waitForTimeout(150);
  ml = await memList("default");
  check(ml.held.includes("ep2") && ml.held.includes("ev9") && ml.held.includes("ev10") && !ml.held.includes("ev5") && ml.list.includes("ep2") && !ml.list.includes("ev9"), "ticking ep2 at 29 brings ev9, ev10 (29), not ev5 (31); the list stays compact");
  check((await chips("default", "data-memfs")).find(x => x.id === "ep2")?.st === "def", "ep2 reads ✓");
  outMan = await build(path.join(WORK, "late-out2.cof"));
  check(JSON.stringify(outMan.presets.default.slots.memories.filter(v => ["ep2", "ev9", "ev10", "ev5"].includes(v)).sort()) === JSON.stringify(["ep2", "ev10", "ev9"]), "built: default lists ep2, ev9, ev10 — not ev5");
  await presets(false); await narrow("en-65", "memories", "ev16");
  await page.evaluate(c => document.querySelector(c + ' [data-memfs] [data-mslot="ev16"]').click(), card("en-65")); await page.waitForTimeout(150);
  check((await memList("en-65")).held.includes("ev16"), "ev16 ticked in en-65");
  await setAge("en-65", 30);
  pop = await popup();
  check(pop && pop.lines.some(l => /ev16 · ≈ 39 ans$/.test(l)) && !pop.lines.some(l => /ev15/.test(l)), "en-65 at 30: the pop-up places the date-only ev16 at « ≈ 39 ans » (ev15, ≈ 30, stays)");
  await press("Garder — je corrige l'âge");
  iss = await checks(/ev16/);
  check(iss.some(l => /memories\.ev16 : souvenir plus vieux que l'âge du preset en-65 \(≈ 39 > 30\)/.test(l)), "and the check reports it: « (≈ 39 > 30) »");

  /* ---- six languages ---- */
  const KEYS = ["{n} souvenir(s) après {a} ans non proposé(s)", "{n} nœud(s) non tenu(s) à {a} ans non proposé(s)", "afficher quand même", "après l'âge", "hérité, après l'âge", "non tenu à cet âge", "hérité, non tenu à cet âge", "retirer pour ce preset", "Âge du preset et sélection", "Ce preset a {a} ans, mais il retient {items} incompatibles avec cet âge :", "Ce preset a {a} ans, mais il retient {items} incompatible avec cet âge :", "{n} souvenirs", "{n} nœuds", "et {n} autres", "Désélectionner ces éléments", "Garder — je corrige l'âge", "après l'âge du preset — non proposé", "après l'âge du preset — clic pour retirer", "non tenu à l'âge du preset — non proposé", "non tenu à l'âge du preset — clic pour retirer", "depuis {a} ans", "jusqu'à {a} ans", "{a} ans"];
  const miss = await page.evaluate(K => ["en", "de", "es", "zh", "ja"].flatMap(l => K.filter(k => !I18N[l] || typeof I18N[l][k] !== "string" || !I18N[l][k]).map(k => l + ":" + k)), KEYS);
  check(!miss.length, "every new string in en, de, es, zh, ja " + miss.slice(0, 5).join(" | "));
  const gd = await page.evaluate(() => ["fr", "en", "de", "es", "zh", "ja"].map(l => GUIDE[l][5].h.split("<li>").length - 1));
  check(gd.every(n => n === 5), "the guide's Presets page has the age bullet in the six languages");
  for (const l of ["en", "de", "ja"]) {
    await page.evaluate(x => { setLang(x); }, l); await presets(false);
    const txt = await line("en-12", "data-memfs");
    check(txt && !/souvenir/.test(txt) && /16/.test(txt) && /12/.test(txt), `${l}: the count line is translated — ${txt}`);
  }
  await page.evaluate(() => setLang("fr"));
  check(!errors.length, "no page errors " + errors.slice(0, 3).join(" | "));
  await browser.close(); server.close();
  console.log(ok ? "ALL OK" : "SOME CHECKS FAILED");
  process.exit(ok ? 0 : 1);
})().catch(e => { console.error(e); process.exit(1); });
