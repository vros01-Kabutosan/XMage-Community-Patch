# XMage Community Patch V6 status

## Base rule

The production base is the user's **last known good local XMage build**: the post-Hobbit build in which the stack is already inverted and the game is stable during real play.

This exact build is the source of truth. Do not replace it with 1.4.60V3, a newer upstream branch, or an experimental V6 package merely because the version number looks newer. The version identifier and commit/hash of the local last-good build must be recorded before any new change is applied.

## Integration rule

All other improvements are currently considered pending unless they are verified in that last-good build. They must be added one at a time as isolated, versioned patches, with a backup and rollback path. A change is not considered integrated until it has been tested in the game.

## Current state

- Last known good base: post-Hobbit local build with inverted stack.
- Confirmed working baseline: the user's current playable installation.
- The random AI deck selector is not confirmed in the baseline and must be implemented without changing the stack.
- The selector must use downloaded legal decks from the selected Standard, Pioneer, or Modern pool.
- Maximum attempts: three. On failure, use the known working fixed deck immediately so the game always starts.

## Preservation requirements

Do not alter the inverted stack, card and image fixes, edition/art selector, deck downloader, 4K stability, client/server compatibility, or any other baseline behavior while implementing the AI selector.