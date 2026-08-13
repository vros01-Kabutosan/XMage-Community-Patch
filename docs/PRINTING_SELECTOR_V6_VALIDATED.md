# Printing Selector V6 — validated on XMage 1.4.61V1

Status: VALIDATED  
Date: 2026-08-13

The printing/edition selector has been recovered on the XMage 1.4.61V1 client base.

Validated behavior:

- `Elegir edición...` is available in Deck Editor.
- The printing list opens correctly.
- Search works by set code or set name.
- A card preview is shown for the selected printing.
- Selecting another printing updates all matching copies of the same card name.
- Cards already using the chosen printing are skipped.
- Normal XMage client/server launch remains functional.

The validated implementation is V6. Earlier V1–V5 attempts are historical development iterations and are not the final selector implementation.

Canonical files:

- `tools/migration/printing_selector_port_source_v6_exact_old.py`
- `tools/migration/RUN_PRINTING_SELECTOR_PORT_SOURCE_V6_EXACT_OLD_WINDOWS.cmd`

Validated candidate SHA-256:

`032fde6804fda8ea20624000f1961f6b3c2435a9faa7834fd6189df92c708ae4`

The source-port build completed successfully and did not modify the active XMage installation during compilation. Backups and rollback material must be preserved until the next release candidate completes broader testing.
