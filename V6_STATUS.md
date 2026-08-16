# XMage Community Patch V6 status

## Base rule

The Community Patch must be built from the stable XMage base **after the Hobbit integration**. The current reference build uses the corresponding XMage **1.4.61** modules (including Hobbit content). Do not roll the project back to 1.4.60V3 and do not mix unrelated experimental upstream changes into this line.

The post-Hobbit stable base is the production foundation. Experimental work must remain isolated until it has been ported and tested against this exact base.

## Current state

- The post-Hobbit stable base is the accepted production foundation.
- The published V6 client package is a compiled reference build of that base.
- The random AI deck selector is not present in the published V6 package and must be implemented as a source patch against the post-Hobbit base.
- Existing community improvements must be ported as explicit, versioned patches.

## Non-negotiable behavior

The AI must select a legal downloaded deck from the selected Standard, Pioneer, or Modern pool. It may try at most three candidates. If loading fails, it must immediately use the known working fallback deck and allow the game to start.

## Preservation requirements

Do not remove the stack UI improvements, edition/art selector, card and image fixes, deck downloader, 4K stability work, or client/server compatibility while reconstructing the source build.