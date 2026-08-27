# XMage Community Patch — Immutable Stability Contract

**Status: Mandatory and permanent**

This contract defines the only permitted development model for the XMage Community Patch. It applies to Victor, every human contributor, every AI system, every script, every automation, and every future version of the project.

## 1. Stable releases are immutable

Any validated release identified as `RC1`, `RC1.1`, `RC1.2`, `RC2.0`, or a later stable checkpoint is a protected base.

A stable base must never be modified directly, overwritten, rebuilt in place, or used as an experimental workspace.

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

A new RC becomes a protected base only after validation, packaging, hash generation, clean-download testing, extraction testing, and functional smoke testing.

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

**This contract is part of the project architecture and remains in force for all future XMage Community Patch versions.**
