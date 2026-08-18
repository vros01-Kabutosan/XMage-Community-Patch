# Repository layout and protection map

This repository stores the XMage Community Patch project metadata, contracts, documentation, installer helpers, tests, and future source/patch payloads.

## Canonical branches

- `main`: clean project index and authoritative documentation.
- `protected/rc1`: reserved for the verified RC1 payload. It must not be created from an empty placeholder.
- `protected/rc1.1`: reserved for the verified RC1.1 payload after local `Computer - mad` gameplay validation.
- `work/*`: temporary development branches only.
- `isolation/*`: quarantined experiments and failed attempts. They must never be merged into stable branches.
- `archive/*`: historical branches retained for traceability and not used as a development base.

## Current status

The Windows RC1.1 candidate is outside this Git repository at the exact prepared installation path supplied by the maintainer. The repository must not pretend to contain the compiled client/server payload until that payload, its manifest, and its verification record are actually committed.

The current verified configuration includes:

`Computer - mad` using `mage-player-ai-mad-1.4.61.jar`.

RC1.1 remains a candidate until a real local game is completed against:

- host: `localhost`
- port: `17171`
- player type: `Computer - mad`

## Non-negotiable rules

1. Never use `J:\\mtg` as the source of truth for this project.
2. Never merge an experiment directly into a protected branch.
3. Never overwrite RC1 or RC1.1; create a new numbered candidate instead.
4. Every candidate requires a manifest, SHA-256 inventory, test record, and rollback point.
5. A failed experiment is quarantined; it is not repaired in place.
6. No branch may be labelled RC1.1 until the normal AI option is visible and playable.
7. Configuration, user decks, images, logs, and compiled binaries are separate concerns.

## Naming

- Small corrective changes: `1.1`, `1.2`, `1.3`.
- Large checkpoints: `v-1`, `v-2`.
- Do not create duplicate Windows-style names such as `(1)` or `(2)`.

## Historical branches

Existing `work/*`, `isolation/*`, `checkpoint/*`, `chore/*`, `port/*`, and `stable/*` branches are retained until their contents have been individually classified. They are not stable release branches merely because their names contain `stable`, `complete`, or `rc2`.
