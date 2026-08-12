# Draft — Upstream maintainer review request

Suggested GitHub issue title for `magefree/mage`:

**Community testing / maintainer review request: XMage Community Patch 1.4.60V3 RC1 (Windows)**

Suggested body:

Hello XMage maintainers,

We have prepared an **unofficial community Release Candidate based on XMage 1.4.60V3** for Windows and would like to ask for maintainer feedback on the best path forward.

This is **not presented as an official XMage release**, and the project explicitly links back to upstream XMage and preserves the upstream license/attribution.

Repository:
https://github.com/vros01-Kabutosan/XMage-Community-Patch

RC1 release:
https://github.com/vros01-Kabutosan/XMage-Community-Patch/releases/tag/v1.4.60V3-community-patch-rc1

The RC1 currently groups several areas of work:
- long-session graphical stability work
- 1440p / 4K usability improvements
- printing/art selection in the deck workflow
- tested multipart-card/image/cache fixes
- selected missing-card / legality corrections
- an integrated Standard / Pioneer / Modern deck-download workflow
- logging, duplicate detection, safe cancellation and resume behavior
- Windows Client / Server / Complete packages with SHA-256 checksums

We have also published:
- `CHANGELOG_RC1.md`
- `TECHNICAL_NOTES.md`
- `TESTING.md`
- `CONTRIBUTING.md`
- upstream MIT license/third-party notices
- a public RC1 testing tracker

The validated baseline for this candidate is Windows 10/11 x64 with Java 8u201 x64, using matching client/server build `2026-08-10 02:05`.

Important limitation: the public RC1 is currently a tested binary/community bundle; **we are not asking upstream to merge the bundle as-is**. We understand that reusable changes should be isolated, rebased onto current upstream, reviewed independently and submitted as focused pull requests with tests where practical.

What we would appreciate from the maintainers is guidance on:
1. whether this community testing effort is useful to XMage;
2. which change areas, if any, you would most like us to isolate first for upstream contribution;
3. whether there is a preferred issue/PR workflow for these contributions;
4. any licensing, packaging or naming changes you want us to make before broader community testing.

We are happy to adapt the project to upstream expectations. The goal is to help XMage, not to create a competing official-looking distribution.

Thank you for maintaining XMage.
