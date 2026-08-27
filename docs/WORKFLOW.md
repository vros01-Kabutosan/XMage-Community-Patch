# Release and recovery workflow

## One generation at a time

Each generation has one immutable protected base. A new change starts as a work branch from that exact base. Multiple changes can be developed in parallel only when each branch records the same base identity.

## Fail-closed gates

The order is fixed:

1. preflight and identity check;
2. isolated clone;
3. source change;
4. complete build;
5. artifact and source hashes;
6. smoke test;
7. human review;
8. activation backup;
9. activation;
10. post-activation verification;
11. promotion of the new protected base;
12. archive of the previous generation.

A failure stops the workflow. It cannot fall through to activation, merge, or a success message.

## Installation protection

J:\mtg\xmage is never a build workspace. The only permitted write operation is the final activation command after every previous gate is green. Every activation must first create a new non-overwriting backup under J:\mtg\_ARCHIVO and a one-file rollback command.

Scripts must use explicit paths, verify source and destination identities, avoid /MIR, preserve user data and images, and record exact hashes before and after activation.

## Version naming

Use a new semantic base version for every promoted generation: rc1.3-v-1.2.12, rc1.3-v-1.2.13, and so on. The name must never encode a mod count. A generation can contain one or several changes.

## Public collaboration

The compatibility pointer is the only branch a casual visitor needs to understand. Protected bases are read-only. Work branches are short-lived candidates. Archive refs are historical evidence. Every pull request links to CURRENT-BASE.md and states exactly which base it used.
