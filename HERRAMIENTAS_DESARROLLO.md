# 🛠️ Herramientas de Desarrollo - SIGMA FUSION

Esta guía describe todas las herramientas de desarrollo disponibles en el proyecto. **Todas estas herramientas solo están activas cuando `DEBUG=True`** y se desactivan automáticamente en producción.

---

## 🎯 Herramientas Principales

### 1. **Django Debug Toolbar** ⭐ (RECIÉN INSTALADO)

La herramienta más útil para desarrollo Django. Muestra información detallada sobre cada request.

#### ¿Qué hace?
- **Ver qué templates se usan**: Muestra todos los templates renderizados (base, includes, el actual)
- **Ver queries SQL**: Muestra todas las consultas a la base de datos y cuánto tiempo toman
- **Ver variables de contexto**: Muestra todas las variables disponibles en los templates
- **Performance**: Muestra tiempo de renderizado, cache hits, señales, etc.

#### ¿Cómo usarla?
1. Inicia el servidor: `python manage.py runserver`
2. Ve a cualquier página de tu aplicación
3. Verás una **barra lateral derecha** con pestañas (SQL, Templates, Time, etc.)
4. Click en **"Templates"** para ver qué archivos se están usando

#### Panel de Templates
```
Templates (3 rendered)
├── templates/portal/home.html (14.2ms)
├── templates/base_icts.html (2.1ms)
└── includes/navbar.html (0.8ms)
```
¡Exactamente lo que necesitabas! Ya no tendrás que buscar qué template está activo.

#### Configuración personalizada
Ya está configurada en `automatizacion/settings.py`:
- Solo aparece cuando `DEBUG=True`
- Muestra el contexto completo de templates
- Configurada para `localhost` y `127.0.0.1`

---

### 2. **Django Extensions** ⭐

Añade comandos útiles de gestión y herramientas de desarrollo.

#### Comandos más útiles:

##### `shell_plus`
Shell de Python mejorado con todos los modelos importados automáticamente.
```bash
python manage.py shell_plus
```
En lugar de:
```python
from sigmalab.models import Equipment
from accounts.models import User
```
Todos los modelos ya están importados:
```python
>>> Equipment.objects.all()  # Listo para usar
>>> User.objects.filter(is_active=True)
```

##### `show_urls`
Lista todas las URLs del proyecto (muy útil para debugging).
```bash
python manage.py show_urls
```
Salida:
```
/admin/                  django.contrib.admin.site.urls
/icts/equipos/           icts.views.equipment_list
/dtf/lab/                sigmalab.views.lab_home
...
```

##### `show_urls` con búsqueda
```bash
python manage.py show_urls | grep sigmalab
```

##### `runserver_plus`
Servidor de desarrollo mejorado con debugger interactivo Werkzeug.
```bash
python manage.py runserver_plus
```
Cuando hay un error, puedes ejecutar código Python en el navegador en cada punto del stack trace.

##### `print_settings`
Muestra todas las configuraciones activas.
```bash
python manage.py print_settings
```

##### `graph_models`
Genera diagramas de tus modelos (requiere graphviz instalado).
```bash
# Todos los modelos
python manage.py graph_models -a -o models.png

# Solo una app
python manage.py graph_models icts -o icts_models.png
```

---

### 3. **Pytest y Pytest-Django** 🧪

Framework de testing moderno y potente.

#### Ventajas sobre unittest:
- Sintaxis más simple
- Mejor output de errores
- Fixtures reutilizables
- Plugins poderosos

#### Uso básico:
```bash
# Ejecutar todos los tests
pytest

# Ejecutar tests de una app
pytest icts/tests.py

# Ejecutar con verbose
pytest -v

# Ejecutar con coverage
pytest --cov=icts --cov-report=html
```

#### Ejemplo de test:
```python
# tests.py
import pytest
from django.contrib.auth import get_user_model

@pytest.mark.django_db
def test_user_creation():
    User = get_user_model()
    user = User.objects.create_user(
        username='test',
        email='test@example.com',
        password='test123'
    )
    assert user.username == 'test'
    assert user.email == 'test@example.com'
```

