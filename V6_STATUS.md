# XMage Community Patch V6 status

## Base rule

The production base is the user's **last known good local XMage build**: the post-Hobbit build in which the stack is already inverted, floating, and the phases are shown below it. It is stable during real play.

This exact build is the source of truth. Do not replace it with 1.4.60V3, a newer upstream branch, or an experimental V6 package merely because the version number looks newer. Record the version identifier and commit/hash of the last-good build before applying any new change.

## Integration rule

The stack is already complete and is part of the stable baseline. Future work starts with the AI. Every new improvement must be isolated, versioned, backed up, and tested in the game before being accepted.

## Roadmap

### Phase 1 — Current priority: random AI deck

Implement only the AI deck selector:

- use downloaded legal decks from the selected Standard, Pioneer, or Modern pool;
- choose a different random deck between games;
- maximum three load attempts;
- on failure, immediately use the known working fixed deck;
- never block the game from starting;
- do not modify the completed stack or any visual component.

### Phase 2 — Stability

Run long real-game tests until the selector is genuinely stable. A build is not accepted merely because it compiles or starts once.

### Phase 3 — Visual improvements

Only after Phase 1 is stable: implement the remaining visual polish and interface improvements.

### Phase 4 — Advanced AI

Only much later: AI memory, threat tracking, and hand-reading behavior. This is a separate high-complexity project and must not be mixed with random deck loading.

## Preservation requirements

Do not alter the completed inverted/floating stack, phases below it, card and image fixes, edition/art selector, deck downloader, 4K stability, client/server compatibility, or any other baseline behavior while implementing Phase 1.