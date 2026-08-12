# Technical Notes — XMage Community Patch 1.4.60-V3 RC1

This document is intended for technically minded testers and upstream XMage maintainers reviewing the RC1.

## Scope

The RC1 combines local client/server changes plus community tooling around an XMage 1.4.60-V3 base. It is **not** presented as an upstream release.

The current public release contains Windows binary packages and documentation. The goal is to make testing reproducible and to identify individual changes that may be suitable for upstream contribution.

## Validated runtime/build

- Target: Windows 10/11 x64
- Validated Java runtime: Java 8u201 x64
- Observed matching client/server build: `2026-08-10 02:05`
- Recommended client heap: `-Xmx4G` on systems with sufficient RAM

## Main change areas

### Client-side UI / graphics
- Long-session repaint/recomposition mitigation.
- High-DPI usability work for 1440p/4K.
- Printing/art selection integrated into deck-editing workflow.
- Image/cache handling for tested multipart-card, token and emblem cases.

### Card/data compatibility
- Selected missing-card/data corrections validated in this build.
- Selected legality corrections validated in this build.
- Tested multipart-card image/display fixes.

### Deck tooling
- Integrated deck-download workflow for Standard, Pioneer and Modern.
- Duplicate detection by deck content.
- Resumable state/cache.
- UTF-8 audit logs.
- Safe cancellation.
- External lookups/connectors may use MTGGoldfish, MTGTop8 and Scryfall depending on the operation.

## External dependencies

Some optional deck tooling can install standard Python packages when absent, including `selenium`, `undetected-chromedriver`, and supporting libraries. In those cases the scripts may invoke `pip` automatically.

This behavior is documented because it changes the local Python environment and because maintainers/testers should be able to audit it before execution.

## Distribution model

The public RC1 ships three matching Windows assets:
- Complete
- Client
- Server

Client and Server must not be mixed with other builds.

The release includes SHA-256 checksums and an audit document. It intentionally does not claim to be an official XMage build.

## Current reproducibility limitation

The repository currently documents the behavior, release assets, checksums and testing procedure, but it does **not yet provide a clean upstream-style patch series/source diff for every binary change in RC1**.

That limitation is important for maintainer review. Before requesting code integration upstream, each reusable fix should be isolated against the appropriate upstream revision, documented, and submitted as a conventional pull request or patch with tests where practical.

## Upstream strategy

The preferred path is:
1. Community-test RC1 as a binary candidate.
2. Collect reproducible failures and confirmations.
3. Isolate individual reusable changes.
4. Rebase each candidate change onto current upstream XMage.
5. Add/adjust automated tests where feasible.
6. Submit focused upstream pull requests rather than asking upstream to adopt the binary bundle wholesale.

This avoids conflating packaging, local tooling, card-data fixes and UI changes into one difficult-to-review patch.

## Security/privacy notes

- No project-owned telemetry is intended.
- Personal decks/logs/preferences are not intentionally uploaded to a project-owned service.
- Testers should sanitize logs before sharing them.
- Optional web-backed tools necessarily connect to their configured external services.

## Licensing/attribution

Upstream XMage uses the MIT License. Original XMage copyright/license notices must remain applicable to redistributed upstream software. Magic: The Gathering names/artwork/trademarks remain with Wizards of the Coast and/or their respective rights holders.
