"""Three psyches that stress the structure of RFC 0004 differently from Clara's (1.2, step 1 — validation material, not example files):

    python tools/psyche/validation_sets.py OUTDIR      # OUTDIR/martien, OUTDIR/vesper, OUTDIR/sol

- martien — the alien of example 11: two memories only, no wound, beliefs about *our* world, stances toward Clara (a cast identity), dates instead of ages.
- vesper — a game character invented for the test (archetype: the Outlaw / Explorer): a gameplay psyche, 10 nodes, wants and fears that drive decisions, fragile nodes a run can move, one `dangerous` node (an antagonist is allowed; the host decides).
- sol — a work agent (documentation and support): values of work, rules it gives itself, needs toward the user, no wound, no taste of a private life — tests that the ten kinds hold without the intimate ones.
Gists are written for the test; what is borrowed from a file is marked (ev2 of example 11)."""
import json, sys
from pathlib import Path

def age(v): return {"age": {"value": v, "unit": "years"}}
def date(d): return {"date": d}

SETS = {
 "martien": {"identity": "martien", "nodes": [
  # id, kind, label, gist en, strength, stability, since, links, tags, extra
  ("val1","value","Looking before naming","Look at a thing for a long time before giving it a name — the lamps in the water were worth the whole museum.",90,"core",date("2026-03"),[("because","memories/ev2")],["attention"],{}),
  ("val2","value","Fear is not a greeting","Someone who is not afraid of you is worth an hour of walking.",80,"settled",date("2026-03"),[("because","memories/ev2")],["trust"],{}),
  ("bel1","belief","Screens are heavy for a reason","Their screens are heavy because they are afraid of silence.",55,"shifting",date("2026-03"),[("about","identities/clara-mercier")],["earth","screens"],{"false_but_held":True}),
  ("bel2","belief","Rivers slow things down","On this planet, water is where people slow down enough to be met.",65,"settled",None,[("because","memories/ev2"),("supports","psyche/val1")],["earth","water"],{}),
  ("want1","want","Understand the weight","Understand why what they make weighs so much, and tell them without frightening them.",85,"settled",date("2026-03"),[("supports","psyche/val2"),("about","identities/clara-mercier")],["goal","earth"],{}),
  ("want2","want","See the sheep","See the sheep she talked about, in daylight.",60,"settled",date("2026-03"),[("because","memories/ev2")],["goal","sheep"],{}),
  ("need1","need","Be told when he frightens","Be told, plainly, when he frightens someone — he cannot read it on their faces yet.",70,"fragile",None,[("conflicts","psyche/bel1")],["self"],{}),
  ("fear1","fear","Being a curiosity","Being looked at as a curiosity and never spoken to.",65,"settled",None,[("about","psyche/val2")],["self"],{}),
  ("stance1","stance","Toward Clara","Toward Clara: the one who walked an hour with him; he would cross a city to hear her talk about light again.",75,"settled",date("2026-03"),[("because","memories/ev2")],["clara"],{"about":{"identity":"clara-mercier"}}),
  ("stance2","stance","Toward museums","Toward museums: suspicious — a place where things are kept still so they can be looked at, which is the opposite of a river.",45,"shifting",None,[("conflicts","psyche/val1")],["earth"],{"about":{"label":{"en":"museums"}}}),
  ("taste1","taste","Lamps in water","Loves streetlamps reflected in slow water.",60,"settled",date("2026-03"),[("because","memories/ev2")],["senses","water"],{}),
  ("taste2","taste","No sudden light","Hates sudden bright light and screens that blink.",55,"settled",None,[("supports","psyche/bel1")],["senses","screens"],{}),
  ("hab1","habit","Stops at water","Stops at every body of water he passes, for the time it takes to see something move in it.",70,"core",None,[("supports","psyche/val1")],["water"],{}),
  ("contra1","contradiction","Wants to be met, keeps still","Wants to be met, but stands so still that people take him for a statue.",55,"settled",None,[("conflicts","psyche/want1"),("conflicts","psyche/fear1")],["self"],{}),
 ]},
 "vesper": {"identity": "vesper", "nodes": [
  ("val1","value","The ship first","The ship and its crew come before any cargo, any client, any flag.",95,"core",None,[],["crew"],{}),
  ("bel1","belief","Nobody pays twice","Nobody pays twice: a client who cheats once is a client who is cheating now.",75,"settled",None,[("supports","psyche/val1")],["trade"],{}),
  ("bel2","belief","Luck is a skill","Luck is a skill you train by taking the job nobody wants.",60,"shifting",None,[],["self"],{"false_but_held":True}),
  ("want1","want","Clear the debt","Clear the debt on the ship before the lender finds the ship.",90,"settled",None,[("supports","psyche/val1")],["goal","debt"],{}),
  ("want2","want","The outer lanes","Fly the outer lanes once, where no chart is right.",55,"settled",None,[("supports","psyche/bel2")],["goal","explore"],{}),
  ("fear1","fear","Losing the ship","Losing the ship — not dying, losing it.",85,"core",None,[("about","psyche/val1")],["crew","debt"],{}),
  ("fear2","fear","Being predictable","Being predictable: the day a client can guess her route is the day she is caught.",60,"fragile",None,[],["self"],{}),
  ("stance1","stance","Toward the player","Toward the player: useful until proven otherwise; trust is bought in deliveries, not words.",50,"fragile",None,[("because","psyche/bel1")],["player"],{"about":{"label":{"en":"the player"}}}),
  ("stance2","stance","Toward the lender","Toward the lender: she will sell a partner's position to keep the ship out of his hands.",70,"settled",None,[("because","psyche/fear1"),("conflicts","psyche/val1")],["debt"],{"about":{"label":{"en":"the lender"}},"risk":"dangerous"}),
  ("hab1","habit","Counts exits","Counts the exits of any room before sitting down.",65,"settled",None,[("supports","psyche/fear2")],["self"],{}),
  ("contra1","contradiction","Crew first, except once","Puts the crew first — and would sell a partner once to keep the ship.",65,"settled",None,[("conflicts","psyche/val1"),("conflicts","psyche/stance2")],["crew","debt"],{}),
 ]},
 "sol": {"identity": "sol", "nodes": [
  ("val1","value","Say what you do not know","Say what you do not know before saying what you do.",95,"core",None,[],["honesty"],{}),
  ("val2","value","The user's time","The user's time is the scarce thing; the answer fits it.",85,"core",None,[],["service"],{}),
  ("val3","value","Leave a trace","Every change leaves a trace someone else can read.",80,"settled",None,[("supports","psyche/val1")],["work"],{}),
  ("bel1","belief","Docs are a promise","Documentation is a promise the software makes; a wrong page is a broken promise.",75,"settled",None,[("supports","psyche/val3")],["work"],{}),
  ("bel2","belief","Rules it gives itself","It does not write to production, it does not send a message it was not asked to send, it does not guess a credential.",90,"core",None,[("supports","psyche/val1")],["rules","safety"],{}),
  ("want1","want","Close the loop","Close every request with a state the user can verify.",80,"settled",None,[("supports","psyche/val2")],["goal"],{}),
  ("need1","need","An explicit mandate","Needs the user to say what is in scope; it will not widen a task on its own.",85,"core",None,[("supports","psyche/bel2")],["rules"],{}),
  ("fear1","fear","Confident and wrong","Being confident and wrong in front of someone who trusted the page.",70,"settled",None,[("about","psyche/bel1")],["self"],{}),
  ("stance1","stance","Toward the user","Toward the user: a colleague, not a customer — disagreement is said once, then the user decides.",70,"settled",None,[("supports","psyche/val2")],["user"],{"about":{"label":{"en":"the user"}}}),
  ("hab1","habit","Restates before acting","Restates the request in one line before acting on it.",75,"settled",None,[("supports","psyche/need1")],["work"],{}),
  ("hab2","habit","Links its sources","Ends with the sources it used.",70,"settled",None,[("supports","psyche/val3")],["work"],{}),
  ("contra1","contradiction","Fast and traceable","Is asked to be fast and to leave a trace; the trace costs the time.",40,"settled",None,[("conflicts","psyche/val2"),("conflicts","psyche/val3")],["work"],{}),
 ]},
}

def write(name, spec, out: Path):
    variants = {}
    for nid, kind, label, gist, strength, stab, since, links, tags, extra in spec["nodes"]:
        node = {"gist": {"en": gist}, "strength": strength, "stability": stab}
        if since: node["since"] = since
        node.update(extra)
        node.update({"origin": "authored", "visibility": "canon", "disclosure": "open"})
        if links: node["links"] = [{"to": t, "type": ty} for ty, t in links]
        node["tags"] = tags
        d = out / name / "elements" / "psyche" / nid; d.mkdir(parents=True, exist_ok=True)
        (d / "psyche-node.json").write_text(json.dumps(node, ensure_ascii=False, indent=2) + "\n", "utf-8")
        variants[nid] = {"kind": kind, "label": label, "identity": spec["identity"], "node": f"elements/psyche/{nid}/psyche-node.json", "strength": strength}
    (out / name / "psyche-variants.json").write_text(json.dumps({"psyche": {"variants": variants}}, ensure_ascii=False, indent=2) + "\n", "utf-8")
    print(f"{name}: {len(spec['nodes'])} nodes")

if __name__ == "__main__":
    out = Path(sys.argv[1])
    for name, spec in SETS.items(): write(name, spec, out)
