# Guía de Migración: Corrección de Grupos y Permisos

## Problemas Corregidos

### 1. **sigmalab/forms.py:826** - Grupo legado eliminado
- **Problema**: Consultaba `tecnicos_s_lab` que se eliminaba en migración de limpieza
- **Solución**: Cambiado a `tecnico_responsable_s_lab` (nombre canónico)

### 2. **sigmadp/templates** - Grupos incorrectos
- **Problema**: Usaba `Tecnicos DP` y sintaxis inválida `user.groups.filter.name__in`
- **Solución**: Cambiado a `tecnico_responsable_s_dp` y filtro `has_group`

### 3. **Múltiples implementaciones de has_group**
- **Problema**: 3 implementaciones diferentes con comportamientos divergentes
- **Solución**: Unificado en `core/templatetags/role_filters.py` con normalización robusta

### 4. **Grupos SEM/Confocal no creados automáticamente**
- **Problema**: Scripts ad hoc que competían con migraciones de limpieza
- **Solución**: Migración centralizada `core/migrations/0001_create_canonical_groups.py`

### 5. **Acceso cruzado entre módulos**
- **Problema**: Sesiones huérfanas permitían acceso ICTS↔DTF
- **Solución**: Middleware `core/middleware.ModuleAccessMiddleware`

## Cambios Implementados

### Nuevos Archivos
- `core/roles.py` - Constantes y utilidades centralizadas
- `core/templatetags/role_filters.py` - Filtros de plantilla unificados
- `core/middleware.py` - Validación de acceso entre módulos
- `core/migrations/0001_create_canonical_groups.py` - Migración centralizada
- `core/management/commands/setup_groups.py` - Comando de gestión
- `scripts/test_groups.py` - Pruebas de verificación

### Archivos Modificados
- `sigmalab/forms.py` - Corregido grupo de técnicos
- `sigmadp/templates/sigmadp/base_sigmadp.html` - Grupo correcto
- `sigmadp/templates/sigmadp/solicitud_termica_detalle.html` - Sintaxis corregida
- `templates/base_icts.html` - Filtro unificado
- `templates/base_dtf.html` - Filtro unificado
- `icts/templates/icts/_sidebar.html` - Filtro unificado
- `sigmalab/templates/sigmalab/base_sigmalab.html` - Filtro unificado
- `sigmadp/templates/sigmadp/base_sigmadp.html` - Filtro unificado
- `automatizacion/settings.py` - App core y middleware añadidos

## Grupos Canónicos

### ICTS
- `icts_users` - Usuarios base ICTS
- `revisores` - Revisores de propuestas
- `responsables` - Responsables de instalaciones
- `managers` - Gestores del sistema

### DTF
- `usuarios_dtf` - Usuarios DTF
- `usuarios_autonomo_s_lab` - Usuarios autónomos S-LAB
- `tecnico_responsable_s_lab` - Técnicos S-LAB
- `tecnico_responsable_s_mec` - Técnicos S-MEC
- `tecnico_responsable_s_dp` - Técnicos S-DP

### Técnicos Especializados
- `tecnicos_sem_fib` - Técnicos SEM/FIB
- `confocal_technicians` - Técnicos Confocal

## Comandos de Gestión

### Crear grupos
```bash
python manage.py setup_groups
```

### Verificar grupos
```bash
python manage.py setup_groups --check
```

### Limpiar grupos legados
```bash
python manage.py setup_groups --cleanup
```

### Listar usuarios en grupos
```bash
python manage.py setup_groups --list-users
```

## Pruebas

### Ejecutar pruebas de verificación
```bash
python scripts/test_groups.py
```

### Verificar migraciones
```bash
python manage.py makemigrations
python manage.py migrate
```

## Filtros de Plantilla Disponibles

### Filtros de verificación de grupos
- `has_group` - Verificación robusta con normalización
- `is_slab_technician` - Técnico S-LAB
- `is_mec_technician` - Técnico S-MEC
- `is_dp_technician` - Técnico S-DP
- `is_sem_technician` - Técnico SEM/FIB
- `is_confocal_technician` - Técnico Confocal
- `is_dtf_user` - Usuario DTF
- `is_any_technician` - Cualquier técnico
- `is_reviewer` - Revisor
- `is_responsable` - Responsable
- `is_manager` - Manager
- `is_icts_user` - Usuario ICTS

### Filtros de formularios
- `add_class` - Añadir clases CSS
- `add_attr` - Añadir atributos

## Uso en Plantillas

### Cargar filtros
```django
{% load role_filters %}
```

### Verificar grupos
```django
{% if user|has_group:'tecnico_responsable_s_lab' %}
  <!-- Contenido para técnicos S-LAB -->
{% endif %}

{% if user|is_dp_technician %}
  <!-- Contenido para técnicos S-DP -->
{% endif %}
```

## Beneficios

1. **Consistencia**: Una sola fuente de verdad para grupos
2. **Robustez**: Normalización de nombres con acentos/espacios
3. **Mantenibilidad**: Código centralizado y reutilizable
4. **Seguridad**: Validación de acceso entre módulos
5. **Pruebas**: Verificación automatizada de funcionalidad

## Próximos Pasos

1. Ejecutar migraciones: `python manage.py migrate`
2. Crear grupos: `python manage.py setup_groups`
3. Verificar funcionamiento: `python scripts/test_groups.py`
4. Actualizar usuarios existentes a grupos canónicos
5. Probar funcionalidad en entorno de desarrollo
6. Desplegar a producción
