#!/usr/bin/env node
/* Builder — a psyche node illustrated by the image of a memory that the build leaves out (a personal memory, the default
   purge): the image leaves with the memory (no psyche-media copy of a user's data), the node stays, the file validates.
   Same rule as cof-cli `drop_personal_memories`. On a copy of example 10 where ev1 (hab1's illustration) is personal.
   Usage: node tests/builder/personal_media_test.js [repo-root] [work-dir]. Exit code 1 on any failure. */
const fs = require("fs"), path = require("path"), http = require("http"), { spawnSync } = require("child_process");
const { chromium } = require("playwright");
const ROOT = path.resolve(process.argv[2] || path.join(__dirname, "..", ".."));
const WORK = path.resolve(process.argv[3] || fs.mkdtempSync(path.join(require("os").tmpdir(), "cof-persmedia-")));
fs.mkdirSync(WORK, { recursive: true });
let ok = true;
const check = (cond, msg) => { console.log((cond ? "ok   " : "FAIL ") + msg); ok = ok && !!cond; };
const py = (args, cwd) => spawnSync(process.env.PYTHON || "python", args, { encoding: "utf8", cwd });
const src = path.join(WORK, "src"); fs.rmSync(src, { recursive: true, force: true });
fs.cpSync(path.join(ROOT, "spec", "examples", "10-clara-mercier"), src, { recursive: true });
const mj = path.join(src, "elements", "memories", "ev1", "memory.json"); const node = JSON.parse(fs.readFileSync(mj, "utf8")); node.visibility = "personal"; fs.writeFileSync(mj, JSON.stringify(node));
const input = path.join(WORK, "in.cof"), out = path.join(WORK, "out.cof");
let r = py(["-m", "cof_cli.cli", "pack", src, "-o", input], path.join(ROOT, "cli")); if (r.status !== 0) throw new Error(r.stdout + r.stderr);
const mime = { ".html": "text/html; charset=utf-8", ".js": "text/javascript", ".json": "application/json", ".css": "text/css", ".svg": "image/svg+xml", ".png": "image/png" };
const server = http.createServer((q, s) => { let f = path.join(ROOT, decodeURIComponent(q.url.split("?")[0])); if (!f.startsWith(ROOT)) { s.writeHead(403); return s.end(); } try { if (fs.statSync(f).isDirectory()) f = path.join(f, "index.html"); s.writeHead(200, { "content-type": mime[path.extname(f)] || "application/octet-stream" }); s.end(fs.readFileSync(f)); } catch (e) { s.writeHead(404); s.end(); } });
(async () => {
  await new Promise(r => server.listen(0, r)); const browser = await chromium.launch(); const page = await browser.newPage({ viewport: { width: 1400, height: 900 } });
  const errors = []; page.on("pageerror", e => errors.push(e.message)); page.on("dialog", d => d.accept().catch(() => {}));
  await page.addInitScript(() => { window.__dl = []; const oc = URL.createObjectURL.bind(URL); URL.createObjectURL = b => { window.__dl.push(b); return oc(b); }; HTMLAnchorElement.prototype.click = function () {}; });
  await page.goto(`http://localhost:${server.address().port}/builder/`); await page.waitForTimeout(800);
  await page.setInputFiles("#fileOpen", input); await page.waitForFunction(() => S.loadedManifest, null, { timeout: 60000 }); await page.waitForTimeout(1500);
  check(await page.evaluate(() => (S.psyche.hab1?.media || []).some(a => /^elements\/memories\/ev1\//.test(a.path || ""))), "hab1 is illustrated by ev1's image in the builder");
  await page.evaluate(() => { window.__dl.length = 0; go("build"); });
  check(await page.evaluate(() => !!document.querySelector("#b_mem_droppers")?.checked), "the personal purge is ticked by default");
  await page.click("#btnBuild"); await page.waitForSelector("#dlg.on .dbtns .primary", { timeout: 10000 }); await page.click("#dlg.on .dbtns .primary");   /* the build confirmation (7 Nov.) */ await page.waitForFunction(() => window.__dl.some(b => b.type === "application/vnd.cof.character+zip"), null, { timeout: 90000 });
  const b64 = await page.evaluate(async () => { const b = window.__dl.filter(x => x.type === "application/vnd.cof.character+zip").pop(); const u = new Uint8Array(await b.arrayBuffer()); let s = ""; for (let i = 0; i < u.length; i += 32768) s += String.fromCharCode.apply(null, u.subarray(i, i + 32768)); return btoa(s); });
  fs.writeFileSync(out, Buffer.from(b64, "base64"));
  const info = JSON.parse(py(["-c", "import json,zipfile,sys;z=zipfile.ZipFile(sys.argv[1]);m=json.loads(z.read('manifest.json'));print(json.dumps({'ev1':'ev1' in (m['elements'].get('memories') or {}).get('variants',{}),'media':m['elements']['psyche']['variants']['hab1'].get('media'),'asset':any(a['id']=='a-mem-ev1-1' for a in m['assets']),'files':[n for n in z.namelist() if n.startswith('elements/memories/ev1/')]}))", out]).stdout);
  check(!info.ev1, "ev1 (personal) left out of the build");
  check(!info.media && !info.asset && info.files.length === 0, "its image left with it: not hab1's illustration, no asset, no file (" + JSON.stringify(info) + ")");
  const v = py(["-m", "cof_cli.cli", "validate", out], path.join(ROOT, "cli")); check(/^OK/m.test(v.stdout), "cof validate OK " + (v.stdout.match(/ERROR.*$/m) || [""])[0]);
  check(errors.length === 0, "no page errors " + errors.join(" | "));
  await browser.close(); server.close(); console.log(ok ? "ALL OK" : "SOME CHECKS FAILED"); process.exit(ok ? 0 : 1);
})().catch(e => { console.error(e); process.exit(1); });
