#!/usr/bin/env node
/* import/ — the Character.AI → COF page (three steps). Checks: the page is up to date with the builder's shared blocks
   (gen.py --check), it opens offline from file://, the six languages are complete, files dropped at once (CAI Tools PNG
   card + history zip + SillyTavern chat) give the right check step, the avatar needs an age (or « without the avatar »),
   the private .cof (conversations as personal moments, one period per platform) and the shareable copy (none) are valid with
   `cof validate`, the memories and transcripts are the ones `cof import` writes for the same files, PersonaText (WebP
   avatar, its chat never in the card), the age rule on content, account files never read, the content tick, the edited name.
   Usage: node tests/builder/import_page_test.js [repo-root] [work-dir]. Exit code 1 on any failure. */
const fs = require("fs"), path = require("path"), http = require("http"), os = require("os"), { spawnSync } = require("child_process");
const { chromium } = require("playwright");
const ROOT = path.resolve(process.argv[2] || path.join(__dirname, "..", ".."));
const WORK = path.resolve(process.argv[3] || fs.mkdtempSync(path.join(os.tmpdir(), "cof-imp-")));
const FX = path.join(ROOT, "tests", "fixtures", "platform-import");
fs.mkdirSync(WORK, { recursive: true });
let ok = true;
const check = (cond, msg) => { console.log((cond ? "ok   " : "FAIL ") + msg); ok = ok && !!cond; };
const PY = process.env.PYTHON || "python3";
const py = (args, cwd) => spawnSync(PY, args, { encoding: "utf8", cwd: cwd || path.join(ROOT, "cli") });
const zread = (file, name) => py(["-c", "import sys,zipfile;sys.stdout.write(zipfile.ZipFile(sys.argv[1]).read(sys.argv[2]).decode('utf-8'))", file, name]).stdout;
const zbytes = (file, name) => Buffer.from(py(["-c", "import sys,zipfile,base64;sys.stdout.write(base64.b64encode(zipfile.ZipFile(sys.argv[1]).read(sys.argv[2])).decode())", file, name]).stdout, "base64");
const zipNames = file => JSON.parse(py(["-c", "import json,sys,zipfile;print(json.dumps(zipfile.ZipFile(sys.argv[1]).namelist()))", file]).stdout);
const validate = file => py(["-m", "cof_cli.cli", "validate", file]);
const mime = { ".html": "text/html; charset=utf-8", ".js": "text/javascript", ".json": "application/json", ".svg": "image/svg+xml", ".png": "image/png" };
const server = http.createServer((q, s) => { let f = path.join(ROOT, decodeURIComponent(q.url.split("?")[0])); if (!f.startsWith(ROOT)) { s.writeHead(403); return s.end(); } try { if (fs.statSync(f).isDirectory()) f = path.join(f, "index.html"); const b = fs.readFileSync(f); s.writeHead(200, { "content-type": mime[path.extname(f)] || "application/octet-stream" }); s.end(b); } catch (e) { s.writeHead(404); s.end(); } });

