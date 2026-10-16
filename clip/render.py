"""Renders the launch clip to video (needs Playwright + Chromium, ffmpeg, and a local server at the repo root:
`python -m http.server 8765`).

    python clip/render.py OUTDIR [--music path.mp3]

Produces, in OUTDIR: clip-16x9.mp4 (silent), clip-16x9-music.mp4, clip-9x16-music.mp4 (when --music is given),
and hero.webp (the whole clip at 15 fps, 1280 px wide, q85, for the README). 30 fps, 38 s."""
import argparse, asyncio, shutil, subprocess, sys, tempfile
from pathlib import Path
from playwright.async_api import async_playwright

BASE = "http://localhost:8765"
FPS, DUR = 30, 38


async def frames(br, page, w, h, out: Path):
    pg = await br.new_page(viewport={"width": w, "height": h}, device_scale_factor=1)
    await pg.goto(f"{BASE}/clip/{page}?render"); await pg.evaluate("document.fonts.ready"); await pg.wait_for_timeout(600)
    n = FPS * DUR
    for i in range(n):
        await pg.evaluate(f"render({i / FPS})")
        await pg.screenshot(path=str(out / f"f{i:05d}.png"))
        if i % 300 == 0: print(f"  {page}: {i}/{n}", flush=True)
    await pg.close()


def encode(frames_dir: Path, out: Path, music: Path | None):
    cmd = ["ffmpeg", "-y", "-hide_banner", "-loglevel", "error", "-framerate", str(FPS), "-i", str(frames_dir / "f%05d.png")]
    if music: cmd += ["-i", str(music), "-map", "0:v", "-map", "1:a", "-c:a", "aac", "-b:a", "192k", "-shortest"]
    cmd += ["-c:v", "libx264", "-pix_fmt", "yuv420p", "-crf", "20", "-preset", "slow", "-movflags", "+faststart", str(out)]
    subprocess.run(cmd, check=True)


def hero(frames_dir: Path, out: Path):
    """Animated WebP for the README: the whole clip at 15 fps, 1280 px wide, lossy q85 with a key frame at least every
    10 frames (lossy sub-rectangle deltas otherwise leave ghost edges on the dark cards)."""
    from PIL import Image
    files = sorted(frames_dir.glob("f*.png"))[::FPS // 15]
    frames = [Image.open(f).convert("RGB").resize((1280, 720), Image.LANCZOS) for f in files]
    frames[0].save(out, save_all=True, append_images=frames[1:], duration=1000 // 15, loop=0, quality=85, method=6,
                   kmin=3, kmax=10, allow_mixed=True)


async def main():
    ap = argparse.ArgumentParser(); ap.add_argument("out"); ap.add_argument("--music"); ap.add_argument("--skip-vertical", action="store_true")
    a = ap.parse_args(); out = Path(a.out); out.mkdir(parents=True, exist_ok=True); music = Path(a.music) if a.music else None
    tmp = Path(tempfile.mkdtemp(prefix="cof-clip-"))
    try:
        async with async_playwright() as p:
            br = await p.chromium.launch()
            d = tmp / "h"; d.mkdir(); await frames(br, "index.html", 1920, 1080, d)
            encode(d, out / "clip-16x9.mp4", None)
            if music: encode(d, out / "clip-16x9-music.mp4", music)
            hero(d, out / "hero.webp")
            if not a.skip_vertical:
                v = tmp / "v"; v.mkdir(); await frames(br, "vertical.html", 1080, 1920, v)
                encode(v, out / "clip-9x16-music.mp4" if music else out / "clip-9x16.mp4", music)
            await br.close()
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    for f in sorted(out.iterdir()): print(f.name, f.stat().st_size // 1024, "KB")


asyncio.run(main())
