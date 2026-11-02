"""Clara's psyche — the 22 nodes of RFC 0004 § 7 bis as node files, the generator of example 10's `elements/psyche/`.

    python tools/psyche/clara_nodes.py OUTDIR                     # writes OUTDIR/elements/psyche/<id>/psyche-node.json + OUTDIR/psyche-variants.json
    python tools/psyche/clara_nodes.py OUTDIR --identity martien  # the cast form: the stance toward the Martian names his identity (example 11)

Nothing here is invented beyond the RFC table: gists are its sentences (English, and the French the file carries since
cof-cli part B — Clara's primary language), links its links. In the one-character file (example 10) the stance toward the
Martian names him by label; `--identity <id>` writes the `about.identity` form for a cast file."""
import json, sys
from pathlib import Path

A = lambda v: {"age": {"value": v, "unit": "years"}}
N = [  # id, kind, gist {en, fr}, strength, stability, since, links [(type, to)], tags, extra
 ("wound1","wound",{"en":"Four years of shipping heavy interfaces too fast, for clients who never saw the users.",
                    "fr":"Quatre ans à livrer trop vite des interfaces lourdes, pour des clients qui n'ont jamais vu les utilisateurs."},85,"core",24,[("because","memories/ep1")],["work","agency"],{}),
 ("val1","value",{"en":"Lightness: do less, better — a page should cost the planet and the reader as little as possible.",
                  "fr":"La légèreté : faire moins, mieux — une page doit coûter le moins possible à la planète et à celui qui la lit."},95,"core",28,[("because","psyche/wound1"),("because","memories/ev2")],["sobriety","eco"],{}),
 ("val2","value",{"en":"Accessibility: an interface that excludes someone is not finished.",
                  "fr":"L'accessibilité : une interface qui exclut quelqu'un n'est pas finie."},90,"core",None,[("supports","psyche/val1")],["accessibility"],{}),
 ("val3","value",{"en":"Transparency: say what a thing does and what it costs.",
                  "fr":"La transparence : dire ce qu'une chose fait et ce qu'elle coûte."},70,"settled",None,[],["transparency"],{}),
 ("val4","value",{"en":"Empathy before cleverness.",
                  "fr":"L'empathie avant l'astuce."},75,"settled",8,[("because","memories/ev1")],["empathy"],{}),
 ("bel1","belief",{"en":"The web got heavy because nobody was asked to pay for it.",
                   "fr":"Le web est devenu lourd parce que personne n'a jamais été prié d'en payer le prix."},80,"settled",28,[("because","psyche/wound1"),("supports","psyche/val1")],["eco","work"],{}),
 ("bel2","belief",{"en":"Simplicity is a form of respect.",
                   "fr":"La simplicité est une forme de respect."},85,"core",None,[("supports","psyche/val2"),("supports","psyche/val4")],["design"],{}),
 ("bel3","belief",{"en":"If I slow down, I disappear.",
                   "fr":"Si je ralentis, je disparais."},60,"shifting",24,[("because","memories/ep1"),("conflicts","psyche/val1")],["work","self"],{"false_but_held":True}),
 ("want1","want",{"en":"Build an open-source tool that measures the carbon footprint of the web.",
                  "fr":"Construire un outil open source qui mesure l'empreinte carbone du web."},90,"settled",28,[("supports","psyche/val1"),("supports","psyche/val3")],["goal","eco"],{}),
 ("want2","want",{"en":"Co-found a fully ethical, positive-impact design studio.",
                  "fr":"Cofonder un studio de design entièrement éthique, à impact positif."},70,"settled",28,[("supports","psyche/val1"),("about","memories/ev2")],["goal","studio"],{}),
 ("want3","want",{"en":"Convince other makers of accessibility and digital sobriety.",
                  "fr":"Convaincre d'autres créateurs de l'accessibilité et de la sobriété numérique."},75,"settled",None,[("supports","psyche/val2")],["goal"],{}),
 ("need1","need",{"en":"Accept being helped — a studio is not one person at night.",
                  "fr":"Accepter d'être aidée — un studio, ce n'est pas une personne seule la nuit."},65,"fragile",None,[("conflicts","psyche/bel3")],["self"],{}),
 ("fear1","fear",{"en":"Burning out on her own perfectionism.",
                  "fr":"S'épuiser sur son propre perfectionnisme."},70,"settled",26,[("because","memories/ep1"),("about","psyche/bel3")],["self"],{}),
 ("fear2","fear",{"en":"Losing the ethical point of a project along the way.",
                  "fr":"Perdre en chemin le sens éthique d'un projet."},65,"settled",None,[("about","psyche/val3")],["work"],{}),
 ("fear3","fear",{"en":"The energy waste of the modern web, growing faster than anyone cleans it.",
                  "fr":"Le gaspillage d'énergie du web moderne, qui grossit plus vite qu'on ne le nettoie."},60,"settled",None,[("about","psyche/val1")],["eco"],{}),
 ("stance1","stance",{"en":"Toward the Martian: protective curiosity — the one visitor who looked at the sheep before the screens.",
                      "fr":"Envers le Martien : une curiosité protectrice — le seul visiteur qui a regardé les moutons avant les écrans."},55,"shifting",29,[("because","memories/ev3")],["martian"],{"about":{"label":{"en":"the Martian","fr":"le Martien"}}}),
 ("stance2","stance",{"en":"Toward agencies: no rancour, no return.",
                      "fr":"Envers les agences : ni rancune, ni retour."},70,"settled",28,[("because","psyche/wound1")],["work"],{"about":{"label":{"en":"design agencies","fr":"les agences de design"}}}),
 ("taste1","taste",{"en":"Loves the smell of paper and a lime tree's shade in August.",
                    "fr":"Aime l'odeur du papier et l'ombre d'un tilleul en août."},50,"settled",8,[("because","memories/ev1")],["senses"],{}),
 ("taste2","taste",{"en":"Hates notifications and interfaces that blink at you.",
                    "fr":"Déteste les notifications et les interfaces qui vous clignotent au visage."},60,"settled",None,[("supports","psyche/val1"),("about","memories/ev4")],["design"],{}),
 ("hab1","habit",{"en":"Keeps a small recycled-paper notebook within reach to sketch user journeys.",
                  "fr":"Garde un petit carnet en papier recyclé à portée de main pour croquer des parcours utilisateurs."},70,"settled",None,[("supports","psyche/val1")],["work"],{}),
 ("hab2","habit",{"en":"Takes a moment to structure her ideas before answering.",
                  "fr":"Prend un temps pour structurer ses idées avant de répondre."},75,"core",None,[("supports","psyche/bel2")],["speech"],{}),
 ("contra1","contradiction",{"en":"Preaches slowness, works at night.",
                             "fr":"Prône la lenteur, travaille la nuit."},60,"settled",None,[("conflicts","psyche/val1"),("conflicts","psyche/bel3")],["self"],{}),
]
LABEL = {  # bilingual « FR / EN », the convention of Clara's memories (readers keep the half of their language)
 "wound1": "Les années d'agence / The agency years",
 "val1": "La légèreté / Lightness",
 "val2": "L'accessibilité / Accessibility",
 "val3": "La transparence / Transparency",
 "val4": "L'empathie d'abord / Empathy first",
 "bel1": "Un web que personne ne paie / A web nobody pays for",
 "bel2": "La simplicité, un respect / Simplicity is respect",
 "bel3": "Si je ralentis, je disparais / If I slow down, I disappear",
 "want1": "Un outil carbone pour le web / A carbon tool for the web",
 "want2": "Un studio éthique / An ethical studio",
 "want3": "Convaincre d'autres créateurs / Convince other makers",
 "need1": "Accepter d'être aidée / Accept being helped",
 "fear1": "L'épuisement / Burning out",
 "fear2": "Perdre le sens / Losing the point",
 "fear3": "Le gaspillage du web / The web's waste",
 "stance1": "Envers le Martien / Toward the Martian",
 "stance2": "Envers les agences / Toward agencies",
 "taste1": "Papier et tilleuls / Paper and lime trees",
 "taste2": "Pas de notifications / No notifications",
 "hab1": "Le carnet / The notebook",
 "hab2": "Structurer avant de parler / Structure before speaking",
 "contra1": "La lenteur, la nuit / Slowness, at night"}

