# RC1 Protection Contract

Status: **MANDATORY / NON-NEGOTIABLE**  
Applies to: XMage Community Patch RC1 and every future patch, mod, migration, or experiment.

## 1. Stable installation is sacred

The known-good RC1 installation is the source of truth. No future change may overwrite, mutate, or mix with it directly.

The stable installation must remain independently playable through the official launcher exactly as the original base installation: same client/server pairing, launcher flow, configuration, 4 GB memory, 4K UI scaling, stack, edition selector, deck downloader, and all previously validated behavior.

## 2. Every change is isolated

Every mod or experiment must be applied to a separate clone, branch, or checkpoint. The working stable installation is never used as the experiment area.

No files may be copied between unrelated XMage installations unless the file is explicitly classified as user data and its origin is recorded.

Never mix:

- client and server binaries from different builds;
- official, beta, experimental, or community-patch directories;
- launcher configuration from one installation with binaries from another;
- user data with replaceable program files.

## 3. Automatic rollback is mandatory

Before any change:

1. Create a complete recoverable backup.
2. Record the exact base version, client/server build identifiers, launcher version, Java runtime, configuration, and hashes.
3. Create a named checkpoint.

If a change fails any validation, the system must immediately return to the last known-good checkpoint. Debugging must continue in the isolated clone; the stable checkpoint must not remain broken.

A failed experiment may never cause several days of reconstruction. The rollback path must be tested before the experiment is accepted.

## 4. Promotion requires proof

A change may become the next checkpoint only after all of these pass:

- official launcher starts normally;
- client and server are the exact compatible pair;
- local connection works;
- normal AI option is present and playable;
- 4 GB memory configuration is preserved;
- 4K UI scaling is preserved;
- stack and phases remain correct;
- edition selector works;
- deck downloader works;
- existing user data remains recoverable;
- no new configuration, launcher, or path regression appears;
- a real game completes successfully.

Compilation or one successful launch is not sufficient.

## 5. User data is separate

Decks, card images, logs, preferences, and other user data must be stored and migrated separately from replaceable binaries and source. Missing user data must never be treated as permission to rebuild or overwrite the stable program.

## 6. Immutable checkpoint rule

The last validated RC1 checkpoint is immutable. Once accepted, it receives:

- a unique version name;
- a commit or tag;
- a manifest;
- SHA-256 hashes;
- a backup;
- a rollback procedure;
- a test report.

For the current migration, the first protected checkpoint is **RC1.1**. It may only be created after the AI option and all required baseline behavior are restored and validated.

## 7. Stop condition

If the exact source, base build, client/server pair, configuration, or rollback path is uncertain, work stops. No guessed patch, replacement build, beta server, or unrelated installation may be used to continue.

This contract exists to prevent a failed mod from consuming days of recovery work again.

---

# Contrato de protección RC1

Estado: **OBLIGATORIO / NO NEGOCIABLE**

La instalación estable de RC1 es sagrada. Ningún mod futuro puede sobrescribirla, mezclarla ni modificarla directamente.

Todo experimento se realiza en un clon aislado con backup completo, versión identificada, hashes y rollback probado. Si falla una sola prueba, vuelve automáticamente al último checkpoint bueno. La instalación estable nunca queda rota para seguir investigando.

No se aceptará ningún cambio sin verificar launcher oficial, pareja cliente/servidor, conexión local, IA normal, 4 GB, UI 4K, pila, selector de edición, descarga de mazos, datos de usuario y una partida real completa.

Los decks, imágenes, preferencias y logs se separan de binarios y código. No se mezclan instalaciones oficiales, beta, experimentales o comunitarias.

El checkpoint actual solo podrá congelarse como **RC1.1** cuando la pestaña de IA esté restaurada y todo el comportamiento base esté validado. Si la fuente exacta, la pareja cliente/servidor o el rollback no están claros, se detiene el trabajo: no se adivina ni se parchea a ciegas.

## 8. Unlimited experiments, zero impact

The project may test one thousand mods, patches, architectural changes, or AI experiments. Success or failure is acceptable inside the experiment sandbox.

What is forbidden is for any failed experiment to damage, overwrite, contaminate, downgrade, or make unrecoverable the last known-good installation.

For every experiment, the workflow is mandatory:

1. Freeze the current known-good checkpoint.
2. Create an isolated clone or branch.
3. Record the base hash and a complete manifest.
4. Apply exactly one experimental change or one clearly defined change set.
5. Run automated checks and a real-game smoke test.
6. If it fails, mark the experiment **FAILED**, preserve its logs for diagnosis, and discard or quarantine the clone.
7. Restore or continue from the untouched known-good checkpoint.
8. Never repair the stable installation by layering emergency fixes over a failed experiment.

