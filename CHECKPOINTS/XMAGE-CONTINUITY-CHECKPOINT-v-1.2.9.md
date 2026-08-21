# XMage Community Patch — v-1.2.9 continuation

This public checkpoint contains only reproducible project state. Private Windows paths, personal profile data and stable-installation locations are intentionally omitted.

- Repository: https://github.com/vros01-Kabutosan/XMage-Community-Patch
- Branch: checkpoint/xmage-stack-v-1.2.9-continuity
- Foundation tag: source-foundation-v-1.7-complete-target
- Authorized foundation SHA: b974aa865b3a8b1a24df52a2321eacc54f06dfac
- Target: XMage 1.4.61
- Current work: v-1.2.9 patch package prepared; Windows portable-Maven build and final smoke remain pending.

## v-1.2.9 changes

- Remove only cached CardIconType.OTHER_HAS_TARGETS visual icons; preserve real targets and interaction.
- Separate Spell and NEXT order guide into compact vertical rows with revalidate/repaint.
- Keep LIFO order: top item resolves first.
- Keep stack draggable, centered by default, compact, readable and without T-1.
- Preserve full card rendering, rounded corners without white spikes, and no inner double shadow.
- Preserve personal Java options, HKCU preferences, UI scale and 4G client memory.
- Use short version naming: v-1.2.9.

## Previous diagnosis

- v-1.2.7 Maven failure: duplicate cardEventSource declaration in Cards.java.
- v-1.2.8 built successfully, but T-1 remained because the target icon was cached before late target clearing. Late target clearing could also break interaction.
- v-1.2.9 fixes the cache point and keeps real target selection intact.

## Acceptance gates

1. Portable Windows Maven reports BUILD SUCCESS.
2. Client/server 1.4.61 are coherent and the isolated server is stable.
3. No T-1; NEXT is visible, minimal and legible.
4. With 1, 2, 3 and more spells, the next card is visible only by a small top strip, the top item resolves first, and multiple counter targets can be selected.
5. Personal preferences match the stable profile.
6. Official images remain linked, not duplicated.
7. SHA-256 and logs are recorded before any activation.

Do not modify main or any stable installation until all gates pass.
