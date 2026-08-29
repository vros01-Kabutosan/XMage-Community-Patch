# XMage Community Patch — Contrato de trabajo seguro y simple

**Estado: obligatorio**

Este contrato protege la base y mantiene el trabajo rápido. Se aplica a cualquier persona, IA o script.

## 1. Tres carpetas permanentes

Solo se usan estas rutas:

- Base sellada: `J:\\mtg\\_XMAGE-BASE-SELLADA`
- Taller único: `J:\\mtg\\_XMAGE-TALLER`
- Smoke único: `J:\\mtg\\_XMAGE-SMOKE`

La instalación activa `J:\\mtg\\xmage` nunca es una carpeta de trabajo.

La base sellada se conserva intacta, con su SHA-256 y un backup independiente. El taller se puede modificar y reutilizar para todos los mods.

## 2. Inicio de cada mod

Cada mod empieza desde la base sellada verificada.

Antes de modificar:

- comprobar que la base y el taller corresponden al SHA autorizado;
- comprobar que el taller está limpio;
- crear un backup reversible;
- cerrar XMage, servidor y procesos Java que puedan bloquear archivos;
- crear un log en `J:\\mtg\\_LOGS`;
- verificar que la fuente contiene el árbol completo necesario para compilar y ejecutar el objetivo.

No se crean clones ni carpetas nuevas para cada intento.

## 3. Integridad de la fuente

La base no se considera completa por tener un SHA correcto únicamente.

Antes de modificar, se debe comprobar que el árbol elegido contiene:

- módulos completos de cliente, servidor, común y motor;
- clases reales requeridas por el objetivo;
- `pom.xml` y dependencias coherentes;
- recursos presentes en fuente y en el JAR;
- una única raíz de compilación identificada.

Si el repositorio contiene árboles paralelos, históricos, upstream o parciales, no se deben mezclar automáticamente. Hay que identificar cuál es la fuente completa de ejecución y usarla como origen del taller.

Si se detecta una fuente híbrida, incompleta, una ruta incorrecta o una dependencia ausente:

1. detener la modificación;
2. registrar el diagnóstico;
3. seleccionar automáticamente la fuente completa verificada si existe;
4. reconstruir el taller desde ella;
5. volver a ejecutar el preflight.

Nunca se parchea una fuente incompleta para “hacerla funcionar”.

## 4. Trabajo

El cambio debe ser mínimo y limitarse al objetivo solicitado.

No se modifica la instalación activa, la base sellada, la configuración personal, las imágenes, el servidor, el launcher ni funciones no relacionadas, salvo que el objetivo lo exija expresamente.

No se usan ramas antiguas ni código de intentos fallidos sin demostrar su procedencia.

## 5. Fallo

Si falla el análisis, la compilación o la prueba:

- no se activa nada;
- se conserva el log y el diagnóstico;
- se restaura el taller desde la base sellada;
- no se borra la base ni el backup;
- no se crean ramas o carpetas de residuos.

Un fallo no se repara sobre un taller contaminado: se restaura y se empieza de nuevo desde la misma base.

## 5.1 Aprendizaje y regresión

Cada fallo reproducible del proceso o del mod se convierte en una mejora permanente:

- registrar la causa exacta y el archivo o fase afectada;
- corregir automáticamente el proceso o el código cuando sea seguro hacerlo;
- incrementar la versión de corrección, sin reutilizar la variante fallida;
- añadir una comprobación de regresión para que el mismo fallo no vuelva a bloquear el flujo;
- conservar únicamente el diagnóstico, el parche corregido y la prueba asociada;
- aplicar esta experiencia a todos los mods futuros, manteniendo el cambio mínimo.

La rapidez se obtiene reutilizando comprobaciones y herramientas ya validadas, no saltándose gates de seguridad. Si aparece un muro técnico, se evalúa otra vía compatible con la base antes de abandonar el objetivo.

## 6. Validación obligatoria

Un mod solo se considera válido después de:

1. revisión del diff;
2. compilación completa;
3. auditoría de recursos del JAR;
4. arranque real del cliente en el smoke;
5. prueba funcional relacionada con el objetivo;
6. comprobación de que la instalación activa sigue intacta.

La compilación correcta por sí sola no demuestra que XMage funcione.

## 7. Activación

La activación es siempre la última fase.

Debe:

- crear backup de los archivos que sustituirá;
- copiar solo los artefactos validados;
- comprobar que el destino es único;
- conservar rollback;
- registrar hashes antes y después.

Si cualquier comprobación falla, la activación se cancela automáticamente.

## 8. GitHub

La rama estable y los tags protegidos no se modifican directamente.

El trabajo diario se hace en el taller local. GitHub recibe únicamente el resultado validado, en una rama temporal y mediante PR. No se fusiona automáticamente.

Solo se conserva de cada mod:

- el commit o parche validado;
- el log;
- el backup;
- el resultado de las pruebas.

Las ramas de trabajo fallidas no se convierten en bases ni se acumulan como método de trabajo.

## 9. Nomenclatura

- Mod inicial: `v-1.0.0`
- Corrección: `v-1.0.0.1`
- Siguiente corrección: `v-1.0.0.2`
- Cambio grande: `v-2.0.0`

El mismo número debe aparecer en el mod, script, log, backup, commit y paquete.

## 10. Resultado obligatorio

Cada ejecución termina con uno de estos estados:

- **COMPLETADO**: compilación, smoke y activación correctos.
- **ABORTADO**: se produjo un fallo y no se activó nada.
- **BLOQUEADO**: falta una ruta, herramienta, permiso o comprobación.

Nunca se informa de éxito si no existe una prueba real.

**Regla central: una base sellada completa, un taller reutilizable, un smoke reutilizable, autocorrección de rutas incompletas y cero cementerios de intentos.**
