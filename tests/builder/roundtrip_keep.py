"""Round-trip of builder 0.14.2: open the fixture of make_fixture_keep.py, build without touching anything, and check
that everything the builder does not model survives (hunt H3-08 / 09 / 10 / 11 / 12 / 13), then that cof validate accepts
the result and that `runChecks` flags an inheritance cycle (H3-14).
Usage (from cli/, PYTHONPATH=.): python ../tests/builder/roundtrip_keep.py ../builder/index.html keep.cof out.cof"""
import json, subprocess, sys, zipfile, hashlib
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
        page.wait_for_selector("#dlg.on .dbtns .primary", timeout=10000)
        page.click("#dlg.on .dbtns .primary")
    dl.value.save_as(str(OUT))
    page.wait_for_timeout(500)
    # H3-14: a cycle is an error of the Checks step
    cyc = page.evaluate("""() => { const keep = JSON.stringify(S.presets);
        S.presets.default.extends = 'young';
        const r1 = runChecks().filter(i => i.sev === 'error' && /extends/.test(i.msg)).length;
        S.presets = JSON.parse(keep);
        const v = S.elements.personality.variants; const k2 = JSON.stringify(v);
        v.p1.derives_from = 'p2';
        const r2 = runChecks().filter(i => i.sev === 'error' && /derives_from/.test(i.msg)).length;
        S.elements.personality.variants = JSON.parse(k2); runChecks();
        return [r1, r2] }""")
    # hunt 1.2.2 BUILDER-05: a dangling derives_from is a Checks error; deleting p1 (p2 derives from it) and f1 (source of a derived asset) leaves nothing dangling
    dang = page.evaluate("""() => { const v = S.elements.personality.variants; const k = JSON.stringify(v); v.p2.derives_from = 'zz';
        const n = runChecks().filter(i => i.sev === 'error' && /derives_from/.test(i.msg) && /zz/.test(i.msg)).length; S.elements.personality.variants = JSON.parse(k); return n }""")
    gone = page.evaluate("""() => { purgeVariant('personality', 'p1'); purgeVariant('appearance', 'f1');
        return { p2: S.elements.personality.variants.p2?.derives_from ?? null, canny: S.assets.some(a => a.id === 'a-head-front-canny'), errors: runChecks().filter(i => i.sev === 'error').map(i => i.msg) } }""")
    OUT2 = OUT.with_name(OUT.stem + ".del.cof")
    with page.expect_download(timeout=60000) as dl2:
        page.evaluate("document.getElementById('btnBuild').click()")
        page.wait_for_selector("#dlg.on .dbtns .primary", timeout=10000)
        page.click("#dlg.on .dbtns .primary")
    dl2.value.save_as(str(OUT2))
    b.close()

print("page errors:", errors or "none")
zi, zo = zipfile.ZipFile(COF), zipfile.ZipFile(OUT)
src, m = json.loads(zi.read("manifest.json")), json.loads(zo.read("manifest.json"))
names = zo.namelist()
ok = True
def check(cond, msg):
    global ok
    print(("ok  " if cond else "FAIL"), msg)
    ok = ok and cond
def same(path):
    return path in names and zo.read(path) == zi.read(path)
