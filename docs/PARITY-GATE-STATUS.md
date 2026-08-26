# Parity gate status

This repository must not advertise a stable reinstallable release until the complete source tree and the active runtime payload have been proven equivalent.

Current verification status:

- The isolated RC1.1 source build completes successfully.
- The current Superior Spider-Man implementation is present once in the isolated source and compiles successfully.
- A read-only provenance scan analyzed 20 copies of `mage-client-1.4.61.jar`.
- Three copies are byte-for-byte identical to the active client JAR. They are valid recovery references for the active client payload.
- No non-identical candidate reproduces all nine active client reference entries: GamePanel, GamePanel$26, Cards, CardPanelRenderModeImage, CardPanelRenderModeImage$1, CardRenderer, CardPluginImpl, MageActionCallback, and the runtime icon.
- The closest non-identical client candidate matches 6 of 9 reference entries but differs in GamePanel, GamePanel$26, and CardPluginImpl.
- The current isolated source build matches 0 of the 9 reference entries and is therefore not the exact active client source/build.
- The active installation is consequently a hybrid generation from the evidence currently available; the source snapshot and the active client binary must not be silently treated as interchangeable.
- The uploaded `source.zip`-type runtime archive contains config, plugins, and lib payloads but no complete Java source tree. It cannot serve as the repository source clone.
- Card artwork/images remain outside source parity scope. Non-artwork runtime resources remain in scope.

Release rule:

1. Keep the protected stable base unchanged.
2. Preserve the exact active runtime payload as a separately verified recovery reference.
3. Resolve or reconstruct the client source provenance in an isolated workspace.
4. Rebuild and compare server and client payloads, including the current Superior Spider-Man code.
5. Validate installation, launcher, Java options, memory, and client/server pairing.
6. Only then create the complete source-plus-runtime release snapshot, tag it, and protect it.

Until all gates pass, the work branch and its pull request are investigative only; they are not the stable clone.
