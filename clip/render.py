"""Renders the launch clip to video (needs Playwright + Chromium, ffmpeg, and a local server at the repo root:
`python -m http.server 8765`).

    python clip/render.py OUTDIR [--music path.mp3]

Produces, in OUTDIR: clip-16x9.mp4 (silent), clip-16x9-music.mp4, clip-9x16-music.mp4 (when --music is given),
and hero.webp (the whole clip at 15 fps, 1280 px wide, q85, for the README). 30 fps, 38 s. The music gets a 0.3 s
fade-in and a 1.4 s fade-out ending with the clip.

Frames are streamed straight into ffmpeg (no full-size frame ever touches the disk); only the hero's frames are kept,
downscaled to 1280×720, until the WebP is written."""
import argparse, asyncio, io, shutil, subprocess, tempfile
from pathlib import Path
from PIL import Image
from playwright.async_api import async_playwright

BASE = "http://localhost:8765"
FPS, DUR = 30, 38
FADE_IN, FADE_OUT = 0.3, 1.4
X264 = ["-c:v", "libx264", "-pix_fmt", "yuv420p", "-crf", "20", "-preset", "slow", "-movflags", "+faststart"]


async def frames(br, page, w, h, out: Path, hero_dir: Path | None = None):
    """Renders every frame of `page` and pipes it as PNG into an ffmpeg H.264 encode to `out` (silent)."""
    enc = subprocess.Popen(["ffmpeg", "-y", "-hide_banner", "-loglevel", "error", "-f", "image2pipe", "-c:v", "png",
                            "-framerate", str(FPS), "-i", "-", *X264, str(out)], stdin=subprocess.PIPE)
    pg = await br.new_page(viewport={"width": w, "height": h}, device_scale_factor=1)
    await pg.goto(f"{BASE}/clip/{page}?render"); await pg.evaluate("document.fonts.ready"); await pg.wait_for_timeout(600)
    n = FPS * DUR
    try:
        for i in range(n):
            await pg.evaluate(f"render({i / FPS})")
            png = await pg.screenshot(type="png")
            enc.stdin.write(png)
            if hero_dir is not None and i % (FPS // 15) == 0:
                Image.open(io.BytesIO(png)).convert("RGB").resize((1280, 720), Image.LANCZOS).save(hero_dir / f"f{i:05d}.png")
            if i % 300 == 0: print(f"  {page}: {i}/{n}", flush=True)
    finally:
        enc.stdin.close(); await pg.close()
    if enc.wait() != 0: raise SystemExit(f"ffmpeg failed on {out.name}")


def add_music(video: Path, music: Path, out: Path):
    """Muxes the music under an already encoded video (video stream copied), with the fades."""
    af = f"afade=t=in:d={FADE_IN},afade=t=out:st={DUR - FADE_OUT}:d={FADE_OUT}"
    subprocess.run(["ffmpeg", "-y", "-hide_banner", "-loglevel", "error", "-i", str(video), "-i", str(music),
                    "-map", "0:v", "-map", "1:a", "-c:v", "copy", "-af", af, "-c:a", "aac", "-b:a", "192k", "-shortest",
                    "-movflags", "+faststart", str(out)], check=True)


def hero(hero_dir: Path, out: Path):
    """Animated WebP for the README: the whole clip at 15 fps, 1280 px wide, lossy q85 with a key frame at least every
    10 frames (lossy sub-rectangle deltas otherwise leave ghost edges on the dark cards)."""
    frames = [Image.open(f) for f in sorted(hero_dir.glob("f*.png"))]
    frames[0].save(out, save_all=True, append_images=frames[1:], duration=1000 // 15, loop=0, quality=85, method=6,
                   kmin=3, kmax=10, allow_mixed=True)


async def main():
    ap = argparse.ArgumentParser(); ap.add_argument("out"); ap.add_argument("--music"); ap.add_argument("--skip-vertical", action="store_true")
    a = ap.parse_args(); out = Path(a.out); out.mkdir(parents=True, exist_ok=True); music = Path(a.music) if a.music else None
    tmp = Path(tempfile.mkdtemp(prefix="cof-clip-"))
    try:
        async with async_playwright() as p:
            br = await p.chromium.launch()
            hd = tmp / "hero"; hd.mkdir()
            await frames(br, "index.html", 1920, 1080, out / "clip-16x9.mp4", hd)
            if music: add_music(out / "clip-16x9.mp4", music, out / "clip-16x9-music.mp4")
            hero(hd, out / "hero.webp"); shutil.rmtree(hd, ignore_errors=True)
            if not a.skip_vertical:
                v = tmp / "clip-9x16.mp4"
                await frames(br, "vertical.html", 1080, 1920, v if music else out / "clip-9x16.mp4")
                if music: add_music(v, music, out / "clip-9x16-music.mp4")
            await br.close()
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    for f in sorted(out.iterdir()): print(f.name, f.stat().st_size // 1024, "KB")


asyncio.run(main())