No experiment is allowed to rely on manual memory, undocumented copying, mixed folders, or a supposedly harmless overwrite. A change is not accepted because it compiles, opens once, or appears visually correct. It is accepted only after it passes the full promotion checklist and can be rolled back.

The stable checkpoint is the protected reference. Experiments are disposable; the reference is not.

### Absolute rule

**A failed mod may lose its own sandbox. It may never lose the project, the stable installation, the last checkpoint, or the user's accumulated work.**

## 9. RC1 and RC1.1 are protected shields

**RC1** is the protected original stable baseline. It is never modified by experiments.

**RC1.1** is the protected corrected clone of RC1. It may include only explicitly validated repairs that preserve the RC1 baseline. Once accepted, it is also immutable.

RC1 and RC1.1 are both recovery points and shields. They are not development sandboxes, staging folders, or disposable branches. Every future mod starts from a separate new clone derived from one of these protected checkpoints.

No future experiment may write directly into RC1 or RC1.1. If an experiment succeeds, it is promoted into a new separately named checkpoint only after full validation. If it fails, RC1 and RC1.1 remain untouched.

### Regla definitiva

**RC1 y RC1.1 son blindajes protegidos. Los experimentos viven fuera de ellos.**

## 10. Separate protected branches

When the real checkpoint payloads are present, the repository will maintain separate protected branches:

- `protected/rc1`: immutable original RC1 baseline.
- `protected/rc1.1`: immutable corrected and validated RC1.1 clone.

They must not be merged into one another and must not be used as development branches. `main` may contain documentation and project coordination, but it is not a substitute for either protected checkpoint.

Future experiments use new branches derived from the appropriate protected checkpoint, for example `experiment/<description>`. Promotion to a new protected checkpoint requires the full validation contract.

The protected branches will be created only from real checkpoint commits containing the corresponding verified payload. Empty placeholder branches are not considered protection.

### Regla de ramas

**RC1 y RC1.1 tendrán ramas protegidas separadas cuando sus clones reales estén incorporados.**

## 11. RC1.1 creation gate: AI is mandatory

The current working clone must not be labelled, tagged, branched, or promoted as RC1.1 until the normal AI option has been restored.

RC1.1 acceptance requires visible and playable proof that:

- the normal AI entry is present in the table player-type selector;
- a human player can create a table against the normal AI;
- the AI starts and completes a real game;
- the repaired AI does not regress the RC1 baseline;
- the client and server are the exact pair from the protected clone.

Until every item passes, the working clone remains an experiment and RC1.1 does not exist.

### Puerta de entrada RC1.1

**Sin IA normal restaurada y probada en una partida real, no existe RC1.1 ni puede crearse su blindaje.**

## 12. Centralized logging is mandatory

Every diagnostic, inventory, audit, backup, copy, migration, repair, validation, launch, rollback, or experiment command must write a log to the centralized directory:

`J:\mtg\_LOGS`

No operational action is considered complete without a corresponding log file containing:

- timestamp;
- command or operation name;
- source and destination paths when applicable;
- result and exit code;
- errors or warnings;
- relevant counts, sizes, and hashes.

Logs inside immutable backups must remain inside those backups to preserve their manifests. New operational logs belong in `J:\mtg\_LOGS`.

If a command cannot create its log, the operation must stop before modifying files.

### Regla estricta de logs

**Sin log en `J:\mtg\_LOGS`, no se ejecuta ni se acepta ninguna operación.**


## 13. Version naming is mandatory

Every patch, checkpoint, experiment, and portable package must receive a unique name according to its scope:

- Small corrective patch: incremental numbering such as `1.1`, `1.2`, `1.3`.
- Large architectural change or major checkpoint: major numbering such as `v-1`, `v-2`, `v-3`.
- RC milestones remain explicit: `RC1`, `RC1.1`, and later milestones only when promoted by the contract.
- Never reuse a version name for different contents.
- Never create ambiguous duplicates such as `(1)`, `(2)`, `final-final`, or unnamed replacements.
- The version name must appear in the folder, branch, package, manifest, log, and test report.

A version number describes the scope of the change; it must not be advanced merely to hide an unvalidated failure.

### Regla estricta de nomenclatura

Cada parche, checkpoint, experimento y paquete portable tendrá un nombre único según su alcance:

- Parche pequeño: numeración incremental (`1.1`, `1.2`, `1.3`).
- Cambio grande o checkpoint arquitectónico: versión mayor (`v-1`, `v-2`, `v-3`).
- Hitos RC explícitos: `RC1`, `RC1.1`.
- Nunca se reutilizan nombres ni se crean duplicados ambiguos como `(1)`, `(2)` o `final-final`.
- El nombre debe coincidir en carpeta, rama, paquete, manifest, log y prueba.

**La nomenclatura identifica el alcance real del cambio; no se usa para ocultar un fallo no validado.**
