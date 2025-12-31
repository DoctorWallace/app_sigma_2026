# Refactor plan para `icts/views.py`

Objetivo: dividir las 1.700 líneas de vistas en módulos especializados y servicios reutilizables siguiendo el patrón probado en SIGMA DTF.

## 1. Agrupar responsabilidades

- **Dashboards** (`dashboard`, `manager_dashboard`, `responsable_dashboard`, etc.) → mover a `icts/views/dashboard.py` y crear un servicio `icts/services/dashboard.py` que prepare métricas por rol.
- **Gestión de propuestas** (`proposal_create`, `proposal_detail`, revisiones) → `icts/views/proposals.py` + `icts/services/proposals.py`.
- **OLMAT** (creación, listado, evaluación) → `icts/views/olmat.py` con un servicio `icts/services/olmat.py`.
- **SIGMA SEM / análisis técnicos** → `icts/views/sem.py`.

Cada submódulo debe importar únicamente los formularios y modelos relevantes, reduciendo dependencias cruzadas.

## 2. Servicios reutilizables

- Replicar el patrón `build_dashboard_data`:
  - `services/dashboard.py`: consultas agregadas por rol (usuario, revisor, responsable, manager).
  - `services/proposals.py`: operaciones de aprobación/rechazo, notificaciones y filtros por estado.
  - `services/olmat.py`: validaciones de solicitudes, cálculos de estado y utilidades de notificación.

## 3. Validaciones y permisos

- Crear decoradores/helpers en `icts/services/auth.py` para encapsular comprobaciones de grupos (`is_plain_icts_user`, `user_in_groups`), permitiendo reutilizar en vistas y tests.

## 4. Tests incrementales

- Añadir carpeta `tests/icts/` con:
  - `test_dashboard_service.py`: verifica agregaciones por rol usando fixtures.
  - `test_proposals_service.py`: asegura transiciones de estado válidas.
  - `test_olmat_service.py`: cubre flujos de creación y evaluación.

## 5. Hoja de ruta

1. Extraer dashboard a nuevo servicio + vista modular (pull request pequeño).
2. Repetir con propuestas, dejando tests que cubran transiciones y notificaciones.
3. Aislar OLMAT y SEM en módulos propios.
4. Una vez divididas las vistas, documentar el nuevo mapa de módulos en `docs/`.

Esta secuencia permite refactorizar en iteraciones cortas, manteniendo los tests verdes en cada paso.
