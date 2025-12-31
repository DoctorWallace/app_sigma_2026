# Guía de Unificación de Templates DTF

## Resumen del Sistema Unificado

He creado un sistema unificado para toda la plataforma DTF que resuelve los problemas que mencionaste:

### ✅ **Características Implementadas**

1. **Template Base Unificado** (`templates/base_dtf_unified.html`)
2. **Templates Específicos por Laboratorio** (base_mec_unified.html, base_sigmadp_unified.html, etc.)
3. **Sidebar Inteligente** que cambia según el rol (usuario/técnico)
4. **Headers Estandarizados** con logos, roles y navegación
5. **Diseño Moderno y Serio** apropiado para laboratorios
6. **Responsive Design** optimizado para móvil

## Estructura del Sistema

```
templates/
├── base_dtf_unified.html           # Template base principal
├── mec/templates/mec/
│   ├── base_mec_unified.html       # Base específica de MEC
│   ├── panel_usuario.html          # Actualizado para usar el nuevo base
│   └── panel_tecnico_unified.html  # Ejemplo de panel técnico
├── sigmadp/templates/sigmadp/
│   └── base_sigmadp_unified.html   # Base específica de DP
├── sigmalab/templates/sigmalab/
│   └── base_sigmalab_unified.html  # Base específica de LAB
└── sigmaoptics/templates/sigmaoptics/
    └── base_optics_unified.html    # Base específica de OPTICS
```

## Características del Diseño

### 🎨 **Colores y Estilo**
- **Colores principales**: Azules serios pero modernos (#2c5282, #1a365d)
- **Acentos**: Verde azulado (#38b2ac) para elementos interactivos
- **Fondos**: Blancos y grises claros para profesionalidad
- **Tipografía**: Inter (moderna pero legible)

### 🧭 **Navegación Inteligente**

#### **Usuarios**:
- Mi Panel
- Nueva Solicitud
- Cerrar Sesión

#### **Técnicos**:
- Mi Panel
- Solicitudes
- Cerrar Sesión

### 📱 **Headers Estandarizados**
- **Botón "Atrás"**: Siempre presente, va al panel correspondiente
- **Título de página**: Claro y descriptivo
- **Role badge**: Muestra "Técnico" o "Usuario" con iconos
- **Logo del laboratorio**: Específico de cada lab
- **Logos del sistema**: SOL e ICTS siempre visibles

## Cómo Migrar Templates Existentes

### 1. **Para Templates de Panel/Dashboard**

**Antes:**
```html
{% extends "base_dtf.html" %}
{% block title %}Mi Panel{% endblock %}
{% block content %}
  <!-- contenido -->
{% endblock %}
```

**Después:**
```html
{% extends "mec/base_mec_unified.html" %}
{% block mec_title %}Mi Panel{% endblock %}
{% block page_title %}Mi Panel - S-MEC{% endblock %}
{% block content %}
  <!-- contenido -->
{% endblock %}
```

### 2. **Para Templates de Formularios**

**Antes:**
```html
{% extends "base_dtf.html" %}
{% block title %}Nueva Solicitud{% endblock %}
```

**Después:**
```html
{% extends "mec/base_mec_unified.html" %}
{% block mec_title %}Nueva Solicitud{% endblock %}
{% block page_title %}Nueva Solicitud - S-MEC{% endblock %}
```

### 3. **Para Templates de Listados**

**Antes:**
```html
{% extends "base_dtf.html" %}
{% block title %}Solicitudes{% endblock %}
```

**Después:**
```html
{% extends "mec/base_mec_unified.html" %}
{% block mec_title %}Solicitudes{% endblock %}
{% block page_title %}Gestionar Solicitudes - S-MEC{% endblock %}
```

## Templates por Laboratorio

### **Sigma MEC**
- Base: `mec/base_mec_unified.html`
- Title block: `{% block mec_title %}`
- Logo: sigma_mec.png

### **Sigma DP**  
- Base: `sigmadp/base_sigmadp_unified.html`
- Title block: `{% block dp_title %}`
- Logo: sigma_DP3.png

### **Sigma Lab**
- Base: `sigmalab/base_sigmalab_unified.html` 
- Title block: `{% block lab_title %}`
- Logo: sigma_lab.png

### **Sigma Optics**
- Base: `sigmaoptics/base_optics_unified.html`
- Title block: `{% block optics_title %}`
- Logo: sigma_optics.png

## Pasos de Migración

### 1. **Actualizar Templates Principales**
```bash
# Para cada laboratorio, actualizar:
- panel_usuario.html
- panel_tecnico.html  
- solicitud_form.html
- solicitud_list.html
- solicitud_detail.html
```

### 2. **Verificar URLs y Navegación**
- Asegurar que todas las URLs existen
- Verificar que los grupos de usuarios son correctos
- Comprobar que los enlaces del sidebar funcionan

### 3. **Probar Responsividad**
- Desktop: Sidebar fijo
- Mobile: Sidebar colapsable con overlay
- Tablets: Adaptación automática

## Beneficios del Nuevo Sistema

### ✅ **Para Usuarios**
- **Navegación consistente** en todos los laboratorios
- **Diseño familiar** reduce curva de aprendizaje
- **Responsive** funciona en cualquier dispositivo
- **Accesible** con buenos contrastes y tamaños

### ✅ **Para Técnicos**  
- **Sidebar simplificado** con solo lo esencial
- **Acciones importantes** dentro de las páginas
- **Navegación rápida** entre solicitudes
- **Información clara** del rol y laboratorio

### ✅ **Para Desarrollo**
- **Código reutilizable** entre laboratorios
- **Mantenimiento simplificado** un solo punto de cambios
- **Escalable** fácil añadir nuevos laboratorios
- **Consistente** mismo patrón en toda la aplicación

## Próximos Pasos

1. **Migrar templates de MEC** (ya iniciado)
2. **Migrar templates de DP**
3. **Migrar templates de Lab**  
4. **Migrar templates de Optics**
5. **Probar todas las funcionalidades**
6. **Ajustar estilos específicos** si es necesario

## Notas Importantes

- **Mantener funcionalidad**: No cambiar lógica, solo presentación
- **Probar navegación**: Verificar que todos los enlaces funcionan
- **Verificar roles**: Comprobar que usuarios/técnicos ven lo correcto
- **Mobile first**: Probar en dispositivos móviles

Este sistema unificado te dará la consistencia y profesionalidad que buscas para toda la plataforma DTF.
