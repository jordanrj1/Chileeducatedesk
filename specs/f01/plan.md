# F01 — Plan

1. **Entorno**: Python compatible con Django LTS vigente (verificar al iniciar) en `.venv`; PostgreSQL local con `pg_trgm` disponible. Requiere autorización para instalar (docs/CONTEXTO.md §0.4).
2. **Proyecto**: `config/` con `settings/{base,local,produccion}.py`; `django-environ` lee `.env`. `LANGUAGE_CODE=es-cl`, `TIME_ZONE=America/Santiago`. Rutas con `pathlib`; `MEDIA_ROOT` configurable fuera del repo.
3. **Apps** en `apps/` (sección 6), registradas pero vacías. `nucleo` contiene layout, vistas de error, `/salud` y dashboard vacío.
4. **Plantillas**: `templates/base.html` (sidebar, header, breadcrumb por bloque, buscador global que apunta a `/buscar`), `403.html`, `404.html`, `login.html`.
5. **Estáticos**: Bootstrap y HTMX descargados una vez a `static/vendor/` (con versión fijada); `whitenoise` los sirve.
6. **Acceso**: `LoginView`/`LogoutView` de Django; `LoginRequiredMiddleware` global (con excepciones `/login`, `/salud`); grupos Gestor y Administrador creados por migración de datos.
7. **Errores**: handlers 403/404 con plantilla propia. Permisos por vista con `permission_required` (403, no redirección, para usuarios ya autenticados).
8. **Arranque**: `iniciar.bat` (activa `.venv`, migra opcionalmente, `waitress-serve`). `.env.example` sin valores reales.
9. **Pruebas** con `pytest-django` (opcional) o el runner de Django.
