# XMage Community Patch — Migration to 1.4.61V1 COMPLETE

Status: **COMPLETED AND VALIDATED**  
Date: 2026-08-13

## Result

The active XMage client was migrated to the 1.4.61V1 base through the controlled migration pipeline and passed the final post-activation validation.

Validated active installation:

`J:\MTG\xmage\mage-client`

Final gate result:

- POST ACTIVATION FINALIZE V1: PASS
- Migration 1.4.61V1: formally finalized
- Active client integrity after smoke test: PASS
- Deck Downloader runtime integrity after smoke test: PASS
- Deck library preserved: Standard 25 / Pioneer 25 / Modern 25
- Immediate pre-activation installation: preserved
- Verified V4 backup: preserved
- Rollback path: preserved and available
- Cleanup: intentionally NOT performed

## Printing / edition selector recovery

The Community Patch printing selector has now also been recovered and visually validated on the active 1.4.61V1 client.

Validated implementation: **Printing Selector V6**.

Confirmed behavior:

- `Elegir edición...` is available in Deck Editor.
- Printing list and set search work.
- Selected printing shows a card preview.
- Choosing a printing updates all matching copies of that card in the deck.
- Normal client/server launch remains functional after activation.

Canonical port tooling:

- `tools/migration/printing_selector_port_source_v6_exact_old.py`
- `tools/migration/RUN_PRINTING_SELECTOR_PORT_SOURCE_V6_EXACT_OLD_WINDOWS.cmd`

See `docs/PRINTING_SELECTOR_V6_VALIDATED.md` for the validation record.

## Safety policy

Do not delete the verified rollback material yet. Keep at least one known-good backup until the 1.4.61V1-based Community Patch has had normal-use testing and the next release candidate has been validated.

## Migration tooling

The migration scripts under `tools/migration/` are now considered historical/recovery infrastructure for the 1.4.61V1 transition. They should not be treated as the normal development workflow for subsequent Community Patch work.

## Development baseline

All new Community Patch development should use the successfully migrated 1.4.61V1 state as the baseline. Existing Community Patch features must be audited before porting so that functionality already provided upstream is not duplicated unnecessarily.

## Next phase

1. Continue normal-use testing of the validated 1.4.61V1 Community Patch state.
2. Audit remaining Community Patch features against 1.4.61V1 upstream behavior.
3. Classify each remaining feature as KEEP / ADAPT / DROP / REIMPLEMENT.
4. Port features incrementally with build and smoke-test gates.
5. Produce a new 1.4.61V1-based release candidate only after the audit and port are clean.
