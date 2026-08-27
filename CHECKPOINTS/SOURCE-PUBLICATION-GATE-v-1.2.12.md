# XMage v-1.2.12 — Exact source publication gate

The continuity branch must expose the exact source that produced the final JAR.

Required files:

- `source/rc1.1-complete-community/Mage.Client/src/main/java/mage/client/game/GamePanel.java`
- `source/rc1.1-complete-community/Mage.Client/src/main/java/mage/client/cards/Cards.java`
- `source/rc1.1-complete-community/Mage.Client/src/main/java/mage/client/plugins/adapters/MageActionCallback.java`

Required verification:

1. Run `activation/PUBLICAR-FUENTE-EXACTA-v-1.2.12.cmd` from the isolated TEST workspace.
2. Keep the generated transcript in `J:\mtg\_LOGS`.
3. Publish the three exact files to this branch.
4. Record each Git blob SHA and the source SHA256 manifest.
5. Rebuild with portable Maven 3.9.15 and confirm JAR SHA256 `743D1FC07B2E1453B82F6BD5A97745A37822716E271922DD75AAE57B12A38E63`.
6. Only then activate, clean temporary material and blind the stable installation.

Protected paths remain excluded: `J:\mtg\xmage`, blind RC1/RC1.1 copies, official image trees and private HKCU data.
