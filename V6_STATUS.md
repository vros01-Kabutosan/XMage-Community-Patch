# XMage Community Patch V6 status

## Current state

- Upstream XMage source has been recovered locally.
- The published V6 client package is a compiled reference build.
- The random AI deck selector is not present in the published V6 package and must be implemented in source.
- Existing community improvements must be ported as explicit, versioned patches.

## Non-negotiable behavior

The AI must select a legal downloaded deck from the selected Standard, Pioneer, or Modern pool. It may try at most three candidates. If loading fails, it must immediately use the known working fallback deck and allow the game to start.

## Preservation requirements

Do not remove the stack UI improvements, edition/art selector, card and image fixes, deck downloader, 4K stability work, or client/server compatibility while reconstructing the source build.