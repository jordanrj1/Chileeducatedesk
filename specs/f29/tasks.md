# F29 — Tareas

- [x] Migración de datos `apps/cuentas/migrations/0004_superadministrador.py`: renombra «Administrador» a «Superadministrador» (lo crea si falta; une si existían ambos), le da todos los permisos y conserva usuarios; reversible. Agrega el permiso `cuentas.respaldar`.
- [x] `asegurar_permisos_superadmin()` en `apps/cuentas/roles.py`, llamada desde `sembrar_roles()` (post_migrate). `reabrir_actividad`, `desactivar_*` y `fusionar_*` quedan en el Superadministrador.
- [x] «Administrador» reemplazado por «Superadministrador» en código, plantillas y textos; `crear_usuario --rol Gestor|Superadministrador`.
- [x] Protección del último Superadministrador activo (`apps/cuentas/protecciones.py`): servidor (desactivar) y formulario (quitar rol), con mensaje y auditoría.
- [x] Auditoría de cuentas, roles, permisos (`permisos_modificados`, `permisos_restablecidos`) y catálogos (`catalogo_agregado`, `catalogo_editado`, `catalogo_activado`, `catalogo_desactivado`).
- [x] Pantallas solo para Superadministrador: Usuarios, Roles y permisos (matriz por módulo y acción, «Restablecer permisos iniciales»), Auditoría, **Respaldos** (lista y «Respaldar ahora», solo POST). El Gestor ve Catálogos (agrega y edita).
- [x] Documentación: `docs/CONTEXTO.md` §3 y §9, manual de uso, `docs/DESPLIEGUE_DOCKER.md`, `docs/COMO_LEVANTAR.md`, `docs/entrega.md`, `levantar.sh` y `levantar.bat`.
- [x] Pruebas: `apps/cuentas/test_f29_superadmin.py`. El fixture `administrador` de `conftest.py` pasó a ser un rol de prueba «Consulta» (solo lectura); el Superadministrador real es `superadmin` / `csa`.
- [ ] Pendiente: añadir los casos al plan de pruebas (`docs/pruebas/PLAN_PRUEBAS.md`, área FP-RP) y aplicar la migración en la base de desarrollo cuando el usuario lo decida.
