# XMage Community Patch V6 status

## Base rule

The Community Patch must always be built from the stable XMage **1.4.60V3** base. Do not merge the latest upstream branch, 1.4.61, or experimental V6 changes into the stable line. Experimental work must remain isolated until it has been ported and tested against 1.4.60V3.

## Current state

- The stable 1.4.60V3 base is the only accepted production foundation.
- The published V6 client package is a compiled reference build, not the new base.
- The random AI deck selector is not present in the published V6 package and must be implemented as a source patch against 1.4.60V3.
- Existing community improvements must be ported as explicit, versioned patches.

## Non-negotiable behavior

The AI must select a legal downloaded deck from the selected Standard, Pioneer, or Modern pool. It may try at most three candidates. If loading fails, it must immediately use the known working fallback deck and allow the game to start.

## Preservation requirements

Do not remove the stack UI improvements, edition/art selector, card and image fixes, deck downloader, 4K stability work, or client/server compatibility while reconstructing the source build.