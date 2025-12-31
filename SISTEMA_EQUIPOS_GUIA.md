# 🔧 Sistema de Gestión de Equipos del Laboratorio

## 📋 Descripción General

El sistema de equipos permite a los técnicos del laboratorio gestionar equipos que pueden ser prestados a usuarios, y a los usuarios solicitar y devolver equipos de forma controlada.

## 🎯 Funcionalidades Principales

### Para Técnicos:
- ✅ **Crear y gestionar equipos** del laboratorio
- ✅ **Ver todos los préstamos** con filtros avanzados
- ✅ **Recibir notificaciones** automáticas de préstamos
- ✅ **Gestionar préstamos vencidos** y bloquear cuentas
- ✅ **Estadísticas** de uso de equipos

### Para Usuarios:
- ✅ **Ver equipos disponibles** para préstamo
- ✅ **Solicitar préstamos** con duración específica
- ✅ **Devolver equipos** con observaciones
- ✅ **Ver historial** de sus préstamos
- ✅ **Recibir notificaciones** de vencimiento

## 🚀 Instalación y Configuración

### 1. Ejecutar Migraciones
```bash
python manage.py migrate sigmalab
```

### 2. Crear Comando de Verificación Automática
El sistema incluye un comando para verificar préstamos vencidos:

```bash
# Verificar préstamos vencidos (modo de prueba)
python manage.py verificar_prestamos_vencidos --dry-run

# Ejecutar verificación real
python manage.py verificar_prestamos_vencidos

# Configurar parámetros personalizados
python manage.py verificar_prestamos_vencidos --dias-bloqueo 10 --dias-notificacion 2
```

### 3. Configurar Tarea Automática (Cron)
Para automatizar la verificación, agregar al crontab:

```bash
# Verificar préstamos vencidos diariamente a las 9:00 AM
0 9 * * * cd /ruta/al/proyecto && python manage.py verificar_prestamos_vencidos
```

## 📱 Uso del Sistema

### Para Técnicos

#### 1. Gestionar Equipos
- **URL**: `/dtf/lab/equipos/`
- **Funciones**:
  - Crear nuevos equipos
  - Editar información de equipos
  - Eliminar equipos (solo si no tienen préstamos activos)
  - Buscar equipos por nombre, código o categoría

#### 2. Gestionar Préstamos
- **URL**: `/dtf/lab/prestamos/gestionar/`
- **Funciones**:
  - Ver todos los préstamos con filtros
  - Ver detalles de cada préstamo
  - Filtrar por estado, usuario, equipo, fechas
  - Ver estadísticas de préstamos

#### 3. Préstamos Vencidos
- **URL**: `/dtf/lab/prestamos/vencidos/`
- **Funciones**:
  - Ver préstamos vencidos
  - Enviar notificaciones a usuarios
  - Contactar usuarios por email

#### 4. Notificaciones
- **URL**: `/dtf/lab/notificaciones/`
- **Funciones**:
  - Ver todas las notificaciones
  - Marcar como leídas
  - Seguimiento de préstamos

### Para Usuarios

#### 1. Ver Equipos Disponibles
- **URL**: `/dtf/lab/equipos/`
- **Funciones**:
  - Ver lista de equipos disponibles
  - Buscar equipos por criterios
  - Ver información detallada de cada equipo

#### 2. Solicitar Préstamo
- **URL**: `/dtf/lab/prestamos/solicitar/`
- **Funciones**:
  - Seleccionar equipo
  - Especificar días de préstamo (máximo 30)
  - Describir propósito del uso
  - Agregar observaciones

#### 3. Mis Préstamos
- **URL**: `/dtf/lab/prestamos/mis-prestamos/`
- **Funciones**:
  - Ver historial de préstamos
  - Ver estado actual de préstamos
  - Devolver equipos
  - Ver días restantes o días vencidos

## 🔔 Sistema de Notificaciones

### Tipos de Notificaciones

1. **Préstamo Realizado**: Se envía al técnico cuando un usuario solicita un préstamo
2. **Recordatorio de Vencimiento**: Se envía al usuario antes del vencimiento
3. **Equipo Vencido**: Se envía al usuario y técnico cuando un préstamo vence
4. **Equipo Devuelto**: Se envía al técnico cuando un usuario devuelve un equipo

### Configuración de Notificaciones

