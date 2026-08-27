# XMage RC1.3 — Base operativa v-1.0.1

## Identidad de la base

- Repositorio: `vros01-Kabutosan/XMage-Community-Patch`
- Rama candidata verificada: `work/rc1.3-v-1.2.13-trigger-indicator`
- Commit mínimo que contiene la corrección de recursos: `50c58509d561be356fede9d481094282210bbcd5`
- Fuente completa que se compila: `source/rc1.1-complete-community`
- Rama estable protegida: `port/1.4.61V1-community-patch`
- Pull Request de trabajo: `https://github.com/vros01-Kabutosan/XMage-Community-Patch/pull/6`

La rama estable y `J:\mtg\xmage` no se deben modificar manualmente. Toda activación se hace en staging, con backup previo y rollback automático.

## Corrección incorporada

La causa del último fallo fue que la fuente no contenía `Mage.Client/src/main/resources/menu`, aunque `MageFrame` carga esos iconos al arrancar. Se incorporaron los nueve recursos oficiales:

`about.png`, `collection.png`, `connect.png`, `deck_editor.png`, `feedback.png`, `images.png`, `memory.png`, `preferences.png` y `symbol.png`.

El instalador también conserva recursos de una JAR histórica válida como salvaguarda. Nunca usa como origen una JAR actual que no contenga, como mínimo, `menu/preferences.png` y `menu/connect.png`.

## Herramientas que funcionan y descarga automática

El instalador detecta primero las herramientas locales y, si faltan, las descarga en `%TEMP%\xmage-tools`:

- Git / MinGit x64: API oficial de `git-for-windows`.
- JDK 17 Temurin: API oficial de Adoptium.
- Maven 3.8.8: distribución oficial de Apache Maven.

No se depende de que el operador conozca rutas, carpetas, PATH o comandos. Las rutas usadas y las versiones detectadas quedan registradas en cada ejecución.

## Archivo oficial de operación

Ejecutar únicamente `ACTIVAR-T-RC1.3-v-1.0.1.cmd` con XMage cerrado. El archivo:

1. clona la candidata indicada;
2. comprueba la fuente y el commit mínimo;
3. localiza o descarga Git, JDK 17 y Maven 3.8.8;
4. compila `Mage.Client` y dependencias;
5. identifica de forma unívoca las JAR activas;
6. crea backup antes de tocar la instalación;
7. incorpora y verifica los recursos gráficos;
8. instala cliente y common;
9. compara SHA-256 de origen y destino;
10. restaura el backup si cualquier paso posterior al backup falla.

El lanzador de diagnóstico `ARRANCAR-CLIENTE-T-RC1.3-v-1.0.1.cmd` solo se usa si el lanzador habitual no abre el cliente. Sus logs capturan Java, stdout y stderr.

## Rutas de trabajo en Windows

- Instalación activa: `J:\mtg\xmage`
- Logs: `J:\mtg\_LOGS\activate_T_RC1.3-v-1.0.1_*`
- Staging: `J:\mtg\_SMOKE\activate_T_RC1.3-v-1.0.1_*`
- Archivo de emergencia: `J:\mtg\_ARCHIVO\trigger-indicator-before-activation_*`

## Protocolo de cada nueva base

Cada nueva modificación debe crear una versión nueva (`v-1.0.2`, `v-1.0.3`, etc.), una rama candidata nueva y un backup fechado. Solo después de compilar, verificar recursos, arrancar y probar visualmente se convierte en la siguiente base. Las bases anteriores se conservan como archivo de emergencia y no se usan como fuente de trabajo normal.

Ninguna IA debe elegir una rama por parecido de nombre. Debe leer primero este inventario, comprobar la rama candidata y el commit, y trabajar únicamente desde la base más reciente verificada.

## Recuperación de emergencia

Si una activación falla, el instalador debe terminar como `ACTIVACION FALLIDA` y restaurar automáticamente los dos JAR desde el backup de esa ejecución. Si se necesita una restauración manual, se utiliza exclusivamente la carpeta fechada más reciente que haya sido declarada válida en el log; nunca se copia desde una rama antigua ni desde un staging sin verificar.

## Estado de seguridad

- No hacer merge automático desde este inventario.
- No hacer force-push sobre la rama estable.
- No borrar backups hasta que la nueva base haya sido probada.
- No declarar una activación exitosa sin log, SHA coincidentes y confirmación de arranque.
