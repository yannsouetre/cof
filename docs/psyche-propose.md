# Personality ↔ psyche: the proposal contract — v0.1 (COF 1.2, RFC 0004 § 3 octies)

Few authors will build a psyche of thirty nodes by hand. The builder and cof-cli therefore **propose** nodes from what the author already wrote — the personality sheet, the 1.0 lists, the memories — and the author ticks what stays. The recipe is **model-agnostic**: this page is the whole contract, the same for an OpenAI-compatible gateway, a chat window the author pastes into, a platform that embeds the builder, or a rule (the 1.0 lists, a zodiac sign). The one rule that never moves: **a proposal is never written as it is**. Nothing enters the file without an explicit accept, node by node (`--accept` in cof-cli, a checkbox per row in the builder).

Two directions:
1. **Decomposition** (personality → nodes): a bundle in, a list of candidate nodes out (§ 1–3).
2. **Rendering** (nodes → text): the « Who she is » section of `SOUL.md`, deterministic, no model (§ 6).

## 1. Input: the bundle

`cof psyche propose <src> --bundle-out bundle.json` writes it (with the prompt of § 3); the builder builds the same object from its state.

```jsonc
{ "cof": "1.2", "contract": "psyche-propose/0.1",
  "languages": ["fr", "en"],                       // the author's languages: every gist comes in each of them (the preset's language first, then the file's)
  "character": { "id": "id1", "name": "Clara Mercier", "gender": "female", "age": 29, "language": "fr", "summary": "…" },
  "preset": "fr-agent",                            // the preset whose personality and language were read (null: the character's default)
  "cast": [ { "id": "martien", "name": "the Martian", "gender": "male" } ],   // the other characters of the file, for stances (`about: {"identity"}`)
  "personality": [                                 // the preset's personality variant first, then one more per other language of the character
    { "variant": "p2", "kind": "card", "language": "fr", "description": "…", "personality": "…", "scenario": "…", "first_mes": "…", "mes_example": "…", "system_prompt": "…" },
    { "variant": "p6", "kind": "description", "language": "en", "text": "…" } ],
  "lists": { "goals": ["…"], "fears": ["…"], "values": ["sobriété", "…"], "behavior": ["…"] },   // the 1.0 lists (psyche.json, card extensions cof.*), merged by text
  "memories": [ { "id": "ev2", "kind": "moment", "gist": "…", "when": "age 28" }, { "id": "ep1", "kind": "period", "gist": "…", "when": "age 24–28" } ],   // the character's memories, copies left out
  "psyche":   [ { "id": "val1", "kind": "value", "gist": "…", "strength": 95 } ],   // the nodes that already exist: not to be proposed again, but linkable
  "max_nodes": 40 }
```

Gists are given in the preset's language (`character.language`). Images are never sent: a psyche is text.

## 2. Output: the proposal (strict JSON)

```jsonc
{ "contract": "psyche-propose/0.1",
  "nodes": [
    { "id": "c1",                                  // a short slug, local to the proposal (c1, c2…); never an id of the file
      "kind": "belief",                            // one of the eleven kinds of RFC 0004 § 3
      "gist": { "fr": "…", "en": "…" },            // one sentence per language, 100–300 characters each
      "strength": 60, "stability": "shifting",     // optional (defaults 50, settled)
      "since": { "age": { "value": 24 } },         // optional: {age: {value}} and/or {date: "YYYY[-MM[-DD]]"}, approx
      "until": { "age": { "value": 45 } },         // optional, same shape: when the character let it go (RFC 0004 § 3 nonies)
      "aware": "no",                               // optional: yes (default) | partly | no — whether the character knows it about itself
      "because": ["memories/ep1"],                 // optional: memories/<id> (preferred), psyche/<id>, or a candidate id of this proposal
      "supports": ["psyche/val1"],                 // optional: psyche/<id> or a candidate id
      "between": ["c3", "psyche/val1"],            // contradiction only, required: exactly two sides (candidate ids or psyche/<id>)
      "about": { "user": true },                   // stance only: {user: true} | {identity: "<cast id>"} | {node: "memories/<id>" | "psyche/<id>" | "<candidate>"} | {label: {lang: text}}
      "false_but_held": true,                      // belief only: the lie the character tells itself
      "valence": 60,                               // stance and taste only, optional: −100 (hostile / hates) … +100 (warm / loves)
      "risk": { "value": "inappropriate", "why": "…" },   // none | inappropriate | dangerous, with the reason
      "tags": ["work", "self"],
      "source": "card.description" } ],            // where it comes from — see below
  "notes": "free text for the reviewer" }
```

