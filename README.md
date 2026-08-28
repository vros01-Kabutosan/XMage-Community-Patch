# XMage Community Patch — RC1.3

This repository contains an independent community patch for XMage 1.4.61.
It is not an official XMage release and is not affiliated with XMage maintainers
or Wizards of the Coast.

## Estado actual

**BASE ESTABLE SELLADA — RC1.3 v-1.2.12 — PRE-T**

La única base válida para trabajar es:

- Rama: `protected/rc1.3-v-1.2.12`
- Commit de la fuente limpia: `414e463c8bec4913a716dc2840c9002f503f81a7`
- Fuente completa: `source/rc1.1-complete-community`
- POM raíz: `source/rc1.1-complete-community/pom.xml`

La fuente completa y sus recursos están en esa ruta. El indicador T no forma parte
de esta base. [SOURCE-OF-TRUTH.md](https://github.com/vros01-Kabutosan/XMage-Community-Patch/blob/protected/rc1.3-v-1.2.12/SOURCE-OF-TRUTH.md)
es la autoridad para cualquier automatización.

## Descarga de la fuente completa

[Descargar RC1.3 Stable Complete Source](https://github.com/vros01-Kabutosan/XMage-Community-Patch/releases/download/RC1.3-STABLE-SOURCE-v-1.0.7/IMPORT-CURRENT-STABLE-SOURCE-v-1.0.7-20260826-032506-CLEAN.zip)

SHA-256 del asset:
`78b5386c1dd3133f93418fdf930cb652e1bddd4bc4866b59b82aa39d7a4ef5fa`

El asset anterior es la fuente completa validada. Los botones genéricos `Source
code` de GitHub no sustituyen a ese asset.

## Regla permanente para nuevos mods

Cada modificación comienza desde la base canónica exacta. Se crea una sola rama
candidata, se conserva toda la fuente, se compila el reactor completo, se
verifican recursos, hashes, dependencias y arranque, y se prueba en aislamiento.
Solo después se puede activar explícitamente en la instalación.

Si un POM, commit, ruta de fuente, recurso, artefacto, log o comprobación no
coincide, el proceso se detiene sin copiar nada. No se seleccionan ramas por
nombre, antigüedad, fecha, cantidad de commits o por ser `main`, `master`,
`port`, `work`, `feature` o `latest`.

Cuando una candidata supera todos los controles y es aceptada, su fuente completa
pasa a ser la siguiente base canónica. La base anterior queda como recuperación
de emergencia. Solo existe una candidata activa.

## Límites de seguridad

- La instalación activa de Windows se trata como objetivo protegido.
- El desarrollo y las pruebas se realizan en una copia aislada.
- Ningún script de build escribe en la instalación activa antes del preflight,
  backup completo, build completa y activación explícita.
- No se permite sincronización `/MIR`.
- La candidata T anterior está retirada y no es fuente de build ni de activación.
- Las ramas y releases históricas no son fuentes válidas aunque sigan visibles;
  el selector automático debe rechazar cualquier referencia que no sea la base
  canónica indicada arriba.