(async () => {
  /* 0. generated from the template and the builder's shared blocks */
  const g = py([path.join(ROOT, "tools", "import-page", "gen.py"), "--check"], ROOT);
  check(g.status === 0, "import/index.html is up to date with builder/index.html and the template (" + (g.stdout + g.stderr).trim() + ")");

  await new Promise(r => server.listen(0, r)); const BASE = `http://localhost:${server.address().port}/import/`;
  const browser = await chromium.launch();
  const newPage = async (lang) => {
    const ctx = await browser.newContext({ viewport: { width: 1200, height: 900 }, acceptDownloads: true });
    const page = await ctx.newPage(); page.errors = [];
    page.on("pageerror", e => page.errors.push(e.message)); page.on("dialog", d => d.accept().catch(() => {}));
    await page.addInitScript(l => { try { localStorage.setItem("cofi-lang", l) } catch (e) {} }, lang || "en");
    await page.goto(BASE); await page.waitForTimeout(400); return page;
  };
  const drop = async (page, files) => { await page.setInputFiles("#file", files); await page.waitForFunction(() => window.cofImport.ST.ready || document.querySelectorAll("#files li").length > 0, null, { timeout: 15000 }); await page.waitForTimeout(300); };
  const download = async (page, btn, name) => {
    const [d] = await Promise.all([page.waitForEvent("download", { timeout: 15000 }), page.click(btn)]);
    const out = path.join(WORK, name); await d.saveAs(out); return { out, suggested: d.suggestedFilename() };
  };

  /* 1. offline, from file:// (the page is one file; only the icon and fonts are outside) */
  {
    const ctx = await browser.newContext(); const p = await ctx.newPage(); const errs = []; p.on("pageerror", e => errs.push(e.message));
    await p.route(/^https?:/, r => r.abort()); await p.goto("file://" + path.join(ROOT, "import", "index.html")); await p.waitForTimeout(300);
    check(errs.length === 0 && await p.evaluate(() => typeof CAI === "object" && typeof zipBuild === "function" && typeof selfDescription === "function"), "opens offline from file:// with the shared code (" + errs.join(" | ") + ")");
    await ctx.close();
  }

  /* 2. the six languages: every visible text is translated, none left in French outside French */
  {
    const page = await newPage("en");
    const miss = await page.evaluate(() => { const out = []; for (const l of ["en", "de", "es", "zh", "ja"]) { document.querySelector("#lang").value = l; document.querySelector("#lang").dispatchEvent(new Event("change")); for (const el of document.querySelectorAll("[data-t]")) if (el.textContent.trim() === el.dataset.t && !/^h\d$/.test(el.dataset.t)) out.push(l + ":" + el.dataset.t.slice(0, 30)); } return out; });
    check(miss.length === 0, "en, de, es, zh, ja: every text of the page translated (" + miss.slice(0, 5).join(" | ") + ")");
    const fr = await page.evaluate(() => { document.querySelector("#lang").value = "fr"; document.querySelector("#lang").dispatchEvent(new Event("change")); return [document.querySelector("h1").textContent, document.querySelector("[data-t=h3]").innerHTML]; });
    check(fr[0] === "Sauvez vos personnages Character.AI" && /export officiel/.test(fr[1]), "fr: the page in French, help included");
    const ja = await page.evaluate(() => { document.querySelector("#lang").value = "ja"; document.querySelector("#lang").dispatchEvent(new Event("change")); return [document.documentElement.lang, document.querySelector("h1").textContent]; });
    check(ja[0] === "ja" && /キャラクター/.test(ja[1]), "ja: html lang and title follow the choice");
    check(page.errors.length === 0, "no page error while switching languages (" + page.errors.join(" | ") + ")");
    await page.context().close();
  }

  /* 3. CAI Tools card + history zip + SillyTavern chat, at once */
  const FILES = [path.join(FX, "caitools-card.png"), path.join(FX, "Wren_Calloway_TavernHistory.zip"), path.join(FX, "sillytavern-chat.jsonl")];
  let mine, share;
  {
    const page = await newPage("en");
    check(await page.evaluate(() => document.querySelector("#s2").classList.contains("off") && document.querySelector("#s3").classList.contains("off")), "steps 2 and 3 wait for files");
    await drop(page, FILES);
    const st = await page.evaluate(() => ({ name: document.querySelector("#name").value, av: !document.querySelector("#av").hidden, age: !document.querySelector("#ageBox").hidden, chats: document.querySelectorAll("#chats > li:not(.hint)").length, lang: document.querySelector("#clang").value, persona: document.querySelector("#persona").value, files: [...document.querySelectorAll("#files li")].map(li => li.textContent), on: !document.querySelector("#s2").classList.contains("off"), share: !document.querySelector("#dlShare").hidden }));
    check(st.on && st.name === "Wren Calloway" && st.av && st.age, "step 2: the character's name from the card, its avatar shown with the age field");
    check(st.chats === 3 && st.lang === "en", "step 2: three conversations listed (two from the zip, one SillyTavern), language detected en");
    check(st.files.length === 3 && st.files[0].includes("character card") && /2 conversation/.test(st.files[1]) && /1 conversation/.test(st.files[2]), "step 1: each file listed with what it is (card, 2 conversations, 1 conversation)");
    const undated = await page.evaluate(() => [...document.querySelectorAll("#chats .meta")].map(x => x.textContent));
    check(undated.filter(x => /undated/.test(x)).length === 2 && undated.some(x => /2026-11-02/.test(x)), "the CAI Tools chats show « undated », the SillyTavern one its dates");
    /* no age: refused, nothing downloaded */
    await page.click("#dlMine"); await page.waitForTimeout(300);
    check(/avatar's age/.test(await page.textContent("#dlNote")), "without an age the download is refused and says why");
    check(await page.evaluate(() => document.activeElement.id === "age" && document.querySelector("#age").classList.contains("need") && document.querySelector("#ageWhy").classList.contains("need")), "… and the age field is focused and marked in red, its hint too (visual test, 5 Nov)");
    await page.fill("#age", "30");
    mine = await download(page, "#dlMine", "wren-mine.cof");
    check(mine.suggested === "Wren-Calloway.cof", "the private file is named after the character (" + mine.suggested + ")");
    share = await download(page, "#dlShare", "wren-share.cof");
    check(share.suggested === "Wren-Calloway-without-conversations.cof", "the copy without conversations says so in its name");
    check(page.errors.length === 0, "no page error (" + page.errors.join(" | ") + ")");
    await page.context().close();
  }
  {
    const v = validate(mine.out); check(v.status === 0 && /\bOK\b/.test(v.stdout), "private .cof: cof validate OK" + (v.status ? " — " + (v.stdout + v.stderr).slice(-600) : ""));
    const names = zipNames(mine.out); const m = JSON.parse(zread(mine.out, "manifest.json"));
    check(names[0] === "mimetype" && zread(mine.out, "mimetype") === "application/vnd.cof.character+zip" && names[1] === "manifest.json" && names.includes("COF.md"), "container: mimetype first, then manifest.json, COF.md");
    const mem = m.elements.memories && m.elements.memories.variants || {};
    const per = Object.keys(mem).filter(k => mem[k].kind === "period"), mom = Object.keys(mem).filter(k => mem[k].kind === "moment");
    check(per.length === 2 && mom.length === 3 && m.cof === "1.1" && m.presets.default.slots.memories.length === 5, "one period per platform (SillyTavern, Character.AI), three conversation moments, cof 1.1, in the default preset");
    check(mom.every(k => /^Chat \d+ · /.test(mem[k].label)) && per.some(k => mem[k].label === "Conversations on Character.AI"), "moments titled from their first message (« Chat 2 · I think it was… »), periods « Conversations on … »");
    const nodes = Object.keys(mem).map(k => JSON.parse(zread(mine.out, mem[k].memory)));
    check(nodes.every(n => n.kind === undefined && n.origin === "lived" && n.visibility === "personal" && n.disclosure === "guarded"), "each memory is lived, personal, guarded (RFC 0006 § 3.2)");
    const node = k => JSON.parse(zread(mine.out, mem[k].memory)); const caiP = per.find(k => mem[k].label === "Conversations on Character.AI");
    check(/between 2022 and/.test(node(caiP).when.label.en) && mom.every(k => node(k).links[0].type === "part-of") && mom.filter(k => node(k).links[0].to === "memories/" + caiP).every(k => !node(k).when) && mom.some(k => node(k).when && node(k).when.date === "2026-11-02"), "the Character.AI period carries the « between 2022 and … » label; its undated chats are moments part-of it, without any date; a dated chat keeps its day");
    const tr = names.filter(n => /chat-\d+\.md$/.test(n)); const t1 = zread(mine.out, tr[0]);
    check(tr.length === 3 && /^---\ncof_transcript: 1\n/.test(t1) && /exported_by: cof-import-page/.test(t1) && /\n> /.test(t1), "transcripts in quoted Markdown, front matter cof_transcript: 1, written by the import page");
    check(m.assets.filter(a => a.role === "memory-media").every(a => a.license === "LicenseRef-Personal" && a.mediaType === "text/markdown"), "transcript assets: memory-media, LicenseRef-Personal");
    check(m.tags.manual.includes("imported-character-ai") && m.tags.manual.includes("content-unreviewed") && m.tags.ip.original === false, "tags: imported-character-ai, content-unreviewed, ip.original false");
    check(m.rights.permissions.allowRedistribution === false && m.rights.permissions.allowTraining === "none", "rights: conservative defaults (no redistribution, no training)");
    const f1 = m.elements.appearance.variants.f1; check(f1.kind === "face" && f1.age.value === 30 && m.presets.default.age_override.value === 30, "avatar kept as a face with the age given");
    const png = zbytes(mine.out, "elements/appearance/f1/head.front.png").toString("latin1");
    check(!/chara\0|ccv3\0/.test(png), "the avatar PNG no longer carries the card text (chara / ccv3)");
    const card = JSON.parse(zread(mine.out, "elements/personality/p1/card.json"));
    check(card.spec === "chara_card_v3" && card.data.name === "Wren Calloway" && !card.data.metadata && card.data.extensions && card.data.extensions.cai_tools, "card: V3, CAI Tools foreign keys moved to extensions.cai_tools");
    check(!/chat_history|avatar_data_url/.test(JSON.stringify(card)), "card: no conversation, no embedded avatar");
    const md = zread(mine.out, "COF.md"); check(/Memories/.test(md) && /import page/.test(md), "COF.md describes the memories and names the import page");

    const vs = validate(share.out); check(vs.status === 0, "shareable copy: cof validate OK");
    const sn = zipNames(share.out); const sm = JSON.parse(zread(share.out, "manifest.json"));
    check(!sn.some(n => /memories|chat-/.test(n)) && !sm.elements.memories && !sm.assets.some(a => a.role === "memory-media"), "shareable copy: no memory, no transcript, no trace in the manifest");
    check(sm.elements.appearance && sm.elements.personality, "shareable copy: the character and its avatar are there");

    /* the same files through `cof import`: same memories, same transcripts (except the writer's name) */
    const cli = path.join(WORK, "cli-out"); fs.rmSync(cli, { recursive: true, force: true });
    const r = py(["-m", "cof_cli.cli", "import", ...FILES, "-o", cli, "--age", "30"]);
    check(r.status === 0, "cof import on the same files");
    const cm = JSON.parse(fs.readFileSync(path.join(cli, "manifest.json"), "utf8"));
    const cv = cm.elements.memories.variants;
    check(JSON.stringify(Object.keys(cv).sort()) === JSON.stringify(Object.keys(mem).sort()), "same memory ids as cof import");
    let sameNodes = true, sameTr = true, why = [];
    for (const k of Object.keys(cv)) {
      const a = JSON.parse(fs.readFileSync(path.join(cli, cv[k].memory), "utf8")), b = JSON.parse(zread(mine.out, mem[k].memory));
      if (JSON.stringify(a) !== JSON.stringify(b)) { sameNodes = false; why.push(k + ": " + JSON.stringify(a).slice(0, 200) + " ≠ " + JSON.stringify(b).slice(0, 200)); }
      for (const aid of cv[k].media || []) { const ca = cm.assets.find(x => x.id === aid); const x = fs.readFileSync(path.join(cli, ca.path), "utf8").replace(/^exported_by: .*$/m, ""), y = zread(mine.out, ca.path).replace(/^exported_by: .*$/m, ""); if (x !== y) { sameTr = false; why.push(ca.path); } }
    }
    check(sameNodes, "memory.json identical to cof import's (" + why.slice(0, 2).join(" | ") + ")");
    check(sameTr, "transcripts identical to cof import's, but for exported_by");
    check(cm.tags.content.join() === m.tags.content.join() && cm.tags.manual.slice().sort().join() === m.tags.manual.slice().sort().join(), "same tags as cof import (content, manual)");
    check(JSON.stringify(m.preset_tags) === JSON.stringify(cm.preset_tags) && JSON.stringify(m.preset_tags) === JSON.stringify([{ id: "age-30", label: "30", facet: "age", presets: ["default"] }, { id: "character-ai", label: "Character.AI", facet: "source", presets: ["default"] }]), "preset tags for the explorer's left column: the age and the source, as cof import");
  }

  /* 3 bis. the explorer for people coming from Character.AI (viewer/character-ai/, generated from the explorer): the page links
     to it; a welcome window on the first visit; an imported file opens on its memories graph; the left column has the facets */
  {
    const gv = py([path.join(ROOT, "tools", "viewer-cai", "gen.py"), "--check"], ROOT);
    check(gv.status === 0, "viewer/character-ai/index.html is up to date with viewer/index.html (" + (gv.stdout + gv.stderr).trim() + ")");
    const page = await newPage("en");
    check(await page.evaluate(() => [...document.querySelectorAll("a")].some(a => a.getAttribute("href") === "../viewer/character-ai/")), "the import page links to the Character.AI explorer");
    await page.context().close();
    const ctx = await browser.newContext({ viewport: { width: 1280, height: 900 } }); const v = await ctx.newPage(); const errs = []; v.on("pageerror", e => errs.push(e.message));
    await v.goto(BASE.replace("/import/", "/viewer/character-ai/")); await v.waitForTimeout(500);
    check(await v.evaluate(() => !document.querySelector("#caiW").hidden && /Character\.AI/.test(document.querySelector("#caiWt").textContent) && /Character\.AI/.test(document.querySelector("#caiHelp").textContent)), "the welcome window and « Character.AI version » in the header");
    await v.click("#caiWx"); await v.setInputFiles("#file", path.join(WORK, "wren-mine.cof")); await v.waitForTimeout(1200);
    const st = await v.evaluate(() => ({ tab, memView, facets: document.getElementById("facets").textContent }));
    check(st.tab === "memories" && st.memView === "graph" && /Character\.AI/.test(st.facets) && /30/.test(st.facets) && !errs.length, `an imported file opens on its memories graph, the age and the source in the left column (${st.tab}, ${st.memView}${errs.length ? ", " + errs.join(" | ") : ""})`);
    await v.click("#btnWren"); await v.waitForTimeout(1500);
    const ex = await v.evaluate(() => ({ tab, presets: Object.keys(M.presets).length, name: M.name, mem: Object.keys(M.elements.memories.variants).length }));
    check(ex.name === "Wren Calloway" && ex.presets === 4 && ex.mem === 4 && ex.tab === "memories", "« Example: Wren » opens the sample on its memories graph: four looks (presets), one period and three conversations (" + JSON.stringify(ex) + ")");
    await v.setInputFiles("#file", path.join(WORK, "wren-mine.cof")); await v.waitForTimeout(1200);
    const strip = await v.evaluate(() => { const ax = document.querySelector(".mgstrip .mgaxis"); return ax ? ax.textContent : ""; });
    check(/2022/.test(strip) && /n\.d\./.test(strip), "the time strip draws the Character.AI period from 2022 and keeps its conversations in « n.d. » (" + strip.replace(/\s+/g, " ").trim() + ")");
    const pop = await v.evaluate(async () => { const x = document.createElement("button"); x.dataset.memtext = "ev2"; x.dataset.memaid = "a-mem-ev2-chat-2"; document.body.appendChild(x); x.click(); x.remove(); await new Promise(r => setTimeout(r, 500));
      const open = { dlg: document.getElementById("memTextPop").open, locked: getComputedStyle(document.documentElement).overflow === "hidden", contain: getComputedStyle(document.querySelector("#memTextPop .pbody")).overscrollBehaviorY === "contain" };
      { const ev = new WheelEvent("wheel", { deltaY: 120, bubbles: true, cancelable: true }); document.querySelector("#memTextPop .pbody").dispatchEvent(ev); open.stopped = ev.defaultPrevented; }
      document.getElementById("memTextPop").close(); await new Promise(r => setTimeout(r, 100)); return { ...open, after: document.documentElement.classList.contains("popopen") }; });
    check(pop.dlg && pop.locked && pop.contain && pop.stopped && !pop.after, "the « + » pop-up: the page behind does not scroll under the wheel while it is open (a short text stops the wheel), and scrolls again once closed");
    await v.reload(); await v.waitForTimeout(400);
    check(await v.evaluate(() => !document.querySelector("#caiW").hidden), "the welcome window comes back at every visit (Yann, 8 Nov.)");
    await ctx.close();
  }

  /* 4. PersonaText alone: WebP avatar, its chat as a memory, never in the card; without the avatar */
  {
    const page = await newPage("fr");
    await drop(page, [path.join(FX, "wren.personatext.json")]);
    const st = await page.evaluate(() => ({ av: !document.querySelector("#av").hidden, n: document.querySelectorAll("#chats > li").length, t: document.querySelector("h1").textContent }));
    check(st.av && st.n === 1 && st.t === "Sauvez vos personnages Character.AI", "PersonaText: avatar shown, one conversation, page in French");
    await page.check("#noav");
    const d = await download(page, "#dlMine", "pt-mine.cof");
    const m = JSON.parse(zread(d.out, "manifest.json")); const names = zipNames(d.out);
    check(validate(d.out).status === 0 && !m.elements.appearance && !names.some(n => /appearance/.test(n)), "« import without the avatar »: valid, no face, no image");
    check(!/chat_history|avatar_data_url/.test(zread(d.out, "elements/personality/p1/card.json")) && m.elements.memories, "PersonaText: the conversation is a memory, never in the card");
    await page.uncheck("#noav"); await page.fill("#age", "28");
    const d2 = await download(page, "#dlMine", "pt-mine2.cof"); const m2 = JSON.parse(zread(d2.out, "manifest.json"));
    check(validate(d2.out).status === 0 && m2.assets.some(a => a.path === "elements/appearance/f1/head.front.webp" && a.mediaType === "image/webp"), "PersonaText: the WebP avatar kept as it is, with its age");
    const node = JSON.parse(zread(d2.out, Object.values(m2.elements.memories.variants)[0].memory));
    check(node.gist.en && /Mes|My/.test(Object.values(node.gist)[0]), "the gist is written in the conversation's language");
    check(page.errors.length === 0, "no page error (" + page.errors.join(" | ") + ")");
    await page.context().close();
  }

  /* 5. your name, the content tick, a conversation without a card */
  {
    const page = await newPage("en");
    await drop(page, [path.join(FX, "sillytavern-chat.jsonl")]);
    check(await page.evaluate(() => document.querySelector("#av").hidden && document.querySelector("#ageBox").hidden && /without a card/.test(document.querySelector("#stop").textContent)), "a conversation alone: no avatar asked, « character without a card » said");
    await page.fill("#persona", "Mara"); await page.check("#checked");
    await page.click("#content input[value=violence]");
    const d = await download(page, "#dlMine", "st.cof"); const m = JSON.parse(zread(d.out, "manifest.json"));
    check(validate(d.out).status === 0, "conversation without a card: valid file");
    const tr = zread(d.out, m.assets.find(a => a.role === "memory-media").path);
    check(/user_persona: Mara/.test(tr) && /## \d+ · Mara · /.test(tr), "the name typed replaces yours in the transcript");
    check(!m.tags.manual.includes("content-unreviewed") && m.tags.content.join() === "violence", "« I have checked » removes content-unreviewed; the content chosen is written");
    const junk = path.join(WORK, "notes.json"); fs.writeFileSync(junk, '{"hello":"world"}');
    await page.setInputFiles("#file", [junk]); await page.waitForTimeout(400);
    check(await page.evaluate(() => [...document.querySelectorAll("#files li.bad")].some(li => /notes\.json/.test(li.textContent) && /no conversation/.test(li.textContent))), "a file with nothing to import is said so, the rest is kept");
    check(await page.evaluate(() => !document.querySelector("#againP").hidden), "« start again » offered once files are dropped");
    await page.context().close();
  }

  /* 6. account files never read; COF's age rule: a face under 18 cannot be tagged sexual or nudity (no text control) */
  {
    const chat = path.join(WORK, "plain.jsonl");
    fs.writeFileSync(chat, ['{"user_name":"You","character_name":"X"}', '{"name":"X","is_user":false,"mes":"Hello."}', '{"name":"You","is_user":true,"mes":"Hi there."}'].join("\n"));
    const acct = path.join(WORK, "user_settings.json"); fs.writeFileSync(acct, '{"email":"someone@example.com","birthday":"2000-01-01"}');
    let page = await newPage("en");
    await drop(page, [chat, acct]);
    const st = await page.evaluate(() => ({ a: document.querySelector("#dlMine").disabled, files: [...document.querySelectorAll("#files li")].map(x => x.textContent) }));
    check(!st.a && st.files.some(x => /account file skipped/.test(x) && /user_settings\.json/.test(x)), "an account file is listed as skipped, never read");
    check(!JSON.stringify(await page.evaluate(() => window.cofImport.ST.chats.map(c => c.messages.map(m => m.text)))).includes("someone@example.com"), "nothing of the account file reaches the conversations");
    await page.context().close();
    const odd = path.join(WORK, "odd.json"); fs.writeFileSync(odd, '{"foo":{"bar":1}}');
    page = await newPage("en"); await drop(page, [odd]);
    check(await page.evaluate(() => !document.querySelector("#report").hidden && /issues\/new\?template=import-format\.yml/.test(document.querySelector("#report a").href)), "a file not recognised: « Report it » links to the GitHub form (D1)");
    await page.context().close();
    page = await newPage("en"); await drop(page, [path.join(FX, "caitools-card.png")]);
    await page.click('#content input[value="sexual"]'); await page.fill("#age", "16"); await page.dispatchEvent("#age", "input");
    const m = await page.evaluate(() => { const b = v => document.querySelector(`#content input[value="${v}"]`); return { s: b("sexual").disabled && !b("sexual").checked, n: b("nudity").disabled, v: !b("violence").disabled } });
    check(m.s && m.n && m.v, "age 16: « sexual » and « nudity » cannot be ticked (unticked, disabled), the others can");
    await page.fill("#age", "30"); await page.dispatchEvent("#age", "input");
    check(await page.evaluate(() => !document.querySelector('#content input[value="sexual"]').disabled), "… and can again at 30");
    await page.context().close();
  }

  /* 6 bis. phone: no horizontal scroll, even with a long file name (visual test, 5 Nov) */
  {
    const ctx = await browser.newContext({ viewport: { width: 390, height: 844 } }); const p = await ctx.newPage();
    await p.addInitScript(() => { try { localStorage.setItem("cofi-lang", "fr") } catch (e) {} }); await p.goto(BASE); await p.waitForTimeout(300);
    const long = path.join(WORK, "Wren_Calloway_TavernHistory_with_a_very_long_name_from_the_extension.zip"); fs.copyFileSync(path.join(FX, "Wren_Calloway_TavernHistory.zip"), long);
    await p.setInputFiles("#file", [path.join(FX, "caitools-card.png"), long]); await p.waitForTimeout(600);
    const w1 = await p.evaluate(() => document.documentElement.scrollWidth);
    await p.reload(); await p.waitForTimeout(300); await p.setInputFiles("#file", [path.join(WORK, "plain.jsonl"), path.join(WORK, "user_settings.json")]); await p.waitForTimeout(600);
    const w2 = await p.evaluate(() => document.documentElement.scrollWidth);
    check(w1 <= 390 && w2 <= 390, `phone 390 px: no horizontal scroll (${w1}, ${w2})`);
    await ctx.close();
  }

  /* 7. after the independent review (5 Nov): one character per file, later card, avatar bytes, malformed cards, long name,
        retyped name, languages of the list, order across drops, no imported-* tag for a plain card, no outside request */
  {
    const st = (file, char, user, date, lines) => { fs.writeFileSync(file, [JSON.stringify({ user_name: user, character_name: char })].concat(lines.map(([u, m], i) => JSON.stringify({ name: u ? user : char, is_user: !!u, send_date: `${date}T10:0${i}:00.000Z`, mes: m }))).join("\n")); return file; };
    const mira = st(path.join(WORK, "mira.jsonl"), "Mira", "Sam", "2026-10-05", [[0, "Mira here."], [1, "Hi Mira."]]);
    const sam = st(path.join(WORK, "sam.jsonl"), "Wren Calloway", "Sam", "2026-10-01", [[0, "Ink again."], [1, "Hello Wren."]]);
    const alex = st(path.join(WORK, "alex.jsonl"), "Wren Calloway", "Alex", "2026-10-02", [[0, "A visitor."], [1, "Hi, I am Alex."]]);
    let page = await newPage("en"); const outside = []; page.on("request", r => { if (/^https?:/.test(r.url()) && !r.url().startsWith(BASE.slice(0, BASE.indexOf("/import/")))) outside.push(r.url()); });
    await page.reload(); await page.waitForTimeout(300);
    await drop(page, [path.join(FX, "caitools-card.png"), mira]);
    const s1 = await page.evaluate(() => ({ warn: document.querySelector("#stop").textContent, n: document.querySelectorAll("#chats > li").length, share: document.querySelector("#dlShare").hidden }));
    check(/another character/.test(s1.warn) && /Mira/.test(s1.warn) && s1.share, "a chat with another character (Mira) is left out and said, never filed under Wren");
    await page.fill("#age", "30"); let d = await download(page, "#dlMine", "mira-left.cof"); let m = JSON.parse(zread(d.out, "manifest.json"));
    check(validate(d.out).status === 0 && !m.elements.memories && !JSON.stringify(m).includes("Mira"), "… and nothing of it reaches the file");
    check(outside.length === 0, "the page requests nothing outside its own site (" + outside.slice(0, 2).join(" ") + ")");
    await page.context().close();

    page = await newPage("en"); await drop(page, [mira]); check(await page.inputValue("#name") === "Mira", "a chat alone: its character's name");
    await page.setInputFiles("#file", [path.join(FX, "caitools-card.json")]); await page.waitForTimeout(400);
    check(await page.inputValue("#name") === "Wren Calloway", "a card dropped later gives its name (the field was not edited)");
    await page.context().close();

    const fake = JSON.parse(fs.readFileSync(path.join(FX, "caitools-card.json"), "utf8")); const fd = fake.data || fake;
    fd.extensions = Object.assign({}, fd.extensions, { avatar_data_url: "data:image/png;base64," + Buffer.from("<html>not an image</html>").toString("base64") });
    const fakeF = path.join(WORK, "fake-avatar.json"); fs.writeFileSync(fakeF, JSON.stringify(fake));
    page = await newPage("en"); await drop(page, [fakeF]);
    check(await page.evaluate(() => document.querySelector("#av").hidden && !window.cofImport.ST.avatar), "an avatar_data_url in a plain card is not taken (and bytes that are not an image never are)");
    d = await download(page, "#dlMine", "fake.cof"); m = JSON.parse(zread(d.out, "manifest.json"));
    check(validate(d.out).status === 0 && !m.elements.appearance, "… the file is valid, without a face");
    check(!m.tags.manual.some(x => /^imported-/.test(x)) || /caitools/.test(m.provenance.source.join()), "tags: imported-* only for a Character.AI source (" + m.tags.manual.join(",") + ")");
    await page.context().close();

    const crcT = []; for (let n = 0; n < 256; n++) { let c = n; for (let k = 0; k < 8; k++) c = c & 1 ? 0xEDB88320 ^ (c >>> 1) : c >>> 1; crcT[n] = c >>> 0; }
    const crc = b => { let c = -1; for (const x of b) c = crcT[(c ^ x) & 255] ^ (c >>> 8); return (c ^ -1) >>> 0; };
    const pngWith = (obj, file) => { const src = fs.readFileSync(path.join(FX, "caitools-card.png")); const parts = [src.subarray(0, 8)]; let p = 8;
      while (p < src.length) { const len = src.readUInt32BE(p), type = src.toString("latin1", p + 4, p + 8); const chunk = src.subarray(p, p + 12 + len); p += 12 + len;
        if (type === "IEND") { const body = Buffer.concat([Buffer.from("tEXt"), Buffer.from("chara\0" + Buffer.from(JSON.stringify(obj)).toString("base64"))]); const h = Buffer.alloc(4); h.writeUInt32BE(body.length - 4); const c = Buffer.alloc(4); c.writeUInt32BE(crc(body)); parts.push(h, body, c, chunk); break; }
        if (type !== "tEXt") parts.push(chunk); }
      fs.writeFileSync(file, Buffer.concat(parts)); return file; };
    const strData = pngWith({ spec: "chara_card_v2", data: "hello" }, path.join(WORK, "str-data.png")), arr = pngWith([1, 2, 3], path.join(WORK, "arr.png"));
    page = await newPage("en"); await drop(page, [strData, arr]);
    check(await page.evaluate(() => [...document.querySelectorAll("#files li.bad")].length === 2 && !window.cofImport.ST.ready), "a card whose data is not an object is « not recognised », no crash");
    check(page.errors.length === 0, "no page error on malformed cards (" + page.errors.join(" | ") + ")");
    await page.context().close();

    page = await newPage("en"); await drop(page, [sam, alex]);
    const order = await page.evaluate(() => window.cofImport.ST.mine.map(c => c.persona));
    await page.fill("#persona", "Samuel"); await page.fill("#persona", "Sam");
    await page.evaluate(() => { const i = document.querySelector("#name"); i.value = "N".repeat(150); i.dispatchEvent(new Event("input")); });
    d = await download(page, "#dlMine", "two.cof"); m = JSON.parse(zread(d.out, "manifest.json"));
    const trs = m.assets.filter(a => a.role === "memory-media").map(a => zread(d.out, a.path));
    check(validate(d.out).status === 0 && m.name.length <= 120 && m.elements.personality.variants.p1.label.length <= 120, "a 150-character name is cut to 120: the file stays valid");
    check(trs.length === 2 && trs.every(x => /user_persona: Sam\n/.test(x)), "your name retyped applies to every conversation (" + order.join(",") + ")");
    await page.context().close();
    page = await newPage("en"); await drop(page, [alex]); await page.setInputFiles("#file", [sam]); await page.waitForTimeout(400);
    d = await download(page, "#dlMine", "order.cof"); m = JSON.parse(zread(d.out, "manifest.json"));
    check(JSON.parse(zread(d.out, m.elements.memories.variants.ep1.memory)).when.from.date === "2026-10-01", "conversations dropped in two goes are put back in date order (ep1 = the oldest)");
    await page.evaluate(() => { document.querySelector("#lang").value = "ja"; document.querySelector("#lang").dispatchEvent(new Event("change")); });
    check(await page.evaluate(() => [...document.querySelectorAll("#files .k")].every(k => /件の会話/.test(k.textContent))), "the file list follows a language change");
    await page.context().close();
  }

  await browser.close(); server.close();
  console.log(ok ? "\nALL OK" : "\nFAILURES"); process.exit(ok ? 0 : 1);
})().catch(e => { console.error(e); process.exit(1); });
