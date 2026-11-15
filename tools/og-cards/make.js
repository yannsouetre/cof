// Share cards (1200 × 630) for the builder and the explorer: a fresh screenshot of each tool in dark theme, Clara loaded,
// set in a card drawn like psyche/img/og-psyche.jpg and import/og-import.jpg (title, rule, tagline, footer line).
//   node tools/og-cards/make.js [repo-root]        → builder/og-builder.jpg, viewer/og-explorer.jpg
// Rule for every communication visual: NO age under 18 on screen, and no face of a variant under 18. Clara's example has a childhood
// variant (it is there to show the age rules), so both captures drop every item that states an age under 18 before the shot
// (the preset rows, the age chip, the variant tile, the summary line « from age 12 … »), and the script stops if one is left.
// Needs playwright, python with cof-cli importable from cli/ (packs spec/examples/10-clara-mercier for the builder shot).
const { chromium } = require("playwright"); const fs = require("fs"), path = require("path"), http = require("http"), os = require("os"), { spawnSync } = require("child_process");
const ROOT = path.resolve(process.argv[2] || path.join(__dirname, "..", "..")); const WORK = fs.mkdtempSync(path.join(os.tmpdir(), "og-"));
const mime = { ".html": "text/html; charset=utf-8", ".js": "text/javascript", ".json": "application/json", ".css": "text/css", ".svg": "image/svg+xml", ".png": "image/png", ".jpg": "image/jpeg", ".cof": "application/zip", ".woff2": "font/woff2" };
const server = http.createServer((q, s) => { let f = path.join(ROOT, decodeURIComponent(q.url.split("?")[0])); if (!f.startsWith(ROOT)) { s.writeHead(403); return s.end(); } try { if (fs.statSync(f).isDirectory()) f = path.join(f, "index.html"); s.writeHead(200, { "Content-Type": mime[path.extname(f)] || "application/octet-stream" }); s.end(fs.readFileSync(f)); } catch (e) { s.writeHead(404); s.end(); } });
const VER = /explorer (\d+\.\d+\.\d+)/.exec(fs.readFileSync(path.join(ROOT, "viewer/index.html"), "utf8"))[1].replace(/\.\d+$/, "");   /* major.minor: the card outlives the patch */
const FONT = /src:url\((data:font\/woff2;base64,[^)]+)\)/.exec(fs.readFileSync(path.join(ROOT, "viewer/index.html"), "utf8"))[1];   /* COF Display, as the tools embed it */

const card = (title, tagline, shot, shift = 0) => `<!doctype html><html><head><meta charset="utf-8"><style>
@font-face{font-family:"COF Display";src:url(${FONT})}
html,body{margin:0;width:1200px;height:630px;overflow:hidden;background:#0c1311;color:#e6efe9;font-family:"Segoe UI",Inter,Roboto,system-ui,sans-serif}
.bg{position:absolute;inset:0;background:radial-gradient(900px 500px at 85% 40%,#15241f 0%,#0c1311 70%)}
.t{position:absolute;left:70px;top:112px;width:560px;font-family:"COF Display","Segoe UI",sans-serif;font-weight:700;font-size:62px;line-height:1.02;letter-spacing:.01em;text-transform:uppercase}
.r{position:absolute;left:70px;top:${title.length > 22 ? 318 : 252}px;width:88px;height:3px;background:#4cc2a8}
.s{position:absolute;left:70px;top:${title.length > 22 ? 342 : 276}px;width:520px;font-size:25px;line-height:1.4;color:#c9d6d0}
.f{position:absolute;left:70px;bottom:52px;font-family:ui-monospace,Consolas,monospace;font-size:16px;letter-spacing:.14em;color:#4cc2a8}
.shot{position:absolute;left:660px;top:64px;width:760px;height:520px;border-radius:14px;overflow:hidden;border:1px solid #2a3b35;box-shadow:0 30px 80px rgba(0,0,0,.6);transform:perspective(1600px) rotateY(-7deg);transform-origin:left center;background:#111}
.shot img{display:block;width:760px;height:auto;margin-top:-${shift}px}
.veil{position:absolute;left:600px;top:0;width:120px;height:630px;background:linear-gradient(90deg,#0c1311 0%,rgba(12,19,17,0) 100%);pointer-events:none}
</style></head><body><div class="bg"></div>
<div class="shot"><img src="${shot}"></div><div class="veil"></div>
<div class="t">${title}</div><div class="r"></div><div class="s">${tagline}</div>
<div class="f">COF · CHARACTER OPEN FILE · ${VER}</div></body></html>`;

/* an age under 18 as the tools write it: « 12 ans », « age 12 », « at 12 », « à 12 ans », « de 12 à 65 ans » */
const MINOR = String.raw`(?:\b(?:age|aged|at|âge|de|à)\s*(?:1[0-7]|[0-9])\b|\b(?:1[0-7]|[0-9])\s*(?:ans|years?|yo)\b)`;
/* removes, in the page, the smallest listed block that states a minor's age; returns what was removed */
const dropMinors = ([re, sel]) => { const R = new RegExp(re, "i"), gone = [];
  for (const e of document.querySelectorAll(sel)) { const t = (e.innerText || "") + " " + [...e.querySelectorAll("input")].map(i => (i.dataset.k === "age" ? "age " : "") + i.value).join(" ");
    if (R.test(t)) { gone.push(t.replace(/\s+/g, " ").trim().slice(0, 40)); e.remove(); } } return gone; };
