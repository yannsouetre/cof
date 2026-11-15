"""Renders the README figures into docs/img/ (needs Playwright + Chromium and a local server at the repo root:
`python -m http.server 8765`). Diagrams from figures.html; slides from the launch clip; screenshots of the tools.
`python render.py explorer` renders only docs/img/cof-explorer.jpg.
Rule for public captures: no age under 18 on screen. Clara's example has a childhood variant, so the explorer capture drops
every listed item that states one (age chips, preset rows, the summary line) and stops if one is left (same rule as tools/og-cards)."""
import asyncio, io, sys
from pathlib import Path
from PIL import Image
from playwright.async_api import async_playwright

ROOT = Path(__file__).resolve().parents[2]; OUT = ROOT / "docs/img"; BASE = "http://localhost:8765"


def save_jpeg(png: bytes, path: Path, width: int = 1600):
    im = Image.open(io.BytesIO(png)).convert("RGB")
    im = im.resize((width, round(im.height * width / im.width)), Image.LANCZOS)
    im.save(path, quality=86, optimize=True, progressive=True)


MINOR = r"(?:\b(?:age|aged|at|âge|de|à)\s*(?:1[0-7]|[0-9])\b|\b(?:1[0-7]|[0-9])\s*(?:ans|years?|yo)\b)"
DROP = """([re, sel]) => { const R = new RegExp(re, "i"); let n = 0; for (const e of document.querySelectorAll(sel)) if (R.test(e.innerText || "")) { e.remove(); n++; } return n; }"""
LEFT = """(re) => { const R = new RegExp(re, "i"), out = []; const w = document.createTreeWalker(document.body, NodeFilter.SHOW_TEXT);
  while (w.nextNode()) { const n = w.currentNode, e = n.parentElement, r = e && e.getBoundingClientRect(); if (r && r.width > 0 && r.height > 0 && r.bottom > 0 && r.top < innerHeight && R.test(n.textContent)) out.push(n.textContent.trim().slice(0, 40)); } return out; }"""


async def explorer_shot(br):
    """The explorer with Clara opened, light theme, English, with no age under 18 on screen."""
    shots = await br.new_page(viewport={"width": 1440, "height": 900}, color_scheme="light")
    await shots.add_init_script("try { localStorage.setItem('cof-theme', 'light'); localStorage.setItem('cofv-lang', 'en'); } catch (e) {}")
    await shots.goto(f"{BASE}/viewer/"); await shots.click("#btnClara"); await shots.wait_for_selector(".pcard", timeout=20000); await shots.wait_for_timeout(4000)
    gone = await shots.evaluate(DROP, [MINOR, "button.chip, button.pcard, .hero p.text"]); await shots.wait_for_timeout(300)
    left = await shots.evaluate(LEFT, MINOR)
    if left: raise SystemExit("explorer: an age under 18 is still on screen: " + " ; ".join(left))
    print("explorer:", gone, "item(s) stating an age under 18 removed before the capture")
    save_jpeg(await shots.screenshot(), OUT / "cof-explorer.jpg", 1440)
    return shots


async def main():
    OUT.mkdir(parents=True, exist_ok=True)
    async with async_playwright() as p:
        br = await p.chromium.launch()
        if sys.argv[1:] == ["explorer"]:
            await explorer_shot(br); await br.close(); return
        pg = await br.new_page(viewport={"width": 1700, "height": 1000}, device_scale_factor=1)
        await pg.goto(f"{BASE}/tools/readme-figures/figures.html"); await pg.evaluate("document.fonts.ready"); await pg.wait_for_timeout(400)
        for fid in ("contents", "tools", "comfy"):
            await pg.locator(f"#{fid}").screenshot(path=str(OUT / f"cof-{fid}.png"), omit_background=True)
        soc = await br.new_page(viewport={"width": 1400, "height": 1000}, device_scale_factor=1)
        await soc.goto(f"{BASE}/tools/readme-figures/figures.html"); await soc.evaluate("document.fonts.ready"); await soc.wait_for_timeout(500)
        await soc.locator("#social").screenshot(path=str(OUT / "cof-social.png"))
        btn = await br.new_page(viewport={"width": 1700, "height": 1000}, device_scale_factor=2)
        await btn.goto(f"{BASE}/tools/readme-figures/figures.html"); await btn.evaluate("document.fonts.ready"); await btn.wait_for_timeout(300)
        for el in await btn.locator(".btnimg").all():
            await el.screenshot(path=str(OUT / f"{await el.get_attribute('id')}.png"), omit_background=True)
        clip = await br.new_page(viewport={"width": 1920, "height": 1080})
        await clip.goto(f"{BASE}/clip/index.html?render"); await clip.evaluate("document.fonts.ready"); await clip.wait_for_timeout(500)
        for name, t in (("presets", 21.6), ("rights", 27.0), ("cast", 31.0)):   # clip times: Français + 29 on, every rights row in, both characters in
            await clip.evaluate(f"render({t})"); save_jpeg(await clip.screenshot(), OUT / f"cof-{name}.jpg")
        shots = await explorer_shot(br)
        await shots.goto(f"{BASE}/builder/"); await shots.wait_for_timeout(1200)
        await shots.select_option("#langSel", "en"); await shots.wait_for_timeout(400)
        await shots.set_input_files("#fileOpen", str(ROOT / "viewer/samples/clara-mercier.cof")); await shots.wait_for_timeout(4000)
        await shots.get_by_role("button", name="Easy version").click(); await shots.wait_for_timeout(1500)
        save_jpeg(await shots.screenshot(), OUT / "cof-builder.jpg", 1440)
        await br.close()
    for f in sorted(OUT.iterdir()):
        print(f.name, f.stat().st_size // 1024, "KB")

asyncio.run(main())
