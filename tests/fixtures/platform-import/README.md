# Platform import fixtures (RFC 0006)

All synthetic: the character "Wren Calloway" is invented, the user is "You" or "Sam". No real person, no licensed character.

| File | Format | Fidelity |
|---|---|---|
| `caitools-card.png` | CAI Tools card (PNG, flat `chara` chunk, no `spec`) | CAI Tools 2.1.0 source |
| `caitools-card.json` | CAI Tools "Download Character as .json" (hybrid keys) | CAI Tools 2.1.0 source |
| `caitools-chat.jsonl` | CAI Tools "Tavern" chat — every `send_date` is the export instant, the user is "You" | CAI Tools 2.1.0 source |
| `Wren_Calloway_TavernHistory.zip` | CAI Tools history: `chat_1.jsonl` (newest), `chat_2.jsonl` | CAI Tools 2.1.0 source |
| `caitools-legacy-histories.json` | `histories.histories[].msgs[].src.is_human` | SillyTavern's importer; extra keys a guess |
| `sillytavern-chat.jsonl` | SillyTavern chat: ISO dates, swipes, a narrator line | SillyTavern source |
| `wren.personatext.json` | PersonaText: V2 card, `data.extensions.chat_history`, `avatar_data_url` (a 1×1 WebP) | PersonaText bookmarklet as read on 4 Nov 2026 |

The official Character.AI export has no public sample: the tests build a small unknown-shape zip in place.