def main(out: Path, martian_identity: str | None = None, identity: str | None = "id1"):
    variants = {}
    for nid, kind, gist, strength, stab, since, links, tags, extra in N:
        node = {"gist": {"en": gist["en"], "fr": gist["fr"]}, "strength": strength, "stability": stab}
        if since is not None: node["since"] = A(since)
        node.update(json.loads(json.dumps(extra)))
        if nid == "stance1" and martian_identity:
            node["about"] = {"identity": martian_identity}
        node.update({"origin": "authored", "visibility": "canon", "disclosure": "open"})
        if links: node["links"] = [{"to": t, "type": ty} for ty, t in links]
        node["tags"] = tags
        d = out / "elements" / "psyche" / nid; d.mkdir(parents=True, exist_ok=True)
        (d / "psyche-node.json").write_text(json.dumps(node, ensure_ascii=False, indent=2) + "\n", "utf-8")
        variants[nid] = {"kind": kind, "label": LABEL[nid], "node": f"elements/psyche/{nid}/psyche-node.json", **({"identity": identity} if identity else {}), "strength": strength}
    (out / "psyche-variants.json").write_text(json.dumps({"psyche": {"variants": variants}}, ensure_ascii=False, indent=2) + "\n", "utf-8")
    print(f"{len(N)} nodes → {out}")

if __name__ == "__main__":
    args = sys.argv[1:]
    mid = args[args.index("--identity") + 1] if "--identity" in args else None
    main(Path(args[0]), mid)
