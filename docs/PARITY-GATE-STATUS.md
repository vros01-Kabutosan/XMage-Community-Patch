# Parity gate status

This repository must not advertise a stable reinstallable release until the complete source tree and the active runtime payload have been proven equivalent.

Current verification status:

- The isolated RC1.1 source build completes successfully.
- The server-side card-set classes match the active installation's server generation.
- The current Superior Spider-Man implementation is present once in the isolated source and compiles successfully.
- The client/UI payload is not yet equivalent to the active installation. Differences remain in the game panel, card panel/rendering components, plugin adapter classes, and a runtime UI icon.
- The client and server card-set payloads are currently from different generations and must not be silently synchronized.
- Card artwork/images are outside the source parity scope. Non-artwork runtime resources remain in scope.

Release rule:

1. Keep the protected stable base unchanged.
2. Resolve the client source/binary provenance in an isolated workspace.
3. Rebuild and compare server and client payloads.
4. Validate installation and launcher behavior.
5. Only then create the complete source-plus-runtime release snapshot, tag it, and protect it.

Until all gates pass, the work branch and its pull request are investigative only; they are not the stable clone.
