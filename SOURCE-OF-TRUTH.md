# Canonical source contract — XMage RC1.3

Status: STABLE / SEALED / PRE-T

This file is the machine- and human-readable source of truth for future work.
If any other branch, release, timestamp, folder name or local copy conflicts with
this file, the operation must stop.

## Canonical stable source

- Repository: vros01-Kabutosan/XMage-Community-Patch
- Canonical ref: protected/rc1.3-v-1.2.12
- Canonical source commit: 78bc19478d56eb4d07e98df991af437ad6d2318b
- Complete source root: source/rc1.1-complete-community
- Root POM: source/rc1.1-complete-community/pom.xml
- Source version: XMage 1.4.61 / RC1.3
- Stable state: pre-T; the trigger indicator is intentionally not included

The commit 78bc194... is the exact source-tree state used by the protected
generation. Its only change after 289337b... is workflow documentation outside
the source tree. The existing source release asset is tagged at 289337b... and
is source-equivalent; that tag is an immutable archive identity, not an
alternative branch selector.

The three source files below were compared against the imported complete source
and must remain unchanged until a new candidate passes every gate:

- Mage.Common/src/main/java/mage/view/PermanentView.java
  Git blob: 6f3684e8e12d873d85a07253c95213cfb54fb7df
- Mage.Client/src/main/java/org/mage/card/arcane/CardPanelRenderModeImage.java
  Git blob: e271704536d53d47212e9ed92a6c7b47ac0b04f5
- Mage.Client/src/main/java/org/mage/card/arcane/CardPanelRenderModeMTGO.java
  Git blob: c0851b79b5e568179ef4f433e5c4fe95d09c7202

## Branch rule

Only the canonical ref above may be used as the starting point for new work.
The compatibility pointer port/1.4.61V1-community-patch is not a source selector.
Branches named work/, feature/, checkpoint/, archive/ or isolation/ are never
valid build sources unless this file explicitly names one as the current
candidate. There is one candidate at a time.

Never select a source by latest, oldest, recent, timestamp, commit count, default
folder, or a similar branch name. Resolve the ref, commit, source root and POM
together; if one does not match, fail closed.

## Required cumulative workflow

1. Start from the exact canonical source above.
2. Create one clearly named candidate branch for the requested mod.
3. Keep the complete source tree and resources; never build from a partial patch,
   a binary-only package, an old installation, or a generated target directory.
4. Build the complete Maven reactor with the declared JDK and Maven versions.
5. Verify source/resource manifests, artifact hashes, launcher dependencies and
   the client/server start path.
6. Run isolated smoke checks, create a dated full backup, and only then perform
   explicit activation.
7. Verify the active installation after activation. If any gate fails, do not
   copy files and do not promote the candidate.
8. Once a candidate is accepted, its exact complete source becomes the next
   canonical stable generation and the previous generation remains the emergency
   rollback point.

Development and staging are isolated from J:\mtg\xmage. No build script may
write to the active installation before all gates pass. No /MIR synchronization
is permitted.

## T status

The T candidate is retired. It is not the stable source, was not promoted, and
must not be used for activation. The stable source remains pre-T until a future
candidate is rebuilt from this exact source and passes the complete protocol.
