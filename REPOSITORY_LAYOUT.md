# Repository layout and protection map

This repository stores the complete, versioned XMage Community Patch project:
source, integrated stable modifications, reproducible build inputs, portable
installer payloads, manifests, contracts, documentation, tests and logs.

## Canonical branches

- `main`: clean project index and authoritative documentation.
- `protected/rc1`: reserved for the verified RC1 payload. It must not be created from an empty placeholder.
- `protected/rc1.1`: reserved for the verified RC1.1 payload after local `Computer - mad` gameplay validation.
- `work/*`: temporary development branches only.
- `isolation/*`: quarantined experiments and failed attempts. They must never be merged into stable branches.
- `archive/*`: historical branches retained for traceability and not used as a development base.

## Current status

The repository is not considered complete until the exact current stable
installation, including the latest stable mod, has been imported as source and
has a matching portable package, manifests and verification record. A reserved
directory or documentation-only source placeholder does not count.

Every stable version must have this structure (names may be versioned):

```text
source/xmage/<exact-version>/          complete Java/source tree
build/<exact-version>/                 reproducible build inputs and records
release/<exact-version>/               portable ZIP/installer and SHA-256
manifests/<exact-version>/             source, binary, config, decks, images
logs/<exact-version>/                  audit, build, install, rollback tests
```

The source snapshot must include all stable changes accumulated to that point.
The portable release must install with a double click and must behave as the
corresponding official XMage installation, plus the accepted community mods.

The current verified configuration includes:

`Computer - mad` using `mage-player-ai-mad-1.4.61.jar`.

RC1.1 remains a candidate until a real local game is completed against:

- host: `localhost`
- port: `17171`
- player type: `Computer - mad`

## Non-negotiable rules

1. The active `J:\\mtg` installation is an input to be imported and verified;
   after import, the protected GitHub snapshot and portable release are the
   authoritative recovery sources.
2. Never merge an experiment directly into a protected branch.
3. Never overwrite RC1 or RC1.1; create a new numbered candidate instead.
4. Every candidate requires a manifest, SHA-256 inventory, test record, and rollback point.
5. A failed experiment is quarantined; it is not repaired in place.
6. No branch may be labelled RC1.1 until the normal AI option is visible and playable.
7. Configuration, user decks, images, logs, and compiled binaries are separate concerns.
8. A stable tag is forbidden without complete source, integrated latest stable
   mod, portable package, manifests, hashes, and clean-install proof.
9. Every future stable mod must be merged into a new complete snapshot; delta-only
   commits are supporting evidence, never the stable recovery source.
10. The repository URL alone must provide enough information for an authorized
    developer or AI to continue under this contract without private context.

## Naming

- Small corrective changes: `1.1`, `1.2`, `1.3`.
- Large checkpoints: `v-1`, `v-2`.
- Do not create duplicate Windows-style names such as `(1)` or `(2)`.

## Historical branches

Existing `work/*`, `isolation/*`, `checkpoint/*`, `chore/*`, `port/*`, and `stable/*` branches are retained until their contents have been individually classified. They are not stable release branches merely because their names contain `stable`, `complete`, or `rc2`.
