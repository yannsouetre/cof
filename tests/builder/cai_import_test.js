#!/usr/bin/env node
/* Builder — import of platform exports (RFC 0006): a CAI Tools card in the Personality step (normalised, « third-party
   rights », imported-character-ai + content-unreviewed, the avatar blocked until it has an age), conversations in the
   Memories step (CAI Tools history zip + SillyTavern chat → one period per platform, personal moment memories with a quoted-Markdown transcript,
   the undated label, the `after` link), a PersonaText file (avatar WebP, its conversation offered as a memory, never in
   the card), the build with and without personal memories, valid with
   `cof validate`, and the translations of the module in en, de, es, zh, ja.
   Usage: node tests/builder/cai_import_test.js [repo-root] [work-dir]. Exit code 1 on any failure. */
const fs = require("fs"), path = require("path"), http = require("http"), { spawnSync } = require("child_process");
const { chromium } = require("playwright");
const ROOT = path.resolve(process.argv[2] || path.join(__dirname, "..", ".."));
const WORK = path.resolve(process.argv[3] || fs.mkdtempSync(path.join(require("os").tmpdir(), "cof-cai-")));
const FX = path.join(ROOT, "tests", "fixtures", "platform-import");
fs.mkdirSync(WORK, { recursive: true });
let ok = true;
const check = (cond, msg) => { console.log((cond ? "ok   " : "FAIL ") + msg); ok = ok && !!cond; };
const py = (args, cwd) => spawnSync(process.env.PYTHON || "python3", args, { encoding: "utf8", cwd: cwd || path.join(ROOT, "cli") });
const readMan = file => JSON.parse(py(["-c", "import json,sys,zipfile;print(json.dumps(json.loads(zipfile.ZipFile(sys.argv[1]).read('manifest.json'))))", file]).stdout);
const zipNames = file => JSON.parse(py(["-c", "import json,sys,zipfile;print(json.dumps(zipfile.ZipFile(sys.argv[1]).namelist()))", file]).stdout);
const validate = file => py(["-m", "cof_cli.cli", "validate", file]);
const mime = { ".html": "text/html; charset=utf-8", ".js": "text/javascript", ".json": "application/json", ".css": "text/css", ".svg": "image/svg+xml", ".png": "image/png" };
const server = http.createServer((q, s) => { let f = path.join(ROOT, decodeURIComponent(q.url.split("?")[0])); if (!f.startsWith(ROOT)) { s.writeHead(403); return s.end(); } try { if (fs.statSync(f).isDirectory()) f = path.join(f, "index.html"); const b = fs.readFileSync(f); s.writeHead(200, { "content-type": mime[path.extname(f)] || "application/octet-stream" }); s.end(b); } catch (e) { s.writeHead(404); s.end(); } });
const b64 = f => fs.readFileSync(f).toString("base64");

