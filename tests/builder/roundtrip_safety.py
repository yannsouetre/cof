"""Safety of the builder 0.14.2 conservation (hunt 1.2.2, SAFETY-01 / SAFETY-02).
SAFETY-01: zip entries and path fields of an opened .cof that are not normalised relative POSIX paths (`..`, leading /, drive letter,
backslash, control character) are dropped at load, listed in the Checks step, and never written into the built .cof.
SAFETY-02: a variant marked nudity in a category the builder keeps as read (x-gallery), on the photo of a 10-year-old and held by
the default preset, is a Checks error and the build is refused.
Usage (from cli/, PYTHONPATH=.): python ../tests/builder/roundtrip_safety.py ../builder/index.html <workdir>"""
import json, shutil, subprocess, sys, tempfile, zipfile
from pathlib import Path
from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[2]
BUILDER = Path(sys.argv[1]).resolve()
W = Path(sys.argv[2]).resolve(); W.mkdir(parents=True, exist_ok=True)
EVIL = ["../evil-root.txt", "/tmp/evil-abs.txt", "elements/../../evil-el.txt", "elements/personality/p1/../../../../evil-kept.txt",
        "rights/../../evil-rights.txt", "C:/evil-win.txt", "x/..\\..\\evil-bs.txt", "notes/evil\x01ctl.txt"]
ok = True
def check(cond, msg):
    global ok
    print(("ok  " if cond else "FAIL"), msg)
    ok = ok and cond
def pack(src, out):
    subprocess.run([sys.executable, "-m", "cof_cli.cli", "pack", str(src), "-o", str(out), "--force"], check=True, capture_output=True)

with tempfile.TemporaryDirectory(dir=str(W)) as tmp:
    tmp = Path(tmp)
    # --- SAFETY-01 input: example 02 packed, plus traversal entries and a variant field pointing outside the container
    shutil.copytree(ROOT / "spec/examples/02-ecoliere", tmp / "src02")
    pack(tmp / "src02", tmp / "base.cof")
    with zipfile.ZipFile(tmp / "base.cof") as zi, zipfile.ZipFile(tmp / "trav.cof", "w") as zo:
        for it in zi.infolist():
            data = zi.read(it.filename)
            if it.filename == "manifest.json":
                m = json.loads(data); v = next(iter(m["elements"]["appearance"]["variants"].values())); v["x-notes"] = "../../evil-notes.md"
                data = json.dumps(m, ensure_ascii=False).encode()
            zo.writestr(it, data)
        for e in EVIL:
            zo.writestr(zipfile.ZipInfo(e), b"traversal")
    # --- SAFETY-02 input: example 02 + a kept-as-read category with a nudity variant on the child's body photo, in every preset
    m = json.loads((tmp / "src02/manifest.json").read_text("utf-8"))
    body = next(a["id"] for a in m["assets"] if "body" in a["id"] and a.get("path"))
    m["elements"]["x-gallery"] = {"variants": {"g1": {"kind": "photo", "label": "gallery", "nudity": True, "images": [body]}}}
    for p in m["presets"].values():
        p.setdefault("slots", {})["x-gallery"] = ["g1"]
    (tmp / "src02/manifest.json").write_text(json.dumps(m, ensure_ascii=False, indent=1), "utf-8")
    pack(tmp / "src02", tmp / "minor.cof")

    with sync_playwright() as p:
        b = p.chromium.launch()
        errors, dialogs = [], []
        def page_for():
            ctx = b.new_context(accept_downloads=True); pg = ctx.new_page()
            pg.on("pageerror", lambda e: errors.append(str(e))); pg.on("dialog", lambda d: (dialogs.append(d.message), d.accept()))
            pg.goto(BUILDER.as_uri()); return pg
        pg = page_for()
        pg.set_input_files("#fileOpen", str(tmp / "trav.cof")); pg.wait_for_timeout(2500)
        msgs = pg.evaluate("() => runChecks().map(i => [i.sev, i.msg])")
        bad = [x for x in msgs if "chemin de fichier non conforme" in x[1] or "non-conformant file path" in x[1]]
        check(len(bad) == len(EVIL) + 1 and all(s == "major" for s, _ in bad), f"each non-conformant path is listed in the Checks step ({len(bad)} of {len(EVIL) + 1})")
        check(not any(s == "error" for s, _ in msgs), "already dropped: no error, the build goes on")
        with pg.expect_download(timeout=60000) as dl:
            pg.evaluate("document.getElementById('btnBuild').click()")
            pg.wait_for_selector("#dlg.on .dbtns .primary", timeout=10000); pg.click("#dlg.on .dbtns .primary")
        dl.value.save_as(str(tmp / "trav.out.cof"))
        names = zipfile.ZipFile(tmp / "trav.out.cof").namelist()
        evil = [n for n in names if "evil" in n or n.startswith("/") or "\\" in n or ".." in n.split("/") or ":" in n]
        check(not evil, f"no traversal, absolute, drive or backslash entry in the built file {evil}")
        mo = json.loads(zipfile.ZipFile(tmp / "trav.out.cof").read("manifest.json"))
        check(not any("x-notes" in v for v in mo["elements"]["appearance"]["variants"].values()), "a variant field pointing outside the container is dropped")
        r = subprocess.run([sys.executable, "-m", "cof_cli.cli", "validate", str(tmp / "trav.out.cof")], capture_output=True, text=True)
        check(r.returncode == 0, "cof validate accepts the built file" + ("" if r.returncode == 0 else "\n" + r.stdout[-1200:]))

        pg = page_for(); dialogs.clear()
        pg.set_input_files("#fileOpen", str(tmp / "minor.cof")); pg.wait_for_timeout(2500)
        msgs = pg.evaluate("() => runChecks().filter(i => i.sev === 'error').map(i => i.msg)")
        check(any(x.startswith("x-gallery.g1") for x in msgs), f"nudity on a minor through a kept-as-read category is a Checks error {[x for x in msgs if 'x-gallery' in x][:1]}")
        pg.evaluate("() => { window.__blobs = 0; const oc = URL.createObjectURL.bind(URL); URL.createObjectURL = x => { if (x && x.type === 'application/vnd.cof.character+zip') window.__blobs++; return oc(x) } }")
        pg.evaluate("document.getElementById('btnBuild').click()"); pg.wait_for_timeout(1500)
        if pg.query_selector("#dlg.on .dbtns .primary"): pg.click("#dlg.on .dbtns .primary"); pg.wait_for_timeout(1500)
        check(pg.evaluate("() => window.__blobs") == 0 and any("erreurs" in d.lower() or "error" in d.lower() for d in dialogs), "the build is refused like for the modelled categories")
        b.close()
    check(not errors, f"no page errors {errors[:2]}")
sys.exit(0 if ok else 1)
