# ✅ Test de Verificación - Django Debug Toolbar

Este documento te guía para verificar que la instalación funcionó correctamente.

---

## 🧪 Test Rápido (2 minutos)

### Paso 1: Verificar configuración Django

```bash
python manage.py check
```

**Resultado esperado:**
```
System check identified no issues (0 silenced).
```
✅ Si ves esto, la configuración está correcta.

---

### Paso 2: Iniciar el servidor

```bash
python manage.py runserver
```

**Resultado esperado:**
```
Watching for file changes with StatReloader
Performing system checks...

System check identified no issues (0 silenced).
October 11, 2025 - 10:30:00
Django version 5.0.1, using settings 'automatizacion.settings'
Starting development server at http://127.0.0.1:8000/
Quit the server with CTRL-BREAK.
```

✅ Si el servidor arranca sin errores, todo está bien.

---

### Paso 3: Verificar Debug Toolbar en el navegador

1. **Abre tu navegador**
2. **Ve a**: `http://127.0.0.1:8000/`
3. **Busca una barra lateral derecha** con pestañas

**¿Qué deberías ver?**

```
┌───────────────────────────────────┐
│  Tu página web                    │
│                                   │  ┌────────────┐
│  [Contenido normal...]            │  │ DjDT       │
│                                   │  ├────────────┤
│                                   │  │ History    │
│                                   │  │ Versions   │
│                                   │  │ Time       │
│                                   │  │ SQL        │
│                                   │  │ Templates  │ ← Este
│                                   │  │ Cache      │
│                                   │  │ Signals    │
│                                   │  └────────────┘
└───────────────────────────────────┘
```

✅ Si ves la barra lateral, ¡funciona perfectamente!

---

### Paso 4: Test del panel Templates

1. **Click en "Templates"** en la Debug Toolbar
2. Deberías ver una lista de templates como:
   ```
   Templates (X rendered)
   📄 templates/portal/home.html
   📄 templates/base_icts.html
   📄 ...
   ```

3. **Click en cualquier nombre de template**
4. Deberías ver:
   - Ruta completa del archivo
   - Variables de contexto
   - Tiempo de renderizado

✅ Si ves esta información, ¡todo funciona a la perfección!

---

## 🔍 Troubleshooting

### ❌ La Debug Toolbar NO aparece

#### Check 1: ¿DEBUG está en True?
```bash
python manage.py shell
```
```python
>>> from django.conf import settings
>>> print(settings.DEBUG)
True  # ← Debe ser True
>>> exit()
```

**Si es False:**
Verifica que no tengas variables de entorno que lo sobrescriban:
```bash
# PowerShell
$env:DJANGO_DEBUG = "True"

# Luego reinicia el servidor
```

---

#### Check 2: ¿Estás en localhost/127.0.0.1?

✅ Correcto:
- `http://127.0.0.1:8000/`
- `http://localhost:8000/`

❌ Incorrecto:
- `http://192.168.x.x:8000/`
- `http://tu-ip:8000/`

**Solución:** Usa localhost o 127.0.0.1

---

#### Check 3: ¿El paquete está instalado?

```bash
python -c "import debug_toolbar; print('✅ Instalado')"
```

**Si da error:**
```bash
pip install django-debug-toolbar
```

---

#### Check 4: ¿Está en INSTALLED_APPS?

```bash
python manage.py shell
```
```python
>>> from django.conf import settings
>>> 'debug_toolbar' in settings.INSTALLED_APPS
True  # ← Debe ser True
```

**Si es False:**
Revisa que en `settings.py` tengas:
```python
if DEBUG:
    INSTALLED_APPS += [
        "debug_toolbar",
        "django_extensions",
    ]
```

---

#### Check 5: ¿Está el middleware?

```bash
python manage.py shell
```
```python
>>> from django.conf import settings
>>> any('debug_toolbar' in m for m in settings.MIDDLEWARE)
True  # ← Debe ser True
```

**Si es False:**
Revisa que en `settings.py` tengas:
```python
if DEBUG:
    MIDDLEWARE.insert(0, 'debug_toolbar.middleware.DebugToolbarMiddleware')
```

---

