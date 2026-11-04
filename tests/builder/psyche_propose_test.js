#!/usr/bin/env node
/* Builder — the psyche converter (docs/psyche-propose.md), end to end in headless Chromium, with a STUBBED gateway (no network).
   Usage: node tests/builder/psyche_propose_test.js [repo-root] [work-dir]
   Needs: playwright (npm i playwright && npx playwright install chromium), python with cof-cli importable from <root>/cli.
   Packs a copy of example 10 (Clara 1.2), serves the repo over HTTP, then: « Proposer une psyché » without a gateway says so and offers
   the paste; with a gateway configured, the fetch to <base>/chat/completions is intercepted and answered with
   tests/fixtures/psyche-propose/clara-proposal.json — the review panel shows one row per candidate, every checkbox off, the duplicate
   flagged; nothing is added until ticked; a contradiction without its side is refused; the ticked rows become cards; the built file
   validates; a pasted proposal breaking the contract is refused; a pasted candidate's until / aware / valence (RFC 0004 § 3 nonies)
   are checked and kept. The inverse: the « Who she is » text rendered by the builder equals
   the section of `cof export --format agent` for three presets, and « append » appends to the card's personality (never replaces).
   The date inputs of a psyche card and of a memory card sit on one line. Exit code 1 on any failure. */
