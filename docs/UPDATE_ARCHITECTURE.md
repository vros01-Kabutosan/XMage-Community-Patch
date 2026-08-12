# XMage Community Patch — Protected Update Architecture

## Goal

An official XMage update must never overwrite a known-good Community Patch installation in place.

The Community Patch treats upstream XMage and community modifications as two separate layers:

1. **Upstream base** — an immutable official XMage tag/commit.
2. **Community layer** — versioned patches, tools, configuration and packaging maintained by this project.

A new official release is first imported into a staging environment. Community changes are then reapplied and validated. Only a validated result can become a new Community Patch release.

## Non-negotiable rules

- Never update the active Community Patch installation in place.
- Always create a backup/snapshot before migration.
- Never overwrite user data as part of a program update.
- Record both the exact upstream tag/commit and Community Patch version.
- Treat an unknown upstream version as incompatible until tested.
- Reapply community changes as independently versioned changes, not by copying an old binary bundle over a new upstream release.
- Keep the previous working installation until the new candidate passes validation.

## Directory model

```text
XMage-Community/
  active/                 # currently validated installation
  staging/                # candidate built from new upstream
  backups/                # timestamped snapshots before migration
  user-data/              # persistent user-owned data, kept outside replaceable program files
  community/
    config/                # version and compatibility manifests
    patches/               # isolated community source patches
    overlays/              # files intentionally layered over upstream
    tools/                 # migration/verification utilities
```

The exact Windows package layout may differ, but these ownership boundaries must remain explicit.

## Update state machine

`DETECTED -> BLOCKED -> BACKED_UP -> STAGED -> PATCHED -> VALIDATED -> ACTIVATED`

Any failure before `VALIDATED` leaves the existing active installation untouched.

## Current migration

Validated Community Patch base:

- Upstream tag: `xmage_1.4.60V3`
- Upstream commit: `06d166b098ad36b277edef01116472203d5a047e`
- Community release: `RC1`

New upstream candidate:

- Upstream tag: `xmage_1.4.61V1`
- Upstream commit: `105d560ece2939d03fe6d052d3479a91c04ca4b2`
- Status: **BLOCKED / migration pending**

`xmage_1.4.61V1` must not be declared compatible merely because XMage starts. Client/server compatibility, Community Patch functionality and preserved user data must all be validated.

## Patch ownership

Every Community Patch source modification should eventually have an entry under `patches/manifest.json` with:

- stable patch ID;
- description;
- affected component;
- source paths;
- upstream base it was last validated against;
- dependencies on other community patches;
- migration/test status.

This is required to make future upstream migrations auditable instead of relying on memory or old binaries.

## Migration procedure

1. Detect the new official XMage tag.
2. Read `config/community-version.json`.
3. If the tag is not explicitly compatible, block in-place updating.
4. Back up the current working installation and relevant user data metadata.
5. Obtain a clean copy of the new upstream release/source in staging.
6. Compare upstream old base -> upstream new base.
7. Reapply each Community Patch change independently.
8. Resolve conflicts in source, never by blindly restoring old JARs.
9. Build matching client/server artifacts.
10. Run smoke tests and feature-specific tests.
11. Verify user-data preservation.
12. Record hashes and the exact new upstream commit.
13. Only then mark the candidate compatible and package a new Community Patch release.

## Rollback

Activation must be reversible. If the candidate fails after activation, restore the previous known-good program directory without replacing persistent user data.

## Important RC1 limitation

RC1 was published before every binary modification had been reconstructed as an isolated source patch. Therefore the first migration also includes a one-time forensic task: identify each RC1 modification from the working source/build and convert it into a reproducible patch entry. Until that inventory is complete, no migration can honestly guarantee preservation of **every** RC1 modification.
