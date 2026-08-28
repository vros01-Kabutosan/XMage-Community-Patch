# Base registry

This is the concise map for humans and automation.

## Active generation

| Role | Ref | State | Rule |
| --- | --- | --- | --- |
| Stable source of truth | protected/rc1.3-v-1.2.12 | sealed, pre-T | Only valid starting point |
| Compatibility pointer | port/1.4.61V1-community-patch | protected | Navigation only; never select as a source |
| Active candidate | none | — | Create one only for an approved new mod |

## Retired and historical references

The T candidate, old feature branches and closed pull requests are not active
code. The old source-foundation references are retained as locked historical
inputs only. None of them may be selected automatically or used as a build base.

## Promotion gate

A new generation is accepted only when all of these exist and agree:

1. exact source ref, commit, root POM and complete source tree;
2. full Maven build with recorded JDK and Maven versions;
3. source, resource and artifact manifests with SHA-256;
4. isolated client/server start and visual smoke evidence;
5. dated full backup and a tested rollback path;
6. post-activation verification and human acceptance.

If any gate fails, stop without copying or promoting. After promotion, the new
complete source becomes the next canonical generation and the previous stable
generation remains the emergency rollback point.

## Prohibited selection

Do not use main, master, latest, oldest, newest, timestamps, commit counts,
local installation contents, or a similarly named branch as a source.
