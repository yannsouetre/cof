#!/usr/bin/env node
/* Builder 0.14 — the Psyché step (RFC 0004, COF 1.2), end to end in headless Chromium.
   Usage: node tests/builder/psyche_test.js [repo-root] [work-dir]
   Needs: playwright (npm i playwright && npx playwright install chromium), python with cof-cli importable from <root>/cli.
   Packs copies of examples 10 (Clara 1.2) and 01 (Clara text-only, 1.0 lists) into the work dir, serves the repo over HTTP
   (the graph button embeds viewer/index.html), then: opens Clara 1.2 → step 4 shows the 22 nodes, kind chips and filter;
   edits a gist and a strength; adds a rule, a stance about the user, a contradiction with two conflicts; derives a node;
   deletes one; ticks a node in a preset's Psyché subsection; checks a deliberately broken node; builds with every purge
   choice and re-validates each output with `cof validate`; converts the 1.0 lists of example 01. Exit code 1 on any failure. */
const fs = require("fs"), path = require("path"), http = require("http"), { spawnSync } = require("child_process");
const { chromium } = require("playwright");
const ROOT = path.resolve(process.argv[2] || path.join(__dirname, "..", ".."));
const WORK = path.resolve(process.argv[3] || fs.mkdtempSync(path.join(require("os").tmpdir(), "cof-psyche-")));
fs.mkdirSync(WORK, { recursive: true });
let ok = true;
const check = (cond, msg) => { console.log((cond ? "ok   " : "FAIL ") + msg); ok = ok && !!cond; };
const py = (args, cwd) => spawnSync(process.env.PYTHON || "python", args, { encoding: "utf8", cwd });
function pack(example, out) {
  const src = path.join(WORK, "src-" + example);
  fs.rmSync(src, { recursive: true, force: true });
  fs.cpSync(path.join(ROOT, "spec", "examples", example), src, { recursive: true });   /* cof pack rewrites the manifest it packs: never the repo's copy */
  const r = py(["-m", "cof_cli.cli", "pack", src, "-o", out], path.join(ROOT, "cli"));
  if (r.status !== 0) throw new Error("pack failed: " + r.stdout + r.stderr);
}
function validate(file) {
  const r = py(["-m", "cof_cli.cli", "validate", file], path.join(ROOT, "cli"));
  return { ok: /^OK/m.test(r.stdout), out: r.stdout + r.stderr };
}
const readManifest = file => {
  const r = py(["-c", "import json,zipfile,sys;Z=zipfile.ZipFile(sys.argv[1]);m=json.loads(Z.read('manifest.json'));print(json.dumps({'cof':m['cof'],'content':m['tags']['content'],'auto':m['tags']['auto'],'psyche':m['elements'].get('psyche',{}).get('variants',{}),'slots':{p:(v.get('slots') or {}).get('psyche') for p,v in m['presets'].items()},'nodes':{k:json.loads(Z.read(v['node'])) for k,v in m['elements'].get('psyche',{}).get('variants',{}).items()}}))", file]);
  return JSON.parse(r.stdout);
};
const mime = { ".html": "text/html; charset=utf-8", ".js": "text/javascript", ".json": "application/json", ".css": "text/css", ".svg": "image/svg+xml", ".png": "image/png" };
const server = http.createServer((q, s) => { let f = path.join(ROOT, decodeURIComponent(q.url.split("?")[0])); if (!f.startsWith(ROOT)) { s.writeHead(403); return s.end(); } try { if (fs.statSync(f).isDirectory()) f = path.join(f, "index.html"); } catch (e) {} fs.readFile(f, (e, d) => { if (e) { s.writeHead(404); return s.end(); } s.writeHead(200, { "content-type": mime[path.extname(f)] || "application/octet-stream" }); s.end(d); }); });