#### Check 6: ¿Tu HTML tiene </body>?

La toolbar se inyecta justo antes de `</body>`.

**Verifica** que tu template base tenga:
```html
<!DOCTYPE html>
<html>
<head>...</head>
<body>
    ...
</body>  ← Debe existir
</html>
```

---

### ❌ Error al importar debug_toolbar

**Error:**
```
ModuleNotFoundError: No module named 'debug_toolbar'
```

**Solución:**
```bash
pip install django-debug-toolbar
```

---

### ❌ Error 404 en /__debug__/

Esto es normal si visitas `/__debug__/` directamente.

La toolbar aparece automáticamente en las páginas normales.

**Solución:** Visita una página normal de tu app, no `/__debug__/`

---

## 🎯 Tests Adicionales

### Test de Django Extensions

```bash
python manage.py show_urls
```

**Resultado esperado:**
Debe mostrar todas las URLs del proyecto.

✅ Si funciona, Django Extensions está correctamente instalado.

---

### Test de shell_plus

```bash
python manage.py shell_plus
```

**Resultado esperado:**
```
# Shell Plus Model Imports
from accounts.models import User
from icts.models import Equipment, Facility, Request
from sigmalab.models import LabRequest
...

Python 3.12.0 (...)
Type "help", "copyright", "credits" or "license" for more information.
(InteractiveConsole)
>>>
```

✅ Si ves los imports automáticos, funciona correctamente.

---

### Test del script de verificación

```bash
python dev_check.py
```

**Resultado esperado:**
```
======================================================================
  VERIFICACION DE CODIGO - SIGMA FUSION
======================================================================

>>> Ejecutando: Django System Check...
   Comando: python manage.py check

[OK] Django System Check - Pasado!

...

TODAS LAS VERIFICACIONES PASARON!
   Tu codigo esta listo para commit.
```

✅ Si pasa el check de Django, todo está bien.

---

## 📊 Checklist Final

Marca cada item cuando lo verifiques:

- [ ] `python manage.py check` pasa sin errores
- [ ] `python manage.py runserver` inicia correctamente
- [ ] La Debug Toolbar aparece en el navegador
- [ ] El panel "Templates" muestra información
- [ ] `python manage.py show_urls` funciona
- [ ] `python manage.py shell_plus` funciona
- [ ] `python dev_check.py` pasa el check de Django

**Si marcaste todos ✅ ¡La instalación fue exitosa!**

---

## 🎓 Siguiente Paso

Ahora que todo funciona, es hora de aprender a usar las herramientas:

1. 📖 Lee: [QUICK_START_DEV.md](QUICK_START_DEV.md)
2. 🎬 Lee: [DEMO_DEBUG_TOOLBAR.md](DEMO_DEBUG_TOOLBAR.md)
3. 🚀 Usa la Debug Toolbar en tu desarrollo diario

---

## 💡 Tips Post-Instalación

### Tip 1: Añade la toolbar a favoritos
Mantén siempre abierta la pestaña "Templates" mientras desarrollas.

### Tip 2: Aprende los atajos
- `Ctrl + Shift + I` para abrir DevTools del navegador
- Luego navega la Debug Toolbar

### Tip 3: Explora todos los paneles
No solo "Templates", también "SQL", "Time", etc. son muy útiles.

### Tip 4: Usa show_urls regularmente
```bash
python manage.py show_urls | grep icts
```
Para encontrar URLs rápidamente.

### Tip 5: Shell_plus es tu amigo
Úsalo en lugar de `python manage.py shell` siempre.

---

## 📞 ¿Problemas?

Si después de seguir el troubleshooting sigues con problemas:

1. ✅ Reinicia el servidor completamente
2. ✅ Borra cache del navegador
3. ✅ Prueba en modo incógnito
4. ✅ Verifica que no hay firewalls bloqueando
5. ✅ Revisa el archivo `automatizacion/settings.py`

---

## ✨ ¡Felicidades!

Si llegaste aquí y todos los tests pasaron, tienes instaladas herramientas profesionales de desarrollo Django.

**¡Ahora a desarrollar!** 🚀

```bash
python manage.py runserver
```

