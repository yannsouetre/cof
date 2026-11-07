#!/usr/bin/env node
/* Builder 0.14 — objects of a memory (RFC 0005, COF 1.2) and the round trip of people, places and objects, in headless Chromium.
   Usage: node tests/builder/objects_test.js [repo-root] [work-dir]
   Needs: playwright (npm i playwright && npx playwright install chromium), python with cof-cli and jsonschema importable from <root>/cli.
   Packs a copy of example 10 (Clara 1.2) with the entries of RFC 0005 § 3 written in (the notebook and the pendant by name, the folk
   guitar as the accessory appearance/x1; a person, a place and two objects on psyche nodes) and a copy of example 11 (the duo, 1.1),
   then: the memory cards show an « Objets » field, its picker holds one option until used and then lists the character's accessories
   only; the file built without any edit carries every memory and psyche node unchanged; objects are added (a free name, « montré », an
   accessory), removed, and written as `what` (absent when empty); the memory filter finds an object by name; the checks report an entry
   with neither reference nor name, an unresolved item, an item that is not an accessory, an element of another character in a cast file;
   a 1.1 file whose memory gains an object is written as 1.2, and stays 1.1 otherwise; the words in the six languages. Every node file of
   the outputs is checked against spec/schemas (and with `cof validate` when the cli of the repository knows RFC 0005). */
const fs = require("fs"), path = require("path"), http = require("http"), { spawnSync } = require("child_process");
const { chromium } = require("playwright");
const ROOT = path.resolve(process.argv[2] || path.join(__dirname, "..", ".."));
const WORK = path.resolve(process.argv[3] || fs.mkdtempSync(path.join(require("os").tmpdir(), "cof-objects-")));
fs.mkdirSync(WORK, { recursive: true });
let ok = true;
const check = (cond, msg) => { console.log((cond ? "ok   " : "FAIL ") + msg); ok = ok && !!cond; };
const py = (args, cwd) => spawnSync(process.env.PYTHON || "python", args, { encoding: "utf8", cwd });
const CLI = path.join(ROOT, "cli");
const CLI_KNOWS_0005 = fs.readFileSync(path.join(CLI, "cof_cli", "schemas", "psyche-node.schema.json"), "utf8").includes('"what"');
/* RFC 0005 § 3 on a copy (idempotent: the example may already carry its own entries) */
const NB = { label: { fr: "le carnet", en: "the notebook" } }, GT = { item: "appearance/x1" }, PD = { label: { fr: "le pendentif de ma grand-mère", en: "my grandmother's pendant" } };
const PATCH10 = { memories: { ev1: { what: [NB] }, ev11: { what: [NB] }, ev2: { what: [GT] }, ev12: { what: [GT] }, ev5: { what: [PD] } },
  psyche: { hab1: { what: [NB] }, contra1: { what: [GT] }, val4: { who: [{ label: { fr: "ma grand-mère", en: "my grandmother" } }] }, want2: { where: [{ environment: "appearance/e1" }] } } };
