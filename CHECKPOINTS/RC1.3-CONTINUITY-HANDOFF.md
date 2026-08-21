# Continuidad XMage desde RC1.3

## Orden obligatorio

1. Leer `CHECKPOINT-RC1.3-BLINDADA-COMPLETE.md`.
2. Leer `docs/CHECKPOINT-MAESTRO-v-1.2.12.md`, `docs/ACTIVATION-RESULT-v-1.2.12.1.txt` y `docs/AUDITORIA-FINAL-v-1.2.12.txt`.
3. Revisar primero los logs de `logs/`; identificar el primer fallo real antes de crear una versión nueva.
4. Verificar la fundación por tag y SHA autorizados.
5. Trabajar únicamente en un clon aislado bajo `J:\mtg\_ARCHIVO\RC1.1-WORK-PILE-1.1`.
6. Mantener la configuración personal, el perfil `J:\mtg\xmage\client`, HKCU, UI scale 1.5, memoria 4G y las imágenes por enlace de lectura.
7. Compilar con Maven portable Apache Maven 3.9.15 y exigir `BUILD SUCCESS` real.
8. Calcular SHA256 del JAR final y guardarlo en `J:\mtg\_LOGS`.
9. Ejecutar servidor aislado y smoke visual con puerto libre confirmado.
10. Verificar que el cliente carga el JAR generado, la configuración personal y la misma versión de servidor.
11. Probar pila de 1, 2, 3 y más objetos, counters con varios objetivos, selección, interacción y orden LIFO.
12. Solo después de todos los gates preparar activación controlada con backup.

## Prohibiciones

- No usar `main` como base.
- No usar `/MIR`.
- No tocar, borrar, limpiar ni sobrescribir las bases estables blindadas.
- No copiar imágenes oficiales dentro del clon.
- No mezclar cambios de pila con IA, dado, selector u otras líneas cerradas.
- No crear nomenclaturas encadenadas: usar el siguiente número corto, por ejemplo `v-1.2.13`.

## Estado conocido

La funcionalidad está aceptada. Persisten únicamente los dos detalles cosméticos descritos en el checkpoint: recorte ligero de texto y del botón `Done` según la geometría de la ventana. No son motivo para reabrir esta etapa.

## Material disponible

Este paquete contiene los logs, paquetes de interacción, kits de activación, publicación de fuente, reparación de recursos y evidencias visuales. El material exacto de continuidad queda accesible sin depender de adjuntos de una conversación concreta.
