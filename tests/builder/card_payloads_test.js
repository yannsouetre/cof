#!/usr/bin/env node
/* Builder — a card that carries a user's conversation (PersonaText's data.extensions.chat_history) and a base64 avatar
   (avatar_data_url): the import leaves both out of the variant (never kept in v._raw, so never written by the build), says so
   in the reader's language, and keeps the rest of the card (character_book, extensions.character_ai, creator); a card that
   still holds a chat (a file built by the builder ≤ 1.1.1) draws a « minor » check, like `cof validate`.
   Usage: node tests/builder/card_payloads_test.js [repo-root] [work-dir]. Exit code 1 on any failure. */
const fs = require("fs"), path = require("path"), http = require("http"), { spawnSync } = require("child_process");
const { chromium } = require("playwright");
const ROOT = path.resolve(process.argv[2] || path.join(__dirname, "..", ".."));
const WORK = path.resolve(process.argv[3] || fs.mkdtempSync(path.join(require("os").tmpdir(), "cof-cardpay-")));
fs.mkdirSync(WORK, { recursive: true });
let ok = true;
const check = (cond, msg) => { console.log((cond ? "ok   " : "FAIL ") + msg); ok = ok && !!cond; };
const py = (args, cwd) => spawnSync(process.env.PYTHON || "python", args, { encoding: "utf8", cwd });
const src = path.join(WORK, "src"); fs.rmSync(src, { recursive: true, force: true });
fs.cpSync(path.join(ROOT, "spec", "examples", "10-clara-mercier"), src, { recursive: true });
const clara = path.join(WORK, "clara.cof");
let r = py(["-m", "cof_cli.cli", "pack", src, "-o", clara], path.join(ROOT, "cli")); if (r.status !== 0) throw new Error(r.stdout + r.stderr);
const CARD = { spec: "chara_card_v2", spec_version: "2.0", data: { name: "Wren Calloway", description: "A lighthouse keeper.", personality: "Calm.", first_mes: "You made it.", creator: "someone",
  character_book: { name: "Wren's lore", entries: [{ keys: ["lighthouse"], content: "Built in 1890.", enabled: true, insertion_order: 0 }] },
  extensions: { character_ai: { external_id: "abc123" }, chat_history: [{ role: "user", content: "My name is Paul, I live in Lyon.", timestamp: 1730000000000 }, { role: "assistant", content: "Welcome, Paul.", timestamp: 1730000005000 }],
    avatar_data_url: "data:image/png;base64," + "A".repeat(4000) } } };
const mime = { ".html": "text/html; charset=utf-8", ".js": "text/javascript", ".json": "application/json", ".css": "text/css", ".svg": "image/svg+xml", ".png": "image/png" };
const server = http.createServer((q, s) => { let f = path.join(ROOT, decodeURIComponent(q.url.split("?")[0])); if (!f.startsWith(ROOT)) { s.writeHead(403); return s.end(); } try { if (fs.statSync(f).isDirectory()) f = path.join(f, "index.html"); const b = fs.readFileSync(f); s.writeHead(200, { "content-type": mime[path.extname(f)] || "application/octet-stream" }); s.end(b); } catch (e) { s.writeHead(404); s.end(); } });

