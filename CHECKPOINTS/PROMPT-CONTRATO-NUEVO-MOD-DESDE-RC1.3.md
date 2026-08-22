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
- paquete de continuidad: `XMAGE-RC1.3-BLINDADA-COMPLETE-v-9.zip`.

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

## Automatización obligatoria

La operación debe entregarse con un lanzador maestro, preferiblemente:

`00-INICIAR-NUEVO-MOD-RC1.3.cmd`

El lanzador debe ejecutar, con log desde el primer segundo:

1. auditoría de Git, Java, Maven y rutas;
2. verificación de rama, tag, SHA y manifiesto;
3. creación del clon aislado;
4. aplicación del mod solo en el clon;
5. compilación y comprobación de `BUILD SUCCESS`;
6. cálculo de SHA256;
7. arranque del servidor y cliente de prueba;
8. carga de la configuración personal mediante enlace de lectura a las imágenes;
9. smoke funcional y visual;
10. generación de logs, manifiesto, paquete reproducible y resultado de gates.

La activación estable debe estar separada en otro script, por ejemplo:

`07-ACTIVAR-CON-BACKUP.ps1`

Nunca debe activarse automáticamente al terminar una compilación.

## Capa adicional de protección: modelo de cero confianza

Antes de modificar nada, el automatizador debe abortar si se cumple cualquiera de estas condiciones:

- el clon está dentro de una ruta protegida;
- la ruta de trabajo no está dentro de `J:\\mtg\\_ARCHIVO\\RC1.1-WORK-PILE-1.1`;
- falta el SHA autorizado o no coincide;
- el manifiesto, los scripts o el JAR no coinciden con sus hashes esperados;
- existe un proceso XMage que pueda bloquear el JAR durante una operación sensible;
- no existe un backup verificable;
- no se puede escribir el log;
- se detecta `/MIR`, `git reset --hard`, borrado recursivo o una ruta destructiva no autorizada.

El sistema debe cumplir además estas reglas:

- empezar siempre en modo `AUDIT/DRY-RUN`;
- usar una lista blanca de rutas y una lista negra explícita de instalaciones blindadas;
- crear un identificador único de ejecución y registrar cada comando, ruta, PID, puerto y hash;
- conservar los logs aunque el cliente no llegue a abrirse;
- verificar el backup antes de cualquier sustitución;
- requerir dos confirmaciones independientes para la activación estable;
- crear un paquete de rollback antes de activar;
- comprobar después de activar el SHA del JAR activo;
- si falla cualquier gate, detenerse y no continuar silenciosamente.

La activación solo podrá continuar si el operador introduce explícitamente:

`CONFIRMAR-ACTIVACION-RC1.3-MOD`

La palabra anterior no debe estar pregrabada en el script ni aceptarse desde un parámetro automático.

## Kit operativo mínimo

Todo nuevo mod debe incluir o reutilizar estos componentes:

- `00-INICIAR-NUEVO-MOD-RC1.3.cmd`;
- `01-AUDITAR-BASE.ps1`;
- `02-CREAR-CLON-AISLADO.ps1`;
- `03-APLICAR-MOD.ps1`;
- `04-COMPILAR-Y-HASH.ps1`;
- `05-SMOKE-VISUAL.ps1`;
- `06-GENERAR-PAQUETE.ps1`;
- `07-ACTIVAR-CON-BACKUP.ps1`;
- `08-ROLLBACK.ps1`;
- contrato, manifiesto SHA256, logs y documentación.

El `.cmd` es únicamente el orquestador. Las comprobaciones de seguridad deben vivir en PowerShell y devolver códigos de salida inequívocos. Ningún error puede ocultarse con `> nul`, `|| exit /b 0` o mensajes que aparenten éxito.
