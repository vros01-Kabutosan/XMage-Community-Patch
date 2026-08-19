# XMage Community Patch — AI and Human Work Contract

Status: mandatory operating contract for development branches.

## Immutable references

- Stable historical foundation branch: `work/source-foundation-v-1.6`
- Complete foundation branch: `work/source-foundation-v-1.7-complete-target`
- Complete foundation tag: `source-foundation-v-1.7-complete-target`
- Complete foundation commit: `b974aa865b3a8b1a24df52a2321eacc54f06dfac`
- Current stack work branch: `work/stack-floating-v-1.1`

The foundation branches and foundation tags are protected against update, deletion, and non-fast-forward history rewrites. They are read-only baselines.

## Absolute prohibitions

No human, AI agent, script, or automation may:

- commit directly to `main`;
- commit directly to either foundation branch;
- rewrite or delete a foundation tag;
- modify RC1, RC1.1, the active installation, or any protected backup;
- use `/MIR`;
- delete or clean partial attempts;
- publish code without successful validation and a SHA256 manifest;
- replace a failed change by silently hiding or deleting its history.

Protected local paths:

- `J:\mtg\xmage`
- `J:\mtg\_ARCHIVO\PRIVADO-BLINDADO-XMAGE`
- `J:\mtg\_ARCHIVO\RC1.1-COMPLETA-PORTABLE`

## Required workflow

1. Read this contract before changing anything.
2. Fetch the repository and verify the immutable base SHA.
3. Create a new versioned branch under `work/*).
4. Inspect before editing. Never invent source files or paths.
5. Make the smallest reversible change possible.
6. Keep server, client, launcher, data, and UI changes separated unless the task explicitly requires otherwise.
7. Generate a binary-safe patch against the exact foundation or work base.
8. Generate a SHA256 manifest for the patch and changed artifacts.
9. Run the relevant GitHub Actions smoke tests and compile/tests.
10. Run static contract checks: changed-file scope, forbidden paths, image policy, source counts, encoding, and preserved behavior.
11. Report exact base SHA, changed files, commit SHA, patch SHA256, tests, and known manual tests.
12. Stop on any failure. Do not publish a partial or speculative result.

## Patch contract

Every completed change must provide:

- one versioned `work/*` branch;
- a reversible `.patch` file;
- `README.md` with exact base and apply/reverse instructions;
- `SMOKE-TESTS.md` with actual CI run and result;
- `SHA256-MANIFEST.txt`;
- no unreported source changes.

A patch is not complete merely because it compiles. GUI, live-game, DPI, and persistence checks must be identified separately when CI cannot execute them.

## AI instruction

If a user request is ambiguous, do not guess a destructive interpretation. Preserve the immutable base, explain the ambiguity, and choose the smallest isolated work branch. An AI may propose or implement changes only on a `work/*` branch. It must return a patch for review; it must never make the stable base the workspace for experimentation.

The only valid route for a new stable foundation is a new, explicitly versioned foundation branch and tag, followed by full validation, manifest generation, and administrative protection. Existing stable foundations remain unchanged forever.
