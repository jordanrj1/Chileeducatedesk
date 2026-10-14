# Pruebas de la auditoría

Fecha: 14-10-2026. Equipo: Mac de desarrollo; el destino es Windows. Rama `auditoria/documentacion`, que parte de `main` en el commit `bb8307d`.

## 1. Entorno

| Revisión | Resultado |
|---|---|
| Python | 3.12.15, en el entorno virtual `.venv` |
| Django | 5.2.18, la versión con soporte largo |
| PostgreSQL | 17, responde en `127.0.0.1:5433` |
| `.env` | Existe. También está `.env.example`. |
| Dependencias (`requirements.txt`) | Solo las de docs/CONTEXTO.md §5: Django, psycopg, django-simple-history, django-htmx, whitenoise, waitress, openpyxl, django-environ y pytest-django |

## 2. Comprobaciones del proyecto

| Comando | Resultado |
|---|---|
| `python manage.py check` | Sin problemas |
| `python manage.py makemigrations --check` | Sin cambios pendientes en los modelos |
| `python manage.py showmigrations` | 0 migraciones sin aplicar |
| `python manage.py check --deploy --settings=config.settings.produccion` | 4 avisos sobre HTTPS (ver abajo) |
| `python -m pytest -q` | **546 pruebas, 0 fallas** (1 min 54 s) |
| Recorrido automático de pantallas (`scripts/revision/recorrer.py`) | **290 páginas** revisadas como Gestor y como Administrador; **0 errores**. Solo hace GET, no modifica datos. |
| Servidor (`iniciar.sh` → waitress) | Responde en `http://127.0.0.1:8000`; `/login` da 200 |

Los 4 avisos de `check --deploy` (W004, W008, W012 y W016) piden cookies seguras y redirección a HTTPS. Para un sistema que solo corre en el propio equipo por HTTP son esperables. Habría que activarlos si algún día se publica en internet; `docs/entrega.md` ya lo dice.

## 3. Recorrido de 15 minutos (Procesos §8)

**Cómo se hizo.** Con un guion que usa el mismo código del sistema, contra la base de desarrollo, como lo haría un navegador: formularios reales, buscador de organizaciones y permisos reales.
- Todo ocurrió **dentro de una transacción que se deshizo al final**. La base quedó igual que antes (comprobado).
- Los archivos subidos fueron a una carpeta temporal fuera del repositorio.
- Los datos son ficticios: «Ana María Pérez Ficticia», «Biblioteca Ficticia».
- La contraseña se pasó por una variable de entorno y no quedó escrita en ningún archivo.

| # | Paso | Resultado | Detalle |
|---|---|---|---|
| 1 | Ingresar como Gestor | Funcionó | Lleva al Panel |
| 2 | Crear una actividad solo con nombre y tipo | Funcionó | Queda en estado **Pendiente** |
| 3 | Agregar una persona que ya existe | Funcionó | Repetirla con el mismo rol **avisa** y no la duplica (respuesta 400 con mensaje) |
| 4 | Agregar una persona nueva con solo el nombre | Funcionó | Queda creada y agregada a la actividad |
| 5 | Agregar una organización y cómo participó | Funcionó | Se elige con el buscador (se escribe «universidad»); tipo de intervención «Aporta personas» |
| 6 | Programar una fecha con un lugar nuevo | Funcionó | «+ Crear lugar» desde la agenda. **Pide nombre, tipo y comuna; no ofrece sector** (ver hallazgos) |
| 7 | Reprogramar con motivo; la anterior visible | Funcionó | 2 versiones; el motivo aparece en la pestaña Agenda |
| 8 | Registrar una llamada con próxima acción | Funcionó | «Enviar el listado» aparece en el Panel |
| 9 | Subir un documento | Funcionó | PDF aceptado. Un `.exe` se **rechaza** con mensaje |
| 10 | La persona muestra la actividad en su ficha | Funcionó | Pestaña Participaciones |
| 11 | Marcar asistencia | Funcionó | 2 asistentes guardados en la base |
| 12 | Finalizar | Funcionó | Sin resultado **no deja** finalizar y explica qué falta; con resultado queda **Realizada** |
| 13 | Buscar sin tilde | Funcionó | «maria perez» encuentra «Ana María Pérez Ficticia» |
| 14 | El Gestor no ve Administración | Funcionó | No tiene el enlace en el menú y la dirección directa da **403**. El Administrador sí entra. |
| 15 | Cerrar sesión y pulsar Atrás | **Parcial** | Tras cerrar sesión, abrir una página privada vuelve al ingreso. **El botón Atrás del navegador no se pudo probar** (ver abajo). |

**Resultado: 18 de 18 comprobaciones del guion pasaron.** El paso 15 queda parcial por lo que no se pudo probar.

## 4. Lo que no se pudo probar

| Qué | Por qué | Cómo probarlo |
|---|---|---|
| **Atrás del navegador después de cerrar sesión** | Requiere un navegador real. Las páginas privadas **no envían** la cabecera que prohíbe guardarlas (`Cache-Control: no-store`), así que es **probable** que Atrás muestre la última página que quedó en la memoria del navegador. No se pueden usar sus botones: cualquier clic pide ingresar. | Ingresar, abrir una persona, cerrar sesión y pulsar Atrás. Si se ve la ficha, hay que corregirlo (una línea de configuración). |
| `iniciar.bat` y `respaldar.bat` | Son de Windows y el equipo de pruebas es Mac. Se probaron sus equivalentes `iniciar.sh` y `respaldar.sh`, y el comando `respaldar` tiene prueba automática (`nucleo/test_comandos.py:34`). | En el computador de la Fundación, seguir `docs/COMO_LEVANTAR.md`. |
| Restaurar un respaldo | No se repitió en esta auditoría. `docs/entrega.md` registra que se probó el 12-10-2026. | Procedimiento en `docs/entrega.md`, sección Respaldos. |
| Cierre de sesión por inactividad | Hay que esperar el tiempo configurado (60 minutos). | Poner `SESION_SEGUNDOS=60` en `.env`, reiniciar y esperar un minuto. |
| Cargar el territorio oficial | Falta el archivo CUT. | `python manage.py cargar_territorio comunas.csv` |
| Uso real por Claudio | Esta auditoría no reemplaza que Claudio lo use. | Recorrido de 15 minutos con él, en pantalla (`docs/auditoria/HISTORIAS_Y_PRUEBAS.md`). |

## 5. Hallazgos del recorrido

1. **Crear un lugar desde la agenda no permite elegir el sector.** El paso 2 de P5 dice «con comuna y sector». Se puede agregar el sector después, editando el lugar.
2. **Crear un lugar rápido exige el tipo de lugar.** Es un dato más de lo mínimo (nombre y comuna).
3. **Programar sin lugar se puede**, y la actividad queda planificada. Es lo flexible que pide P5 paso 5. El lugar (o la modalidad virtual) se exige recién al **confirmar**.
4. **La asistencia y el botón Finalizar solo se habilitan desde el día de la actividad** (`nucleo/test_escenarios_catalogo.py:537`). Una actividad programada para la próxima semana no se puede cerrar hoy. Es razonable, pero es una restricción que conviene conocer.
5. **La base de desarrollo solo tiene datos de demostración.** Hay «Región Demo», «Comuna Demo» y ningún sector, porque falta el archivo oficial CUT. Al probar a mano, la cascada de dirección ofrecerá una sola comuna.
6. En la base de demostración no hay ninguna persona con tilde para probar la búsqueda. El paso 4 del recorrido crea una («Ana María»), y luego el paso 13 la busca.
