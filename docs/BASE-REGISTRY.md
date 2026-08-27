# Base registry

This file is the human and machine-readable map of the repository generations.

## Active generation

| Role | Ref | Status | Rule |
| --- | --- | --- | --- |
| Compatibility/default pointer | port/1.4.61V1-community-patch | protected pointer | Must point only to the promoted protected base |
| Recovered complete base | protected/rc1.3-v-1.2.12 | protected/frozen | Authoritative rollback and next-work source |
| T candidate | work/rc1.3-v-1.2.13-trigger-indicator | candidate | Pending full Windows build, smoke, activation and verification |

## Historical refs

| Ref | Classification | Use |
| --- | --- | --- |
| archive/legacy-port-1.4.61V1-community-patch-20260827 | archived | Preserves the old public pointer before migration |
| checkpoint/xmage-stack-v-1.2.9-continuity | recovery input | Historical source of the recovered complete base; do not use directly for new work |
| feature/trigger-active-indicator-v1.0.0 | legacy candidate | The earlier T-only line; not a base |
| isolation/* | quarantine | Diagnostics and experiments only |
| work/* other than the current candidate | historical work | Do not use without an explicit registry entry |

## Promotion rule

A protected base is promoted only after:

1. the exact source tree is identified;
2. the complete build succeeds on the declared JDK/Maven pair;
3. artifacts and source manifests are hashed;
4. smoke testing proves the UI and stack are intact;
5. activation creates a new backup and a rollback command;
6. post-activation verification succeeds;
7. a human reviews the evidence.

After promotion, the old protected base is retained as an emergency rollback point and the old work branch is archived. No branch is deleted as part of a normal release.

## Prohibited source selection

Never use main, master, the oldest or newest branch, a branch selected by timestamp, or a branch with a similar name. The exact ref and commit in CURRENT-BASE.md are authoritative.