/* what is still visible in the window and states a minor's age (texts and field values) */
const leftMinors = (re) => { const R = new RegExp(re, "i"), out = [], seen = e => { const r = e.getBoundingClientRect(); return r.width > 0 && r.height > 0 && r.bottom > 0 && r.top < innerHeight; };
  const w = document.createTreeWalker(document.body, NodeFilter.SHOW_TEXT); while (w.nextNode()) { const n = w.currentNode; if (R.test(n.textContent) && n.parentElement && seen(n.parentElement)) out.push(n.textContent.trim().slice(0, 40)); }
  for (const i of document.querySelectorAll("input,textarea")) if (seen(i) && R.test((i.dataset.k === "age" ? "age " : "") + i.value)) out.push("field: " + i.value.slice(0, 40)); return out; };
const noMinor = async (page, sel, what) => { const gone = await page.evaluate(dropMinors, [MINOR, sel]); await page.waitForTimeout(300);
  const left = await page.evaluate(leftMinors, MINOR); console.log(what + ": removed " + gone.length + " item(s) stating an age under 18" + (gone.length ? " (" + gone.join(" ; ") + ")" : ""));
  if (left.length) throw new Error(what + ": an age under 18 is still on screen: " + left.join(" ; ")); };

(async () => {
  await new Promise(r => server.listen(0, r)); const BASE = `http://localhost:${server.address().port}`;
  const browser = await chromium.launch({ args: ["--disable-dev-shm-usage"] });
  // 1. the explorer, dark, Clara opened
  let page = await browser.newPage({ viewport: { width: 1280, height: 860 }, deviceScaleFactor: 1 });
  await page.addInitScript(() => { try { localStorage.setItem("cof-theme", "dark"); localStorage.setItem("cofv-lang", "en"); } catch (e) {} });
  await page.goto(`${BASE}/viewer/`, { waitUntil: "load" }); await page.click("#btnClara"); await page.waitForTimeout(4000);
  await noMinor(page, "button.chip, button.pcard, .hero p.text", "explorer");
  await page.screenshot({ path: path.join(WORK, "explorer.png") });
  // 2. the builder, dark, Clara 1.2 loaded, elements step (the tiles)
  const clara = path.join(WORK, "clara12.cof");
  fs.cpSync(path.join(ROOT, "spec/examples/10-clara-mercier"), path.join(WORK, "10"), { recursive: true });   /* pack writes completeness into its source: work on a copy */
  const r = spawnSync("python3", ["-m", "cof_cli.cli", "pack", path.join(WORK, "10"), "-o", clara], { cwd: path.join(ROOT, "cli"), encoding: "utf8" });
  if (r.status !== 0) throw new Error("pack failed: " + r.stdout + r.stderr);
  page = await browser.newPage({ viewport: { width: 1280, height: 1000 }, deviceScaleFactor: 1 });
  await page.addInitScript(() => { try { localStorage.setItem("cof-theme", "dark"); localStorage.setItem("cof-lang", "en"); localStorage.setItem("cof-mode", "advanced"); localStorage.setItem("cof-view-elPanel", "tiles"); } catch (e) {} });
  page.on("dialog", d => d.accept().catch(() => {}));
  await page.goto(`${BASE}/builder/`, { waitUntil: "load" }); await page.waitForTimeout(800);
  await page.evaluate(() => { window.__prev = S.loadedManifest; }); await page.setInputFiles("#fileOpen", clara);
  await page.waitForFunction(() => S.loadedManifest !== window.__prev && !document.getElementById("busy").classList.contains("on"), null, { timeout: 120000 });
  await page.waitForTimeout(600); await page.click("#nav button[data-step=elements]"); await page.waitForTimeout(800);
  await page.getByRole("button", { name: /Appearance/ }).first().click(); await page.waitForTimeout(900);   /* the looks: tiles with faces */
  await page.evaluate(() => { const t = document.querySelector("#elPanel .tiles"); if (t) window.scrollTo(0, t.getBoundingClientRect().top + scrollY - 250); });
  await page.waitForTimeout(500); await noMinor(page, "#elPanel .variant", "builder");
  await page.screenshot({ path: path.join(WORK, "builder.png") });
  // 3. the cards
  const out = [["builder/og-builder.jpg", "Build a character file", "Looks, voice, memories, psyche and rights — a .cof built in your browser, offline. Nothing is uploaded.", "builder.png", 150],
               ["viewer/og-explorer.jpg", "Open a character file", "Presets, looks, voices, memories, psyche and rights of a .cof, in your browser. Nothing leaves your machine.", "explorer.png", 0]];
  for (const [dst, title, tag, shot, shift] of out) {
    const html = card(title, tag, "file://" + path.join(WORK, shot), shift); const f = path.join(WORK, path.basename(dst) + ".html"); fs.writeFileSync(f, html);
    const p = await browser.newPage({ viewport: { width: 1200, height: 630 }, deviceScaleFactor: 1 });
    await p.goto("file://" + f); await p.waitForTimeout(600); await p.screenshot({ path: path.join(ROOT, dst), type: "jpeg", quality: 90 }); await p.close();
    console.log("wrote", dst);
  }
  await browser.close(); server.close(); console.log("work:", WORK);
})();
