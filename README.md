# AgroTrace · Seguridad aplicada (Semana 15)

[![Repo oficial](https://img.shields.io/badge/GitHub-Agrotrace__lab15-1d6b3c?logo=github)](https://github.com/carlosjunco2025/Agrotrace_lab15)
[![Django](https://img.shields.io/badge/Django-6.1-092E20?logo=django&logoColor=white)](https://www.djangoproject.com/)
[![DRF](https://img.shields.io/badge/DRF-TokenAuth-ff1709?logo=djangorestframework)](https://www.django-rest-framework.org/)
[![React](https://img.shields.io/badge/React-19-61DAFB?logo=react&logoColor=black)](https://react.dev/)
[![Seguridad](https://img.shields.io/badge/Seguridad-401%20%7C%20403%20%7C%20404%20%7C%20400-blue)](#tabla-de-pruebas-de-seguridad-agrotrace)
[![Check deploy](https://img.shields.io/badge/check--deploy-sin%20advertencias-brightgreen)](#verificaciones)

**Repositorio oficial:** https://github.com/carlosjunco2025/Agrotrace_lab15

Proyecto integrador **AgroTrace** (Fundo, Lote, Evaluación de calidad, OrdenComercial/OrdenDespacho y usuarios Operador/Administrador) con seguridad por capas implementada y verificada en la Semana 15. No se mezcla código ni modelos de cafetería: la Parte 1 del laboratorio se traslada íntegramente a las entidades reales de AgroTrace.

---

## Arquitectura de seguridad por capas

```text
Navegador (React 19)
 ├─ /login → POST /api/login/ → GET /api/me/ (id, username, email, is_staff, rol)
 ├─ localStorage: agrotrace_token / agrotrace_perfil  (sin contraseñas)
 ├─ api.js: interceptor request → Authorization: Token ****
 ├─ api.js: interceptor response → 401 limpia sesión y vuelve a /login
 ├─ <RutaProtegida>: /dashboard, /lotes, /productores, /pedidos, /trazabilidad
 └─ UI por perfil: Eliminar solo si is_staff === true; React escapa <script> como texto
                         │
                         ▼
Django 6.1 + Django REST Framework
 ├─ Password hashing: User.objects.create_user() → pbkdf2_sha256$1500000$...
 ├─ Autenticación: TokenAuthentication (+ SessionAuthentication)
 ├─ Permiso global: IsAuthenticated
 ├─ Permisos por acción: GET autenticado | POST/PUT gestores | DELETE IsAdminUser
 ├─ get_queryset(): admin ve todas las órdenes; operador solo registrado_por=request.user → 404 IDOR
 ├─ Validación: validate_codigo_lote, validate_toneladas_brutas, validate_cantidad_sacos,
 │              validate_estado / validate_estado_evaluacion, stock desde la BD
 └─ Campos derivados read_only: total_valorizado, precio_unitario_aplicado,
                                fecha_registro, registrado_por → se calculan en el servidor
                         │
                         ▼
Configuración y despliegue
 ├─ os.environ: DJANGO_DEBUG, DJANGO_SECRET_KEY, DJANGO_ALLOWED_HOSTS, DJANGO_HSTS_SECONDS
 ├─ Producción (DEBUG=False): SECURE_SSL_REDIRECT, cookies Secure, HSTS 3600,
 │                            SECURE_HSTS_INCLUDE_SUBDOMAINS/PRELOAD, X_FRAME_OPTIONS=DENY
 └─ .gitignore excluye .env, .venv/, node_modules/, dist/, __pycache__/, db.sqlite3
```

### Usuarios de demostración (clave enmascarada)

| Usuario | Rol (`PerfilUsuario`) | is_staff | Datos propios en AgroTrace |
|---|---|---|---|
| `admin_agro` | ADMINISTRADOR | `True` | Fundo Administración, lote `LOT-ADM-001`, orden comercial propia; ve todas |
| `operador_agro` | OPERADOR | `False` | Fundo La Esperanza, lotes `LOT-OP1-*`, orden `#2` |
| `operador_agro2` | OPERADOR | `False` | Fundo San Miguel, lote `LOT-OP2-001`, orden `#3` |

Las contraseñas se crean con `User.objects.create_user(...)` y solo se guarda el hash PBKDF2. La clave de demostración se puede sobreescribir con `AGROTRACE_DEMO_PASSWORD`; nunca se almacena en texto plano ni se muestra en las evidencias.

---

## Tabla de pruebas de seguridad AgroTrace

| # | Prueba | Resultado esperado | Resultado obtenido | Evidencia |
|---|---|---|---|---|
| 1 | Acceso a `/api/lotes/` sin token | `401 Unauthorized` | `401` + `{"detail":"Las credenciales de autenticación no se proveyeron."}` | [02](docs/evidencias_s15/02_api_login_y_401.png) |
| 2 | Login con credenciales correctas / incorrectas | `200` con token / `400` | `200` (token oculto) y `400` | [02](docs/evidencias_s15/02_api_login_y_401.png) |
| 3 | Operador intenta `DELETE /api/lotes/{id}/` | `403 Forbidden` | `403` (IsAdminUser) | [03](docs/evidencias_s15/03_api_permisos_y_404_idor.png) |
| 4 | Operador consulta orden de otro operador (IDOR) | `404 Not Found` | `404` (get_queryset filtrado) | [03](docs/evidencias_s15/03_api_permisos_y_404_idor.png) |
| 5 | Administrador lista y crea registros | `200` / `201` | `200` (ve todas) y `201` | [03](docs/evidencias_s15/03_api_permisos_y_404_idor.png) |
| 6 | `cantidad_sacos = 0`, código inválido, toneladas = 0 | `400 Bad Request` | `400` en los tres casos | [04](docs/evidencias_s15/04_api_validacion_servidor_400.png) |
| 7 | `total_valorizado` alterado en el JSON | Total real desde BD | `9200.00` y `precio_unitario_aplicado=920.00` (se ignoró `1.00`) | [04](docs/evidencias_s15/04_api_validacion_servidor_400.png) |
| 8 | Texto `<script>alert('XSS')</script>` en React | Texto plano, sin ejecución | Mostrado como texto; 0 alertas | [06](docs/evidencias_s15/06_react_panel_roles_y_xss.png) |
| 9 | Cierre de sesión y ruta protegida | Token borrado y redirect `/login` | `/login` tras logout; `/dashboard` redirige sin sesión | [05](docs/evidencias_s15/05_react_login_y_network.png), [06](docs/evidencias_s15/06_react_panel_roles_y_xss.png) |
| 10 | `check --deploy`, `check`, `lint`, `build` | Sin errores | Sin advertencias y build correcto | [07](docs/evidencias_s15/07_check_deploy_lint_build.png) |

> Checklist Parte 2 (criterios 1–9) y Ejercicio 14 respondidos con estas mismas pruebas en `GLAB-S15-YBESTARD-2026-02-COMPLETADO.docx`.

---

## Galería visual (capturas reales, secretos enmascarados)

| Captura | Contenido |
|---|---|
| [01_shell_hash_authenticate.png](docs/evidencias_s15/01_shell_hash_authenticate.png) | `create_user`, hash `pbkdf2_sha256$…`, `make_password`, `check_password`, `authenticate` |
| [02_api_login_y_401.png](docs/evidencias_s15/02_api_login_y_401.png) | `/api/login/` 200/400 y `/api/lotes/` 401/200 |
| [03_api_permisos_y_404_idor.png](docs/evidencias_s15/03_api_permisos_y_404_idor.png) | 401 / 403 / 404 IDOR / 200 y 201 |
| [04_api_validacion_servidor_400.png](docs/evidencias_s15/04_api_validacion_servidor_400.png) | Validaciones 400 y total calculado en BD |
| [05_react_login_y_network.png](docs/evidencias_s15/05_react_login_y_network.png) | Login React + Network con `Authorization: Token ****` |
| [06_react_panel_roles_y_xss.png](docs/evidencias_s15/06_react_panel_roles_y_xss.png) | Operador vs Administrador, Cerrar sesión y XSS como texto |
| [07_check_deploy_lint_build.png](docs/evidencias_s15/07_check_deploy_lint_build.png) | `check --deploy`, `check`, `npm run lint`, `npm run build` |
| [08_git_log_colaboradores.png](docs/evidencias_s15/08_git_log_colaboradores.png) | Commits alternados de Carlos Junco y Matteo Lajara |

Documento Word completo: [GLAB-S15-YBESTARD-2026-02-COMPLETADO.docx](GLAB-S15-YBESTARD-2026-02-COMPLETADO.docx)

---

## Puesta en marcha

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt python-docx
.\.venv\Scripts\python.exe manage.py migrate
.\.venv\Scripts\python.exe manage.py seed_seguridad_s15
.\.venv\Scripts\python.exe manage.py runserver 127.0.0.1:8000
cd frontend
npm install
npm run dev
```

Verificaciones:

```powershell
.\.venv\Scripts\python.exe manage.py test agrotrace.tests_seguridad_s15 -v 2
$env:DJANGO_DEBUG="False"
$env:DJANGO_SECRET_KEY="valor-largo-y-aleatorio-de-entorno"
.\.venv\Scripts\python.exe manage.py check --deploy
cd frontend; npm run lint; npm run build
```

## Autores

- **Carlos Junco** ([carlosjunco2025](https://github.com/carlosjunco2025)) — carlos.junco@tecsup.edu.pe
- **Matteo Lajara** ([mtl-124](https://github.com/mtl-124)) — matteolajara@gmail.com
