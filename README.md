# XMage Community Patch

This repository uses an immutable-base workflow for the XMage RC1.3 line.

## Start here

- Canonical recovered base: protected/rc1.3-v-1.2.12
- Current candidate: work/rc1.3-v-1.2.13-trigger-indicator
- Compatibility/default pointer: port/1.4.61V1-community-patch

The compatibility pointer is never a development branch. It must point only to a promoted and verified protected base. Do not select a branch by its age, timestamp, commit count, or name similarity.

## Source of truth

The complete source for this generation is under source/rc1.1-complete-community. The protected base includes the game UI, stack work, layout work, and the complete source tree. The previous partial source line is archived and is not a valid starting point.

Read CURRENT-BASE.md and docs/BASE-REGISTRY.md before changing anything.

## Non-negotiable safety rules

- Work only from the exact protected base named in CURRENT-BASE.md.
- Use a new work branch for every change.
- Never modify the installed Windows copy directly.
- Never replace only a client JAR when the base contains coordinated client, common, server, plugin, or resource changes.
- A candidate is not stable until the full build, hashes, smoke test, activation backup, and post-activation verification all pass.
- Any failed gate stops the process and leaves the previous stable base untouched.

## For contributors

The complete workflow is in CONTRIBUTING.md and docs/WORKFLOW.md. Pull requests must identify the exact base commit and include reproducible build and smoke evidence.
