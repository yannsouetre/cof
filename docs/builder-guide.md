# Builder guide — advanced version

*The same guide opens from the **📖 Guide** button of the builder in advanced version. Source: `builder/guide_src.py` (it also feeds the builder window, in six languages).*

Français : [builder-guide.fr.md](builder-guide.fr.md)

## 1. The advanced version in short

Seven steps, in the order of the left column:

- **1 · Character(s)** — who it is: name, fictional or real, morphology.
- **2 · Elements** — everything that describes it: texts, photos, voice, LoRA, 3D, poses, motion, files.
- **3 · Memories** — its past: moments and periods, with what it felt, what it keeps to itself, and a few traces (a photo, a sound).
- **4 · Presets** — ready-to-use combinations: a look, an age, a style, a language.
- **5 · Rights** — what others may do with it.
- **6 · Checks** — what is missing or does not fit.
- **7 · Build** — the final .cof file.

Only the name, fictional or real, the morphology and the rights are required. The easy version handles only a simple character (one card, photos, one voice): a richer file stays in the advanced version.

## 2. Categories and variants

Elements are sorted into 8 categories: Personality, Appearance, Identity weights (LoRA), 3D, Voice, Postures, Motion, Files. In each category you add **variants**, each of one type: face, body, hairstyle, garment, place…

**Golden rule: one variant = a consistent set of one thing.** Several photos only show different angles. Another face, another hairstyle, another garment, another place = another variant.

- **Loose photos**: the only exception, by design. Face, body and outfit mixed, but always the same person, at the same age, in the same style.
- **Character sheet**: one image showing the whole character (face, body, hairstyle, outfit).

## 3. Age

- Age belongs to each **representation** (face, body, sheet, loose photos, LoRA, 3D), not to the character: Clara can have a face at 12 and another at 29.
- Clothes, accessories, places and descriptions have no age.
- A preset takes the lowest age of its variants.
- One image can never serve both an age under 18 and an adult age.

## 4. Memories

The character's past, node by node. A **moment** (green ●, code `ev`) is a point in time, a **period** (purple ■, code `ep`) a span; a moment can belong to a period (“part-of” link).

- **The gist**: a few first-person sentences in the character's primary language; other languages are optional (an English agent reads the English gist).
- **When, where, with whom**: an age or a date, a place in words or one of the character's places, the people present — and who is **shown** in the media.
- **Felt then / now, fidelity, salience**: what makes a memory alive rather than a record.
- **Origin, visibility, disclosure**: authored or lived during use; canon or personal (a user's data, never shared unless asked); open, guarded or secret (what the character does not say).
- **Media**: one to three traces — image, sound, a short video, a few lines — or the same media as another memory (two characters, one evening, one photo).
- **Explicit** (nudity, intimate): only if the memory is lived at 18 or more, someone is declared shown, and every person shown is a known adult. Otherwise the options are greyed out, with the reason.
- **Presets** pick their memories like a library: a ticked period brings its moments. At build, two purges: all audiences (explicit media leave, texts stay) and without personal memories.

## 5. Presets

A preset = one character + a combination of variants. For example: "Clara 29, photo", "Clara manga", "Clara 65".

- **Only one** face, body, hairstyle per preset.
- **Stackable**: clothes and accessories (if they don't cover the same body part), facial and body hair, features, places, several LoRAs.
- **Offered** = available in this preset, never applied by default (a spare outfit, for example).
- The **default preset** opens first; its front face becomes the file's thumbnail.

## 6. Several characters

A file can group several characters: a duo, a team. Each variant and each preset belongs to one character, chosen in the "Character" menu at the top of the screen.

- A face, a voice or a LoRA is never shared between two characters.
- A neutral place, pose or file can serve several.
- To reuse a preset from another file: Presets step, "Import a preset (.cof)".

## 7. Rights and sensitive content

- Rights are **closed by default**: you open what you allow (commercial use, redistribution, voice cloning, training…), per preset if needed.
- **Real person**: consent is recommended, and required for nudity or intimate content.
- **Under 18**: never nudity or intimate content in the preset.
- Intimate content goes only in its "intimate" variant, kept apart and ignored by readers by default.

## 8. Checks and build

- **Checks**: completeness (what each preset lacks) and coherence (what does not fit). Warnings never block; only errors prevent the build.
- **AI check** (optional): you choose the AI (address, key, model). It checks that the preset describes one consistent character and that each variant shows one thing. The images are sent to that AI; the key is not saved.
- **Build**: choose the image size and compression, then download the .cof. Open it in the COF explorer to check the result.
