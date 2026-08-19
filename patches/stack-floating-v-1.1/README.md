# Stack Floating v-1.1

Base exacta:

- Branch: work/source-foundation-v-1.7-complete-target
- Foundation repair commit: b974aa865b3a8b1a24df52a2321eacc54f06dfac
- Original immutable foundation: 2f0f2b7765d892cbba76f0e73ab396318213de63

Scope:

- One source file: Mage.Client/src/main/java/mage/client/game/GamePanel.java
- Clarifies that the top stack object resolves first.
- Labels the drag handle.
- Replaces the corrupted resize glyph with an ASCII-safe Java Unicode escape.
- Does not change stack ordering, server logic, priority, targets, or resolution.

Apply:

```text
git switch -c work/stack-floating-v-1.1 b974aa865b3a8b1a24df52a2321eacc54f06dfac
git apply patches/stack-floating-v-1.1/stack-floating-v-1.1.patch
```

Reverse:

```text
git apply -R patches/stack-floating-v-1.1/stack-floating-v-1.1.patch
```

The patch is intentionally small and reversible. It is not a substitute for a manual visual game smoke test.