El sistema envía notificaciones automáticamente basado en:
- **Días antes del vencimiento**: Por defecto 1 día
- **Días de bloqueo**: Por defecto 7 días después del vencimiento

## 🛡️ Sistema de Bloqueo de Cuentas

### Criterios de Bloqueo
- Usuario con préstamo vencido por más de 7 días (configurable)
- Bloqueo automático mediante comando de gestión
- Desbloqueo manual por parte del técnico

### Proceso de Bloqueo
1. El comando verifica préstamos vencidos
2. Identifica usuarios con préstamos muy vencidos
3. Bloquea automáticamente las cuentas
4. Envía notificación al técnico responsable

## 📊 Modelos de Datos

### EquipoLaboratorio
- Información básica del equipo
- Estado (disponible, prestado, mantenimiento, deshabilitado)
- Categoría y ubicación
- Instrucciones de uso
- Disponibilidad para préstamo

### PrestamoEquipo
- Relación entre usuario y equipo
- Fechas de préstamo y devolución
- Estado del préstamo
- Observaciones y propósito
- Seguimiento de notificaciones

### NotificacionPrestamo
- Sistema de notificaciones
- Tipos de notificación
- Estado de envío
- Historial de comunicaciones

## 🔧 Comandos de Gestión

### verificar_prestamos_vencidos

**Parámetros**:
- `--dias-bloqueo`: Días después del vencimiento para bloquear cuenta (default: 7)
- `--dias-notificacion`: Días antes del vencimiento para notificar (default: 1)
- `--dry-run`: Modo de prueba sin realizar cambios

**Funciones**:
1. Marca préstamos como vencidos
2. Envía notificaciones de recordatorio
3. Bloquea cuentas de usuarios con préstamos muy vencidos
4. Crea notificaciones para técnicos

## 🎨 Interfaz de Usuario

### Características de la UI
- **Responsive**: Adaptable a dispositivos móviles
- **Búsqueda avanzada**: Filtros por múltiples criterios
- **Estados visuales**: Colores para identificar estados
- **Modales informativos**: Detalles sin cambiar de página
- **Alertas contextuales**: Información importante destacada

### Navegación
- **Menú principal**: Acceso rápido a todas las funciones
- **Breadcrumbs**: Navegación clara
- **Botones de acción**: Acciones principales visibles
- **Filtros persistentes**: Mantiene criterios de búsqueda

## 🔒 Seguridad y Permisos

### Control de Acceso
- **Técnicos**: Acceso completo al sistema
- **Usuarios DTF**: Solo pueden solicitar y devolver equipos
- **Autenticación**: Requerida para todas las operaciones
- **Validación**: Verificación de permisos en cada vista

### Protección de Datos
- **Validación de formularios**: Prevención de datos inválidos
- **Sanitización**: Limpieza de datos de entrada
- **Logs de auditoría**: Registro de todas las operaciones
- **Backup automático**: Respaldo de datos críticos

## 📈 Métricas y Estadísticas

### Para Técnicos
- Total de equipos disponibles
- Préstamos activos vs devueltos
- Equipos más solicitados
- Usuarios con más préstamos
- Tiempo promedio de préstamo

### Para Administradores
- Uso del sistema por período
- Equipos con más problemas
- Usuarios bloqueados
- Efectividad de notificaciones
- Tendencias de uso

## 🚨 Solución de Problemas

### Problemas Comunes

1. **Error de permisos**: Verificar que el usuario tenga el grupo correcto
2. **Equipo no disponible**: Verificar estado del equipo
3. **Préstamo no se crea**: Verificar que el técnico responsable existe
4. **Notificaciones no llegan**: Verificar configuración de email

### Logs y Debugging
- Revisar logs de Django para errores
- Verificar configuración de base de datos
- Comprobar permisos de archivos
- Validar configuración de email

## 🔄 Mantenimiento

### Tareas Regulares
- Ejecutar comando de verificación diariamente
- Revisar logs de errores
- Limpiar notificaciones antiguas
- Actualizar información de equipos
- Revisar usuarios bloqueados

### Backup y Recuperación
- Backup de base de datos
- Respaldo de archivos de configuración
- Documentación de cambios
- Plan de recuperación ante desastres

## 📞 Soporte

Para problemas o dudas sobre el sistema:
1. Revisar esta documentación
2. Verificar logs del sistema
3. Contactar al administrador técnico
4. Reportar bugs en el sistema de issues

---

**¡Sistema de Equipos implementado exitosamente!** 🎉