function pack(example, out, patch) {
  const src = path.join(WORK, "src-" + example);
  fs.rmSync(src, { recursive: true, force: true });
  fs.cpSync(path.join(ROOT, "spec", "examples", example), src, { recursive: true });   /* cof pack rewrites the manifest it packs: never the repo's copy */
  if (patch) { const man = JSON.parse(fs.readFileSync(path.join(src, "manifest.json"), "utf8"));
    for (const [cat, todo] of Object.entries(patch)) for (const [vid, add] of Object.entries(todo)) { const v = man.elements[cat].variants[vid]; const f = path.join(src, v.memory || v.node); fs.writeFileSync(f, JSON.stringify({ ...JSON.parse(fs.readFileSync(f, "utf8")), ...add }, null, 2) + "\n"); } }
  const r = py(["-m", "cof_cli.cli", "pack", src, "-o", out, ...(CLI_KNOWS_0005 ? [] : ["--force"])], CLI);   /* --force while the cli of the repository predates RFC 0005 */
  if (r.status !== 0) throw new Error("pack failed: " + r.stdout + r.stderr);
}
/* the manifest and every memory / psyche node of a .cof, and the node files checked against spec/schemas */
const SCHEMA_PY = `import json,zipfile,sys
from jsonschema import Draft202012Validator as V
Z=zipfile.ZipFile(sys.argv[1]);m=json.loads(Z.read('manifest.json'));root=sys.argv[2]
sch={k:V(json.load(open(root+'/spec/schemas/'+k+'.schema.json',encoding='utf-8'))) for k in ('memory','psyche-node')}
out={'cof':m['cof'],'mem':{},'psy':{},'bad':[]}
for cat,key,s,o in (('memories','memory','memory','mem'),('psyche','node','psyche-node','psy')):
  for vid,v in m['elements'].get(cat,{}).get('variants',{}).items():
    n=json.loads(Z.read(v[key]));out[o][vid]=n
    out['bad']+=[vid+': '+e.message for e in sch[s].iter_errors(n)]
print(json.dumps(out,ensure_ascii=False))`;
const readCof = file => { const r = py(["-c", SCHEMA_PY, file, ROOT]); if (r.status !== 0) throw new Error(r.stderr); return JSON.parse(r.stdout); };
const validate = file => { if (!CLI_KNOWS_0005) return { ok: true, out: "cof validate skipped (cli before RFC 0005)" }; const r = py(["-m", "cof_cli.cli", "validate", file], CLI); return { ok: /^OK/m.test(r.stdout), out: r.stdout.split("\n").filter(l => /ERROR|^OK|NOT/.test(l)).join(" | ") }; };
const mime = { ".html": "text/html; charset=utf-8", ".js": "text/javascript", ".json": "application/json", ".css": "text/css", ".svg": "image/svg+xml", ".png": "image/png" };
const server = http.createServer((q, s) => { let f = path.join(ROOT, decodeURIComponent(q.url.split("?")[0])); if (!f.startsWith(ROOT)) { s.writeHead(403); return s.end(); } try { if (fs.statSync(f).isDirectory()) f = path.join(f, "index.html"); } catch (e) {} fs.readFile(f, (e, d) => { if (e) { s.writeHead(404); return s.end(); } s.writeHead(200, { "content-type": mime[path.extname(f)] || "application/octet-stream" }); s.end(d); }); });

