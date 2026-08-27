# Contributing safely

Thank you for helping with XMage Community Patch. This project uses a protected-base workflow so a contributor never has to guess which history is authoritative.

## Before writing code

1. Read CURRENT-BASE.md.
2. Confirm the exact protected base commit.
3. Create one work branch from that base.
4. Record the base commit in the pull request.
5. Keep the installed copy and every protected base read-only.

## Branch names

- protected/rc1.3-v-X.Y.Z: immutable promoted base
- work/rc1.3-v-X.Y.Z-feature: one isolated candidate
- archive/YYYYMMDD-description: retained historical line
- isolation/...: temporary diagnostics only

Do not create ad-hoc branches such as test, final, latest, new, fixed, or copy.

## Pull request gates

A pull request must include:

- exact base branch and commit;
- complete file list;
- source diff;
- full Maven result;
- Java and Maven versions;
- SHA-256 manifest for generated artifacts;
- smoke-test transcript;
- visual or functional evidence;
- activation backup and rollback path when activation is requested;
- explicit statement that the installed copy and protected base were not changed during development.

If one item is missing, the status is BLOCKED or FAILED. It is never treated as successful.

## Full-auto operator experience

The operator should receive one master .cmd file. It may download missing JDK/Maven tools, discover paths automatically, create the isolated staging area, write timestamped logs, and stop on the first error. It must not require manual folder navigation or hand-edited paths.

The command file may ask only for the final activation authorization. It must never report success after a failed command or hide stderr.

## What is never allowed

- working from the default pointer as a feature branch;
- using a different checkpoint because it looks newer;
- copying a partial JAR set over a complete installation;
- modifying J:\mtg\xmage during development;
- using /MIR;
- overwriting backups;
- deleting failed evidence;
- inventing build, hash, smoke, or visual results.