---

### i18n (gettext)

Para generar y compilar traducciones de forma reproducible:
```bash
python manage.py makemessages -l en -l fr
python manage.py compilemessages
```

Requisitos (Windows):
- Instala gettext y asegurate de que `msgfmt` y `msguniq` esten en PATH.
- Opciones habituales: `choco install gettext` o `scoop install gettext`.
- Abre una nueva terminal despues de instalar.

Requisitos (CI/Linux):
- Instala gettext en la imagen de CI (ej. `apt-get install gettext`).
- Verifica con `msgfmt --version` y `msguniq --version`.

---

### 4. **Coverage** 📊

Mide qué porcentaje de tu código está cubierto por tests.

```bash
# Ejecutar tests con coverage
pytest --cov=icts --cov=sigmalab --cov-report=html

# Ver reporte en el navegador
# Abre: htmlcov/index.html
```

El reporte HTML muestra:
- Líneas cubiertas en verde
- Líneas no cubiertas en rojo
- Porcentaje de cobertura por archivo

---

### 5. **Black** 🎨

Formateador de código Python automático. **Zero configuration**.

```bash
# Formatear un archivo
black archivo.py

# Formatear toda una app
black icts/

# Formatear todo el proyecto
black .

# Solo verificar sin cambios
black --check .

# Ver qué cambiaría
black --diff .
```

Beneficios:
- Código consistente en todo el proyecto
- No más discusiones sobre estilo
- Ahorra tiempo en code reviews

---

### 6. **Flake8** ✅

Linter que detecta errores de estilo y problemas potenciales.

```bash
# Analizar todo el proyecto
flake8

# Analizar una app específica
flake8 icts/

# Ignorar errores específicos
flake8 --ignore=E501,W503

# Ver estadísticas
flake8 --statistics
```

Detecta:
- Variables no usadas
- Imports no utilizados
- Errores de sintaxis
- Violaciones de PEP 8
- Complejidad ciclomática alta

---

### 7. **isort** 📦

Ordena y organiza los imports automáticamente.

```bash
# Ordenar imports en un archivo
isort archivo.py

# Ordenar en toda una app
isort icts/

# Ordenar todo
isort .

# Ver qué cambiaría
isort --diff .

# Compatible con black
isort --profile black .
```

Antes:
```python
from django.contrib.auth import get_user_model
import os
from .models import Equipment
import sys
from django.db import models
```

Después:
```python
import os
import sys

from django.contrib.auth import get_user_model
from django.db import models

from .models import Equipment
```

---

## 🔄 Workflow Recomendado

### Antes de hacer commit:

```bash
# 1. Formatear código
black .

# 2. Ordenar imports
isort --profile black .

# 3. Verificar estilo
flake8

# 4. Ejecutar tests
pytest

# 5. Ver coverage (opcional)
pytest --cov --cov-report=term-missing
```

### Script todo-en-uno (crear en la raíz):

Crea un archivo `dev_check.py`:
```python
#!/usr/bin/env python
"""Run all development checks"""
import subprocess
import sys

def run(cmd, description):
    print(f"\n{'='*60}")
    print(f"  {description}")
    print(f"{'='*60}")
    result = subprocess.run(cmd, shell=True)
    if result.returncode != 0:
        print(f"❌ {description} failed!")
        return False
    print(f"✅ {description} passed!")
    return True

checks = [
    ("black --check .", "Black format check"),
    ("isort --check-only --profile black .", "Import sorting check"),
    ("flake8 --max-line-length=88 --extend-ignore=E203,W503", "Flake8 linting"),
    ("pytest --maxfail=1", "Unit tests"),
]

all_passed = all(run(cmd, desc) for cmd, desc in checks)
sys.exit(0 if all_passed else 1)
```

Luego:
```bash
python dev_check.py
```

---

## 🎓 Otras Herramientas Ya Disponibles

### Django Admin Interface
Ya instalado (`django-admin-interface==0.28.5`)
- Admin de Django con tema moderno
- Más visual y agradable

