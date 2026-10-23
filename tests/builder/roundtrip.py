"""Round-trip test for the builder: open a .cof whose manifest carries a category the builder does not know,
build, and check that the category, its sub-file, its asset and its preset slot survive unchanged."""
import json, sys, zipfile, io, hashlib
from pathlib import Path
from playwright.sync_api import sync_playwright

BUILDER = Path(sys.argv[1]).resolve()
COF = Path(sys.argv[2]).resolve()
OUT = Path(sys.argv[3]).resolve()

with sync_playwright() as p:
    b = p.chromium.launch()
    ctx = b.new_context(accept_downloads=True)
    page = ctx.new_page()
    errors = []
    page.on("pageerror", lambda e: errors.append(str(e)))
    page.on("dialog", lambda d: d.accept())
    page.goto(BUILDER.as_uri())
    page.set_input_files("#fileOpen", str(COF))
    page.wait_for_timeout(2500)
    with page.expect_download(timeout=60000) as dl:
        page.evaluate("document.getElementById('btnBuild').click()")
    dl.value.save_as(str(OUT))
    page.wait_for_timeout(500)
    log = page.inner_text("#buildLog")
    b.close()

print("build log:", log)
print("page errors:", errors or "none")
z = zipfile.ZipFile(OUT)
names = z.namelist()
m = json.loads(z.read("manifest.json"))
src = json.loads(zipfile.ZipFile(COF).read("manifest.json"))
ok = True
def check(cond, msg):
    global ok
    print(("ok  " if cond else "FAIL"), msg)
    ok = ok and cond
check(m["cof"] == src["cof"], f"version kept: {m['cof']}")
check(m["elements"].get("sketches") == src["elements"]["sketches"], "unknown category written back byte for byte")
check(m["presets"]["default"]["slots"].get("sketches") == ["n1", "n2"], "preset slot of the unknown category kept")
check("elements/sketches/n1/sketch.json" in names and z.read("elements/sketches/n1/sketch.json") == zipfile.ZipFile(COF).read("elements/sketches/n1/sketch.json"), "sub-file kept unchanged")
a = next((x for x in m["assets"] if x["id"] == "a-n1"), None)
check(a is not None and a["path"] in names and hashlib.sha256(z.read(a["path"])).hexdigest() == a["sha256"], "media asset kept with its hash")
check("sketches" in m.get("coverage", {}).get("elements", []), "coverage lists the category")
check(not errors, "no page errors")
sys.exit(0 if ok else 1)