(async () => {
  const claraO = path.join(WORK, "clara-objects.cof"), duo = path.join(WORK, "duo.cof");
  pack("10-clara-mercier", claraO, PATCH10); pack("11-duo-clara-martien", duo);
  const src = readCof(claraO);
  await new Promise(r => server.listen(0, r)); const URL = `http://localhost:${server.address().port}/builder/`;
  const browser = await chromium.launch();
  const ctx = await browser.newContext({ viewport: { width: 1400, height: 900 }, acceptDownloads: true });
  const page = await ctx.newPage(); const errors = [];
  page.on("pageerror", e => errors.push(e.message)); page.on("dialog", d => d.accept().catch(() => {}));
  await page.addInitScript(() => { window.__dl = []; const oc = URL.createObjectURL.bind(URL); URL.createObjectURL = b => { window.__dl.push(b); return oc(b); }; HTMLAnchorElement.prototype.click = function () {}; });
  const setE = (sel, v) => page.evaluate(([s, v]) => { const el = document.querySelector(s); if (!el) throw new Error("no " + s); if (el.type === "checkbox") el.checked = !!v; else el.value = v; el.dispatchEvent(new Event("input", { bubbles: true })); el.dispatchEvent(new Event("change", { bubbles: true })); }, [sel, v]);
  const open = async file => { await page.evaluate(() => { window.__prev = S.loadedManifest; }); await page.setInputFiles("#fileOpen", file); await page.waitForFunction(() => S.loadedManifest !== window.__prev && !document.getElementById("busy").classList.contains("on"), null, { timeout: 120000 }); await page.waitForTimeout(500); };
  const build = async out => { await page.evaluate(() => { window.__dl.length = 0; go("build"); }); await page.click("#btnBuild"); await page.waitForSelector("#dlg.on .dbtns .primary", { timeout: 10000 }); await page.click("#dlg.on .dbtns .primary");   /* the build confirmation (7 Nov.) */ await page.waitForFunction(() => window.__dl.some(b => b.type === "application/vnd.cof.character+zip"), null, { timeout: 90000 }); const b64 = await page.evaluate(async () => { const b = window.__dl.filter(x => x.type === "application/vnd.cof.character+zip").pop(); const u = new Uint8Array(await b.arrayBuffer()); let s = ""; for (let i = 0; i < u.length; i += 32768) s += String.fromCharCode.apply(null, u.subarray(i, i + 32768)); return btoa(s); }); fs.writeFileSync(out, Buffer.from(b64, "base64")); };
  const checks = async re => { await page.evaluate(() => go("checks")); await page.click("#btnRunChecks"); await page.waitForTimeout(300); return (await page.evaluate(() => document.querySelector("#issueList").innerText)).split("\n").filter(l => re.test(l)); };
  const card = vid => `#memList .variant[data-vid="${vid}"]`;
  const unfold = vid => page.evaluate(v => { (S._fold = S._fold || {})["m:memories:" + v] = false; memReveal(v); renderMemories(); }, vid).then(() => page.waitForTimeout(200));
  const rows = vid => page.evaluate(c => [...document.querySelectorAll(c + " [data-axrow=what]")].map(r => ({ sel: r.querySelector("[data-axsel]").value, n: r.querySelector("[data-axsel]").options.length, lab: r.querySelector("[data-axlab]").value, shown: !!r.querySelector("[data-axflag=shown]")?.checked })), card(vid));

  await page.goto(URL, { waitUntil: "load" }); await page.evaluate(() => setMode("advanced"));
  await open(claraO); await page.click("#nav button[data-step=memories]"); await page.waitForTimeout(300);

  /* ---- the field, its lazy picker ---- */
  let r1 = await rows("ev1"), r2 = await rows("ev2");
  check(r1.length === 1 && r1[0].sel === "" && r1[0].lab === "le carnet" && r2.length === 1 && r2[0].sel === "appearance/x1" && r2[0].lab === "", "ev1 shows the notebook by name, ev2 the guitar as appearance/x1");
  check(r2[0].n === 1 && await page.evaluate(() => document.querySelectorAll("#memList [data-axsel]").length === document.querySelectorAll("#memList [data-axsel] option").length), "the object pickers hold one option until used (lazy)");
  await unfold("ev2"); await page.focus(card("ev2") + " [data-axsel]");
  const opts = await page.evaluate(c => [...document.querySelector(c + " [data-axsel]").options].map(o => o.value).join(), card("ev2"));
  check(opts === ",appearance/x1,appearance/x2,appearance/x3" && (await rows("ev2"))[0].sel === "appearance/x1", "on first use: a free name and the three accessories, no clothing or environment (" + opts + ")");
  check(await page.evaluate(() => /🧸/.test(document.querySelector('#memList .variant[data-vid="ev1"] [data-axbox=m] > label').textContent) && /pendentif/.test(memHay("ev5"))), "the field is labelled « 🧸 Objets »; the memory filter finds an object by name");

  /* ---- round trip: nothing edited, everything written back unchanged ---- */
  const t0 = path.join(WORK, "t0-unchanged.cof"); await build(t0); let o = readCof(t0);
  const same = (a, b) => JSON.stringify(a) === JSON.stringify(b);
  const diffM = Object.keys(src.mem).filter(v => !same(src.mem[v], o.mem[v])), diffP = Object.keys(src.psy).filter(v => !same(src.psy[v], o.psy[v]));
  check(o.cof === "1.2" && !diffM.length && !diffP.length && Object.keys(o.mem).length === Object.keys(src.mem).length, `load → build without edits: every memory and psyche node unchanged (${diffM.concat(diffP).join(", ") || "none differ"})`);
  check(same(o.mem.ev2.what, [GT]) && same(o.mem.ev5.what, [PD]) && same(o.psy.val4.who, PATCH10.psyche.val4.who) && same(o.psy.want2.where, [{ environment: "appearance/e1" }]) && !o.bad.length, "what / who / where kept as read; node files valid against spec/schemas" + (o.bad.length ? ": " + o.bad.slice(0, 3).join(" | ") : ""));
  let v = validate(t0); check(v.ok, "cof validate: " + v.out);

  /* ---- edit: add, name, show, pick an accessory, remove ---- */
  await page.evaluate(() => go("memories")); await unfold("ev3");
  check(await page.evaluate(() => !S.memories.ev3.node.what) && (await rows("ev3")).length === 0, "ev3 starts without objects (no field written)");
  await page.click(card("ev3") + " [data-axadd=what]"); await page.waitForTimeout(200);
  await setE(card("ev3") + ' [data-axrow=what][data-axi="0"] [data-axlab]', "la lettre"); await setE(card("ev3") + ' [data-axrow=what][data-axi="0"] [data-axflag=shown]', true);
  await page.click(card("ev3") + " [data-axadd=what]"); await page.waitForTimeout(200);
  await page.focus(card("ev3") + ' [data-axrow=what][data-axi="1"] [data-axsel]'); await setE(card("ev3") + ' [data-axrow=what][data-axi="1"] [data-axsel]', "appearance/x2");
  check(await page.evaluate(() => JSON.stringify(S.memories.ev3.node.what)) === JSON.stringify([{ label: { fr: "la lettre" }, shown: true }, { item: "appearance/x2" }]), "a free name in the main language with « montré », then an accessory: " + await page.evaluate(() => JSON.stringify(S.memories.ev3.node.what)));
  await page.click(card("ev2") + ' [data-axrow=what][data-axi="0"] [data-axrm]').catch(async () => { await unfold("ev2"); await page.click(card("ev2") + ' [data-axrow=what][data-axi="0"] [data-axrm]'); }); await page.waitForTimeout(200);
  await unfold("ev1"); await setE(card("ev1") + ' [data-axrow=what][data-axi="0"] [data-axlab]', "le carnet de papier recyclé");
  check(await page.evaluate(() => !("what" in S.memories.ev2.node) && JSON.stringify(S.memories.ev1.node.what) === JSON.stringify([{ label: { fr: "le carnet de papier recyclé", en: "the notebook" } }])), "removing the last object drops `what`; renaming keeps the other languages");
  const t1 = path.join(WORK, "t1-edited.cof"); await build(t1); o = readCof(t1);
  check(same(o.mem.ev3.what, [{ label: { fr: "la lettre" }, shown: true }, { item: "appearance/x2" }]) && !("what" in o.mem.ev2) && o.mem.ev1.what[0].label.en === "the notebook" && !o.bad.length && o.cof === "1.2", "written as `what` in memory.json, absent when empty, schema-valid");
  v = validate(t1); check(v.ok, "cof validate: " + v.out);

  /* ---- checks (RFC 0005 § 2.5) ---- */
  await page.evaluate(() => { S.memories.ev4.node.what = [{}, { item: "appearance/zz" }, { item: "appearance/c1" }, { label: { fr: "la clé" }, shown: true }]; S.memories.ev6.node.who = [...(S.memories.ev6.node.who || []), { label: { fr: "Sam" }, real: true }]; });
  let L = await checks(/memories\.ev[46]/); const has = re => L.some(l => re.test(l));
  check(has(/✖ memories\.ev4\.what\[0\]/) && has(/✖ memories\.ev4\.what\[1\].*appearance\/zz/), "errors: an entry with neither reference nor name, an unresolved item");
  check(has(/memories\.ev4\.what\[2\].*appearance\/c1.*clothing/) && !has(/✖ memories\.ev4\.what\[2\]/) && !has(/ev4\.what\[3\]/) && has(/memories\.ev6\.who\[\d\]/), "warnings: an item that is not an accessory, a real person who is not a character; nothing on a valid entry");
  await page.evaluate(() => { S.memories.ev4.node.what = [{ label: { fr: "la clé" } }]; S.memories.ev6.node.who.pop(); if (!S.memories.ev6.node.who.length) delete S.memories.ev6.node.who; });

  /* ---- a cast file, 1.1: the minor and the other character's elements ---- */
  await open(duo); await page.evaluate(() => go("memories"));
  const duoInfo = await page.evaluate(() => { const own = Object.keys(S.memories).map(v => [v, memOwner(v)]); return { own, clara: own.find(([, i]) => i === "clara-mercier")?.[0] }; });
  const cm = duoInfo.clara;
  const tD0 = path.join(WORK, "d0.cof"); await build(tD0); check(readCof(tD0).cof === "1.1", "the duo built without objects stays 1.1");
  await page.evaluate(() => { const V = S.elements.appearance.variants; V.xc = { kind: "accessory", label: "Carnet", identity: "clara-mercier" }; V.xm = { kind: "accessory", label: "Martian toy", identity: "martien" }; });
  await page.evaluate(() => go("memories")); await unfold(cm);
  await page.click(card(cm) + " [data-axadd=what]"); await page.waitForTimeout(200); await page.focus(card(cm) + ' [data-axrow=what][data-axi="0"] [data-axsel]');
  check(await page.evaluate(c => [...document.querySelector(c + ' [data-axrow=what][data-axi="0"] [data-axsel]').options].map(o => o.value).join(), card(cm)) === ",appearance/xc", "in a cast file the picker lists only that character's accessories");
  await page.evaluate(() => { const V = S.elements.appearance.variants; delete V.xc; delete V.xm; });
  await setE(card(cm) + ' [data-axrow=what][data-axi="0"] [data-axlab]', "le carnet");
  await page.evaluate(c => { S.memories[c].node.what.push({ item: "appearance/env-martien" }); }, cm);
  L = await checks(new RegExp("memories\\." + cm + "\\.what"));
  check(L.some(l => /✖.*what\[1\].*env-martien.*martien/.test(l)) && L.some(l => /what\[1\].*environment/.test(l) && !/✖/.test(l)), "an element of another character: error; not an accessory: warning");
  await page.evaluate(c => { S.memories[c].node.what.pop(); }, cm);
  const tD1 = path.join(WORK, "d1.cof"); await build(tD1); o = readCof(tD1);
  check(o.cof === "1.2" && same(o.mem[cm].what, [{ label: { fr: "le carnet" } }]) && !o.bad.length, "a 1.1 file whose memory gains an object is written as 1.2");
  v = validate(tD1); check(v.ok, "cof validate: " + v.out);

  /* ---- six languages ---- */
  for (const [l, word, add] of [["fr", "🧸 Objets", "+ objet"], ["en", "🧸 Objects", "+ object"], ["de", "🧸 Gegenstände", "+ Gegenstand"], ["es", "🧸 Objetos", "+ objeto"], ["zh", "🧸 物品", "+ 物品"], ["ja", "🧸 物品", "+ 物品"]]) {
    await page.evaluate(x => { setLang(x); go("memories"); }, l); await page.waitForTimeout(150);
    const got = await page.evaluate(c => [document.querySelector(c + " [data-axbox=m] > label").textContent, document.querySelector(c + " [data-axadd=what]").textContent], card(cm));
    check(got[0] === word && got[1] === add, `${l}: ${got.join(" | ")}`);
  }
  await page.evaluate(() => setLang("fr"));
  check(!errors.length, "no page errors" + (errors.length ? ": " + errors.join(" | ") : ""));
  await browser.close(); server.close();
  console.log(ok ? "ALL OK" : "FAILURES"); process.exit(ok ? 0 : 1);
})().catch(e => { console.error(e); server.close(); process.exit(1); });
