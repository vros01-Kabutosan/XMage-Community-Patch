# RC1 Testing Guide

This guide is for community testers of **XMage Community Patch 1.4.60-V3 RC1**.

## Before testing
1. Back up the existing `mage-client` and `mage-server` folders.
2. Use Client and Server from the same RC1.
3. Verify the SHA-256 hash of the downloaded package.
4. Use the validated Java runtime where possible: 64-bit Java 8u201.
5. For the client, use one `-Xmx` option only. `-Xmx4G` is recommended on systems with sufficient RAM.

## Baseline information to record
- Windows edition/version
- Java version and architecture
- CPU / RAM
- GPU
- display resolution and Windows scaling percentage
- RC1 package used: Complete / Client / Server
- whether this was a clean install or an upgrade from an existing XMage installation

## Test matrix

### 1. Launch and client/server pairing
- Launch Client & Server once from the XMage launcher.
- Confirm both components show build `2026-08-10 02:05`.
- Connect to `localhost:17171`.
- Play a short local game.

Expected: no protocol mismatch, no duplicate server and normal game startup.

### 2. Long-session graphics stability
- Play or leave the client active for an extended session.
- Switch between game, lobby, Deck Editor and dialogs.
- Watch for battlefield duplication, shifted components, stale overlays or broken repainting.

Expected: no recurring battlefield duplication/recomposition issue.

### 3. 1440p / 4K UI
- Test menus, context menus, dialogs, hand, battlefield and Deck Editor.
- Test with the user's normal Windows scaling.

Expected: usable layout without important clipping or inaccessible controls.

### 4. Printing / artwork selector
- Open a deck in Deck Editor.
- Select a card with multiple printings.
- Search by set code/name.
- Preview and apply a printing.
- Save, close and reload the deck.
- Start a game using that deck.

Expected: selected printing persists in the saved deck and during play.

### 5. Multipart cards and images
Test representative double-faced/split-like cards, Adventures and Rooms in relevant zones: hand, battlefield, stack, graveyard/exile where applicable.

Expected: the appropriate face/part/art is shown in the tested zone.

### 6. Tokens and emblems
- Create tokens/emblems in a clean session.
- Repeat after an image-cache refresh if possible.

Expected: no permanently blank token/emblem due only to stale cache state.

### 7. Deck downloader
Run each supported format separately and then combined where applicable:
- Standard
- Pioneer
- Modern

Check:
- successful deck creation
- duplicate detection
- logs
- rejection reasons
- cancellation
- resume after restarting XMage

Expected: a temporary HTTP/site error must not crash XMage or cause endless retries.

### 8. Memory behavior
- Observe client memory during normal use, large-image browsing and long sessions.

Expected: memory may rise with caches, but report continuous unbounded growth that does not stabilize.

### 9. Rollback
- Close all Java processes.
- Restore the backed-up `mage-client` and `mage-server` folders.
- Launch the previous installation.

Expected: rollback is straightforward and does not require deleting personal data.

## How to report a failure
Open an issue in this repository and include:
- patch version
- client/server build
- Windows version
- Java version
- resolution/scaling
- minimal reproduction steps
- expected result
- actual result
- anonymized relevant log excerpt
- screenshot when useful

For a card-specific issue, also include exact card name, set, collector number and the zone where the problem occurs.

Never publish credentials, cookies, private paths or personal information in logs/screenshots.
