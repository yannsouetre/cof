"""Structural check of a psyche (RFC 0004 § 3 bis / 3 sexies, draft) on an unpacked set:
    python tools/psyche/check.py DIR [--memories ev1,ev2,...] [--identities a,b]
DIR holds psyche-variants.json and elements/psyche/<id>/psyche-node.json. Prints schema errors, structure problems, cycles."""
import json, sys
from pathlib import Path

KINDS = {"value","belief","want","need","fear","wound","stance","taste","habit","contradiction"}

def check(root: Path, memories=set(), identities=set(), schema_path=None):
    import jsonschema
    schema = json.load(open(schema_path or Path(__file__).resolve().parents[2] / "spec/schemas/psyche-node.schema.json"))
    V = jsonschema.Draft202012Validator(schema)
    variants = json.load(open(root / "psyche-variants.json"))["psyche"]["variants"]
    nodes = {vid: json.load(open(root / v["node"])) for vid, v in variants.items()}
    out = {"schema": [], "errors": [], "info": [], "cycles": []}
    for vid, node in nodes.items():
        for e in V.iter_errors(node): out["schema"].append(f"{vid}: {e.message}")
        k = variants[vid]["kind"]
        if k not in KINDS: out["errors"].append(f"{vid}: unknown kind {k}")
        for l in node.get("links", []):
            cat, t = l["to"].split("/", 1)
            if cat == "psyche" and t not in nodes: out["errors"].append(f"{vid}: dangling {l['to']}")
            if cat == "memories" and memories and t not in memories: out["errors"].append(f"{vid}: unknown memory {t}")
            if cat == "identities" and identities and t not in identities: out["errors"].append(f"{vid}: unknown identity {t}")
            if l["type"] in ("supports", "conflicts") and cat != "psyche": out["errors"].append(f"{vid}: {l['type']} must target a psyche node")
        if k == "contradiction" and sum(1 for l in node.get("links", []) if l["type"] == "conflicts") != 2: out["errors"].append(f"{vid}: a contradiction carries exactly two conflicts")
        if k == "wound" and not any(l["type"] == "because" and l["to"].startswith("memories/") for l in node.get("links", [])): out["info"].append(f"{vid}: wound without a memory cause")
        if "false_but_held" in node and k != "belief": out["errors"].append(f"{vid}: false_but_held on a {k}")
        if "about" in node and k != "stance": out["errors"].append(f"{vid}: about field on a {k}")
        if k == "stance" and "about" not in node: out["info"].append(f"{vid}: stance without a subject")
        a = node.get("about", {})
        if "identity" in a and identities and a["identity"] not in identities: out["errors"].append(f"{vid}: stance about unknown identity {a['identity']}")
        if "strength" in variants[vid] and variants[vid]["strength"] != node.get("strength", 50): out["errors"].append(f"{vid}: manifest strength differs from the node")
    unset = [vid for vid, n in nodes.items() if "strength" not in n]
    if len(unset) * 2 > len(nodes): out["info"].append(f"strength unset on {len(unset)}/{len(nodes)} nodes — set it node by node for a finished psyche")
    g = {vid: [l["to"].split("/", 1)[1] for l in n.get("links", []) if l["type"] == "because" and l["to"].startswith("psyche/")] for vid, n in nodes.items()}
    def cyc(s, seen):
        return any(t in seen or cyc(t, seen | {t}) for t in g.get(s, []))
    out["cycles"] = [vid for vid in g if cyc(vid, {vid})]
    if out["cycles"]: out["errors"].append("because-cycle through " + ", ".join(out["cycles"]))
    risk = {vid: n.get("risk", "none") for vid, n in nodes.items()}
    out["content_tags"] = sorted({"psyche-" + r for r in risk.values() if r != "none"})
    out["counts"] = {"nodes": len(nodes), "kinds": {k: sum(1 for v in variants.values() if v["kind"] == k) for k in KINDS if any(v["kind"] == k for v in variants.values())}}
    return out

if __name__ == "__main__":
    args = sys.argv[1:]; root = Path(args[0]); mem = set(); ids = set()
    if "--memories" in args: mem = set(args[args.index("--memories") + 1].split(","))
    if "--identities" in args: ids = set(args[args.index("--identities") + 1].split(","))
    r = check(root, mem, ids)
    print(json.dumps(r, ensure_ascii=False, indent=1))
    sys.exit(1 if r["schema"] or r["errors"] else 0)
