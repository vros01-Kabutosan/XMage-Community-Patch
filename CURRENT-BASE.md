# Current Base Contract

Status: CANDIDATE WORK IN PROGRESS

## Exact base for the next operation

Use this protected base and no other branch:

- Protected recovered base: protected/rc1.3-v-1.2.12
- Base commit: 289337b244f2a47aeffca6f60707c73e6f1b890b
- Historical continuity input: checkpoint/xmage-stack-v-1.2.9-continuity
- Source root: source/rc1.1-complete-community

The base above is the recovered complete line containing the stack and UI state. The old port line is not equivalent.

## Candidate being prepared

- Work branch: work/rc1.3-v-1.2.13-trigger-indicator
- Change: synchronized red T marker for a permanent whose triggered ability is on the stack
- Candidate state: build and activation evidence pending

Until the candidate passes every gate, the protected base remains the rollback target. Do not merge or activate the candidate by inference.

## Branch selection rule

Do not choose a branch using latest, recent, main, master, port, timestamp, or commit count. Read this file, resolve the exact commit, and stop if the branch or commit does not match.

## Installation boundary

The protected installation is J:\mtg\xmage. Development and staging must use an isolated copy under J:\mtg\_ARCHIVO. No script may write to the installation before a complete preflight, an immutable backup, a successful full build, and an explicit activation step.

## Emergency rollback

The previous stable installation must always have a dated, hash-verified backup and a one-file rollback command. Rollback is allowed only for recovery; it must never become the normal development workflow.
