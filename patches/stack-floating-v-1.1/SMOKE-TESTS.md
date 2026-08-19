# Smoke tests — Stack Floating v-1.1

Validated commit: 184fb0f8e0610e5f197c59f813341bcfafb35c1c

Automated GitHub Actions run:

- Run: 32223569806
- Result: success
- Checkout: success
- JDK 17: success
- Maven client plus dependencies: success
- Tests: success
- Restored Mage target source count: 84
- Stack presentation contract: success
- Mojibake check: success
- LIFO call preserved: loadCards(game.getStack(), bigCard, gameId, false)

Not executed by CI:

- Manual visual launch of the Swing client.
- Human interaction with a live stack.
- DPI checks at 100%, 150% and 200%.

Those require the protected local XMage installation and must be tested only on a disposable work build.
