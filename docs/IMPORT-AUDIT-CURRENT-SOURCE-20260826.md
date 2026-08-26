# Import audit: current XMage source candidate

Date: 2026-08-26
Authoritative installation: `J:\mtg\xmage`
Images: excluded from source comparison and package scope.

## Findings

The complete ZIP `source.zip` has SHA-256 `863FE675291E65E1DA2A4E1B22B4206AD6B371AE6C68DF7B2D13E8926B14130B`, but its source files and embedded target artifacts are older than the active installation.

Active installation evidence:
- `client\lib\mage-client-1.4.61.jar`: modified 2026-08-23, SHA-256 `1C054517B28B2BF7EB2B98C426AAF5E5F17CC1A24F75A391565A0B6DF7C5C4A3`
- `server\lib\mage-sets-1.4.61.jar`: modified 2026-08-25, SHA-256 `2736D159898F74612C2993C311FD72EBA8DE9C0C582542B185490C257B7DB305`
- installed deck catalogue includes 25 Standard, 25 Pioneer and 25 Modern entries.
- installed.properties modified 2026-08-25.

## Selected source candidate

`J:\mtg\_ARCHIVO\00-FUENTE\rc1.1-complete-community`

Evidence from SOURCE-SEARCH-20260826-025755.log:
- `Mage.Client...GamePanel.java`: 162860 bytes, modified 2026-08-24 01:10:25
- `Mage.Sets...SuperiorSpiderMan.java`: 4861 bytes, modified 2026-08-24 23:11:00

The isolated MOD-004 build contains the final Superior Spider-Man v1.0.3 source:
- `J:\mtg\_ARCHIVO\MODS\MOD-004-SUPERIOR-SPIDER-MAN-v-1.0.3\BUILD\20260825-125014\source\rc1.1-complete-community\Mage.Sets...SuperiorSpiderMan.java`
- 5191 bytes, modified 2026-08-25 12:50:27

## Required integration

Create a new isolated complete snapshot from `00-FUENTE\rc1.1-complete-community`, replace only its Superior Spider-Man source with the validated MOD-004 v1.0.3 file, rebuild all required client/server artifacts, and compare the resulting manifests to the active installation. Do not use v7/r5.1, do not copy images, and do not modify the protected installation during this phase.

Status: import gate open; no stable baseline promoted yet.
