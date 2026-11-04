#!/usr/bin/env node
/* Builder — the illustrations of a psyche node (RFC 0004 § 3 decies), end to end in headless Chromium.
   Usage: node tests/builder/images_test.js [repo-root] [work-dir]
   On a copy of example 10: Clara's contra1 and hab1 load with their thumbnails (the guitar, the photo of ev1) and are written back
   unchanged in meaning; two images are added to a node (the first is the icon, the card says so), more than 3 warn, a non-image is
   refused, the character shown needs an age, nudity needs an adult; build → cof validate OK → reopen → the images are kept; the
   all-audiences purge drops the images of a nudity node only. The bubble of the embedded graph is the explorer's (tests/explorer).
   Exit code 1 on any failure. */
const fs = require("fs"), path = require("path"), http = require("http"), { spawnSync } = require("child_process");
const { chromium } = require("playwright");
const ROOT = path.resolve(process.argv[2] || path.join(__dirname, "..", ".."));
const WORK = path.resolve(process.argv[3] || fs.mkdtempSync(path.join(require("os").tmpdir(), "cof-images-")));
fs.mkdirSync(WORK, { recursive: true });
let ok = true;
const check = (cond, msg) => { console.log((cond ? "ok   " : "FAIL ") + msg); ok = ok && !!cond; };
const py = (args, cwd) => spawnSync(process.env.PYTHON || "python", args, { encoding: "utf8", cwd });
const validate = file => { const r = py(["-m", "cof_cli.cli", "validate", file], path.join(ROOT, "cli")); return { ok: /^OK/m.test(r.stdout), out: r.stdout + r.stderr }; };
const manifestOf = file => JSON.parse(py(["-c", "import json,zipfile,sys;print(json.dumps(json.loads(zipfile.ZipFile(sys.argv[1]).read('manifest.json'))))", file]).stdout);
const src = path.join(WORK, "src"); fs.rmSync(src, { recursive: true, force: true });
fs.cpSync(path.join(ROOT, "spec", "examples", "10-clara-mercier"), src, { recursive: true });
const clara = path.join(WORK, "clara.cof");
let r = py(["-m", "cof_cli.cli", "pack", src, "-o", clara], path.join(ROOT, "cli")); if (r.status !== 0) throw new Error(r.stdout + r.stderr);
const png = (name, rgb) => { const f = path.join(WORK, name); py(["-c", `from PIL import Image;Image.new("RGB",(24,24),tuple(${JSON.stringify(rgb)})).save(${JSON.stringify(f)})`]); return f; };
const imgs = ["a.png", "b.png", "c.png", "d.png"].map((n, i) => png(n, [40 * i, 90, 160 - 30 * i]));
const txt = path.join(WORK, "notes.txt"); fs.writeFileSync(txt, "not an image");
const mime = { ".html": "text/html; charset=utf-8", ".js": "text/javascript", ".json": "application/json", ".css": "text/css", ".svg": "image/svg+xml", ".png": "image/png" };
const server = http.createServer((q, s) => { let f = path.join(ROOT, decodeURIComponent(q.url.split("?")[0])); if (!f.startsWith(ROOT)) { s.writeHead(403); return s.end(); } try { if (fs.statSync(f).isDirectory()) f = path.join(f, "index.html"); const b = fs.readFileSync(f); s.writeHead(200, { "content-type": mime[path.extname(f)] || "application/octet-stream" }); s.end(b); } catch (e) { s.writeHead(404); s.end(); } });

