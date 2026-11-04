# Builder guide — advanced version

*The same guide opens from the **📖 Guide** button of the builder in advanced version. Source: `builder/guide_src.py` (it also feeds the builder window, in six languages).*

Français : [builder-guide.fr.md](builder-guide.fr.md)

## 1. The advanced version in short

Eight steps, in the order of the left column:

- **1 · Character(s)** — who it is: name, fictional or real, morphology.
- **2 · Elements** — everything that describes it: texts, photos, voice, LoRA, 3D, poses, motion, files.
- **3 · Memories** — its past: moments and periods, with what it felt, what it keeps to itself, and a few traces (a photo, a sound).
- **4 · Psyche** — its inner life as a graph: values, beliefs, wants, needs, fears, wounds, stances, tastes, habits, contradictions, rules — tied to the memories.
- **5 · Presets** — ready-to-use combinations: a look, an age, a style, a language.
- **6 · Rights** — what others may do with it.
- **7 · Checks** — what is missing or does not fit.
- **8 · Build** — the final .cof file.

Only the name, fictional or real, the morphology and the rights are required. The easy version handles only a simple character (one card, photos, one voice): a richer file stays in the advanced version.

## 2. Categories and variants

Elements are sorted into 8 categories: Personality, Appearance, Identity weights (LoRA), 3D, Voice, Postures, Motion, Files. In each category you add **variants**, each of one type: face, body, hairstyle, garment, place…

**Golden rule: one variant = a consistent set of one thing.** Several photos only show different angles. Another face, another hairstyle, another garment, another place = another variant.

- **Loose photos**: the only exception, by design. Face, body and outfit mixed, but always the same person, at the same age, in the same style.
- **Character sheet**: one image showing the whole character (face, body, hairstyle, outfit).

## 3. Age

- Age belongs to each **representation** (face, body, sheet, loose photos, LoRA, 3D), not to the character: Clara can have a face at 12 and another at 29.
- Clothes, accessories, places and descriptions have no age.
- For the safety rules, a preset takes the lowest age of its variants; when it declares an age, that age bounds its life (memories, psyche: see Presets).
- One image can never serve both an age under 18 and an adult age.

## 4. Memories

The character's past, node by node. A **moment** (green ●, code `ev`) is a point in time, a **period** (purple ■, code `ep`) a span; a moment can belong to a period (“part-of” link).

