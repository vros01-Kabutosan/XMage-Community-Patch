# XMage Community Patch — RC1 / 1.4.61V1

Independent community source snapshot for XMage 1.4.61V1. This project is not
official XMage and is not affiliated with the upstream maintainers.

## Canonical stable source

The canonical source branch is:

`port/1.4.61V1-community-patch`

It contains the complete RC1.1 / XMage 1.4.61 source tree with the latest
accepted source integration, including the corrected Superior Spider-Man card
implementation:

`source/xmage/1.4.61V1-community-patch-v-1`

The source snapshot was built successfully with Maven. Generated
`target/` directories, nested `.git/` directories, runtime logs, user
profiles, and card-art/image payloads are intentionally excluded from source
publication.

## Repository contract

- Stable source snapshots are immutable reference points.
- New work starts from a clone of the latest validated snapshot.
- Changes are made in isolated work branches and promoted only after build,
  verification, rollback, and restore checks pass.
- Client and server artifacts must come from the same XMage 1.4.61V1 build.
- Every operational script must write a transcript to the caller-provided log
  root.
- No workflow uses `/MIR`; destructive synchronization is forbidden.
- Local installation data, preferences, runtime logs, and card images are not
  committed to the public source tree.

Read the mandatory rules in
[`PROJECT-CONTRACT-IMMUTABLE-STABILITY.md`](PROJECT-CONTRACT-IMMUTABLE-STABILITY.md)
and [`RC1_PROTECTION_CONTRACT.md`](RC1_PROTECTION_CONTRACT.md).

## Build

From the complete source directory:

```powershell
mvn clean verify
```

Use the Java/Maven versions documented by the source tree and record the full
build log. Do not build over a protected installation.

## Recovery and user data

The tested Windows recovery clone, launcher/runtime files, accepted settings,
deck catalogue, and image payload are operational artifacts separate from this
public source snapshot. Their manifests and verification records must remain
private unless explicitly approved for publication.

The public repository provides the source, contracts, manifests, documentation,
and safety tooling required to reproduce and audit the build. It is not a
substitute for the tested recovery package.

## License and notices

See [LICENSE](LICENSE) and
[THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md).
