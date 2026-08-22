# Contrato para crear un nuevo mod desde XMage RC1.3

## Punto de partida obligatorio

Trabajas sobre XMage Community Patch RC1.3-BLINDADA-COMPLETE, ya cerrada con `FINAL_SEAL: PASS`.

No reconstruyas desde `main`, desde otra rama ni desde una copia antigua.

Usa como referencia:

- repositorio: `vros01-Kabutosan/XMage-Community-Patch`;
- rama: `checkpoint/xmage-stack-v-1.2.9-continuity`;
- fundación: `source-foundation-v-1.7-complete-target`;
- SHA de fundación: `b974aa865b3a8b1a24df52a2321eacc54f06dfac`;
- checkpoint RC1.3: `CHECKPOINTS/CIERRE-DEFINITIVO-RC1.3-20260822-015725.md`;
- paquete de continuidad: `XMAGE-RC1.3-BLINDADA-COMPLETE-v-10.zip`.

## Regla de aislamiento

Nunca modifiques directamente:

- `J:\\mtg\\xmage`;
- `J:\\mtg\\_ARCHIVO\\PRIVADO-BLINDADO-XMAGE`;
- `J:\\mtg\\_ARCHIVO\\RC1.1-COMPLETA-PORTABLE`;
- cualquier RC1/RC1.1 estable o copia blindada.

Crea un clon de trabajo nuevo dentro de:

`J:\\mtg\\_ARCHIVO\\RC1.1-WORK-PILE-1.1`

El nombre de la nueva línea debe ser corto y único, por ejemplo `XMAGE-MOD-NOMBRE-v-1.0-TEST`.

## Antes de tocar código

1. Lee el checkpoint RC1.3 y el manifiesto.
2. Verifica tag y SHA de fundación.
3. Comprueba que el clon de trabajo coincide con la base autorizada.
4. Crea backup del clon de trabajo.
5. Define el objetivo del mod y los archivos exactos que puede modificar.
6. No mezcles el nuevo mod con dado, random IA, PHS u otras líneas cerradas.

## Reglas de operación

- Toda operación, incluso si falla antes de abrir una ventana, debe generar log.
- Los logs deben ir a `J:\\mtg\\_LOGS`.
- No uses `/MIR`.
- No copies imágenes oficiales dentro del clon; usa el enlace de lectura al perfil personal.
- Conserva preferencias HKCU, perfil personal, UI scale 1.5, memoria cliente 4G y `client.java.options`.
- No cambies servidor si el mod es solo de cliente.
- No sustituyas el JAR activo durante desarrollo.
- No hagas varios cambios no relacionados en una misma versión.

## Versionado

El mod nuevo debe tener su propia línea. Usa versiones cortas:

- `v-1.0` para la primera implementación;
- `v-1.0.1` para un parche mínimo;
- `v-1.1` para un cambio funcional mayor.

No uses cadenas interminables ni reutilices `v-1.2.12` de RC1.3.

## Gates obligatorios

Antes de considerar el mod válido:

1. Maven portable Apache Maven 3.9.15 termina con `BUILD SUCCESS` real.
2. Se calcula SHA256 del JAR generado.
3. Servidor aislado y cliente son coherentes.
4. El smoke arranca usando la configuración personal real.
5. Se prueban las funciones afectadas y el juego normal.
6. Se verifica que la pila, counters, selección y resolución siguen funcionando si el mod las toca.
7. Se comprueba que no aparece T-1 ni regresiones visuales anteriores.
8. Se genera manifest SHA256 y log final.
9. Solo después se prepara un paquete de prueba independiente.

## Formato de entrega a la siguiente IA/persona

Entrega siempre:

- nombre y versión del mod;
- base exacta y SHA;
- clon de trabajo utilizado;
- archivos modificados;
- logs;
- SHA256 del JAR;
- resultado Maven;
- resultado smoke;
- problemas conocidos;
- instrucciones de rollback;
- paquete reproducible.

## Regla de publicación

No actives el mod sobre la instalación estable hasta superar todos los gates y obtener autorización explícita para una activación controlada. La RC1.3 sellada permanece intacta como punto de retorno.
