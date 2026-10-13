# Security policy

## Reporting a vulnerability
Please **do not open a public issue** for a vulnerability. Use GitHub's private reporting (*Security → Report a vulnerability*) on this repository. We acknowledge within 72 hours and aim to ship a fix within 14 days for anything that lets a crafted `.cof` harm a reader.

## Scope
- **The container**: path traversal, zip bombs, symlinks, oversized entries — readers MUST open `.cof` files defensively (`docs/IMPLEMENTING.md` § 9). The reference validator rejects `..` and absolute paths, checks entry order, hashes and sizes.
- **Executable content**: scripts are only allowed when `container.executableContent` declares them, and hosts must never run them without explicit user approval. Pickles (`.pt`, `.ckpt`, `.pkl`, pickled `.bin`) are always refused; weights are safetensors.
- **Rights and safety rules**: the per-preset age rules, consent for real persons and per-character rights are enforced by the validator; a way to bypass them is a vulnerability — report it privately.

## Content that must be removed
Real person without consent, third-party character without licence, content that breaks the age rules: open a *Rights / takedown* issue (public, without attaching the material) or report privately as above. Reports are handled within 72 hours.

## Supported versions
The latest `1.x` release of the format, of `cof-cli` and of the builder.