(async () => {
  const clara12 = path.join(WORK, "clara12.cof"), clara10 = path.join(WORK, "clara10.cof");
  pack("10-clara-mercier", clara12); pack("01-clara-text-only", clara10);
  await new Promise(r => server.listen(0, r)); const URL = `http://localhost:${server.address().port}/builder/`;
  const browser = await chromium.launch();
  const ctx = await browser.newContext({ viewport: { width: 1400, height: 900 }, acceptDownloads: true });
  const page = await ctx.newPage(); const errors = [];
  page.on("pageerror", e => errors.push(e.message)); page.on("dialog", d => d.accept().catch(() => {}));
  await page.addInitScript(() => { window.__dl = []; const oc = URL.createObjectURL.bind(URL); URL.createObjectURL = b => { window.__dl.push(b); return oc(b); }; HTMLAnchorElement.prototype.click = function () {}; });
  const setE = (sel, v) => page.evaluate(([s, v]) => { const el = document.querySelector(s); if (!el) throw new Error("no " + s); el.value = v; el.dispatchEvent(new Event("input", { bubbles: true })); el.dispatchEvent(new Event("change", { bubbles: true })); }, [sel, v]);
  const open = async file => { await page.evaluate(() => { window.__prev = S.loadedManifest; }); await page.setInputFiles("#fileOpen", file); await page.waitForFunction(() => S.loadedManifest !== window.__prev && !document.getElementById("busy").classList.contains("on"), null, { timeout: 120000 }); await page.waitForTimeout(500); };
  const build = async out => { await page.evaluate(() => { window.__dl.length = 0; go("build"); }); await page.click("#btnBuild"); await page.waitForFunction(() => window.__dl.some(b => b.type === "application/vnd.cof.character+zip"), null, { timeout: 90000 }); const b64 = await page.evaluate(async () => { const b = window.__dl.filter(x => x.type === "application/vnd.cof.character+zip").pop(); const u = new Uint8Array(await b.arrayBuffer()); let s = ""; for (let i = 0; i < u.length; i += 32768) s += String.fromCharCode.apply(null, u.subarray(i, i + 32768)); return btoa(s); }); fs.writeFileSync(out, Buffer.from(b64, "base64")); };
  const checks = async re => { await page.evaluate(() => go("checks")); await page.click("#btnRunChecks"); await page.waitForTimeout(300); return (await page.evaluate(() => document.querySelector("#issueList").innerText)).split("\n").filter(l => re.test(l)); };

  await page.goto(URL, { waitUntil: "load" }); await page.evaluate(() => setMode("advanced"));
  check(await page.evaluate(() => [...document.querySelectorAll("#nav button")].map(b => b.dataset.step).join(",")) === "identity,elements,memories,psyche,presets,rights,checks,build", "eight steps, Psyché fourth");

  /* ---- Clara 1.2: load, list, filter, edit, build ---- */
  await open(clara12); await page.click("#nav button[data-step=psyche]"); await page.waitForTimeout(300);
  const info = await page.evaluate(() => ({ n: Object.keys(S.psyche).length, cards: document.querySelectorAll("#psyList .variant").length, kinds: document.querySelectorAll("#psyList [data-pkind]").length, first: document.querySelector("#psyList .variant")?.dataset.vid, passthrough: Object.keys(S.passthrough.elements).length }));
  check(info.n === 22 && info.cards === 22, `22 nodes loaded and shown (${info.n} / ${info.cards})`);
  check(info.kinds === 11 && info.first === "wound1", "kind chips (all + 10 kinds present) and the wound first");
  check(info.passthrough === 0, "the category left the passthrough");
  await page.click("#psyList [data-pkind=value]"); await page.waitForTimeout(200);
  check(await page.evaluate(() => document.querySelectorAll("#psyList .variant").length) === 4, "kind chip filters to the 4 values");
  await page.click("#psyList [data-pkind=all]"); await setE("#psyList [data-q=psyche]", "lightness"); await page.waitForTimeout(500);
  check(await page.evaluate(() => [...document.querySelectorAll("#psyList .variant")].map(d => d.dataset.vid).join()) === "val1", "text filter finds val1");
  await setE("#psyList [data-q=psyche]", ""); await page.waitForTimeout(500);
  await page.evaluate(() => { S._fold["m:psyche:val1"] = false; renderPsyche(); }); await page.waitForTimeout(200);
  await setE('#psyList .variant[data-vid="val1"] [data-pg=fr]', "La légèreté : faire moins, mieux."); await setE('#psyList .variant[data-vid="val1"] [data-pn=strength]', "96");
  check(await page.evaluate(() => S.psyche.val1.node.gist.fr === "La légèreté : faire moins, mieux." && S.psyche.val1.node.strength === 96), "gist and strength edited in the model");
  const t1 = path.join(WORK, "t1.cof"); await build(t1); let v = validate(t1); check(v.ok, "built Clara 1.2 validates: " + v.out.split("\n").filter(l => /ERROR|^OK|NOT/.test(l)).join(" | "));
  let m = readManifest(t1);
  check(m.cof === "1.2" && m.auto.includes("has-psyche") && Object.keys(m.psyche).length === 22, "cof 1.2, has-psyche, 22 variants written");
  check(m.psyche.val1.strength === 96 && m.nodes.val1.strength === 96 && m.nodes.val1.gist.fr, "strength mirrored on the variant, gist written");
  check(JSON.stringify(m.slots.default) === JSON.stringify(["wound1", "val1", "val2", "val3", "val4", "bel1", "bel2", "bel3", "want1", "want2", "want3", "need1", "fear1", "fear2", "fear3", "stance1", "stance2", "taste1", "taste2", "hab1", "hab2", "contra1"]) && JSON.stringify(m.slots["en-12"]) === JSON.stringify(["val4", "taste1", "hab2"]) && m.slots["en-manga"] === null, "preset slots kept (en-12 three nodes, en-manga inherits)");

  /* ---- add, link, derive, delete ---- */
  await page.evaluate(() => go("psyche")); await page.click("#psyList [data-padd]"); await page.waitForTimeout(200);
  check(await page.evaluate(() => document.querySelectorAll("#dlg .psykinds button").length) === 11, "kind chooser offers eleven kinds");
  await page.click("#dlg .psykinds button[data-dv=rule]"); await page.waitForTimeout(300);
  const rule = await page.evaluate(() => Object.keys(S.psyche).pop()); check(rule === "rule1" && (await page.evaluate(() => S.psyche.rule1.node.stability)) === "core", "a new rule is core by default (" + rule + ")");
  await setE(`#psyList .variant[data-vid="${rule}"] [data-pk=label]`, "No unasked message"); await setE(`#psyList .variant[data-vid="${rule}"] [data-pg=fr]`, "N'envoie jamais un message que personne n'a demandé.");
  await page.evaluate(() => psyNew("stance", false)); await page.waitForTimeout(200);
  const st = await page.evaluate(() => Object.keys(S.psyche).pop());
  await setE(`#psyList .variant[data-vid="${st}"] [data-pg=fr]`, "Envers la personne qui lui parle : une curiosité patiente."); await setE(`#psyList .variant[data-vid="${st}"] [data-pab=mode]`, "user"); await setE(`#psyList .variant[data-vid="${st}"] [data-pn=risk]`, "inappropriate");
  check(await page.evaluate(s => S.psyche[s].node.about?.user === true && S.psyche[s].node.risk === "inappropriate", st), "stance about the user, risk inappropriate");
  await page.evaluate(() => psyNew("contradiction", false)); await page.waitForTimeout(200);
  const co = await page.evaluate(() => Object.keys(S.psyche).pop());
  await setE(`#psyList .variant[data-vid="${co}"] [data-pg=fr]`, "Veut se taire, veut répondre.");
  await page.click(`#psyList .variant[data-vid="${co}"] [data-pladd]`); await page.waitForTimeout(150); await page.click(`#psyList .variant[data-vid="${co}"] [data-pladd]`); await page.waitForTimeout(150);
  await page.focus(`#psyList .variant[data-vid="${co}"] [data-plink="1"] [data-plk=to]`); await setE(`#psyList .variant[data-vid="${co}"] [data-plink="1"] [data-plk=to]`, "psyche/" + st);
  check(await page.evaluate(c => JSON.stringify((S.psyche[c].node.links || []).map(l => l.type)), co) === '["conflicts","conflicts"]', "contradiction carries two conflicts links");
  await page.evaluate(() => { S._fold["m:psyche:val1"] = false; renderPsyche(); }); await page.waitForTimeout(200);
  await page.click('#psyList .variant[data-vid="val1"] [data-pderive]'); await page.waitForTimeout(300);
  check(await page.evaluate(() => Object.values(S.psyche).some(x => x.derives_from === "val1" && x.node.gist.en === S.psyche.val1.node.gist.en)), "derive makes a copy with derives_from");
  await page.evaluate(() => { S._fold["m:psyche:fear3"] = false; renderPsyche(); }); await page.waitForTimeout(200);
  await page.click('#psyList .variant[data-vid="fear3"] [data-pdel]'); await page.waitForTimeout(200); await page.click("#dlg .dbtns button.primary"); await page.waitForTimeout(300);
  check(await page.evaluate(() => !S.psyche.fear3 && !document.querySelector('#psyList .variant[data-vid="fear3"]')), "delete removes the node and its card");

  /* ---- presets subsection ---- */
  await page.evaluate(() => go("presets")); await page.waitForTimeout(500);
  const pf = await page.evaluate(() => { const d = [...document.querySelectorAll("#presetList .variant")].find(x => x.dataset.pid === "en-12"); const fs = d && d.querySelector("[data-psyfs]"); return fs ? { groups: fs.querySelectorAll(".psygrp").length, ticked: [...fs.querySelectorAll("[data-prow][data-state=def]")].map(b => b.dataset.prow), bar: !!fs.querySelector("[data-subbar]") } : null; });
  check(pf && pf.groups >= 5 && pf.bar, "en-12 has a Psyché subsection grouped by kind with its filter bar");
  await page.evaluate(() => { const d = [...document.querySelectorAll("#presetList .variant")].find(x => x.dataset.pid === "en-12"); d.querySelector("[data-psyfs] [data-prow=wound1]").click(); }); await page.waitForTimeout(300);
  check(await page.evaluate(() => S.psyPresets["en-12"].includes("wound1")), "ticking a chip adds the node to the preset");
  let L = await checks(/psyche|Psyche/i);
  check(L.some(l => /en-12/.test(l) && /wound1/.test(l)), "a preset younger than the node's since is a finding");
  check(L.some(l => /psyche-inappropriate/.test(l)), "the declared risk announces its content tag");
  await page.evaluate(() => { S.psyPresets["en-12"] = S.psyPresets["en-12"].filter(v => v !== "wound1"); });

  /* ---- purges ---- */
  const t2 = path.join(WORK, "t2-none.cof"); await build(t2); v = validate(t2); m = readManifest(t2);
  check(v.ok && m.content.includes("psyche-inappropriate") && m.psyche[st] && m.psyche[co] && m.psyche.rule1, "no purge: validates, tag psyche-inappropriate, new nodes written");
  await page.evaluate(() => go("build")); await setE("#b_purge", "norisk"); const t3 = path.join(WORK, "t3-norisk.cof"); await build(t3); v = validate(t3); m = readManifest(t3);
  check(v.ok && JSON.stringify(m.content) === '["none"]' && !m.psyche[st] && !m.psyche[co] && m.psyche.rule1, "no-risk purge: validates, drops the inappropriate node and the contradiction that lost a side, fixes tags.content");
  await setE("#b_purge", "both"); const t4 = path.join(WORK, "t4-both.cof"); await build(t4); v = validate(t4); check(v.ok && !readManifest(t4).psyche[st], "both purges: validates");
  await setE("#b_purge", "allaud"); const t5 = path.join(WORK, "t5-allaud.cof"); await build(t5); v = validate(t5); check(v.ok && readManifest(t5).psyche[st], "all-audiences purge alone keeps the risk nodes and validates");
  await setE("#b_purge", "none");

  /* ---- checks on a broken node ---- */
  await page.evaluate(() => { S.psyche.val2.node.links = [{ to: "memories/ev1", type: "supports" }]; S.psyche.val3.node.links = [{ to: "psyche/val4", type: "because" }]; S.psyche.val4.node.links = [{ to: "psyche/val3", type: "because" }]; S.psyche.contra1.node.links = [{ to: "psyche/val1", type: "conflicts" }]; S.psyche.taste1.node.false_but_held = true; delete S.psyche.stance2.node.about; S.psyche.hab1.node.revisions = [{ date: "2026-01-01T00:00:00Z", gist: { en: "old" } }]; S.psyche.want1.node.links = [{ to: "psyche/nope", type: "because" }]; S.psyche.bel1.node.gist = {}; for (const x of Object.keys(S.psyche)) delete S.psyche[x].node.strength; });
  L = await checks(/psyche/i); const has = re => L.some(l => re.test(l));
  check(has(/val2/) && has(/bel1/) && has(/want1/) && has(/contra1/) && has(/val3 → val4 → val3/), "errors: supports to a memory, no gist, unknown target, one conflicts, because cycle");
  check(has(/taste1/) && has(/stance2/) && has(/hab1/) && has(/\d+ \/ \d+/), "warnings: false_but_held off a belief, stance without subject, revisions on authored; info: strength unset");

  /* ---- 1.0 lists → nodes ---- */
  await open(clara10); await page.click("#nav button[data-step=psyche]"); await page.waitForTimeout(300);
  check(await page.evaluate(() => !!document.querySelector("#psyList [data-psyoffer]") && !Object.keys(S.psyche).length), "a 1.0 file with card lists offers the conversion");
  await page.click("#psyList [data-pconvert]"); await page.waitForTimeout(300);
  const conv = await page.evaluate(() => Object.values(S.psyche).map(x => x.kind + ":" + (x.node.strength || "")).join(","));
  check(conv === "want:70,fear:,value:,value:,value:,habit:,habit:,habit:", "one want (70), one fear, three values, three habits (" + conv + ")");
  check(await page.evaluate(() => Object.values(S.psyche).filter(x => x.kind === "value").every(x => /^[A-ZÀ-Ý].*\.$/.test(Object.values(x.node.gist)[0]))), "a value's word becomes a sentence");
  const t6 = path.join(WORK, "t6-converted.cof"); await build(t6); v = validate(t6); m = readManifest(t6);
  check(v.ok && m.cof === "1.2" && Object.keys(m.psyche).length === 8, "converted file validates as 1.2 with 8 nodes");
  check(!errors.length, "no page errors" + (errors.length ? ": " + errors.join(" | ") : ""));
  await browser.close(); server.close();
  console.log(ok ? "ALL OK" : "FAILURES"); process.exit(ok ? 0 : 1);
})().catch(e => { console.error(e); server.close(); process.exit(1); });
