# Protocolo de sellado final RC1.3

El paquete contiene `final-close/CIERRE-FINAL-RC1.3.cmd`.

Ejecutarlo desde Windows después de extraer el paquete. El script no usa `/MIR`, no modifica las bases blindadas y solo crea el acta dentro de:

`J:\mtg\_ARCHIVO\RC1.1-WORK-PILE-1.1\XMAGE-RC1.3-CLOSURE`

El log queda en:

`J:\mtg\_LOGS\CIERRE-FINAL-RC1.3-<timestamp>.log`

El cierre solo imprime `FINAL_SEAL: PASS` si encuentra y verifica:

- JAR de cliente y servidor 1.4.61;
- perfil personal `J:\mtg\xmage\client`;
- exportación de la fuente exacta;
- backup de activación;
- backup de reparación de recursos;
- recursos UI dentro del JAR, incluido `background/background.png`;
- SHA256 del cliente y del servidor;
- manifiesto y acta final.

Si falla un requisito, no sella nada y deja el motivo en el log. El SHA del JAR posterior a la reparación no debe sustituirse por el SHA histórico de v-1.2.12.1.
