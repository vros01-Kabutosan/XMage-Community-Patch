# Complete source snapshots

This directory is reserved for complete versioned XMage source snapshots.

It is not valid to publish a stable tag while this directory contains only a
placeholder, a README, a patch, or partial modules. Each protected stable
snapshot must contain the complete source corresponding to the latest stable
portable installation, with every accepted mod already integrated.

The matching release must also provide a double-click Windows installation
package, reproducible build inputs, source/binary manifests, SHA-256 hashes,
configuration/deck restoration instructions, and a verified image
download/rebuild route when images are not bundled.

Future work always clones the newest protected complete snapshot, applies one
isolated change, validates it, integrates it into a new complete snapshot and
seals that snapshot again.