A candidate MAY carry `until`, `aware` and `valence` (RFC 0004 § 3 nonies), checked and written like the other optional fields. The prompt of § 3 does not ask the model for them (they are the author's judgement: what the character does not know about itself, how warm a stance is); an author or another tool may add them to a proposal before `--apply`.

`source` is required and names one of: `card.description`, `card.personality`, `card.scenario`, `card.first_mes`, `card.mes_example`, `card.system_prompt` (a field of the card, optionally `@<variant>`), `text` (the free description), `memory <id>` (a memory of the bundle), `list goals[n]` / `list fears[n]` / `list values[n]` / `list behavior[n]` (an entry of the 1.0 lists), `inferred` (read between the lines), `zodiac`, `mbti`, `enneagram` or `big-five` (the rule-based profile entries of § 4, never a model's).

**Validation** (`cof_cli/propose.py › validate`, the same checks in the builder). Refused: a kind outside the eleven; an empty gist or one over 600 characters; a strength outside 0–100 or a stability outside the four levels; a malformed `since` or `until`, or an `until` before the `since`; an `aware` other than yes / partly / no; a `valence` off a stance or a taste, or outside −100 … +100; a `because` / `about` / `supports` / `between` that names a memory or a node the bundle does not have (never invent a memory); a candidate pointing at itself; a contradiction with other than two different sides, or `between` off a contradiction; `about` off a stance, or a subject that is none of the four forms, or an identity that is not in the cast; `false_but_held` off a belief; a `risk` outside the three values; tags that are not slugs; a missing or unknown `source`, or `memory <id>` naming a memory the character does not have; duplicate candidate ids. Noted, not refused: a gist outside 100–300 characters or missing one of the author's languages; a rule that is not `core`; a stance with no subject; a risk with no reason; a field outside the contract (ignored); more than 40 candidates. Tolerated shapes, normalised before validation: a bare list (taken as `nodes`), a missing id (`c<n>`), `risk` as a plain string, `because` / `supports` / `between` / `tags` as one comma-separated string, a float strength.

**Duplicates**: a candidate whose gist says what an existing node (or an earlier candidate) says — the same text once normalised, or most of the same words — is flagged in the review (`≈ psyche/val1`), never dropped: the author decides.

## 3. Rules for the model (the prompt)

System message: *You decompose a fictional character's personality into psyche nodes (COF 1.2, RFC 0004). Answer in strict JSON only.* User message: the text below, then the bundle as JSON. The exact text lives in `cli/cof_cli/propose.py` (`PROMPT`) and in the builder; `--bundle-out` writes both with the bundle.

> Read the character bundle below and propose candidate psyche nodes. Answer ONLY with strict JSON of this shape: *(the shape of § 2)*
> 1. One sentence per node, 100 to 300 characters per language, in every language of `languages` (the same meaning in each).
> 2. Kinds: value (what matters), belief (held true about the world or oneself), want (consciously pursued), need (what would heal, unseen), fear, wound (the founding injury, almost always because a memory), stance (a position toward a person, the user or a thing: set `about`), taste (likes and dislikes), habit (an observable recurring behaviour), contradiction (an owned tension between two nodes: `between` names them), rule (a boundary kept whatever the pressure; stability core).
> 3. `source` names where the node comes from: the card field, the free text, the memory (`memory ev3`), the list entry (`list goals[2]`), or `inferred` when you read it between the lines. Never invent a memory: `because` and `about` name only ids of the bundle. Prefer `because` to a memory over `because` to a node.
> 4. `strength`: how much it weighs in decisions (70 or more is said in full; the default is 50). `stability`: core never changes at use time, settled changes only through a declared lived node, shifting with evidence, fragile within one conversation.
> 5. A belief the character holds that is false (the lie it tells itself) is `false_but_held: true`. Propose a contradiction whenever a want and a fear, or a value and a habit, pull against each other.
> 6. Declare `risk` with a reason: `inappropriate` (unsuitable for some audiences, not harmful in itself: instability, deviant sexuality, self-destructive traits), `dangerous` (would make the character harmful if it acted on it: aggression, manipulation, contempt for others' safety). `none` otherwise.
> 7. Do not repeat an existing node of `psyche`; you may link to it. At most 40 nodes; fewer, well-sourced nodes beat many.
> 8. Nothing you propose is written: the author reviews every node.

The gateway is the one the builder uses for the coherence check (`docs/coherence-api.md`): `POST {base_url}/chat/completions`, `temperature: 0`, the first `{…}` block of the answer is the proposal. A model that cannot answer in JSON, or answers with a memory that does not exist, produces a refused proposal, not a half-written file.

## 4. The rule-based entries (no model)

These sources go through the same format, the same validation and the same review:

- **The 1.0 lists** (`cof psyche propose --rules`; the builder's « Propose nodes from the lists »): the conversion of RFC 0004 § 3 quater — a goal becomes a `want` (strength 70), a fear a `fear` (70), a value a one-word gist made into a sentence (« Sobriété. »), a behaviour a `habit`; duplicates merged by text and by id, a card written once per language giving one candidate with a gist per language; `source: "list goals[n]"`. `cof migrate --psyche` writes the same nodes without review (for a file with lists and no psyche); the proposal is the reviewed path.
- **A zodiac sign** (`--zodiac virgo`, also the French names; `cli/cof_cli/zodiac.py`): many authors describe a personality by a sun sign (Yann, 31 October 2026). A small static table gives three or four `value` / `taste` / `habit` candidates typical of the sign, gists in English and French, strength 50, stability `shifting`, tag `zodiac:<sign>`, `source: "zodiac"` — **to review by the author**, like every candidate. A sign is an author's shorthand: it is neither a node kind nor a field of the format, and the nodes it suggests are ordinary nodes once accepted (the tag keeps the trace).
  The builder offers the same table offline: « ♈ From an astrological sign » in the « Propose a psyche » dialog opens the review panel exactly like a pasted proposal (every row unticked; the table is embedded by `tools/psyche/zodiac_to_builder.py` and a test keeps it equal to `zodiac.py`). Gists only exist in English and French: in another language of the character, the English gist is proposed, to translate at review.
- **A Myers-Briggs type (four letters)** (`--mbti INFJ`, any case; `cli/cof_cli/profiles.py`): the sixteen types, three or four common descriptive readings each — values, tastes, habits, a need or a fear where natural, never caricatures; tag `mbti:<type>` (`mbti:infj`), `source: "mbti"`, strength 50, stability `shifting`, gists in English and French. « MBTI » is a registered trademark: this documentation and the tools' texts say « Myers-Briggs type (four letters) »; the four-letter types are used descriptively, with no affiliation (`mbti` is only an identifier in the code).
- **An Enneagram type** (`--enneagram 4`; a wing such as `4w5` is accepted, only the main type is used and the wing is noted in the proposal's `notes`; a wing that is not next to the type is refused): per type, the classic core — one `fear` (the basic fear), one `want` (the basic desire), a `value` and a `habit`; tag `enneagram:<n>`, `source: "enneagram"`, strength 50, `shifting`, English and French.
- **Big Five scores** (`--big-five O=80,C=35,E=20,A=70,N=60`: the letters or the trait names, 0–100 each, any subset): for each trait a score of **70 or more** proposes the high-pole candidates, **30 or less** the low-pole ones, in between nothing; one or two candidates per pole (`value` / `taste` / `habit` / `fear` / `need`); tag `bigfive:<trait>-<high|low>` (`bigfive:openness-high`), `source: "big-five"`, strength 50, `shifting`, English and French. Without a value, `--big-five` reads the personality's `psyche.json` › `traits` › `big5` annex instead (the preset's variant first, else any of the character's): that annex stores each trait from 0 to 1, mapped to 0–100 (0.78 → 78); a file without that annex is refused with a clear message. Scores given on the command line are used alone: they are never mixed with the annex.

All four shorthands (the sign, the type, the Enneagram type, the scores) are combinable with each other and with `--rules` (the proposals are merged, ids kept unique: `z`, `m`, `e`, `b`), and none is a node kind or a field of the format: the nodes they suggest are ordinary nodes once accepted, the tag keeps the trace. The builder offers the same three tables offline, next to the sign, in the same dialog (see the builder guide): a select of the sixteen types, a select of the nine types, five 0–100 fields prefilled from the file's `traits` annex when it has one — each with its « Propose » button, opening the same review panel (every row unticked). The tables are embedded by `tools/psyche/profiles_to_builder.py` (`--check` verifies) and a test keeps them equal to `profiles.py`; in the four builder languages other than English and French the English gist is proposed, to translate at review.

## 5. What is written on accept

For each accepted candidate: `elements/psyche/<id>/psyche-node.json` with the gist, strength, stability (default `settled`; `core` for a rule), `since`, `until`, `false_but_held`, `aware` (unless `yes`), `valence`, `about`, the links (`because`, `supports`, the two `conflicts` of a contradiction) with candidate ids mapped to the ids just written, the risk value, the tags, and `origin: authored`, `visibility: canon`, `disclosure: open`; the manifest variant (`kind`, `label` from the gist, `node`, `identity` in a cast, the mirrored `strength`), ids by kind (`val3`, `bel4`…); the candidate listed in `slots.psyche` by every preset of the character that holds one of the personality variants the bundle read (else any personality variant, else the character's presets); `cof: "1.2"`, `has-psyche`, `tags.content` following the risk. A contradiction is written only if both its sides are accepted or already exist; a reference to a candidate that was not accepted is dropped with a note. The file is validated before anything lands (cof-cli edits a copy); the builder's checks run as for any node.

## 6. The inverse: nodes → text

`cof psyche text <src> [--preset p] [--keep-personal] [--keep-dangerous] [--out who.md | --into-card]` prints the « Who she is » section that `cof export --format agent` puts in `SOUL.md` (RFC 0004 § 3 quinquies): one line per node in the fixed order wound → values → beliefs (lies marked) → wants and needs → fears → stances → tastes → habits → contradictions → rules, the whole gist at strength ≥ 70 and a short clause below, `guarded`, `lived` and the subject of a stance as markers, secret nodes left out with one line saying so, in the preset's language. `--into-card` **appends** it to the `personality` field of the preset's card (never replaces: the sheet keeps the voice, the psyche gives the substance). The builder's « Text from the psyche » button renders the same text (the same rules, in JavaScript) into a dialog with a copy button and « append to the card's personality field ». No model is involved: the rendering is deterministic, and the round trip psyche → text → psyche is not meant to be lossless — prose is for the reader, nodes for the tools.

## 7. Command line and builder

```bash
cof psyche propose clara.cof --preset fr-agent --provider openai-compatible --base-url http://localhost:11434/v1 --model qwen2.5 --out proposal.json   # COF_AI_KEY in the environment; the table, nothing written
cof psyche propose clara.cof --preset fr-agent --from-file proposal.json --apply --accept c2,c3,c4   # the chosen candidates, validated, written (--accept all for every one)
cof psyche propose clara.cof --rules --zodiac virgo --out proposal.json                            # no model: the 1.0 lists and the sign's traits
cof psyche propose clara.cof --mbti INFJ --enneagram 4w5 --big-five O=80,C=35,E=20,A=70,N=60       # no model: a Myers-Briggs type, an Enneagram type, Big Five scores (--big-five alone reads the psyche.json traits annex)
cof psyche propose clara.cof --bundle-out bundle.json                                              # take the bundle and the prompt to any chat, save the answer, come back with --from-file
cof psyche text clara.cof --preset fr-agent --into-card                                            # the inverse
```

Builder (Psyché step, advanced mode): « 🤖 Propose a psyche from the personality » builds the bundle from the current state, calls the gateway configured in the Checks step (base URL, key, model — the same settings as the coherence check; with none configured it says so and offers to paste a proposal JSON produced elsewhere, `cof psyche propose --out`), validates the answer and opens the review panel: one row per candidate (kind, gist, strength, stability, source, risk and its reason, links, a duplicate warning), a checkbox per row — **all unticked** —, « Add the selected nodes » creates the cards. A contradiction needs its two sides ticked or existing. The key stays in the browser; the bundle leaves it only toward the gateway the author entered.
