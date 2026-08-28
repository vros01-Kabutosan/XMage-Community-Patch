# Handoff vigente — XMage RC1.3 v-1.0.0

Estado: BASE ESTABLE SELLADA / PRE-T / SIN CANDIDATA ACTIVA

Este es el único punto de continuidad operativo para el siguiente hilo o para
cualquier otra IA. Leer primero este archivo y después `SOURCE-OF-TRUTH.md`.
Los documentos de continuidad anteriores son históricos y no son instrucciones
de ejecución.

## Identidad canónica

- Repositorio: `vros01-Kabutosan/XMage-Community-Patch`
- Rama canónica: `protected/rc1.3-v-1.2.12`
- Commit actual de la rama canónica: `cdcb0a955353a10f549e125a2b4bccac1c863d8b`
- Commit de la fuente sellada: `414e463c8bec4913a716dc2840c9002f503f81a7`
- Raíz de fuente completa: `source/rc1.1-complete-community`
- POM raíz: `source/rc1.1-complete-community/pom.xml`
- Estado de código: RC1.3 pre-T; la T no está implementada ni activada

Asset único de fuente completa validado:

- Release: `RC1.3-STABLE-SOURCE-v-1.0.7`
- Archivo: `IMPORT-CURRENT-STABLE-SOURCE-v-1.0.7-20260826-032506-CLEAN.zip`
- Entradas: 42.204
- SHA-256: `78b5386c1dd3133f93418fdf930cb652e1bddd4bc4866b59b82aa39d7a4ef5fa`
- Descarga directa: https://github.com/vros01-Kabutosan/XMage-Community-Patch/releases/download/RC1.3-STABLE-SOURCE-v-1.0.7/IMPORT-CURRENT-STABLE-SOURCE-v-1.0.7-20260826-032506-CLEAN.zip

## Estado de las referencias

- `protected/rc1.3-v-1.2.12`: única fuente canónica.
- `port/1.4.61V1-community-patch`: rama de publicación/navegación; no es
  selector de fuente.
- `work/rc1.3-trigger-indicator-v-1.0.0`: neutralizada, apunta a la base
  canónica; no contiene la T.
- `maintenance/canonical-base-clean-v-1.0.0`: neutralizada, apunta a la base
  canónica; no es candidata.
- `work/source-foundation-v-1.6` y
  `work/source-foundation-v-1.7-complete-target`: referencias históricas
  bloqueadas; nunca usarlas como base.
- No existe candidata activa y no hay PR abierta.

## Verificaciones de la base

- POM raíz presente.
- Fuente completa y recursos presentes.
- Los tres archivos Java de la base conservan sus blobs validados:
  - `PermanentView.java`: `6f3684e8e12d873d85a07253c95213cfb54fb7df`
  - `CardPanelRenderModeImage.java`: `e271704536d53d47212e9ed92a6c7b47ac0b04f5`
  - `CardPanelRenderModeMTGO.java`: `c0851b79b5e568179ef4f433e5c4fe95d09c7202`
- La base no contiene lógica `isTriggeredAbility`,
  `triggerSourceId` ni `triggerActive`.
- No contiene `.class`, `.pyc`, carpetas Maven `target` ni logs de ejecución.
- Los logs conservados bajo `CHECKPOINTS/LOGS` son evidencia histórica
  intencionada, no artefactos de build.

## Protocolo fijo para el próximo mod

1. Resolver exclusivamente la rama canónica, su commit, la raíz de fuente y el
   POM juntos.
2. Si uno no coincide, detenerse sin compilar ni copiar.
3. Crear una sola candidata con nomenclatura nueva y exacta.
4. Trabajar en un clon aislado de la fuente completa; nunca desde un binario,
   una instalación local, un parche parcial o una build antigua.
5. Mantener todos los recursos y la configuración necesaria; no usar
   sincronización `/MIR`.
6. Registrar absolutamente cada paso en
   `J:\mtg\_LOGS\<NOMBRE-FASE>_<timestamp>\`; ningún proceso silencioso.
7. Compilar el reactor completo con JDK 17 y Maven validado, capturando toda la
   salida.
8. Verificar fuente, recursos, dependencias, artefactos y SHA-256.
9. Ejecutar cliente y servidor en aislamiento y realizar smoke visual.
10. Crear backup completo fechado y comprobar rollback.
11. Solo con todas las puertas superadas y aceptación humana se puede activar.
12. Tras la aceptación, la fuente completa de esa generación pasa a ser la
    siguiente base canónica; esta base anterior queda como emergencia.

La instalación activa `J:\mtg\xmage` permanece fuera del repositorio y no debe
tocarse hasta el final explícito del protocolo. La T retirada no puede
reintroducirse desde ninguna referencia histórica.

## Limitación de protección conocida

La conexión disponible puede leer y escribir contenido, refs y PRs, pero no
ofrece la operación para crear o editar rulesets de protección de GitHub. La
rama `port/1.4.61V1-community-patch` sí aparece protegida; GitHub todavía
reporta `protected/rc1.3-v-1.2.12` como no protegida técnicamente aunque su
contrato la designa como única fuente. Hasta aplicar esa regla en GitHub, se
debe considerar obligatorio el control de commit, POM, ruta y SHA anterior.
