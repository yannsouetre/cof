# test-purges.cof

A small 1.2 file for the builder's build confirmation and purges (7 November 2026): one neutral appearance variant,
one `intimate` variant and one `nudity: true` variant (neutral placeholder images, adult of 30), three memories
(one `personal`, one `explicit: nudity` shown by the character at 29, one ordinary), four psyche nodes (one value,
one rule declared `dangerous`, one taste declared `inappropriate`, one `personal` belief). `cof validate` says OK.

Opened in the builder, « Build and download » must announce, depending on the purge (none / all audiences / no risk
/ both) and the « drop personal » box: 1 memory and 1 node personal removed or included; 2 intimate or nude variants
and 1 explicit memory removed or included; 2 inappropriate or dangerous nodes removed or included. The built files
validate, and `tags.content` loses `nudity` / `sexual` with the intimate variants and `psyche-*` with the risky nodes.