P1, F1, O1 = (m["elements"]["personality"]["variants"]["p1"], m["elements"]["appearance"]["variants"]["f1"], m["elements"]["appearance"]["variants"]["o1"])
# H3-08
check(P1.get("story") == "elements/personality/p1/story.md" and same("elements/personality/p1/story.md"), "story kept (field + story.md byte for byte)")
check(P1.get("lorebook") == "elements/personality/p1/lorebook.json" and same("elements/personality/p1/lorebook.json"), "lorebook kept (field + file)")
check(P1.get("tags") == ["canon", "lyon"], "variant tags kept")
check(O1.get("neutral") is False, "neutral:false kept on the outfit")
# H3-09
ps_in, ps_out = json.loads(zi.read("elements/personality/p1/psyche.json")), json.loads(zo.read("elements/personality/p1/psyche.json"))
check(ps_out.get("contradictions") == ps_in.get("contradictions"), "psyche.json contradictions kept")
check(ps_out.get("baseline_emotion") == ps_in.get("baseline_emotion"), "psyche.json baseline_emotion kept")
check(ps_out.get("traits", {}).get("custom") == ps_in["traits"].get("custom"), "psyche.json custom traits kept")
check([ (g["id"], g.get("horizon"), g.get("priority")) for g in ps_out["goals"] ] == [ (g["id"], g.get("horizon"), g.get("priority")) for g in ps_in["goals"] ], "goal ids, horizon and priority kept")
check([ (f["id"], f.get("intensity")) for f in ps_out["fears"] ] == [ (f["id"], f.get("intensity")) for f in ps_in["fears"] ], "fear ids and intensity kept")
check(ps_out.get("traits", {}).get("big5") == ps_in["traits"]["big5"], "big5 unchanged")
# H3-10
check(m.get("x-studio") == src["x-studio"], "unknown root key kept")
I = m["identities"]["clara"]
check(I.get("x-casting") == {"agency": "none"} and I.get("tags") == {"mood": "calm"} and I.get("language") == "fr", "identity unknown keys, tags and language kept")
D = m["presets"]["default"]
check(D.get("x-render") == {"seed": 42} and D.get("style_tags") == ["warm-light"], "preset unknown key and style_tags kept")
check(F1.get("x-note") == "keep me" and F1.get("estimated") is True, "variant unknown key and estimated kept")
check(m["rights"]["permissions"].get("x-house-rule") == "no-ads", "permissions unknown key kept")
check(m["provenance"].get("x-batch") == "b-17" and m["provenance"]["created"] == src["provenance"]["created"], "provenance unknown key and created kept")
check(m["provenance"]["generator"] == "cof-builder/0.14.2", "generator is 0.14.2")
prof = json.loads(zo.read("elements/voice/v1/profile.json"))
check(prof.get("x-studio") == {"take": 3} and prof["speech_style"].get("x-pauses") == "long" and prof["canonical"]["pitch"].get("hz") == [180, 220], "voice profile unknown keys kept at every level")
check(prof.get("engines", [{}])[0].get("x-temperature") == 0.6 and prof["engines"][0].get("voice_id") == "clara-fr", "voice engine extra field kept")
check(m["elements"]["voice"]["variants"]["v1"].get("x-recorded") is False, "voice variant unknown key kept")
check(m["priorities"]["by_target"].get("x-kiosk") == {"visual": ["images"]} and "game-3d" in m["priorities"]["by_target"], "priorities.by_target kept")
# H3-11
check(F1.get("derived") == ["a-head-front-canny"] and any(a["id"] == "a-head-front-canny" for a in m["assets"]) and same("elements/appearance/f1/head.front.canny.png"), "derived asset kept with its file")
check(P1.get("profiles") == src["elements"]["personality"]["variants"]["p1"]["profiles"], "token profiles kept")
check(O1.get("spec") == "elements/appearance/o1/outfit.json" and same("elements/appearance/o1/outfit.json"), "outfit.json kept (spec + file)")
check(F1.get("code") == "elements/appearance/f1/face.json" and same("elements/appearance/f1/face.json"), "face.json kept (code + file)")
check(m.get("mapping_vocabularies") == src["mapping_vocabularies"], "mapping_vocabularies kept")
# H3-13
W = [a for a in m["assets"] if a.get("role") == "weights"]
check(len(W) == 1 and W[0]["id"] == "a-lora-l1" and W[0].get("uri") == src["assets"][[a["id"] for a in src["assets"]].index("a-lora-l1")]["uri"], "one weights asset, same id as the file, by link")
wj = json.loads(zo.read("elements/identity_weights/l1/weights.json"))
check(wj["base_model"].get("version") == "1.0" and wj["pages"][0]["label"] == "Page du modèle (exemple fictif)" and wj.get("rank") == 16 and wj.get("training"), "weights.json version, page label, rank and training kept")
# H3-12
check(m["presets"]["young"].get("defaults", {}).get("appearance") == "f1", "child preset default on an inherited category kept")
# H3-14
check(cyc == [1, 1], f"cycle checks report an error for extends and derives_from (got {cyc})")
# nothing else lost: every file of the source is in the output except the ones the builder regenerates
regen = {"manifest.json", "COF.md", "Thumbnails/thumbnail.png"}
missing = [n for n in zi.namelist() if n not in names and n not in regen]
check(not missing, f"no file lost ({len(zi.namelist())} in, {len(names)} out){': ' + ', '.join(missing) if missing else ''}")
# hunt 1.2.2
PS, MEM = m["elements"].get("psyche", {}), m["elements"].get("memories", {})
check(PS.get("variants", {}).get("dream1", {}).get("kind") == "x-dream" and json.loads(zo.read("elements/psyche/dream1/psyche-node.json")) == json.loads(zi.read("elements/psyche/dream1/psyche-node.json")), "unknown psyche kind kept as written, node unchanged (BUILDER-03, D-H1)")
check(MEM.get("variants", {}).get("ev1", {}).get("x-mood") == "blue" and MEM.get("x-index") == "v2" and PS.get("x-graph-layout") == {"seed": 7}, "x- keys on a memory entry and on the memories / psyche category objects kept (BUILDER-04)")
check(MEM.get("variants", {}).get("ev1", {}).get("identity") == "clara", "memory identity kept with a single identity (BUILDER-08)")
check(m.get("languages") == src["languages"] and all(l in m["tags"]["auto"] for l in src["languages"]), f"declared languages kept, with their tags (BUILDER-01, got {m.get('languages')})")
check(m["metadata"].get("@context") == src["metadata"]["@context"], "metadata @context kept with all its prefixes (BUILDER-02)")
check("elements/motion/m1/visemes.json" not in names and "visemes" not in m["elements"]["motion"]["variants"]["m1"], "no visemes.json added to a clips variant that had none (BUILDER-06)")
check("elements/personality/p2/psyche.json" not in names and "psyche" not in m["elements"]["personality"]["variants"]["p2"], "no psyche.json made from a card that had none (BUILDER-06)")
c_in, c_out = json.loads(zi.read("elements/personality/p1/card.json")), json.loads(zo.read("elements/personality/p1/card.json"))
check(c_out["data"]["extensions"]["cof"] == c_in["data"]["extensions"]["cof"], "card extensions.cof goal / fear ids kept (BUILDER-06)")
check(json.loads(zo.read("elements/personality/p2/card.json"))["data"].get("creator") == "", "empty card creator kept (BUILDER-08)")
check(m["presets"]["young"]["slots"].get("psyche") == src["presets"]["young"]["slots"]["psyche"] and "memories" not in m["presets"]["young"]["slots"], "preset lists exactly as declared: own list equal to the inherited one kept, none added (BUILDER-07)")
check(not any(k in m for k in ("x-casting", "language")), "identity unknown keys and language not copied to the manifest root (BUILDER-08)")
check(dang == 1, f"a dangling derives_from is a Checks error (BUILDER-05, got {dang})")
check(gone["p2"] is None and not gone["canny"] and not gone["errors"], f"deleting p1 and f1 clears p2.derives_from and drops the orphan derived asset (BUILDER-05, {gone})")
md = json.loads(zipfile.ZipFile(OUT2).read("manifest.json"))
check("derives_from" not in md["elements"]["personality"]["variants"]["p2"] and not any(a.get("source") == "a-head-front" for a in md["assets"]) and "elements/appearance/f1/head.front.canny.png" not in zipfile.ZipFile(OUT2).namelist(), "rebuilt file after the deletion: no dangling pointer, no orphan derived file")
r2 = subprocess.run([sys.executable, "-m", "cof_cli.cli", "validate", str(OUT2)], capture_output=True, text=True)
check(r2.returncode == 0, "cof validate accepts the file rebuilt after the deletion (BUILDER-05)" + ("" if r2.returncode == 0 else "\n" + r2.stdout[-1500:]))
check(not errors, "no page errors")
r = subprocess.run([sys.executable, "-m", "cof_cli.cli", "validate", str(OUT)], capture_output=True, text=True)
check(r.returncode == 0, "cof validate accepts the rebuilt file" + ("" if r.returncode == 0 else "\n" + r.stdout[-1500:]))
sys.exit(0 if ok else 1)
