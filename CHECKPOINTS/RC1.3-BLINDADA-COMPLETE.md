# XMage Community Patch — RC1.3-BLINDADA-COMPLETE

Estado congelado para continuidad.

## Identidad

- Repositorio: `vros01-Kabutosan/XMage-Community-Patch`
- Rama de continuidad: `checkpoint/xmage-stack-v-1.2.9-continuity`
- Fundación obligatoria: `source-foundation-v-1.7-complete-target`
- SHA de fundación autorizado: `b974aa865b3a8b1a24df52a2321eacc54f06dfac`
- Línea funcional cerrada: `v-1.2.12`
- Corrección de recursos UI: `v-1.2.12.3`
- Hito: `RC1.3-BLINDADA-COMPLETE`

## Resultado funcional aceptado

La evidencia visual final confirma:

- pila flotante centrada;
- carta superior completa;
- orden LIFO operativo;
- selección e interacción de objetos conservadas;
- etiquetas fuera de la carta;
- `NEXT` verde, compacto y legible;
- ausencia de `T-1`;
- funcionamiento del juego normal.

## Defectos cosméticos aceptados

Se congelan como deuda visual no bloqueante:

1. el texto de la guía puede quedar ligeramente recortado en determinadas dimensiones;
2. el botón `Done` puede quedar parcialmente oculto por la franja de fase.

No se abre otro parche por estos dos detalles en esta etapa. La corrección futura deberá usar el siguiente número corto de versión y partir de este checkpoint.

## Evidencia y trazabilidad

- Evidencia visual final: `evidence/smoke-visual-final-v-1.2.12.3.png`
- Evidencia visual anterior: `evidence/smoke-visual-v-1.2.12.png`
- Logs de compilación, servidor, smoke, activación, publicación de fuente y cliente: `logs/`
- Paquetes y kits reproducibles: `packages/`
- Activación controlada registrada en `logs/activar-xmage-stack-v-1.2.12.1.log`
- Publicación de fuente exacta registrada en `logs/publicar-fuente-exacta-v-1.2.12.1-20260822-005744.log`

## Blindaje respetado

- No se usó `/MIR`.
- No se copiaron imágenes oficiales dentro del clon.
- La configuración personal y las preferencias HKCU se conservaron.
- La activación creó backup antes de sustituir el JAR.
- Las bases estables blindadas no forman parte de este paquete ni deben modificarse.
- Toda futura operación debe generar log en `J:\mtg\_LOGS`.

## SHA256

La activación certificada de `v-1.2.12.1` registró el JAR:

`743D1FC07B2E1453B82F6BD5A97745A37822716E271922DD75AAE57B12A38E63`

La reparación posterior de recursos `v-1.2.12.3` cambia el JAR. Por tanto, ese SHA no debe reutilizarse como SHA final del estado reparado. El SHA final posterior a la reparación debe calcularse en la máquina Windows mediante el validador de continuidad antes de cualquier nueva modificación o publicación binaria.

## Regla de continuidad

La siguiente IA o persona debe leer este documento y `docs/CONTINUITY-INSTRUCTIONS-RC1.3.md` antes de tocar nada. No debe reconstruir desde `main`, no debe pedir de nuevo los materiales archivados y no debe modificar ninguna base blindada.
