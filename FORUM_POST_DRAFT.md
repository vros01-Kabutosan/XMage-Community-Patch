# Draft — Community forum announcement

## Suggested title

**XMage Community Patch 1.4.60V3 RC1 — testers wanted (Windows, unofficial community build)**

## English

Hello everyone,

We have published **XMage Community Patch 1.4.60V3 RC1**, an **unofficial community Release Candidate for Windows** built on top of XMage.

The goal is to gather real-world testing, document reproducible problems and identify improvements that may be worth proposing back to upstream XMage as focused contributions.

This project is **not an official XMage release** and is not affiliated with or endorsed by the official maintainers.

Repository:
https://github.com/vros01-Kabutosan/XMage-Community-Patch

RC1 release:
https://github.com/vros01-Kabutosan/XMage-Community-Patch/releases/tag/v1.4.60V3-community-patch-rc1

For most Windows users, the recommended download is **Complete Windows**.

### Main areas included in RC1
- long-session graphical stability work
- 1440p / 4K usability improvements
- printing/art selection in the deck workflow
- tested multipart-card, token/emblem and cache/image fixes
- selected card/data/legalities fixes
- integrated deck downloading for Standard, Pioneer and Modern
- duplicate detection, logs, safe cancellation and resume behavior
- matching Client / Server / Complete packages
- SHA-256 checksums and audit documentation

### Validated baseline
- Windows 10/11 x64
- Java 8u201 x64
- matching client/server build `2026-08-10 02:05`
- `-Xmx4G` recommended for the client on systems with enough RAM

### What we need testers to check
- long sessions without battlefield duplication/repaint problems
- 1440p/4K menus, dialogs and Deck Editor usability
- printing/art selection persistence after saving/reloading a deck
- multipart-card images in relevant game zones
- token/emblem behavior after cache refresh
- Standard/Pioneer/Modern deck downloader behavior
- cancellation/resume
- memory behavior during long sessions

Testing guide:
https://github.com/vros01-Kabutosan/XMage-Community-Patch/blob/main/TESTING.md

RC1 testing tracker:
https://github.com/vros01-Kabutosan/XMage-Community-Patch/issues/1

If you find a reproducible problem, please include Windows version, Java version, display resolution/scaling, package used, exact reproduction steps, expected/actual behavior and an anonymized log excerpt where relevant.

Please do not post credentials, cookies or private paths in logs/screenshots.

Upstream XMage remains the original project and base of this work:
https://github.com/magefree/mage

Thank you to anyone willing to test RC1 and report reproducible results.

---

## Español

Hola a todos,

Hemos publicado **XMage Community Patch 1.4.60V3 RC1**, una **Release Candidate comunitaria no oficial para Windows** construida sobre XMage.

El objetivo es conseguir pruebas reales en más equipos, documentar fallos reproducibles e identificar mejoras que puedan merecer la pena proponer posteriormente al XMage oficial como contribuciones independientes.

Este proyecto **no es una versión oficial de XMage** ni está afiliado o respaldado por sus mantenedores oficiales.

Repositorio:
https://github.com/vros01-Kabutosan/XMage-Community-Patch

Release RC1:
https://github.com/vros01-Kabutosan/XMage-Community-Patch/releases/tag/v1.4.60V3-community-patch-rc1

Para la mayoría de usuarios de Windows se recomienda descargar **Complete Windows**.

### Principales áreas incluidas en RC1
- trabajo sobre estabilidad gráfica en sesiones largas
- mejoras de uso en 1440p / 4K
- selector de edición/ilustración dentro del flujo del Deck Editor
- correcciones probadas de cartas multiparte, fichas/emblemas y caché/imágenes
- determinadas correcciones de cartas/datos/legalidad
- descarga integrada de mazos Standard, Pioneer y Modern
- detección de duplicados, logs, cancelación segura y reanudación
- paquetes Client / Server / Complete emparejados
- hashes SHA-256 y documentación de auditoría

### Entorno validado
- Windows 10/11 x64
- Java 8u201 x64
- cliente/servidor con build `2026-08-10 02:05`
- `-Xmx4G` recomendado para el cliente en equipos con RAM suficiente

### Qué necesitamos que pruebe la comunidad
- sesiones largas sin duplicaciones o problemas de repintado del campo
- menús, diálogos y Deck Editor en 1440p/4K
- persistencia del selector de edición tras guardar y recargar el mazo
- imágenes de cartas multiparte en las zonas correspondientes
- fichas/emblemas después de limpiar/refrescar caché
- descargador de Standard/Pioneer/Modern
- cancelación y reanudación
- comportamiento de memoria en sesiones largas

Guía de pruebas:
https://github.com/vros01-Kabutosan/XMage-Community-Patch/blob/main/TESTING.md

Seguimiento público de pruebas RC1:
https://github.com/vros01-Kabutosan/XMage-Community-Patch/issues/1

Si encuentras un fallo reproducible, incluye versión de Windows, versión de Java, resolución/escalado, paquete utilizado, pasos exactos, resultado esperado/real y un fragmento de log anonimizado cuando corresponda.

No publiques credenciales, cookies ni rutas privadas en logs o capturas.

XMage oficial sigue siendo el proyecto original y la base de este trabajo:
https://github.com/magefree/mage

Gracias a cualquiera que quiera probar la RC1 y aportar resultados reproducibles.