const fs = require("fs"), path = require("path"), http = require("http"), { spawnSync } = require("child_process");
const { chromium } = require("playwright");
const ROOT = path.resolve(process.argv[2] || path.join(__dirname, "..", ".."));
const WORK = path.resolve(process.argv[3] || fs.mkdtempSync(path.join(require("os").tmpdir(), "cof-propose-")));
fs.mkdirSync(WORK, { recursive: true });
let ok = true;
const check = (cond, msg) => { console.log((cond ? "ok   " : "FAIL ") + msg); ok = ok && !!cond; };
const py = (args, cwd) => spawnSync(process.env.PYTHON || "python", args, { encoding: "utf8", cwd });
const CLI = path.join(ROOT, "cli");
function pack(example, out) {
  const src = path.join(WORK, "src-" + example);
  fs.rmSync(src, { recursive: true, force: true });
  fs.cpSync(path.join(ROOT, "spec", "examples", example), src, { recursive: true });
  const r = py(["-m", "cof_cli.cli", "pack", src, "-o", out], CLI);
  if (r.status !== 0) throw new Error("pack failed: " + r.stdout + r.stderr);
}
const validate = file => { const r = py(["-m", "cof_cli.cli", "validate", file], CLI); return { ok: /^OK/m.test(r.stdout), out: r.stdout + r.stderr }; };
function cliWho(file, preset) {
  const out = path.join(WORK, "agent-" + preset);
  fs.rmSync(out, { recursive: true, force: true });
  const r = py(["-m", "cof_cli.cli", "export", file, "--format", "agent", "--preset", preset, "-o", out], CLI);
  if (r.status !== 0) throw new Error("export failed: " + r.stdout + r.stderr);
  const soul = fs.readFileSync(path.join(out, "SOUL.md"), "utf8");
  const i = soul.search(/^## (Who|Qui) /m); if (i < 0) return "";
  const j = soul.indexOf("\n## ", i + 1); return soul.slice(i, j < 0 ? undefined : j);   /* the section ends with one newline: the blank line before the next heading is not part of it */
}
const readManifest = file => JSON.parse(py(["-c", "import json,zipfile,sys;Z=zipfile.ZipFile(sys.argv[1]);m=json.loads(Z.read('manifest.json'));print(json.dumps({'psyche':m['elements'].get('psyche',{}).get('variants',{}),'content':m['tags']['content'],'slots':{p:(v.get('slots') or {}).get('psyche') for p,v in m['presets'].items()},'nodes':{k:json.loads(Z.read(v['node'])) for k,v in m['elements'].get('psyche',{}).get('variants',{}).items()}}))", file]).stdout);
const FIXTURE = JSON.parse(fs.readFileSync(path.join(ROOT, "tests", "fixtures", "psyche-propose", "clara-proposal.json"), "utf8"));
const mime = { ".html": "text/html; charset=utf-8", ".js": "text/javascript", ".json": "application/json", ".css": "text/css", ".svg": "image/svg+xml", ".png": "image/png" };
const server = http.createServer((q, s) => { let f = path.join(ROOT, decodeURIComponent(q.url.split("?")[0])); if (!f.startsWith(ROOT)) { s.writeHead(403); return s.end(); } try { if (fs.statSync(f).isDirectory()) f = path.join(f, "index.html"); } catch (e) {} fs.readFile(f, (e, d) => { if (e) { s.writeHead(404); return s.end(); } s.writeHead(200, { "content-type": mime[path.extname(f)] || "application/octet-stream" }); s.end(d); }); });

(async () => {
  const clara = path.join(WORK, "clara12.cof"); pack("10-clara-mercier", clara);
  await new Promise(r => server.listen(0, r)); const URL = `http://localhost:${server.address().port}/builder/`;
  const browser = await chromium.launch();
  const ctx = await browser.newContext({ viewport: { width: 1400, height: 900 }, acceptDownloads: true });
  const page = await ctx.newPage(); const errors = [];
  page.on("pageerror", e => errors.push(e.message)); page.on("dialog", d => d.accept().catch(() => {}));
  await page.addInitScript(() => { window.__dl = []; const oc = URL.createObjectURL.bind(URL); URL.createObjectURL = b => { window.__dl.push(b); return oc(b); }; HTMLAnchorElement.prototype.click = function () {}; });
  const setE = (sel, v) => page.evaluate(([s, v]) => { const el = document.querySelector(s); if (!el) throw new Error("no " + s); el.value = v; el.dispatchEvent(new Event("input", { bubbles: true })); el.dispatchEvent(new Event("change", { bubbles: true })); }, [sel, v]);
  const open = async file => { await page.evaluate(() => { window.__prev = S.loadedManifest; }); await page.setInputFiles("#fileOpen", file); await page.waitForFunction(() => S.loadedManifest !== window.__prev && !document.getElementById("busy").classList.contains("on"), null, { timeout: 120000 }); await page.waitForTimeout(500); };
  const build = async out => { await page.evaluate(() => { window.__dl.length = 0; go("build"); }); await page.click("#btnBuild"); await page.waitForFunction(() => window.__dl.some(b => b.type === "application/vnd.cof.character+zip"), null, { timeout: 90000 }); const b64 = await page.evaluate(async () => { const b = window.__dl.filter(x => x.type === "application/vnd.cof.character+zip").pop(); const u = new Uint8Array(await b.arrayBuffer()); let s = ""; for (let i = 0; i < u.length; i += 32768) s += String.fromCharCode.apply(null, u.subarray(i, i + 32768)); return btoa(s); }); fs.writeFileSync(out, Buffer.from(b64, "base64")); };
  const dlg = () => page.evaluate(() => ({ on: document.querySelector("#dlg").classList.contains("on"), title: document.querySelector("#dlg h3").textContent, body: document.querySelector("#dlg .dbody").innerText, buttons: [...document.querySelectorAll("#dlg .dbtns button")].map(b => b.textContent) }));
  const press = async label => { await page.evaluate(l => { const b = [...document.querySelectorAll("#dlg .dbtns button")].find(x => x.textContent === l); if (!b) throw new Error("no button " + l); b.click(); }, label); await page.waitForTimeout(250); };
  const nodes = () => page.evaluate(() => Object.keys(S.psyche).length);

  await page.goto(URL, { waitUntil: "load" }); await page.evaluate(() => setMode("advanced"));
  await open(clara); await page.click("#nav button[data-step=psyche]"); await page.waitForTimeout(300);
  check(await page.evaluate(() => !!document.querySelector("#psyList [data-ppropose]") && !!document.querySelector("#psyList [data-ppsoul]")), "the Psyché step shows « Proposer une psyché » and « Texte depuis la psyché »");

  /* ---- the date inputs of a psyche card and of a memory card are on one line ---- */
  await page.evaluate(() => { S._fold["m:psyche:wound1"] = false; renderPsyche(); }); await page.waitForTimeout(200);
  const tops = await page.evaluate(() => { const d = document.querySelector('#psyList .variant[data-vid="wound1"]'); const a = d.querySelector("[data-ps=age]").getBoundingClientRect(), b = d.querySelector("[data-ps=date]").getBoundingClientRect(); return [a.top, b.top, d.querySelector("[data-ps=date]").title]; });
  check(Math.abs(tops[0] - tops[1]) < 2 && /AAAA/.test(tops[2]), `psyche card: « since » age and date inputs aligned (${tops[0].toFixed(1)} / ${tops[1].toFixed(1)}), formats in the tooltip`);
  await page.evaluate(() => { go("memories"); S._fold["m:memories:ev1"] = false; renderMemories(); }); await page.waitForTimeout(300);
  const mtops = await page.evaluate(() => { const d = document.querySelector('#memList .variant[data-vid="ev1"]'); const a = d.querySelector("[data-mw=age]").getBoundingClientRect(), b = d.querySelector("[data-mw=date]").getBoundingClientRect(); return [a.top, b.top]; });
  check(Math.abs(mtops[0] - mtops[1]) < 2, `memory card: « when » age and date inputs aligned (${mtops[0].toFixed(1)} / ${mtops[1].toFixed(1)})`);
  await page.evaluate(() => go("psyche")); await page.waitForTimeout(200);

  /* ---- no gateway: it says so, offers the paste ---- */
  await page.click("#psyList [data-ppropose]"); await page.waitForTimeout(200);
  let d = await dlg();
  check(d.on && /cof psyche propose/.test(d.body) && !d.buttons.includes("Envoyer à l'IA") && d.buttons.includes("Relire le JSON collé"), "without a gateway: the dialog says so, offers the paste, no « send » button");
  await press("Annuler"); check(await nodes() === 23, "cancel: still 23 nodes");

  /* ---- the stubbed gateway ---- */
  const BASE = "https://gateway.stub.test/v1"; let sent = null;
  await page.route(BASE + "/chat/completions", async route => { sent = JSON.parse(route.request().postData()); sent.auth = route.request().headers()["authorization"]; await route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify({ choices: [{ message: { role: "assistant", content: "Voici la proposition :\n```json\n" + JSON.stringify(FIXTURE) + "\n```" } }] }) }); });
  await page.evaluate(() => go("checks")); await setE("#ai_url", BASE + "/"); await setE("#ai_key", "sk-test"); await setE("#ai_model", "stub-model"); await page.evaluate(() => go("psyche")); await page.waitForTimeout(200);
  await page.click("#psyList [data-ppropose]"); await page.waitForTimeout(200);
  d = await dlg(); check(d.buttons.includes("Envoyer à l'IA") && /stub-model/.test(d.body), "with a gateway: model and URL shown, « send » offered");
  await page.selectOption("#dlg [data-pppreset]", "fr-agent"); await press("Envoyer à l'IA");
  await page.waitForFunction(() => document.querySelectorAll("#dlg [data-ppick]").length > 0, null, { timeout: 10000 });
  const b = JSON.parse(sent.messages[1].content.slice(sent.messages[1].content.lastIndexOf("\n") + 1));   /* the prompt, then the bundle as one JSON line */
  check(sent.model === "stub-model" && sent.temperature === 0 && sent.auth === "Bearer sk-test" && sent.messages[0].role === "system" && /strict JSON/.test(sent.messages[0].content), "the request: model, temperature 0, the key as a bearer, the system message");
  check(b.contract === "psyche-propose/0.1" && b.preset === "fr-agent" && b.character.language === "fr" && JSON.stringify(b.languages) === '["fr","en"]' && b.psyche.length === 23, "the bundle: contract, preset, language fr, languages fr + en, 23 existing nodes");
  check(b.personality[0].variant === "p2" && b.personality[0].personality && b.personality[1].language === "en" && b.memories.some(m => m.id === "ev2") && !b.memories.some(m => m.id === "ev12") && b.lists.goals.length === 3, "the bundle: the card first, one English variant, memories without the manga copies, the 1.0 lists");
  const rows = await page.evaluate(() => [...document.querySelectorAll("#dlg .psyprow")].map(r => ({ id: r.dataset.prowC, on: r.querySelector("input").checked, dup: r.classList.contains("dup"), text: r.innerText })));
  check(rows.length === 6 && rows.every(r => !r.on), "review panel: six rows, every checkbox off");
  check(rows[0].dup && /val1/.test(rows[0].text) && !rows[1].dup, "the duplicate of val1 is flagged on c1 only");
  check(/card\.description/.test(rows[2].text) && /fausse mais tenue/.test(rows[2].text) && /inappropri/i.test(rows[4].text) && /brusque|bluntness|rudeness/.test(rows[4].text) && /60/.test(rows[2].text) && /shifting/.test(rows[2].text), "rows carry kind, gist, strength, stability, source, lie, risk and its reason");
  check(await nodes() === 23, "nothing added while the panel is open");
  await press("Ajouter les nœuds cochés"); d = await dlg(); check(/Aucun nœud coché/.test(d.body), "« add » with nothing ticked: says nothing was added"); await press("OK");
  await page.waitForFunction(() => document.querySelectorAll("#dlg [data-ppick]").length === 6); check(await nodes() === 23, "still 23 nodes, the panel is back");
  await page.check('#dlg [data-ppick="c4"]'); await press("Ajouter les nœuds cochés"); d = await dlg();
  check(/c4/.test(d.body) && /c3/.test(d.body), "a contradiction ticked without its side is refused"); await press("Retour à la relecture");
  await page.waitForFunction(() => document.querySelectorAll("#dlg [data-ppick]").length === 6);
  check(await page.evaluate(() => document.querySelector('#dlg [data-ppick="c4"]').checked) && await nodes() === 23, "back to the review with c4 still ticked, nothing added");
  for (const c of ["c2", "c3", "c5"]) await page.check(`#dlg [data-ppick="${c}"]`);
  await press("Ajouter les nœuds cochés"); await page.waitForTimeout(300);
  const added = await page.evaluate(() => { const o = {}; for (const v of ["taste3", "bel5", "contra2", "stance3"]) o[v] = S.psyche[v] ? { kind: S.psyche[v].kind, node: S.psyche[v].node, label: S.psyche[v].label } : null; return { n: Object.keys(S.psyche).length, o, cards: [...document.querySelectorAll("#psyList .variant")].map(x => x.dataset.vid), status: document.querySelector("#psyList [data-ppstatus]")?.textContent || "" }; });
  check(added.n === 27 && Object.values(added.o).every(Boolean), "four ticked candidates became four nodes (taste3, bel5, contra2, stance3): " + added.n);
  check(added.o.bel5.node.false_but_held === true && JSON.stringify(added.o.bel5.node.links) === '[{"to":"memories/ep1","type":"because"}]' && added.o.bel5.node.origin === "authored" && added.o.bel5.node.visibility === "canon" && added.o.bel5.node.since.age.value === 24, "bel5: the lie, because → ep1, authored, canon, since 24");
  check(JSON.stringify(added.o.contra2.node.links) === '[{"to":"psyche/bel5","type":"conflicts"},{"to":"psyche/val1","type":"conflicts"}]', "contra2: the candidate side mapped to bel5, the existing val1 kept");
  check(added.o.stance3.node.about.user === true && added.o.stance3.node.risk === "inappropriate" && added.o.taste3.label.startsWith("Aime le silence"), "stance3 about the user with its risk; labels from the gist");
  check(["taste3", "bel5", "contra2", "stance3"].some(v => added.cards.includes(v)) && /4/.test(added.status), "the new cards are in the list, the status line counts them");
  check(await page.evaluate(() => !S.psyche.val5 && !Object.values(S.psyche).some(m => /La légèreté : faire moins, mieux — une page doit coûter le moins possible à la planète et à celui/.test(m.node.gist.fr || "") && m.label !== S.psyche.val1.label)), "the unticked duplicate c1 was not written");
  const t1 = path.join(WORK, "t1-proposed.cof"); await build(t1); let v = validate(t1); const m1 = readManifest(t1);
  check(v.ok, "built file validates: " + v.out.split("\n").filter(l => /ERROR|^OK|NOT/.test(l)).join(" | "));
  check(Object.keys(m1.psyche).length === 27 && m1.content.includes("psyche-inappropriate") && (m1.slots["fr-agent"] || m1.slots["fr"] || m1.slots["default"] || []).includes("bel5") && !(m1.slots["fr-12"] || []).includes("bel5"), "27 nodes written, the risk tag, fr-agent holds them (its own list or the one it inherits: fr-agent → fr → default) and fr-12 does not");

  /* ---- a pasted proposal that breaks the contract is refused ---- */
  await page.evaluate(() => go("psyche")); await page.click("#psyList [data-ppropose]"); await page.waitForTimeout(200);
  await page.click("#dlg details summary");   /* folded when a gateway is set: the author unfolds it */
  await page.fill("#dlg [data-pppaste]", JSON.stringify({ nodes: [{ id: "c1", kind: "opinion", gist: { fr: "x" }, because: ["memories/ev99"], source: "inferred" }] }));
  await press("Relire le JSON collé"); d = await dlg();
  check(/opinion/.test(d.body) && /ev99/.test(d.body), "a pasted proposal with a bad kind and an unknown memory is refused, both reasons listed");
  await press("OK"); check(await nodes() === 27, "nothing added by a refused proposal");
  /* ---- the optional until / aware / valence of the contract (RFC 0004 § 3 nonies) ---- */
  const G = { fr: "Le café noir du matin, sans sucre, bu debout devant la fenêtre de l'atelier avant que la journée ne commence vraiment.", en: "Black coffee in the morning, no sugar, drunk standing at the studio window before the day really begins." };
  await page.click("#psyList [data-ppropose]"); await page.waitForTimeout(200); await page.click("#dlg details summary");
  await page.fill("#dlg [data-pppaste]", JSON.stringify({ contract: "psyche-propose/0.1", nodes: [{ id: "c1", kind: "belief", gist: G, valence: 20, aware: "maybe", since: { age: { value: 30 } }, until: { age: { value: 25 } }, source: "inferred" }] }));
  await press("Relire le JSON collé"); d = await dlg();
  check(/valence/.test(d.body) && /aware/.test(d.body) && /until/.test(d.body) && /since/.test(d.body), "refused: a valence on a belief, an unknown aware, an until before the since");
  await press("OK");
  await page.click("#psyList [data-ppropose]"); await page.waitForTimeout(200); await page.click("#dlg details summary");
  await page.fill("#dlg [data-pppaste]", JSON.stringify({ contract: "psyche-propose/0.1", nodes: [{ id: "c1", kind: "taste", gist: G, valence: -30, aware: "partly", since: { age: { value: 20 } }, until: { age: { value: 40 } }, source: "inferred" }] }));
  await press("Relire le JSON collé"); await page.waitForFunction(() => document.querySelectorAll("#dlg [data-ppick]").length === 1);
  const row9 = await page.evaluate(() => document.querySelector("#dlg .psyprow").innerText);
  await page.check('#dlg [data-ppick="c1"]'); await press("Ajouter les nœuds cochés"); await page.waitForTimeout(300);
  const t9 = await page.evaluate(() => { const v = Object.keys(S.psyche).pop(); return [v, JSON.stringify([S.psyche[v].node.valence, S.psyche[v].node.aware, S.psyche[v].node.until, S.psyche[v].node.since])]; });
  check(/Valence −30/.test(row9) && /jusqu'à 40/.test(row9) && /Conscience de soi : en partie/.test(row9) && t9[1] === '[-30,"partly",{"age":{"value":40}},{"age":{"value":20}}]', `accepted and kept: the row shows them, ${t9[0]} carries valence, aware and until (${t9[1]})`);

  /* ---- the inverse: the « Who she is » text equals cof-cli's ---- */
  await open(clara); await page.click("#nav button[data-step=psyche]"); await page.waitForTimeout(300);
  for (const pid of ["fr-agent", "default", "en-12"]) {
    const want = cliWho(clara, pid); const got = await page.evaluate(p => psypSoul(p, false, false)[0], pid);
    check(want.length > 200 && got === want, `« Who she is » for ${pid}: the builder renders exactly what cof export --format agent writes (${got.length} / ${want.length} chars)`);
    if (got !== want) { const a = got.split("\n"), w = want.split("\n"); const i = a.findIndex((x, k) => x !== w[k]); console.log("  first difference, line " + i + ":\n  builder: " + a[i] + "\n  cli:     " + w[i]); }
  }
  const before = await page.evaluate(() => S.elements.personality.variants.p2.card.personality);
  await page.click("#psyList [data-ppsoul]"); await page.waitForTimeout(200); await page.selectOption("#dlg [data-pptpreset]", "fr-agent"); await page.waitForTimeout(100);
  const shown = await page.evaluate(() => document.querySelector("#dlg [data-ppttext]").value);
  check(shown === cliWho(clara, "fr-agent"), "the dialog shows the same text");
  await press("Ajouter au champ « Personnalité » de la carte"); await press("OK");
  const after = await page.evaluate(() => S.elements.personality.variants.p2.card.personality);
  check(after.startsWith(before.replace(/\s+$/, "")) && after.trim().endsWith(shown.trim()) && after.length > before.length + 1000, "« append » appends the text after the card's personality (nothing replaced)");
  await page.click("#psyList [data-ppsoul]"); await page.waitForTimeout(200); await page.selectOption("#dlg [data-pptpreset]", "default"); await page.waitForTimeout(100);
  check(await page.evaluate(() => document.querySelector("#dlg .dbtns .btn.primary").disabled), "a preset whose personality is not a card: « append » is disabled (copy only)");
  await press("Fermer");
  /* ---- the six languages: the buttons and the dialog are translated ---- */
  /* ---- the horoscope entry (« Depuis un signe astrologique »): the same table as `cof psyche propose --zodiac`, offline ---- */
  await page.evaluate(() => { setLang("fr"); go("psyche"); }); await page.waitForTimeout(200);
  const nz = await nodes();
  const cliZ = JSON.parse(py(["-c", "import json;from cof_cli import zodiac;print(json.dumps({'v':zodiac.candidates('virgo',['fr','en','de']),'n':len(zodiac.TABLE['virgo'])}))"], CLI).stdout);
  check(await page.evaluate(() => JSON.stringify(psypZodiac("virgo", ["fr", "en", "de"]).nodes)) === JSON.stringify(cliZ.v), "the builder builds Virgo's candidates exactly as cof-cli does (ids, kinds, gists with the English fallback, strength 50, shifting, tag, source)");
  await page.click("#psyList [data-ppropose]"); await page.waitForTimeout(200);
  d = await dlg();
  check(d.on && /Depuis un signe astrologique/.test(d.body) && d.buttons.includes("♈ Proposer depuis le signe"), "the dialog offers « ♈ Depuis un signe astrologique » with its button");
  check(await page.evaluate(() => [...document.querySelectorAll("#dlg .dbtns button")].find(b => b.textContent.startsWith("♈")).disabled), "the button waits for a sign");
  check(await page.evaluate(() => [...document.querySelectorAll("#dlg [data-ppzodiac] option")].length) === 13, "a select of the 12 signs (and its empty choice)");
  await page.selectOption("#dlg [data-ppzodiac]", "virgo");
  check(!(await page.evaluate(() => [...document.querySelectorAll("#dlg .dbtns button")].find(b => b.textContent.startsWith("♈")).disabled)), "a sign chosen: the button is enabled");
  await press("♈ Proposer depuis le signe");
  await page.waitForFunction(() => document.querySelectorAll("#dlg [data-ppick]").length > 0, null, { timeout: 10000 });
  let zrows = await page.evaluate(() => [...document.querySelectorAll("#dlg .psyprow")].map(r => ({ id: r.dataset.prowC, on: r.querySelector("input").checked, text: r.innerText })));
  check(zrows.length === cliZ.n && zrows.every(r => !r.on) && zrows.every(r => /zodiac/.test(r.text)), `the review panel: ${cliZ.n} rows (Virgo), every checkbox off, source zodiac`);
  check(await nodes() === nz, "nothing is written while the panel is open");
  await page.check('#dlg [data-ppick="z1"]'); await press("Ajouter les nœuds cochés"); await page.waitForTimeout(300);
  const zn = await page.evaluate(() => Object.values(S.psyche).filter(m => (m.node.tags || []).includes("zodiac:virgo")).map(m => ({ kind: m.kind, st: m.node.stability, str: m.node.strength, tags: m.node.tags, gist: m.node.gist })));
  check(await nodes() === nz + 1 && zn.length === 1 && zn[0].kind === cliZ.v[0].kind && zn[0].st === "shifting" && zn[0].str === 50 && zn[0].gist.fr === cliZ.v[0].gist.fr && zn[0].gist.en === cliZ.v[0].gist.en, "one ticked row, one node, tag zodiac:virgo, shifting, strength 50, the gists of the table");
  const tz = path.join(WORK, "t2-zodiac.cof"); await build(tz); v = validate(tz);
  check(v.ok, "the file with the zodiac node validates: " + v.out.split("\n").filter(l => /ERROR|^OK|NOT/.test(l)).join(" | "));
  for (const [l, vir] of [["fr", "Vierge"], ["en", "Virgo"], ["de", "Jungfrau"], ["es", "Virgo"], ["zh", "处女座"], ["ja", "乙女座"]]) {
    await page.evaluate(x => { setLang(x); go("psyche"); }, l); await page.waitForTimeout(150);
    await page.click("#psyList [data-ppropose]"); await page.waitForTimeout(150);
    const z = await page.evaluate(() => ({ virgo: document.querySelector('#dlg [data-ppzodiac] option[value="virgo"]').textContent, n: [...document.querySelectorAll("#dlg [data-ppzodiac] option")].filter(o => o.value && o.textContent === o.value).length, btn: [...document.querySelectorAll("#dlg .dbtns button")].map(b => b.textContent).find(t => t.startsWith("♈")) }));
    check(z.virgo === vir && z.n === 0 && z.btn && (l === "fr" || !/Proposer depuis/.test(z.btn)), `${l}: the sign is « ${z.virgo} », the button « ${z.btn} »`);
    await page.keyboard.press("Escape"); await page.waitForTimeout(100);
  }
  await page.evaluate(() => setLang("fr"));
  for (const [l, re] of [["en", /Propose a psyche/], ["de", /Psyche aus der Persönlichkeit/], ["es", /Proponer una psique/], ["zh", /根据性格提议心理/], ["ja", /性格から心理を提案/]]) {
    await page.evaluate(x => { setLang(x); go("psyche"); }, l); await page.waitForTimeout(150);
    const txt = await page.evaluate(() => document.querySelector("#psyList [data-ppropose]").textContent + " | " + document.querySelector("#psyList [data-ppsoul]").textContent);
    check(re.test(txt) && !/Proposer|Texte depuis/.test(txt), `${l}: ${txt}`);
  }
  await page.click("#psyList [data-ppsoul]"); await page.waitForTimeout(200); d = await dlg();
  check(/心理からテキスト/.test(d.title) && d.buttons.includes("カードの「性格」欄に追記"), "ja: the inverse dialog is translated"); await press("閉じる").catch(async () => { await page.keyboard.press("Escape"); });
  await page.evaluate(() => setLang("fr"));
  check(!errors.length, "no page errors" + (errors.length ? ": " + errors.join(" | ") : ""));
  await browser.close(); server.close();
  console.log(ok ? "ALL OK" : "FAILURES"); process.exit(ok ? 0 : 1);
})().catch(e => { console.error(e); server.close(); process.exit(1); });
