# XMage Community Patch — Master Continuity Checkpoint v-1.2.12

## Repository contract

- Repository: https://github.com/vros01-Kabutosan/XMage-Community-Patch
- Continuity branch: `checkpoint/xmage-stack-v-1.2.9-continuity`
- Required foundation tag: `source-foundation-v-1.7-complete-target`
- Authorized foundation SHA: `b974aa865b3a8b1a24df52a2321eacc54f06dfac`
- Target: XMage 1.4.61

The complete working source must remain accessible in GitHub. The local Windows clone is only a build/test workspace. Stable installations, private profiles, official images and blind backups are excluded.

## Final tested state

- Green `NEXT` guide with compact typography and wrapped long names.
- Spell/type row separated; no T-1; full top card; draggable stack.
- Maven: `BUILD SUCCESS`.
- Final compiled JAR SHA256: `743D1FC07B2E1453B82F6BD5A97745A37822716E271922DD75AAE57B12A38E63`.
- Isolated server: Java 17, XMage 1.4.61-V1, fallback port 17172.
- HKCU preferences loaded; official images linked read-only.

## Mandatory source publication gate

Before final activation/cleanup is considered closed, publish the exact final working versions of:

- `Mage.Client/src/main/java/mage/client/game/GamePanel.java`
- `Mage.Client/src/main/java/mage/client/cards/Cards.java`
- `Mage.Client/src/main/java/mage/client/plugins/adapters/MageActionCallback.java`

The published source must produce the JAR SHA above. Record each blob SHA.

## Protected exclusions

Never include or modify `J:\mtg\xmage`, blind RC1/RC1.1 installations, official image trees, personal HKCU exports, or stable backups during source publication or package cleanup.