### Widget Tweaks
Ya instalado (`django-widget-tweaks==1.5.0`)
- Facilita personalizar widgets de formularios en templates
```django
{% load widget_tweaks %}
{{ form.username|add_class:"form-control" }}
```

### Django Crispy Forms + Bootstrap5
Ya instalado (`django-crispy-forms==2.1`, `crispy-bootstrap5==2023.10`)
- Renderiza formularios con estilos Bootstrap automáticamente
```django
{% load crispy_forms_tags %}
{{ form|crispy }}
```

### Django CORS Headers
Ya instalado (`django-cors-headers==4.3.1`)
- Maneja CORS para APIs
- Útil si tienes frontend separado

### Django REST Framework
Ya instalado (`djangorestframework==3.14.0`)
- Framework para crear APIs REST
- Serializers, ViewSets, Routers, etc.

---

## 🚀 Tips de Productividad

### 1. Alias útiles (PowerShell)
Añade a tu perfil de PowerShell (`$PROFILE`):
```powershell
# Django
function rs { python manage.py runserver }
function mm { python manage.py makemigrations }
function m { python manage.py migrate }
function sp { python manage.py shell_plus }
function su { python manage.py show_urls }

# Testing
function t { pytest }
function tc { pytest --cov --cov-report=html }

# Code quality
function fmt { black . ; isort --profile black . }
function check { flake8 ; pytest }
```

Luego puedes hacer:
```bash
rs        # En lugar de python manage.py runserver
sp        # En lugar de python manage.py shell_plus
fmt       # Formatear todo el código
```

### 2. VS Code / Cursor Extensions recomendadas
- **Python** (Microsoft)
- **Pylance** (Microsoft)
- **Django** (Baptiste Darthenay)
- **Better Jinja** (samuelcolvin)
- **SQLite Viewer** (Florian Klampfer)

### 3. Configuración VS Code / Cursor
Crea `.vscode/settings.json`:
```json
{
    "python.linting.enabled": true,
    "python.linting.flake8Enabled": true,
    "python.formatting.provider": "black",
    "editor.formatOnSave": true,
    "python.linting.flake8Args": [
        "--max-line-length=88",
        "--extend-ignore=E203,W503"
    ],
    "[python]": {
        "editor.codeActionsOnSave": {
            "source.organizeImports": true
        }
    }
}
```

---

## 📚 Recursos Adicionales

### Django Debug Toolbar
- [Documentación oficial](https://django-debug-toolbar.readthedocs.io/)
- [Tutorial en español](https://www.youtube.com/watch?v=example)

### Django Extensions
- [Documentación oficial](https://django-extensions.readthedocs.io/)
- [Lista completa de comandos](https://django-extensions.readthedocs.io/en/latest/command_extensions.html)

### Pytest
- [Documentación oficial](https://docs.pytest.org/)
- [Pytest-Django docs](https://pytest-django.readthedocs.io/)

### Code Quality
- [Black docs](https://black.readthedocs.io/)
- [Flake8 docs](https://flake8.pycqa.org/)
- [isort docs](https://pycqa.github.io/isort/)

---

## ⚠️ Importante

**Todas estas herramientas de debugging:**
- ✅ Solo están activas cuando `DEBUG=True`
- ✅ Se desactivan automáticamente en producción
- ✅ No afectan el rendimiento en producción
- ✅ No aparecen en el código final

Para producción, recuerda:
```bash
export DJANGO_DEBUG=False
export DJANGO_SECRET_KEY="your-production-secret-key"
export DJANGO_ALLOWED_HOSTS="your-domain.com,www.your-domain.com"
```

---

## 🎉 ¡Listo para Desarrollar!

Ahora tienes acceso a herramientas profesionales que usan los mejores equipos de desarrollo Django.

**Siguiente paso**: Inicia el servidor y mira la Debug Toolbar en acción:
```bash
python manage.py runserver
```

Luego visita cualquier página y verás la barra lateral derecha con toda la información. 🚀