- **The gist**: a few first-person sentences in the character's primary language; other languages are optional (an English agent reads the English gist).
- **When, where, with whom**: an age or a date, a place in words or one of the character's places, the people present — and who is **shown** in the media.
- **Objects**: what the memory holds on to — one of the character's accessories (picked from the list) or a free name (“the notebook”); tick “shown” when the object appears in a media. Written as `what` (COF 1.2, RFC 0005); a memory with objects makes the file 1.2.
- **Felt then / now, fidelity, salience**: what makes a memory alive rather than a record.
- **Origin, visibility, disclosure**: authored or lived during use; canon or personal (a user's data, never shared unless asked); open, guarded or secret (what the character does not say).
- **Media**: one to three traces — image, sound, a short video, a few lines — or the same media as another memory (two characters, one evening, one photo).
- **Explicit** (nudity, intimate): only if the memory is lived at 18 or more, someone is declared shown, and every person shown is a known adult. Otherwise the options are greyed out, with the reason.
- **Presets** pick their memories like a library: a ticked period brings its moments. At build, two purges: all audiences (explicit media leave, texts stay) and without personal memories.

## 5. Psyche

The character's inner life, as a graph (COF 1.2). Eleven kinds of nodes: wound, value, belief, want, need, fear, stance, taste, habit, contradiction, rule. Each node is one or two sentences per language.

- **Strength** (0–100, set node by node), **stability** (core, settled, shifting, fragile: what a host may change at use time), **since** (the age it appeared), origin, visibility, disclosure.
- **Illustration** (RFC 0004 § 3 decies): a row on every card to add images to the node — the first replaces the kind icon in its bubble, the others show in the card (more than three draws a warning); ✕ removes one. For each image say who is shown and at what age, and whether it shows nudity: an image of the character gives the node an age, which counts for the preset's lowest age, and the memory rules for nudity and real people apply. Images only: no sound, no video.
- **Links**: “because” and “about” to a memory or a node; “supports” and “conflicts” between nodes. A contradiction carries exactly two “conflicts”; a wound almost always comes from a memory.
- **People, places, objects**: what the node is tied to without going through a memory (RFC 0005) — self or a character of the file, an environment, an accessory, or a free name (“my grandmother”, “Lyon”, “the notebook”), with “real person” for someone real who is not a character. Folded on one line while empty. A link to a character written by an older draft becomes a person when the file is opened (the checks say how many).
- **Self-awareness, valence, until** (RFC 0004 § 3 nonies): “Self-awareness” (yes, partly, no; default yes, not written) says what the character knows about itself — not what it tells others, which is disclosure: an unconscious node is acted on, never stated. A stance or a taste has a **valence** slider from −100 (hostile / hates) to +100 (warm / loves), centred on 0, “unset” and absent from the file until it is moved (✕ clears it; changing the kind away from stance or taste drops it, and the card says so). “Until (age)” / “Until (date)”, next to “Since”, is when the character stopped holding the node. Checks: errors for a valence off a stance or taste and for an until before the since (ages with ages, dates with dates); warnings for “self-awareness: no” on a secret node and for a preset older than the until of a node it holds.
- **Declared risk**: none, inappropriate, dangerous. A host that gives the character tools never loads a dangerous node; fiction may load everything. At build, the “no risk” purge drops them.
- A belief can be **false but held** (the lie the character tells itself); a stance has a **subject** (a character, the user, a memory, a label).
- **Propose a psyche** (🤖 “Propose a psyche from the personality”) — a proposal, never automatic. The dialog builds a bundle from what the builder holds (the card's description, personality, scenario, first message and dialogue examples, or the free text; the 1.0 lists; the gists of the memories; the nodes that already exist) and takes the proposal from one of three places: **the AI gateway** of the Checks step (address, key, model; the key is not saved), **a pasted proposal** (JSON produced elsewhere — `cof psyche propose --out`, or any chat — offered when no gateway is set), or **“Copy the bundle and the prompt”**, which puts the bundle and the instructions on the clipboard for any chat; paste its answer back. A broken proposal is refused, with its reasons. The answer opens a **review panel**: one row per candidate (kind, sentence, strength, source, risk and why it is declared), every box unticked (“Tick all” / “Untick all”); only the ticked nodes are added, and a contradiction ticked without its other side sends you back to the review.
- **From the 1.0 lists**: when a file opens with card lists (goals, fears, values, behaviours) and no psyche node, a banner offers “Propose nodes from the lists” — a goal becomes a want, a fear a fear, a value a value, a behaviour a habit, each to review; the lists stay in the card.
- **Offline entries** (no AI, same review panel, all unticked): **from a sun sign** (“♈ From an astrological sign”: a select of the twelve signs, names in the six languages) — three or four `value` / `taste` / `habit` candidates from the same table as `cof psyche propose --zodiac`, all unticked in the review panel (the sentences exist in English and French only: another language gets the English text, to translate at review); nothing is written without ticking. The same dialog offers three more offline entries, each with its “Propose” button: **“From a Myers-Briggs type (four letters)”** (a select of the sixteen types; the four letters are used descriptively, no affiliation), **“From an Enneagram type”** (a select of the nine types: the basic fear and desire, a value, a habit) and **“From Big Five scores (OCEAN)”** (five 0–100 fields, prefilled from the personality's typed traits when it has any; 70 or more proposes the high pole, 30 or less the low pole, in between nothing) — the tables of `cof psyche propose --mbti / --enneagram / --big-five`, trait names in the six languages, English text in the four languages other than English and French.
- **Text from the psyche** (📝): writes the psyche of the chosen preset as the short “Who she is” text — word for word the one `cof export --format agent` puts in `SOUL.md` — with the options to keep personal and dangerous nodes; copy it, or “Append to the card's ‘Personality’ field” (it appends, never replaces; unavailable when the preset's personality is not a card).
- **Presets** pick their nodes like a library; a node that changes with age is a second node, derived from the first. “Graph view” shows the constellation in the explorer.

## 6. Presets

A preset = one character + a combination of variants. For example: "Clara 29, photo", "Clara manga", "Clara 65".

- **Only one** face, body, hairstyle per preset.
- **Stackable**: clothes and accessories (if they don't cover the same body part), facial and body hair, features, places, several LoRAs.
- **Offered** = available in this preset, never applied by default (a spare outfit, for example).
- The **default preset** opens first; its front face becomes the file's thumbnail.
- **The age stops the memories and the psyche**: when the preset has an age (its declared age when it has one, else the lowest age its variants show — a 40-year-old shown at 25 keeps her life up to 40, with a coherence warning), its Memories offer only what had begun by then (a moment's age, a period's start; a date alone, through the birth year the dated memories give) and its Psyche only the nodes held at that age (appeared, not yet let go). A line counts the rest; “show anyway” shows it greyed out, not tickable. A ticked period brings only its moments lived by that age. An inherited item the age excludes is struck through, with “remove for this preset”. Changing the age afterwards (never on file load) opens a window listing what no longer fits (“This preset is 12 years old, but it keeps 4 memories and 10 nodes that do not fit that age:”): **Deselect these items**, or **Keep — I'll fix the age** (the checks keep reporting them).
- **Declared age and apparent age**: the declared age is the character's life; if the variants show someone younger, the checks warn (“declares age 40 but its variants show 25”) and nothing more can be done — it is never an error. Every safety rule (minors, nudity, intimacy) keeps reading the lowest age shown.

## 7. Several characters

A file can group several characters: a duo, a team. Each variant and each preset belongs to one character, chosen in the "Character" menu at the top of the screen.

- A face, a voice or a LoRA is never shared between two characters.
- A neutral place, pose or file can serve several.
- To reuse a preset from another file: Presets step, "Import a preset (.cof)".

## 8. Rights and sensitive content

- Rights are **closed by default**: you open what you allow (commercial use, redistribution, voice cloning, training…), per preset if needed.
- **Real person**: consent is recommended, and required for nudity or intimate content.
- **Under 18**: never nudity or intimate content in the preset.
- Intimate content goes only in its "intimate" variant, kept apart and ignored by readers by default.

## 9. Checks and build

- **Checks**: completeness (what each preset lacks) and coherence (what does not fit). Warnings never block; only errors prevent the build.
- **AI check** (optional): you choose the AI (address, key, model). It checks that the preset describes one consistent character and that each variant shows one thing. The images are sent to that AI; the key is not saved.
- **Build**: choose the image size and compression, then download the .cof. Open it in the COF explorer to check the result.
