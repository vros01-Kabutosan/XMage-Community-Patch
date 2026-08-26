# Tooling index — XMage Community Patch

This directory contains the reproducible, safety-gated PowerShell tooling for the RC1/1.4.61 community patch workflow.

## Canonical tool set

- `AUDIT-CURRENT-XMAGE-INSTALL.ps1`: read-only inventory of the active installation.
- `TRACE-ACTIVE-CLIENT-PROVENANCE-v-1.0.0.ps1`: traces client provenance without mutating the active installation.
- `BUILD-COMPARE-SOURCE-CANDIDATE-v-1.0.0.ps1`: builds and compares an isolated source candidate.
- `IMPORT-CURRENT-STABLE-SOURCE-v-1.0.7.ps1`: imports the current stable source into a new isolated stage.
- `PREPARE-COMPLETE-SOURCE-SNAPSHOT-v-1.0.1.ps1`: prepares the complete source snapshot.
- `COMPARE-STAGED-BUILD-VS-INSTALL-v-1.0.0.ps1`: read-only staged-build parity check.
- `FINALIZE-RECOVERY-CLONE-v-1.0.0.ps1`: creates a recoverable clone with explicit exclusions.
- `VERIFY-RECOVERY-CLONE-v-1.0.2.ps1`: verifies the clone manifest, hashes, decks, and exclusions.
- `BUILD-RECOVERY-PACKAGE-v-1.0.0.ps1`: creates the portable recovery ZIP without `/MIR`.
- `VERIFY-RECOVERY-PACKAGE-v-1.0.0.ps1`: verifies ZIP safety and installability.
- `COMPARE-RECOVERY-RESTORE-v-1.0.0.ps1`: proves restored files match the recovery manifest.
- `COMPARE-ACTIVE-CLIENT-COPIES-v-1.0.0.ps1`: compares active client copies read-only.

## Safety contract

- The active installation and protected stable bases are never written by these tools.
- Every run must create a transcript under the caller-provided log root.
- No tool uses `/MIR`; destructive synchronization is forbidden.
- Generated `target/` directories, nested Git metadata, runtime logs, and card-art/image payloads are excluded where the tool contract says so.
- The recovery package is a local/private operational artifact. Runtime paths, user configuration, and local hashes must not be committed to the public source branch.
- A new stable source snapshot is promoted only after isolated build, verification, recovery, and restore comparison all pass.

Older failed script revisions remain recoverable through Git history; they are intentionally absent from the working tree so operators use one unambiguous version of each procedure.
