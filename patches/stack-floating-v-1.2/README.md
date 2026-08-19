# Stack Floating v-1.2

Base exacta:

- Previous work branch: `work/stack-floating-v-1.1`
- Base commit: `2e49dfdea5b2cb7a5b0c7cfff85239644d048b6c`
- Immutable foundation: `source-foundation-v-1.7-complete-target`
- Foundation commit: `b974aa865b3a8b1a24df52a2321eacc54f06dfac`

Change:

- Adds drag listeners to the visible `Drag to move` hint.
- The stack header, title, and hint now all support moving the floating window.
- No change to server logic, stack order, priority, targets, or resolution.

Apply:

```text
git switch -c work/stack-floating-v-1.2 2e49dfdea5b2cb7a5b0c7cfff85239644d048b6c
git apply patches/stack-floating-v-1.2/stack-floating-v-1.2.patch
```

Reverse:

```text
git apply -R patches/stack-floating-v-1.2/stack-floating-v-1.2.patch
```

The patch is intentionally small and reversible. Manual GUI testing remains required for the final visual acceptance.
