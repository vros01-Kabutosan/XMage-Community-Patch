# Community Patch 1.4.61V1 — Port Audit

This document is the control sheet for the post-migration development phase.

## Rules

- Do not modify the known-good migration checkpoint.
- Do not remove rollback backups during this phase.
- Do not blindly reapply old patches.
- Compare every Community Patch feature with 1.4.61V1 first.
- Prefer upstream functionality when it already solves the same problem correctly.
- Integrate one logical feature at a time and smoke-test it before moving on.

## Classification

Each feature must end in exactly one state:

- **KEEP** — still needed and compatible.
- **ADAPT** — still needed but must change for 1.4.61V1.
- **DROP** — upstream now provides it or it is obsolete.
- **REIMPLEMENT** — desired behavior remains, but the old implementation is unsafe/incompatible.

## Audit queue

| Area | Initial state | Required validation |
|---|---|---|
| Deck Downloader GUI integration | ADAPT / verify | Confirm menu/pane integration, runtime location, errors, cancellation, progress and logs |
| Standard deck download | KEEP / verify | 25 valid decks, 60+15 where applicable, clean replacement behavior |
| Pioneer deck download | KEEP / verify | 25 valid decks, 60+15 where applicable, clean replacement behavior |
| Modern deck download | KEEP / verify | 25 valid decks, 60+15 where applicable, clean replacement behavior |
| Deck Downloader logging | KEEP / verify | General log is created reliably and records OK/FAIL details |
| Cancel operation | KEEP / verify | Cancellation stops safely without corrupting deck folders |
| Card-name normalization | KEEP / verify | Split/double-faced names remain XMage-compatible |
| Image-related fixes | AUDIT | Determine what 1.4.61V1 already fixed upstream before carrying anything forward |
| Launcher/runtime compatibility work | AUDIT | Drop workarounds made obsolete by 1.4.61V1 |
| Memory/4 GB launch guidance | VERIFY | Confirm recommended launcher/JVM configuration for Community release |
| Community documentation | ADAPT | Rewrite release notes and instructions for 1.4.61V1 base |

## First integration target

**Deck Downloader** is the first feature to harden because the migrated client has already demonstrated that the UI entry opens and the preserved deck library is present.

Acceptance criteria before moving to the next feature:

1. GUI opens without exception.
2. Standard/Pioneer/Modern selectable.
3. Download operation completes for each supported format.
4. Expected deck counts are produced.
5. General log is created.
6. Cancel works safely.
7. Restarting XMage preserves functionality.
8. No regression in normal Deck Editor operation.

## Release gate

Do not call the 1.4.61V1 Community Patch a release candidate until all retained features are classified and all KEEP/ADAPT/REIMPLEMENT items pass their smoke tests.
