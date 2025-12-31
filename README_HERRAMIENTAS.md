# 📚 Guía de Herramientas de Desarrollo - SIGMA FUSION

Índice de toda la documentación sobre las herramientas de desarrollo instaladas.

---

## 🎯 Empezar Aquí

Si es tu primera vez usando estas herramientas, **empieza por estos archivos en orden**:

### 1️⃣ [RESUMEN_INSTALACION.md](RESUMEN_INSTALACION.md)
**Lee esto primero** - 5 minutos

Resumen de qué se instaló y cómo verificar que todo funciona.

### 2️⃣ [QUICK_START_DEV.md](QUICK_START_DEV.md)
**Guía rápida** - 3 minutos

Los comandos y herramientas más importantes que usarás día a día.

### 3️⃣ [DEMO_DEBUG_TOOLBAR.md](DEMO_DEBUG_TOOLBAR.md)
**Demostración visual** - 5 minutos

Cómo se ve y funciona la Debug Toolbar (la herramienta principal).

---

## 📖 Documentación Completa

### [HERRAMIENTAS_DESARROLLO.md](HERRAMIENTAS_DESARROLLO.md)
**Referencia completa** - 30 minutos

Todo sobre las herramientas disponibles:
- Django Debug Toolbar
- Django Extensions
- Pytest
- Coverage
- Black, Flake8, isort
- Tips de productividad
- Configuración de VS Code/Cursor
- Y mucho más...

---

## 🛠️ Archivos de Configuración

### `.vscode/settings.json`
Configuración automática para VS Code/Cursor:
- Formateo automático al guardar
- Linting en tiempo real
- Soporte para templates Django
- Testing con pytest

### `dev_check.py`
Script para verificar calidad del código antes de commit:
```bash
python dev_check.py
```

### `.gitignore`
Archivos que Git debe ignorar (caché, compilados, etc.)

---

## 🚀 Quick Start Ultra Rápido

### ¿Quieres saber qué template estás viendo?

```bash
# 1. Inicia el servidor
python manage.py runserver

# 2. Ve a tu página en el navegador
# 3. Mira la barra lateral derecha → Click en "Templates"
# 4. ¡Listo! Ya ves todos los templates usados
```

### ¿Quieres verificar tu código antes de commit?

```bash
python dev_check.py
```

### ¿Quieres ver todas las URLs del proyecto?

```bash
python manage.py show_urls
```

### ¿Quieres usar la shell con todos los modelos importados?

```bash
python manage.py shell_plus
```

---

## 📊 Mapa de Documentación

```
README_HERRAMIENTAS.md  ← Estás aquí (índice)
│
├─ RESUMEN_INSTALACION.md  ← ¿Qué se instaló?
│  └─ Cómo verificar instalación
│     └─ Troubleshooting
│
├─ QUICK_START_DEV.md  ← Comandos más usados
│  └─ Workflow recomendado
│     └─ Tips rápidos
│
├─ DEMO_DEBUG_TOOLBAR.md  ← Cómo se ve la toolbar
│  └─ Casos de uso reales
│     └─ Otros paneles útiles
│
└─ HERRAMIENTAS_DESARROLLO.md  ← Documentación completa
   ├─ Django Debug Toolbar
   ├─ Django Extensions
   ├─ Testing (Pytest)
   ├─ Code Quality (Black, Flake8, isort)
   ├─ Workflow recomendado
   └─ Recursos adicionales
```

---

## 🎓 Rutas de Aprendizaje

### Ruta 1: "Solo quiero ver qué template usar"
1. Lee: [QUICK_START_DEV.md](QUICK_START_DEV.md) - Sección "Django Debug Toolbar"
2. Ejecuta: `python manage.py runserver`
3. Visita cualquier página
4. ✅ Listo

### Ruta 2: "Quiero ser más productivo"
1. Lee: [QUICK_START_DEV.md](QUICK_START_DEV.md) - Completo
2. Lee: [HERRAMIENTAS_DESARROLLO.md](HERRAMIENTAS_DESARROLLO.md) - Secciones 1-2
3. Practica: Usa `shell_plus` y `show_urls`
4. ✅ Ya eres más productivo

### Ruta 3: "Quiero dominar las herramientas"
1. Lee: [RESUMEN_INSTALACION.md](RESUMEN_INSTALACION.md) - Completo
2. Lee: [HERRAMIENTAS_DESARROLLO.md](HERRAMIENTAS_DESARROLLO.md) - Completo
3. Lee: [DEMO_DEBUG_TOOLBAR.md](DEMO_DEBUG_TOOLBAR.md) - Completo
4. Practica: Usa todas las herramientas en un proyecto real
5. ✅ Eres un experto

---

## 💡 Preguntas Frecuentes

### ¿Por dónde empiezo?
👉 [QUICK_START_DEV.md](QUICK_START_DEV.md)

