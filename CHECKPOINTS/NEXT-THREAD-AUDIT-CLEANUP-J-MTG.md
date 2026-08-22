# Siguiente hilo — Auditoría y limpieza integral J:\\mtg

## Punto de partida congelado

- Estado: `RC1.3-BLINDADA-COMPLETE`
- Cierre final: `FINAL_SEAL: PASS`
- Cliente JAR SHA256: `FB65799B1285E21BB06EC439D721CB067FBFEBB7A32CED4E76ED8870E7EB4384`
- Servidor JAR SHA256: `EB269A6EC1477D50759F7439CF018B6B8361E723F6DE08C3B9DB72ECB0EE065D`
- Fundación: `source-foundation-v-1.7-complete-target`
- Fundación SHA: `b974aa865b3a8b1a24df52a2321eacc54f06dfac`
- Paquete maestro: `XMAGE-RC1.3-BLINDADA-COMPLETE-v-8.zip`

## Objetivo de mañana

Auditar y limpiar el cementerio de `J:\\mtg`, estimado en más de 400 GB, conservando exclusivamente material útil, reproducible y trazable.

## Exclusiones absolutas

No tocar, mover, borrar ni sobrescribir:

- `J:\\mtg\\xmage`
- `J:\\mtg\\_ARCHIVO\\PRIVADO-BLINDADO-XMAGE`
- `J:\\mtg\\_ARCHIVO\\RC1.1-COMPLETA-PORTABLE`
- cualquier carpeta o copia identificada como RC1/RC1.1 blindada o estable
- la fuente exacta y el backup certificado de RC1.3

No usar `/MIR`. No borrar durante la primera fase.

## Método obligatorio

### Fase 1 — Auditoría sin cambios

Inventariar rutas, tamaños, fechas, extensiones y duplicados. Generar log en `J:\\mtg\\_LOGS`.

### Fase 2 — Clasificación

Separar:

- conservar: RC1.3, fuente exacta, smoke funcional, scripts válidos, herramientas, manifiestos, documentación y backups buenos;
- revisar: material ambiguo, duplicados con distinta fecha o contenido, versiones no identificadas;
- cuarentena: builds fallidas, scripts obsoletos, duplicados confirmados y temporales.

### Fase 3 — Cuarentena reversible

Mover, nunca borrar directamente, a una carpeta de cuarentena con fecha dentro de `_ARCHIVO`. Registrar origen, destino, tamaño y SHA256 cuando proceda.

### Fase 4 — Verificación

Comprobar que RC1.3 arranca, que el paquete maestro abre, que los scripts y manifests están presentes y que las bases excluidas no han cambiado.

### Fase 5 — Eliminación selectiva

Solo eliminar material confirmado como inútil después de la cuarentena y de una segunda verificación. Todo con log.

## Resultado esperado

Estructura limpia con únicamente:

- instalación RC1.3 funcional;
- fuente exacta;
- smoke y herramientas válidas;
- scripts reproducibles;
- backups certificados;
- logs y manifiestos;
- documentación y paquetes de continuidad.

## Estimación

Entre 4 y 7 horas en condiciones normales; hasta 8–10 horas si hay muchos duplicados ambiguos. La primera noche no se ejecuta ninguna eliminación irreversible.

## Regla de continuidad

El siguiente hilo debe leer este documento antes de ejecutar cualquier operación. Debe comenzar por la auditoría de solo lectura y detenerse ante cualquier ruta que pueda coincidir con una base blindada.
