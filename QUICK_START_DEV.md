# 🚀 Quick Start - Herramientas de Desarrollo

Guía rápida de las herramientas más importantes. Para documentación completa ver [HERRAMIENTAS_DESARROLLO.md](HERRAMIENTAS_DESARROLLO.md).

---

## 🎯 La Herramienta Que Necesitabas: Django Debug Toolbar

### ¿Qué hace?
**Te muestra qué templates se están usando en cada página**, incluyendo los heredados.

### ¿Cómo usarla?
1. Inicia el servidor:
   ```bash
   python manage.py runserver
   ```

2. Ve a cualquier página de tu app en el navegador

3. Verás una **barra lateral derecha** con pestañas

4. Click en **"Templates"** y verás algo como:
   ```
   Templates (3 rendered)
   ├── templates/portal/home.html (14.2ms)
   ├── templates/base_icts.html (2.1ms)  ← Template base heredado
   └── includes/navbar.html (0.8ms)      ← Include usado
   ```

5. **Click en cualquier template** para ver:
   - Ruta completa del archivo
   - Variables de contexto disponibles
   - Dónde está ubicado en tu sistema

### ¡Eso es todo! 🎉
Ya no necesitas buscar qué template está activo. La toolbar te lo dice al instante.

---

## 📋 Comandos Más Útiles

### Ver templates activos
```bash
python manage.py runserver
# Luego visita tu página y mira la Debug Toolbar
```

### Ver todas las URLs del proyecto
```bash
python manage.py show_urls
```

### Shell con modelos auto-importados
```bash
python manage.py shell_plus
# Todos tus modelos ya están disponibles sin import
```

### Verificar calidad del código
```bash
python dev_check.py
```

### Formatear todo el código
```bash
black .
isort --profile black .
```

### Ejecutar tests
```bash
pytest
```

### i18n (gettext)
```bash
# Requiere msgfmt/msguniq en PATH
python manage.py makemessages -l en -l fr
python manage.py compilemessages
```
Windows: instala gettext (ej. `choco install gettext` o `scoop install gettext`) y abre una nueva terminal.
CI (Linux): instalar gettext (ej. `apt-get install gettext`).

### Tests con cobertura
```bash
pytest --cov --cov-report=html
# Abre htmlcov/index.html
```

---

## 🔧 Configuración Actual

### ✅ Ya Instalado y Configurado:
- **Django Debug Toolbar**: Ver templates, SQL, performance
- **Django Extensions**: Comandos útiles (`shell_plus`, `show_urls`, etc.)
- **Pytest**: Testing moderno
- **Black**: Formateo automático de código
- **Flake8**: Análisis de código
- **isort**: Ordenar imports

### ⚙️ Configuración automática en VS Code/Cursor:
- Formateo al guardar
- Organización de imports automática
- Linting en tiempo real
- Soporte Django templates

Todo está en `.vscode/settings.json`

---

## 🎓 Workflow Recomendado

### Cuando quieres modificar un template:
1. Visita la página en el navegador
2. Mira la Debug Toolbar (pestaña "Templates")
3. Ve qué archivo es y su ruta completa
4. Edita el archivo correcto

### Antes de hacer commit:
```bash
# Opción 1: Script todo-en-uno
python dev_check.py

# Opción 2: Manual
black .
isort --profile black .
flake8
pytest
```

---

## 💡 Tips Rápidos

### La Debug Toolbar no aparece?
Verifica:
1. ¿Tienes `DEBUG=True` en settings?
2. ¿Estás en `localhost` o `127.0.0.1`?
3. ¿El HTML tiene `</body>`? (la toolbar se inyecta ahí)

### Ver variables disponibles en un template:
1. Abre la página
2. Debug Toolbar → "Templates"
3. Click en el template que te interesa
4. Verás todas las variables del contexto

### Comandos de Django Extensions:
```bash
python manage.py help
# Busca los que empiezan con tu nombre (nuevos comandos añadidos)
```

---

## 🚨 Importante

Todas estas herramientas:
- ✅ Solo activas cuando `DEBUG=True`
- ✅ Se desactivan automáticamente en producción
- ✅ No afectan rendimiento en producción

---

## 📚 Más Información

- Guía completa: [HERRAMIENTAS_DESARROLLO.md](HERRAMIENTAS_DESARROLLO.md)
- Django Debug Toolbar: https://django-debug-toolbar.readthedocs.io/
- Django Extensions: https://django-extensions.readthedocs.io/

---

**¡Listo! Ahora puedes desarrollar más rápido y con mejores herramientas.** 🚀

Para empezar, simplemente ejecuta:
```bash
python manage.py runserver
```

Y visita cualquier página para ver la Debug Toolbar en acción.

