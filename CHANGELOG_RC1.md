# XMage Community Patch 1.4.60-V3 RC1 — Changelog

This document summarizes the changes included in the public RC1. It describes the community build; it does not claim these changes are part of upstream XMage.

## Graphics and long-session stability
- Reduces the observed battlefield duplication/shift/recomposition issue after long sessions.
- Coordinates client-side Java graphics parameters used by the validated build.
- Preserves XMage size preferences while improving visual recovery behavior.

## 1440p / 4K usability
- Improves readability of menus and dialogs on high-density displays.
- Allows Java scaling to be combined with XMage's own configurable sizes.
- Includes validation around hand, battlefield, dialogs and Deck Editor clipping.

## Printing / artwork selection
- Adds a printing/art selector from the Deck Editor.
- Adds preview before applying a printing.
- Stores the selected printing in the deck and preserves it during play.
- Supports search by set code or set name.
- Uses lazy loading and local caching to avoid loading every artwork at once.

## Cards, images and special objects
- Fixes tested Superior Spider-Man image variants.
- Improves image handling for double-faced/split-like cards, Adventures and Rooms.
- Improves stack artwork behavior for tested multipart-card cases.
- Improves token/emblem image recovery when stale cache data exists.
- Includes verified missing-card and selected legality fixes, including the tested Supreme Verdict Modern legality case.

## Deck downloader
- Adds an integrated "Download decks" workflow.
- Supports Standard, Pioneer and Modern.
- Supports compatible sources including MTGGoldfish and MTGTop8, with Scryfall lookups where needed.
- Converts recent lists into XMage-compatible `.dck` decks.
- Keeps older decks and skips content-identical duplicates.
- Uses caching, bulk lookups and delays to reduce repeated external requests.
- Supports safe cancellation, background operation and resume behavior.
- Produces UTF-8 general/per-format logs with explicit success/rejection reasons.

## Distribution and recovery
- Client and server are distributed as a matching pair and must not be mixed with other builds.
- Public packages are validated for structure/readability before release.
- Installation guidance is deliberately reversible and backup-first.
- RC1 does not intentionally bundle personal decks, caches, logs, databases, credentials or card images.

## Memory
- `-Xmx4G` is strongly recommended for the client on systems with sufficient physical RAM.
- 8 GB or more physical RAM is recommended when using a 4 GB Java heap limit.

## Validated baseline
- Windows 10/11 x64 target.
- Java 8u201 x64 validated runtime for this RC1.
- Client and server build observed during validation: `2026-08-10 02:05`.
- A validated downloader run produced 25 valid decks per format (75 total).

## Known scope limits
- This is RC1, not a stable release.
- Compatibility testing on more Windows/Java configurations is still needed.
- Website-backed deck sources can change independently and may temporarily break connectors.
- Some fixes are currently present only in this community build and have not been accepted upstream.