(async () => {
  await new Promise(r => server.listen(0, r)); const URL = `http://localhost:${server.address().port}/builder/`;
  const browser = await chromium.launch();
  const ctx = await browser.newContext({ viewport: { width: 1400, height: 900 }, acceptDownloads: true });
  const page = await ctx.newPage(); const errors = [], dialogs = [];
  page.on("pageerror", e => errors.push(e.message)); page.on("dialog", d => { dialogs.push(d.message()); d.accept().catch(() => {}); });
  await page.addInitScript(() => { window.__dl = []; const oc = URL.createObjectURL.bind(URL); URL.createObjectURL = b => { window.__dl.push(b); return oc(b); }; HTMLAnchorElement.prototype.click = function () {}; });
  const open = async file => { await page.evaluate(() => { window.__prev = S.loadedManifest; }); await page.setInputFiles("#fileOpen", file); await page.waitForFunction(() => S.loadedManifest !== window.__prev && !document.getElementById("busy").classList.contains("on"), null, { timeout: 120000 }); await page.waitForTimeout(500); };
  const build = async out => { await page.evaluate(() => { window.__dl.length = 0; go("build"); }); await page.click("#btnBuild"); await page.waitForFunction(() => window.__dl.some(b => b.type === "application/vnd.cof.character+zip"), null, { timeout: 90000 }); const b64 = await page.evaluate(async () => { const b = window.__dl.filter(x => x.type === "application/vnd.cof.character+zip").pop(); const u = new Uint8Array(await b.arrayBuffer()); let s = ""; for (let i = 0; i < u.length; i += 32768) s += String.fromCharCode.apply(null, u.subarray(i, i + 32768)); return btoa(s); }); fs.writeFileSync(out, Buffer.from(b64, "base64")); };
  const checks = async re => { await page.evaluate(() => go("checks")); await page.click("#btnRunChecks"); await page.waitForTimeout(300); return (await page.evaluate(() => document.querySelector("#issueList").innerText)).split("\n").filter(l => re.test(l)); };
  const card = vid => `#psyList .variant[data-vid="${vid}"]`;
  const show = async vid => { await page.evaluate(v => { go("psyche"); gotoVariant("psyche", v); }, vid); await page.waitForSelector(card(vid) + " [data-psyimg]"); };
  const thumbs = vid => page.evaluate(v => document.querySelectorAll(`#psyList .variant[data-vid="${v}"] [data-psyimg] .thumb`).length, vid);

  await page.goto(URL, { waitUntil: "load" }); await page.evaluate(() => setMode("advanced"));
  await open(clara);
  /* Clara's two illustrated nodes load with their images; the guitar stays an image of appearance/x1 too */
  await show("contra1");
  check(await thumbs("contra1") === 1 && await page.evaluate(() => S.psyche.contra1.media[0].id === "a-ac-x1" && S.assets.some(a => a.id === "a-ac-x1")), "contra1 loads with the guitar (a-ac-x1), still an asset of x1");
  check(await page.evaluate(() => /^blob:/.test(document.querySelector('#psyList .variant[data-vid="contra1"] [data-psyimg] img').src)), "the guitar has a thumbnail");
  check(await page.evaluate(() => document.querySelector('#psyList .variant[data-vid="contra1"] [data-psyimg]').innerText.includes(t("icône du nœud"))), "the first image is marked as the node's icon");
  await show("hab1");
  check(await page.evaluate(() => S.psyche.hab1.media.length === 1 && S.psyche.hab1.media[0].id === "a-mem-ev1-1"), "hab1 loads with the photo of ev1 (shared with the memory)");
  check(await page.evaluate(() => { const b = document.querySelector('#psyList .variant[data-vid="hab1"] [data-psyimg] .hint').innerText; return b.includes("1 recommandée") && b.includes("plus de 3"); }), "the hint says 1 recommended, more than 3 → a memory");
  /* the untouched file is written back with the same media */
  const out0 = path.join(WORK, "out0.cof"); await build(out0);
  const m0 = manifestOf(out0), V0 = m0.elements.psyche.variants;
  check(JSON.stringify(V0.contra1.media) === '["a-ac-x1"]' && JSON.stringify(V0.hab1.media) === '["a-mem-ev1-1"]' && !("age" in V0.contra1), "untouched: media written back, no age invented");
  check(m0.assets.filter(a => a.id === "a-ac-x1").length === 1 && m0.assets.filter(a => a.id === "a-mem-ev1-1").length === 1, "untouched: each shared asset listed once");
  check(validate(out0).ok, "untouched build validates");

  /* two images on a node; the bubble's icon is the first */
  await show("want1");
  check(await thumbs("want1") === 0, "want1 starts without an image");
  await page.setInputFiles(card("want1") + " [data-psyimg] input[type=file]", imgs.slice(0, 2));
  await page.waitForFunction(() => document.querySelectorAll('#psyList .variant[data-vid="want1"] [data-psyimg] .thumb').length === 2);
  check(await page.evaluate(() => S.psyche.want1.media.map(a => a.path).join() === "elements/psyche/want1/a.png,elements/psyche/want1/b.png"), "two images added in the node's folder, in order");
  check(await page.evaluate(() => document.querySelectorAll('#psyList .variant[data-vid="want1"] [data-psyimg] .thumb')[0].innerText.includes(t("icône du nœud")) && !document.querySelectorAll('#psyList .variant[data-vid="want1"] [data-psyimg] .thumb')[1].innerText.includes(t("icône du nœud"))), "only the first is the icon");
  /* a non-image is refused */
  dialogs.length = 0; await page.setInputFiles(card("want1") + " [data-psyimg] input[type=file]", txt); await page.waitForTimeout(300);
  check(await thumbs("want1") === 2 && dialogs.some(d => /image/.test(d)), "a text file is refused with a message, nothing added");
  /* more than 3 */
  await page.setInputFiles(card("want1") + " [data-psyimg] input[type=file]", imgs.slice(2)); await page.waitForFunction(() => S.psyche.want1.media.length === 4);
  let w = await checks(/want1/); check(w.some(l => /plus de 3 images|more than 3 images/.test(l)), "checks: more than 3 images warns (" + w.length + " lines)");
  await show("want1"); await page.evaluate(() => { document.querySelectorAll('#psyList .variant[data-vid="want1"] [data-pmrm]')[3].click(); document.querySelectorAll('#psyList .variant[data-vid="want1"] [data-pmrm]')[2].click(); });
  await page.waitForFunction(() => S.psyche.want1.media.length === 2);
  check(await thumbs("want1") === 2, "two ✕ remove two images");
  /* the character shown: an age is required */
  await page.evaluate(() => { const c = document.querySelector('#psyList .variant[data-vid="want1"] [data-pim=self]'); c.checked = true; c.dispatchEvent(new Event("change", { bubbles: true })); });
  await page.waitForSelector(card("want1") + " [data-pim=age]");
  w = await checks(/want1/); check(w.some(l => /sans âge|without an age/.test(l)), "checks: an image showing the character needs an age");
  await show("want1"); await page.fill(card("want1") + " [data-pim=age]", "30"); await page.dispatchEvent(card("want1") + " [data-pim=age]", "change");
  w = await checks(/want1/); check(!w.some(l => /sans âge|without an age/.test(l)), "checks: the age clears it");
  /* nudity: an adult is needed (set 12 to see the error, 30 for the file) */
  await show("want1"); await page.evaluate(() => { const c = document.querySelector('#psyList .variant[data-vid="want1"] [data-pim=nudity]'); c.checked = true; c.dispatchEvent(new Event("change", { bubbles: true })); S.psyche.want1.age = 12; });
  w = await checks(/want1/); check(w.some(l => /nudité|nudity/.test(l)), "checks: nudity with the character under 18 is an error");
  await page.evaluate(() => { S.psyche.want1.age = 30; });
  /* a second node with ordinary images and no nudity, for the purge */
  await show("val2"); await page.setInputFiles(card("val2") + " [data-psyimg] input[type=file]", imgs[2]); await page.waitForFunction(() => S.psyche.val2.media.length === 1);
  /* build → validate → reopen */
  const out1 = path.join(WORK, "out1.cof"); await build(out1);
  const v1 = validate(out1); check(v1.ok, "build validates with cof validate" + (v1.ok ? "" : "\n" + v1.out));
  const m1 = manifestOf(out1), V1 = m1.elements.psyche.variants, A1 = Object.fromEntries(m1.assets.map(a => [a.id, a]));
  check(V1.want1.media.length === 2 && V1.want1.media.every(i => A1[i] && A1[i].role === "psyche-media" && A1[i].mediaType === "image/png" && A1[i].path.startsWith("elements/psyche/want1/")), "want1: two psyche-media image assets in its folder");
  check(V1.want1.age.value === 30 && V1.want1.nudity === true && m1.tags.content.includes("nudity"), "want1: age, nudity and tags.content nudity written");
  check(V1.val2.media.length === 1 && !("nudity" in V1.val2), "val2: one ordinary illustration");
  await open(out1); await show("want1");
  check(await thumbs("want1") === 2 && await page.evaluate(() => S.psyche.want1.age === 30 && S.psyche.want1.nudity === true && (S.psyche.want1.node.who || []).some(x => x.identity === "self" && x.shown)), "reopened: the images, the age and the nudity are kept");
  /* the all-audiences purge: only the nudity node loses its images; the node stays */
  await page.evaluate(() => { S._purge = "allaud"; const c = document.querySelector("#b_mem_allaud"); if (c) c.checked = true; });
  const out2 = path.join(WORK, "out2.cof"); await build(out2);
  const m2 = manifestOf(out2), V2 = m2.elements.psyche.variants;
  check(validate(out2).ok, "all-audiences build validates");
  check(V2.want1 && !V2.want1.media && !V2.want1.nudity && !V2.want1.age, "all-audiences: want1 keeps its words and loses its images, nudity and age");
  check(V2.val2.media.length === 1 && V2.contra1.media[0] === "a-ac-x1", "all-audiences: ordinary illustrations stay");
  check(!m2.assets.some(a => a.path && a.path.startsWith("elements/psyche/want1/")), "all-audiences: want1's files are gone");
  /* six languages */
  for (const l of ["en", "de", "es", "zh", "ja"]) { const ok2 = await page.evaluate(l => { const d = I18N[l]; return d["Illustration"] && ["Glissez des images ici ou cliquez — elles sont ajoutées au fichier comme nouveaux assets", "1 recommandée : la première remplace l'icône ; plus de 3 → un souvenir conviendrait mieux", "icône du nœud"].every(k => d[k] && d[k] !== k); }, l); check(ok2, "i18n " + l + ": the illustration words are translated"); }
  check(errors.length === 0, "no page errors" + (errors.length ? ": " + errors.slice(0, 3).join(" | ") : ""));
  await browser.close(); server.close(); process.exit(ok ? 0 : 1);
})().catch(e => { console.error(e); process.exit(1); });
