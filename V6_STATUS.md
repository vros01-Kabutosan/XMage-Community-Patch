# XMage Community Patch V6 status

## Base rule

The production base is the user's **last known good local XMage build**: the post-Hobbit build in which the stack is already inverted, floating, and the phases are shown below it. It is stable during real play.

This exact build is the source of truth. Do not replace it with 1.4.60V3, a newer upstream branch, or an experimental V6 package merely because the version number looks newer. The version identifier and commit/hash of the local last-good build must be recorded before any new change is applied.

## Integration rule

All other improvements are pending unless verified in that last-good build. They must be added one at a time as isolated, versioned patches, with a backup and rollback path. A change is not integrated until it has been tested in the game.

## Roadmap

### Phase 1 — Current priority: random AI deck

Implement only the AI deck selector:

- use downloaded legal decks from the selected Standard, Pioneer, or Modern pool;
- choose a different random deck between games;
- maximum three load attempts;
- on failure, immediately use the known working fixed deck;
- never block the game from starting;
- do not modify the stack or any visual component.

### Phase 2 — Stability

Run long real-game tests until the selector is genuinely stable. A build is not accepted merely because it compiles or starts once.

### Phase 3 — Visual improvements

Only after Phase 1 is stable: implement the remaining visual polish and interface improvements.

### Phase 4 — Advanced AI

Only much later: AI memory, threat tracking, and hand-reading behavior. This is a separate high-complexity project and must not be mixed with random deck loading.

## Preservation requirements

Do not alter the inverted/floating stack, phases below it, card and image fixes, edition/art selector, deck downloader, 4K stability, client/server compatibility, or any other baseline behavior while implementing Phase 1.