# XMage Community Patch — Immutable Stability Contract

**Status: Mandatory and permanent**

This contract defines the only permitted development model for the XMage Community Patch. It applies to Victor, every human contributor, every AI system, every script, every automation, and every future version of the project.

## 1. Stable releases are immutable

Any validated release identified as `RC1`, `RC1.1`, `RC1.2`, `RC2.0`, or a later stable checkpoint is a protected base.

A stable base must never be modified directly, overwritten, rebuilt in place, or used as an experimental workspace.

## 1A. A stable base is a complete installation clone

The words **stable base**, **complete source**, and **portable release** have a
strict meaning in this project. A stable base is not a patch collection, a
delta, a set of notes, or a repository containing only tools.

For every accepted stable version, GitHub must provide a complete, reproducible
clone of the latest known-good XMage installation, including every previously
accepted modification and the newest accepted modification:

- the complete XMage source tree for the exact client/server version;
- every community change integrated into that source tree;
- all build files, dependencies, scripts, patches, and build instructions;
- the exact launcher and Java/runtime requirements;
- the generated client/server artifacts or a reproducible build route;
- the user's accepted launcher/UI/memory settings;
- the accepted deck catalogue and user-data migration rules;
- manifests and SHA-256 hashes for source, binaries, installer inputs, and user data;
- a tested Windows portable package that can be downloaded and installed from
  scratch with a double click.

The package may omit card images only when its manifest and installer provide a
verified download/rebuild route. Omitting images must never omit their mapping,
version, checksum policy, or restoration instructions.

An empty `source/` directory, a README promising future source, a patch without
the base source, or a binary without corresponding source is **not** a stable
base and must not receive a stable tag.

## 2. All work starts from a clone

Every new feature, mod, refactor, experiment, or test must start from a separate clone or work branch created from the latest protected stable base.

Examples:

```text
RC1.1 stable
  -> work/stack-floating-v-1
  -> work/feature-name-v-1
```

No tool may use the stable release directory as its output, build, extraction, or temporary directory.

## 3. Failed work must be disposable

A failed mod, broken build, bad prompt, incorrect merge, or experimental change may only affect its own work branch or clone.

If a work branch is broken, it is discarded. The stable base is restored by starting again from the protected checkpoint.

## 4. Promotion to a new stable release

Validated changes are accumulated and tested only in a development branch. When the selected changes are confirmed functional, the result is promoted to a new stable release:

```text
RC1.1 stable
  -> work branch
  -> validated changes
  -> RC1.2 or RC2.0
  -> full verification
  -> protected stable checkpoint
```

A new RC becomes a protected base only after validation, packaging, hash generation,
clean-download testing, extraction testing, functional smoke testing, and the
complete-installation gate defined in section 4A.

## 4A. Complete-installation promotion gate

Promotion is blocked unless all of the following are present in the same
versioned checkpoint:

1. complete source, not only a delta;
2. all stable modifications integrated, including the latest stable mod;
3. source and binary manifests with SHA-256 hashes;
4. a reproducible build record with successful exit code;
5. a portable Windows package and its checksum;
6. a double-click installation test on a clean destination;
7. launcher, client, server, Java, UI scale, memory, configuration and deck
   restoration records;
8. an image download/rebuild manifest, where images are not bundled;
9. rollback material that restores the preceding stable checkpoint;
10. a log proving every gate passed.

The new checkpoint is then sealed as a complete snapshot. Future work starts
from that sealed snapshot, never from an older branch and never by applying a
delta to the active installation.

## 5. GitHub protection

The public repository may be read, cloned, forked, and used to propose changes. Stable release tags and stable branches must be protected against deletion, force updates, and direct changes.

Development must occur through separate branches and Pull Requests. A Pull Request is never merged into a stable base without deliberate human approval.

## 6. Local protection

Each stable checkpoint must also have a local protected copy with:

- no normal write permission;
- a SHA-256 manifest;
- a dedicated log;
- no experiments or temporary files;
- no use as a build or work directory.

## 7. No exceptions by ambiguity

An incomplete prompt, mistaken instruction, automated tool, AI hallucination, rushed fix, or accidental path selection must never be interpreted as permission to modify a stable base.

When the target path or version is ambiguous, the operation must stop.

## 8. Recovery principle

At all times, at least one verified stable checkpoint must remain recoverable independently of the active work.

No single mod, branch, AI, script, merge, or failed experiment may be capable of destroying the project's last stable base.

## 9. Stable snapshot continuity

After a mod becomes stable, the exact complete source snapshot is committed,
the portable package is rebuilt, and the new snapshot is protected. The next
mod starts by cloning that newest protected snapshot. This cycle is mandatory:

```text
protected complete snapshot
    -> isolated clone
    -> one new mod
    -> validation and package test
    -> source integration
    -> new complete snapshot
    -> new protected tag
```

No future contributor or AI may need private conversation history to understand
the project. The repository, its manifests, contracts, build instructions and
logs must be sufficient for an authorized developer to continue under the same
rules using only the repository URL.

## 10. Recovery from a failed PC or installation

The ultimate recovery path is a clean download of the latest protected portable
package followed by a double-click installer. It must restore the same playable
program baseline as the accepted installation, including all stable mods. User
configuration, decks and images are backed up separately, but the package must
also document verified restoration or download steps for each of them.

The active PC installation is never the only copy of the project. If the active
installation is lost, recovery starts from the latest protected GitHub snapshot
and package, not from memory or from an experimental folder.

**This contract is part of the project architecture and remains in force for all future XMage Community Patch versions.**
