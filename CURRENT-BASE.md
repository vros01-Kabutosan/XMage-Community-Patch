# Current base contract

Status: STABLE / SEALED / PRE-T

Use exactly this source for every future mod:

- Canonical ref: protected/rc1.3-v-1.2.12
- Sealed source-tree commit: 414e463c8bec4913a716dc2840c9002f503f81a7
- Complete source root: source/rc1.1-complete-community
- Root POM: source/rc1.1-complete-community/pom.xml
- Validated complete-source asset SHA-256: 78b5386c1dd3133f93418fdf930cb652e1bddd4bc4866b59b82aa39d7a4ef5fa

There is no active candidate. The T candidate is retired and its branch is
neutralized on the pre-T source commit. The compatibility pointer
port/1.4.61V1-community-patch is protected for navigation only; it is not a
source selector.

The previous value 289337b244f2a47aeffca6f60707c73e6f1b890b identifies the
immutable source-release tag tree, but it must not be selected by a branch-name
heuristic. Resolve this exact canonical ref, source commit, source root and POM
together. If one does not match, fail closed.

Never select by latest, oldest, timestamp, commit count, default branch, folder
name, main, master, port, work, feature or local installation contents.

A future change must use one candidate branch, the complete source and resources,
a full Maven build, source/resource/artifact hashes, isolated smoke tests, a
dated backup, and post-activation verification. Any failed gate leaves the
stable installation untouched. The previous stable generation remains the
emergency rollback point.