### ¿Cómo veo qué template se usa?
👉 [DEMO_DEBUG_TOOLBAR.md](DEMO_DEBUG_TOOLBAR.md)

### ¿Qué comandos nuevos tengo disponibles?
👉 [HERRAMIENTAS_DESARROLLO.md](HERRAMIENTAS_DESARROLLO.md) - Sección 2

### ¿Cómo funciona pytest?
👉 [HERRAMIENTAS_DESARROLLO.md](HERRAMIENTAS_DESARROLLO.md) - Sección 3

### ¿Cómo formateo mi código?
👉 [HERRAMIENTAS_DESARROLLO.md](HERRAMIENTAS_DESARROLLO.md) - Sección 5

### La Debug Toolbar no aparece, ¿qué hago?
👉 [RESUMEN_INSTALACION.md](RESUMEN_INSTALACION.md) - Sección Troubleshooting

---

## 🎯 Casos de Uso

### Caso: "Quiero modificar el navbar"
```bash
# 1. Visita cualquier página con el navbar
# 2. Debug Toolbar → Templates
# 3. Busca "navbar" en la lista
# 4. Ver ruta completa: templates/includes/navbar.html
# 5. Edita ese archivo
```

### Caso: "Esta página es lenta"
```bash
# 1. Visita la página lenta
# 2. Debug Toolbar → Time
# 3. Ver qué parte toma más tiempo
# 4. Si es SQL: Debug Toolbar → SQL
# 5. Ver qué queries son lentas
# 6. Optimizar
```

### Caso: "¿Qué variables puedo usar en este template?"
```bash
# 1. Visita la página
# 2. Debug Toolbar → Templates
# 3. Click en el template principal
# 4. Ver lista completa de variables de contexto
```

### Caso: "¿Qué URLs tengo disponibles?"
```bash
python manage.py show_urls
```

---

## 🚀 Comandos Esenciales

```bash
# Desarrollo diario
python manage.py runserver       # Servidor con Debug Toolbar
python manage.py shell_plus      # Shell mejorado
python manage.py show_urls       # Ver todas las URLs

# Testing
pytest                          # Ejecutar tests
pytest --cov                    # Tests con cobertura

# Calidad de código
python dev_check.py             # Verificar todo
black .                         # Formatear código
flake8                          # Análisis de código

# Django checks
python manage.py check          # Verificar configuración
python manage.py makemigrations # Crear migraciones
python manage.py migrate        # Aplicar migraciones
```

---

## 🎨 Personalización

### VS Code / Cursor
Ya está configurado en `.vscode/settings.json`:
- Formateo automático
- Linting en tiempo real
- Soporte Django

### PowerShell Aliases (opcional)
Añade a tu `$PROFILE`:
```powershell
function rs { python manage.py runserver }
function sp { python manage.py shell_plus }
function mm { python manage.py makemigrations }
function m { python manage.py migrate }
```

---

## ⚠️ Importante

**Todas estas herramientas:**
- ✅ Solo activas en desarrollo (`DEBUG=True`)
- ✅ Se desactivan en producción automáticamente
- ✅ No afectan rendimiento en producción
- ✅ Son estándares de la industria

---

## 📚 Recursos Externos

### Django Debug Toolbar
- [Documentación oficial](https://django-debug-toolbar.readthedocs.io/)
- [GitHub](https://github.com/jazzband/django-debug-toolbar)

### Django Extensions
- [Documentación oficial](https://django-extensions.readthedocs.io/)
- [Lista de comandos](https://django-extensions.readthedocs.io/en/latest/command_extensions.html)

### Testing
- [Pytest docs](https://docs.pytest.org/)
- [Pytest-Django](https://pytest-django.readthedocs.io/)

### Code Quality
- [Black](https://black.readthedocs.io/)
- [Flake8](https://flake8.pycqa.org/)
- [isort](https://pycqa.github.io/isort/)

---

## 🔄 Actualizaciones

### ¿Cómo actualizar las herramientas?

```bash
# Actualizar dependencias de desarrollo
pip install -U -r requirements-dev.txt

# Verificar versiones
pip list | grep -E "django-debug-toolbar|django-extensions|pytest|black|flake8|isort"
```

---

## 🎉 ¡Ya Estás Listo!

Tienes todo lo necesario para desarrollar de forma profesional en Django.

**Siguiente paso:**
```bash
python manage.py runserver
```

Y empieza a explorar la Debug Toolbar. 🚀

---

## 📞 Ayuda

Si tienes problemas:
1. ✅ Lee el [RESUMEN_INSTALACION.md](RESUMEN_INSTALACION.md) - Troubleshooting
2. ✅ Verifica: `python manage.py check`
3. ✅ Revisa que `DEBUG=True`
4. ✅ Consulta la documentación oficial

---

**¡Feliz desarrollo!** 🎈

Recuerda: La mejor herramienta es la que usas. Empieza con Debug Toolbar y explora el resto a tu ritmo.

