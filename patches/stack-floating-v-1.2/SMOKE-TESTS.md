# Smoke tests — Stack Floating v-1.2

Automated workflow:

- `.github/workflows/stack-floating-v-1.2-smoke.yml`
- JDK 17.
- Maven client compile and tests with four attempts.
- Exactly 84 restored `mage.target` Java files.
- Stack title and LIFO load call preserved.
- Drag listeners present on the visible drag hint.
- Mojibake check passed as a required contract.

Patch validation:

- Base: `2e49dfdea5b2cb7a5b0c7cfff85239644d048b6c`
- Source commit: `f0d621bd450a8b4009d432e40a2d2b14b7df0e88`
- Apply and reverse checks are required before acceptance.

Not executable in GitHub Actions:

- Manual Swing visual launch.
- Live-game interaction.
- Dragging the header, title, and hint independently.
- DPI checks at 100%, 150%, and 200%.
- Persistence after restart and reconnect.

Those checks must use a disposable work build, never the protected installation.
