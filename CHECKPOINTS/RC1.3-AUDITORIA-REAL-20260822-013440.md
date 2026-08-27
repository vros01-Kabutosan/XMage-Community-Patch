# Auditoría real de activación y fuente

## Resultado

Los dos logs recibidos pasan sus gates:

- fuente exacta exportada y verificada;
- manifiesto de fuente generado;
- backup de activación creado;
- SHA de origen y destino idénticos;
- no se copiaron imágenes, configuración ni perfiles;
- no se utilizó `/MIR`.

## SHA verificado

`743D1FC07B2E1453B82F6BD5A97745A37822716E271922DD75AAE57B12A38E63`

## Rutas confirmadas

- Fuente exacta: `J:\mtg\_ARCHIVO\RC1.1-WORK-PILE-1.1\XMAGE-SOURCE-EXACT-v-1.2.12`
- Manifiesto fuente: `SOURCE-MANIFEST-SHA256-v-1.2.12.txt`
- Backup: `J:\mtg\_ARCHIVO\STACK-ACTIVATION-BACKUP-v-1.2.12-20260822-013417`
- Log de fuente: `J:\mtg\_LOGS\publicar-fuente-exacta-v-1.2.12-20260822-013440.log`

## Estado del cierre

Estos logs certifican la activación y la fuente, pero no contienen el resultado del cierre final automatizado `FINAL_SEAL: PASS`. El último gate sigue siendo ejecutar el cierre final sobre el JAR instalado, porque ese proceso calcula el SHA del estado real que queda en la máquina.
