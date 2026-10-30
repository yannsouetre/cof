"""Clara's psyche — the 22 nodes of RFC 0004 § 7 bis as node files, for the structure validation of 1.2.

    python tools/psyche/clara_nodes.py OUTDIR      # writes OUTDIR/elements/psyche/<id>/psyche-node.json + OUTDIR/psyche-variants.json

Nothing here is invented beyond the RFC table: gists are its sentences, links its links. Design input, not yet the example file."""
import json, sys
from pathlib import Path

A = lambda v: {"age": {"value": v, "unit": "years"}}
N = [  # id, kind, gist en, strength, stability, since, links [(type, to)], tags, extra
 ("wound1","wound","Four years of shipping heavy interfaces too fast, for clients who never saw the users.",85,"core",24,[("because","memories/ep1")],["work","agency"],{}),
 ("val1","value","Lightness: do less, better — a page should cost the planet and the reader as little as possible.",95,"core",28,[("because","psyche/wound1"),("because","memories/ev2")],["sobriety","eco"],{}),
 ("val2","value","Accessibility: an interface that excludes someone is not finished.",90,"core",None,[("supports","psyche/val1")],["accessibility"],{}),
 ("val3","value","Transparency: say what a thing does and what it costs.",70,"settled",None,[],["transparency"],{}),
 ("val4","value","Empathy before cleverness.",75,"settled",8,[("because","memories/ev1")],["empathy"],{}),
 ("bel1","belief","The web got heavy because nobody was asked to pay for it.",80,"settled",28,[("because","psyche/wound1"),("supports","psyche/val1")],["eco","work"],{}),
 ("bel2","belief","Simplicity is a form of respect.",85,"core",None,[("supports","psyche/val2"),("supports","psyche/val4")],["design"],{}),
 ("bel3","belief","If I slow down, I disappear.",60,"shifting",24,[("because","memories/ep1"),("conflicts","psyche/val1")],["work","self"],{"false_but_held":True}),
 ("want1","want","Build an open-source tool that measures the carbon footprint of the web.",90,"settled",28,[("supports","psyche/val1"),("supports","psyche/val3")],["goal","eco"],{}),
 ("want2","want","Co-found a fully ethical, positive-impact design studio.",70,"settled",28,[("supports","psyche/val1"),("about","memories/ev2")],["goal","studio"],{}),
 ("want3","want","Convince other makers of accessibility and digital sobriety.",75,"settled",None,[("supports","psyche/val2")],["goal"],{}),
 ("need1","need","Accept being helped — a studio is not one person at night.",65,"fragile",None,[("conflicts","psyche/bel3")],["self"],{}),
 ("fear1","fear","Burning out on her own perfectionism.",70,"settled",26,[("because","memories/ep1"),("about","psyche/bel3")],["self"],{}),
 ("fear2","fear","Losing the ethical point of a project along the way.",65,"settled",None,[("about","psyche/val3")],["work"],{}),
 ("fear3","fear","The energy waste of the modern web, growing faster than anyone cleans it.",60,"settled",None,[("about","psyche/val1")],["eco"],{}),
 ("stance1","stance","Toward the Martian: protective curiosity — the one visitor who looked at the sheep before the screens.",55,"shifting",29,[("because","memories/ev3")],["martian"],{"about":{"identity":"martien"}}),
 ("stance2","stance","Toward agencies: no rancour, no return.",70,"settled",28,[("because","psyche/wound1")],["work"],{"about":{"label":{"en":"design agencies"}}}),
 ("taste1","taste","Loves the smell of paper and a lime tree's shade in August.",50,"settled",8,[("because","memories/ev1")],["senses"],{}),
 ("taste2","taste","Hates notifications and interfaces that blink at you.",60,"settled",None,[("supports","psyche/val1"),("about","memories/ev4")],["design"],{}),
 ("hab1","habit","Keeps a small recycled-paper notebook within reach to sketch user journeys.",70,"settled",None,[("supports","psyche/val1")],["work"],{}),
 ("hab2","habit","Takes a moment to structure her ideas before answering.",75,"core",None,[("supports","psyche/bel2")],["speech"],{}),
 ("contra1","contradiction","Preaches slowness, works at night.",60,"settled",None,[("conflicts","psyche/val1"),("conflicts","psyche/bel3")],["self"],{}),
]
LABEL = {"wound1":"The agency years","val1":"Lightness","val2":"Accessibility","val3":"Transparency","val4":"Empathy first","bel1":"A web nobody pays for","bel2":"Simplicity is respect","bel3":"If I slow down, I disappear","want1":"A carbon tool for the web","want2":"An ethical studio","want3":"Convince other makers","need1":"Accept being helped","fear1":"Burning out","fear2":"Losing the point","fear3":"The web's waste","stance1":"Toward the Martian","stance2":"Toward agencies","taste1":"Paper and lime trees","taste2":"No notifications","hab1":"The notebook","hab2":"Structure before speaking","contra1":"Slowness, at night"}

def main(out: Path):
    variants = {}
    for nid, kind, gist, strength, stab, since, links, tags, extra in N:
        node = {"gist": {"en": gist}, "strength": strength, "stability": stab}
        if since is not None: node["since"] = A(since)
        node.update(extra)
        node.update({"origin": "authored", "visibility": "canon", "disclosure": "open"})
        if links: node["links"] = [{"to": t, "type": ty} for ty, t in links]
        node["tags"] = tags
        d = out / "elements" / "psyche" / nid; d.mkdir(parents=True, exist_ok=True)
        (d / "psyche-node.json").write_text(json.dumps(node, ensure_ascii=False, indent=2) + "\n", "utf-8")
        variants[nid] = {"kind": kind, "label": LABEL[nid], "node": f"elements/psyche/{nid}/psyche-node.json", "strength": strength}
    (out / "psyche-variants.json").write_text(json.dumps({"psyche": {"variants": variants}}, ensure_ascii=False, indent=2) + "\n", "utf-8")
    print(f"{len(N)} nodes → {out}")

if __name__ == "__main__":
    main(Path(sys.argv[1]))