(async () => {
  await new Promise(r => server.listen(0, r)); const URL = `http://localhost:${server.address().port}/builder/`;
  const browser = await chromium.launch();
  const page = await (await browser.newContext({ viewport: { width: 1400, height: 900 } })).newPage(); const errors = [];
  page.on("pageerror", e => errors.push(e.message)); page.on("dialog", d => d.accept().catch(() => {}));
  await page.addInitScript(() => { window.__dl = []; const oc = URL.createObjectURL.bind(URL); URL.createObjectURL = b => { window.__dl.push(b); return oc(b); }; HTMLAnchorElement.prototype.click = function () {}; });
  await page.goto(URL); await page.waitForTimeout(600);
  await page.evaluate(() => { try { localStorage.setItem("cof-lang", "en") } catch (e) {} }); await page.reload(); await page.waitForTimeout(800);
  const primary = async () => { await page.waitForSelector("#dlg.on .dbtns .primary", { timeout: 15000 }); const txt = await page.evaluate(() => document.querySelector("#dlg .dbody").innerText); await page.click("#dlg.on .dbtns .primary"); await page.waitForTimeout(150); return txt; };
  const run = async (fn, arg, clicks) => { const p = page.evaluate(fn, arg); const texts = []; for (let i = 0; i < clicks; i++) texts.push(await primary()); await p; return texts; };
  const files = { png: b64(path.join(FX, "caitools-card.png")), zip: b64(path.join(FX, "Wren_Calloway_TavernHistory.zip")), st: b64(path.join(FX, "sillytavern-chat.jsonl")), pt: b64(path.join(FX, "wren.personatext.json")) };
  await page.evaluate(f => { window.__f = (k, name, type) => { const s = atob(f[k]); const u = new Uint8Array(s.length); for (let i = 0; i < s.length; i++) u[i] = s.charCodeAt(i); return new File([u], name, { type }); }; }, files);
  await page.evaluate(() => S.identities[S.defaultIdentity].name = "");

  /* 1. a CAI Tools card in the Personality step */
  await page.evaluate(() => go("elements"));
  const vid = await page.evaluate(() => { const v = addVariant("personality", { kind: "import" }); return v; });
  let t = await run(vid => importInto(vid, __f("png", "Wren_Calloway.png", "image/png")), vid, 1);
  check(/third-party rights/.test(t[0]) && /needs an age/.test(t[0]), "card: the reader is told (rights, the avatar's age) — " + t[0].slice(0, 80));
  const st1 = await page.evaluate(vid => { const v = variants("personality")[vid]; const I = S.identities[S.defaultIdentity]; return { raw: v._raw.data, ip: I.ip, tags: I.tags, name: I.name, faces: Object.entries(variants("appearance")).filter(([, x]) => x.kind === "face").map(([k, x]) => [k, x.age]) }; }, vid);
  check(!("metadata" in st1.raw) && st1.raw.extensions?.cai_tools?.metadata?.tool?.name === "CAI Tools", "card: CAI Tools metadata moved to data.extensions.cai_tools");
  check(st1.ip === "franchise" && /imported-character-ai/.test(st1.tags) && /content-unreviewed/.test(st1.tags) && st1.name === "Wren Calloway", "card: third-party rights, tags, name (" + st1.tags + ")");
  check(st1.faces.length === 1 && st1.faces[0][1] === undefined, "card: the avatar is a face variant, without an age");
  await page.evaluate(() => go("checks")); await page.click("#btnRunChecks"); await page.waitForTimeout(400);
  const ageErr = await page.evaluate(() => [...document.querySelectorAll("#issueList li.err")].map(li => li.textContent).filter(x => /age/.test(x)).length);
  check(ageErr >= 1, "card: the build is blocked until the avatar has an age (" + ageErr + " error)");
  await page.evaluate(fv => { variants("appearance")[fv].age = 30; }, st1.faces[0][0]);

  /* 2. conversations in the Memories step */
  await page.evaluate(() => go("memories")); await page.waitForTimeout(300);
  check(await page.evaluate(() => !!document.querySelector("#memList [data-caiimp]")), "memories: the « Import conversations » button is there");
  t = await run(() => caiImportChats([__f("zip", "Wren_Calloway_TavernHistory.zip", "application/zip"), __f("st", "sillytavern-chat.jsonl", "application/jsonl")]), null, 2);
  check(/3 conversation\(s\)/.test(t[0]) && /each becomes a personal memory/.test(t[0]), "memories: the summary before importing — " + t[0].split("\n")[0]);
  const mem = await page.evaluate(() => Object.fromEntries(Object.entries(S.memories).map(([k, m]) => [k, { kind: m.kind, label: m.label, vis: m.node.visibility, origin: m.node.origin, disc: m.node.disclosure, when: m.node.when, links: m.node.links, media: m.media.map(a => [a.path, a.mediaType, a.license, a.language]) }])));
  const ids = Object.keys(mem).filter(k => mem[k].kind === "moment"), per = Object.keys(mem).filter(k => mem[k].kind === "period");
  check(ids.length === 3 && per.length === 2 && Object.keys(mem).every(k => mem[k].vis === "personal" && mem[k].origin === "lived" && mem[k].disc === "guarded"), "memories: one period per platform, 3 conversation moments, all personal, lived, guarded (" + Object.keys(mem).join(",") + ")");
  check(mem[ids[0]].when?.date === "2026-11-02" && /^Chat \d+ · /.test(mem[ids[1]].label), "memories: the dated SillyTavern chat comes first, with its day; moments titled from their first message");
  const caiP = per.find(k => mem[k].label === "Conversations on Character.AI");
  check(caiP && /between 2022 and 2026/.test(JSON.stringify(mem[caiP].when)) && mem[caiP].when.from?.date === "2022" && mem[caiP].when.from.approx === true && mem[caiP].when.to?.approx === true && !mem[ids[1]].when?.date, "memories: the Character.AI period spans 2022 → the export year, both bounds approximate, with its label; its chats carry no date");
  check(JSON.stringify(mem[ids[2]].links) === JSON.stringify([{ to: "memories/" + caiP, type: "part-of" }, { to: "memories/" + ids[1], type: "after" }]), "memories: part-of the period, `after` between the two chats of the history zip");
  check(ids.every(k => mem[k].media.length === 1 && mem[k].media[0][1] === "text/markdown" && mem[k].media[0][2] === "LicenseRef-Personal"), "memories: one Markdown transcript each, personal licence");
  const md = await page.evaluate(async p => await S.memFiles.get(p).text(), mem[ids[0]].media[0][0]);
  check(md.startsWith("---\ncof_transcript: 1\n") && /\n## 2 · Sam · 2026-11-02T18:05:02Z\n> I lost the teapot island\./.test(md) && /## 4 · \[note\]/.test(md), "memories: the transcript layout (front matter, headings, quoted lines)");

  /* 3. PersonaText in the Personality step: avatar WebP, its conversation offered as a memory */
  await page.evaluate(() => go("elements"));
  const vid2 = await page.evaluate(() => addVariant("personality", { kind: "import" }));
  t = await run(vid => importInto(vid, __f("pt", "wren.personatext.json", "application/json")), vid2, 3);
  check(/also holds a conversation/.test(t[0]), "PersonaText: the conversation is offered as a personal memory");
  const st3 = await page.evaluate(vid => ({ raw: JSON.stringify(variants("personality")[vid]._raw), faces: Object.values(variants("appearance")).filter(x => x.kind === "face").length, mems: Object.keys(S.memories).length }), vid2);
  check(!/chat_history|avatar_data_url|teapot island/.test(st3.raw), "PersonaText: neither the conversation nor the base64 avatar in the card");
  check(st3.faces === 2 && st3.mems === 6, "PersonaText: a second face (WebP avatar) and a fourth conversation, in the existing Character.AI period (" + st3.faces + ", " + st3.mems + ")");
  await page.evaluate(() => { for (const [k, v] of Object.entries(variants("appearance"))) if (v.kind === "face" && v.age === undefined) v.age = 30; });

  /* 5. build: personal memories left out by default, kept on request; valid */
  await page.evaluate(() => go("checks")); await page.click("#btnRunChecks"); await page.waitForTimeout(400);
  const errs = await page.evaluate(() => [...document.querySelectorAll("#issueList li.err")].map(li => li.textContent));
  check(errs.length === 0, "checks before the build: no error " + errs.join(" | "));
  const build = async out => { await page.evaluate(() => { window.__dl.length = 0; go("build"); }); await page.click("#btnBuild"); for (let i = 0; i < 300; i++) { if (await page.evaluate(() => window.__dl.some(b => b.type === "application/vnd.cof.character+zip"))) break; if (await page.evaluate(() => document.querySelector("#dlg").classList.contains("on"))) { console.log("     (build dialog: " + (await page.evaluate(() => document.querySelector("#dlg .dbody").innerText)).slice(0, 160).replace(/\n/g, " ") + ")"); await page.click("#dlg.on .dbtns .primary"); } await page.waitForTimeout(300); } const b = await page.evaluate(async () => { const b = window.__dl.filter(x => x.type === "application/vnd.cof.character+zip").pop(); const u = new Uint8Array(await b.arrayBuffer()); let s = ""; for (let i = 0; i < u.length; i += 32768) s += String.fromCharCode.apply(null, u.subarray(i, i + 32768)); return btoa(s); }); fs.writeFileSync(out, Buffer.from(b, "base64")); };
  const o1 = path.join(WORK, "shared.cof"); await build(o1);
  let m = readMan(o1); let names = zipNames(o1);
  check(!m.elements.memories && !names.some(n => n.startsWith("elements/memories/")), "build (default): no personal memory, no transcript in the shared file");
  check(m.tags.ip.original === false && m.tags.manual.includes("content-unreviewed"), "build: tags.ip.original false, content-unreviewed kept");
  let v = validate(o1); check(v.status === 0, "build (default): cof validate OK " + (v.status ? v.stdout.split("\n").filter(l => /ERROR/.test(l)).join(" | ") : ""));
  await page.evaluate(() => { go("build"); const c = document.querySelector("#b_mem_droppers"); if (c && c.checked) c.click(); });
  const o2 = path.join(WORK, "mine.cof"); await build(o2);
  m = readMan(o2); names = zipNames(o2);
  check(Object.keys(m.elements.memories?.variants || {}).length === 6 && names.filter(n => /elements\/memories\/ev\d+\/chat-\d+\.md$/.test(n)).length === 4, "build (keep personal): 2 periods, 4 conversations and their transcripts");
  const cards = names.filter(n => /personality\/.*card\.json$/.test(n)).map(n => py(["-c", "import sys,zipfile;print(zipfile.ZipFile(sys.argv[1]).read(sys.argv[2]).decode())", o2, n]).stdout).join("");
  check(!/chat_history|avatar_data_url/.test(cards), "build: no card carries a conversation, even when personal data are kept");
  v = validate(o2); check(v.status === 0, "build (keep personal): cof validate OK " + (v.status ? v.stdout.split("\n").filter(l => /ERROR/.test(l)).join(" | ") : ""));

  /* 6. the Personality step: a chat under any key leaves the card; the avatar's base64 stays as it is */
  await page.reload(); await page.waitForTimeout(800);
  await page.evaluate(() => go("elements"));
  const clean = JSON.stringify({ spec: "chara_card_v2", spec_version: "2.0", data: { name: "Wren", description: "A cartographer.", first_mes: "Hi.", chat: [{ text: "my secret is 4242" }],
    extensions: { source: "character.ai", avatar_data_url: "data:image/webp;base64,AAAA+nu+kid/9yo+AAAA", character_ai: {} } } });
  const vid5 = await page.evaluate(() => addVariant("personality", { kind: "import" }));
  t = await run(([vid, c]) => importInto(vid, new File([c], "w.personatext.json")), [vid5, clean], 1);
  const r8 = await page.evaluate(vid => JSON.stringify(variants("personality")[vid]._raw || {}), vid5);
  check(r8.includes("A cartographer.") && !r8.includes("4242"), "PersonaText: a chat under another key leaves the card");

  /* 8 bis. the all-audiences purge (psyche b77fee4) drops « sexual » with the intimate variants, but a card whose own text
     is sexual keeps the tag: its words stay in the file (called directly: the purge runs inside the build) */
  const kept = await page.evaluate(() => { const card = { spec: "chara_card_v3", data: { name: "Ada", description: "An adult novelist who writes erotic fiction." } };
    const mk = c => ({ name: "elements/personality/p1/card.json", data: new TextEncoder().encode(JSON.stringify(c)) });
    const m1 = { elements: { appearance: { variants: { x: { kind: "intimate" } } } }, presets: {}, tags: { content: ["sexual", "nudity"] }, assets: [] }; stripIntimateBuild(m1, [mk(card)]);
    const m2 = { elements: { appearance: { variants: { x: { kind: "intimate" } } } }, presets: {}, tags: { content: ["sexual", "nudity"] }, assets: [] }; stripIntimateBuild(m2, [mk({ spec: "chara_card_v3", data: { name: "Ada", description: "A cartographer." } })]);
    return [m1.tags.content, m2.tags.content]; });
  check(JSON.stringify(kept[0]) === JSON.stringify(["sexual"]) && JSON.stringify(kept[1]) === JSON.stringify(["none"]), "all-audiences purge: a card whose text is sexual keeps « sexual », a clean one gets « none » (" + JSON.stringify(kept) + ")");

  /* 9. translations */
  const miss = await page.evaluate(() => { const fr = ["Importer des conversations", "Votre nom dans les conversations", "Personnage importé", "Conversations importées", "Ce fichier contient aussi une conversation : l'importer comme souvenir personnel (jamais dans la carte) ?"]; return ["en", "de", "es", "zh", "ja"].flatMap(l => fr.filter(k => !(I18N[l] && I18N[l][k])).map(k => l + ":" + k.slice(0, 20))); });
  check(miss.length === 0, "translations in en, de, es, zh, ja " + miss.join(","));
  check(errors.length === 0, "no page errors " + errors.join(" | "));
  await browser.close(); server.close();
  console.log(ok ? "ALL OK" : "SOME CHECKS FAILED"); process.exit(ok ? 0 : 1);
})().catch(e => { console.error(e); process.exit(1); });