(async () => {
  await new Promise(r => server.listen(0, r)); const URL = `http://localhost:${server.address().port}/builder/`;
  const browser = await chromium.launch();
  const ctx = await browser.newContext({ viewport: { width: 1400, height: 900 } });
  const page = await ctx.newPage(); const errors = [], dialogs = [];
  page.on("pageerror", e => errors.push(e.message)); page.on("dialog", d => { dialogs.push(d.message()); d.accept().catch(() => {}); });
  await page.addInitScript(() => { window.__dl = []; const oc = URL.createObjectURL.bind(URL); URL.createObjectURL = b => { window.__dl.push(b); return oc(b); }; HTMLAnchorElement.prototype.click = function () {}; });
  await page.goto(URL); await page.waitForTimeout(800);
  await page.evaluate(() => { try { localStorage.setItem("cof-lang", "en") } catch (e) {} }); await page.reload(); await page.waitForTimeout(800);
  await page.setInputFiles("#fileOpen", clara); await page.waitForFunction(() => S.loadedManifest && Object.keys(variants("personality")).length > 0, null, { timeout: 60000 }); await page.waitForTimeout(800);
  const vid = await page.evaluate(() => Object.entries(variants("personality")).find(([, v]) => v.kind === "card")[0]);

  /* 1. import into the card variant */
  dialogs.length = 0;
  await page.evaluate(async ([vid, json]) => { await importInto(vid, new File([json], "wren.personatext.json", { type: "application/json" })); }, [vid, JSON.stringify(CARD)]);
  const raw = await page.evaluate(vid => JSON.stringify(variants("personality")[vid]._raw), vid);
  check(!raw.includes("chat_history") && !raw.includes("avatar_data_url") && !raw.includes("Paul"), "import: neither chat_history nor avatar_data_url kept in the variant");
  const kept = JSON.parse(raw).data;
  check(kept.character_book?.entries?.[0]?.content === "Built in 1890." && kept.extensions?.character_ai?.external_id === "abc123" && kept.creator === "someone", "import: character_book, extensions.character_ai, creator intact");
  check(dialogs.some(m => /^Embedded chat \/ avatar not imported: a user's personal data, not part of the character\. \(data\.extensions\.chat_history, data\.extensions\.avatar_data_url\)$/.test(m)), "import: the reader is told, in English (" + dialogs.join(" | ") + ")");
  const built = await page.evaluate(vid => JSON.stringify(buildCard(variants("personality")[vid], "Wren")), vid);
  check(!built.includes("chat_history") && !built.includes("avatar_data_url") && built.includes("Built in 1890."), "build: the card written has no chat / avatar, keeps its lore");
  const call = await page.evaluate(() => JSON.stringify(CARD_PAYLOADS)); check(call === '["chat_history","avatar_data_url"]', "same keys as cof-cli convert.CARD_PAYLOADS");

  /* 2. a card that still holds a chat (≤ 1.1.1) → minor check */
  await page.evaluate(vid => { const v = variants("personality")[vid]; v._raw.data.extensions.chat_history = [{ role: "user", content: "hi" }]; }, vid);
  await page.evaluate(() => go("checks")); await page.click("#btnRunChecks"); await page.waitForTimeout(400);
  const lines = (await page.evaluate(() => document.querySelector("#issueList").innerText)).split("\n").filter(l => /chat_history/.test(l));
  check(lines.length === 1 && /a user's conversation/.test(lines[0]) && /re-import the original card/.test(lines[0]), "checks: one line for a chat kept in a card (" + lines.join(" | ") + ")");
  const sev = await page.evaluate(() => [...document.querySelectorAll("#issueList li")].filter(li => /chat_history/.test(li.textContent)).map(li => li.className).join(","));
  check(sev === "sev-minor", "checks: a « minor » warning, never an error (" + sev + ")");

  /* 3. the message in the five other languages */
  const tr = await page.evaluate(() => ["en", "de", "es", "zh", "ja"].map(l => [l, ...["Conversation et avatar intégrés à la carte non importés : les données personnelles d'un utilisateur, qui ne font pas partie du personnage.", "la carte contient la conversation d'un utilisateur (data.extensions.chat_history) — une donnée personnelle, qui partirait avec la carte : réimportez la carte d'origine pour la retirer"].map(k => !!(I18N[l] && I18N[l][k]))]).filter(x => !x[1] || !x[2]).map(x => x[0]));
  check(tr.length === 0, "both strings in en, de, es, zh, ja " + tr.join(","));
  check(errors.length === 0, "no page errors " + errors.join(" | "));
  await browser.close(); server.close();
  console.log(ok ? "ALL OK" : "SOME CHECKS FAILED"); process.exit(ok ? 0 : 1);
})().catch(e => { console.error(e); process.exit(1); });
