# Preguntas abiertas (bloquean o afectan F01–F06)

## Para el usuario (programador)
1. ¿Autorizas instalar Python (versión compatible con Django LTS) y PostgreSQL en esta Mac? Hoy hay Python 3.9.6 y no hay PostgreSQL ni Homebrew.
2. ¿Se desarrolla en esta Mac y se prueba en Windows al final? Los `.bat` no se pueden probar aquí.
3. ¿Tienes el Excel de requerimientos con las filas en amarillo? No está en el repo ni lo encontré en el disco. Lo necesito antes de F16, F18, F19.
4. ¿Tienes el archivo oficial de regiones, provincias y comunas (códigos CUT)? Hace falta en la carga de territorio (F03/F04).

## Para Claudio / Manuel ([V], docs/CONTEXTO.md §4)
- **#5 Acceso**: ¿solo el equipo donde corre o desde la red de la Fundación (y celulares)? Afecta F01 (`ALLOWED_HOSTS`, interfaz de waitress).
- **#1 Administrador después del 30-11**: ¿quién? Afecta F03 (creación de usuarios) y F21 (traspaso).
- **#9 Contraseña**: ¿basta con que la restablezca el Administrador?
- **#2 Menores de edad**: qué datos se guardan, autorización del apoderado y plazo. Afecta F04 (campos de persona).
- **#7 Proyecto/campaña**: ¿agrupador opcional? Afecta F07/F09, no F01–F06.

## Contradicciones entre docs/CONTEXTO.md y docs/oficiales
- **Estado "cerrada"**: docs/CONTEXTO.md §3 dice que no existe; doc 05 (Nivel 1) habla de "actividad cerrada" y RF-24/doc 03 de "registro cerrado". Propuesta: mantener *realizada* + resultados, y tratar "cerrar" como acción, no estado. Confirmar.
- **"Zona"**: los docs 03/04 usan "zona" (actividad, lugar, matching); docs/CONTEXTO.md la reemplaza por territorio jerárquico (región→sector) [P]. Confirmar que "zona" = comuna/sector.
- **Documentos**: doc 04 los asocia solo a actividad; docs/CONTEXTO.md agrega persona/organización [P].
- **Administrador**: doc 02 lo marca "si se separa la función"; docs/CONTEXTO.md lo da por decidido. Coherente, pero depende de #1.
- **Doc 01 vs 03**: matching es MVP en ambos; el tutor pudo marcarlo en amarillo [V#8].
