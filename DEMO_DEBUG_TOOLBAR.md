# 🎬 Demo Visual: Django Debug Toolbar

Este documento muestra cómo se verá la Debug Toolbar en tu navegador.

---

## 🖼️ Vista General

Cuando visites cualquier página de tu aplicación (con `DEBUG=True`), verás algo así:

```
┌─────────────────────────────────────────────────────────────┐
│  Tu Página Web Normal                                       │
│                                                             │
│  ┌─────────────────────────────────────────┐               │
│  │  SIGMA FUSION                           │               │
│  │  [Menú] [Equipos] [Solicitudes] [...]  │               │
│  └─────────────────────────────────────────┘               │
│                                                             │
│  Contenido de tu página...                                 │
│                                                             │
│                                        ┌──────────────────┐│
│                                        │ DEBUG TOOLBAR    ││
│                                        │ ════════════════ ││
│                                        │                  ││
│                                        │ 📜 History       ││
│                                        │ 📦 Versions      ││
│                                        │ ⏱️  Time         ││
│                                        │ 🗄️  SQL          ││
│                                        │ 📄 Templates ⭐  ││
│                                        │ 💾 Cache         ││
│                                        │ 📡 Signals       ││
│                                        │ 📊 Settings      ││
│                                        │                  ││
│                                        └──────────────────┘│
└─────────────────────────────────────────────────────────────┘
```

La toolbar aparece como una **barra lateral derecha** que no interfiere con tu contenido.

---

## 🎯 Panel de Templates (El que necesitas)

Cuando haces click en **"Templates"**, se expande y muestra:

```
╔═══════════════════════════════════════════════════════════════╗
║  Templates (3 rendered)                             [↓ Hide]  ║
╠═══════════════════════════════════════════════════════════════╣
║                                                               ║
║  📄 templates/portal/home.html                                ║
║     ├─ Template path: C:\Users\...\templates\portal\home.html║
║     ├─ Render time: 14.23 ms                                 ║
║     └─ Context variables (12):                               ║
║        • user = <User: admin>                                ║
║        • request = <WSGIRequest: GET '/'>                    ║
║        • equipos = <QuerySet [Equipment(1), ...]>            ║
║        • perms = <PermWrapper>                               ║
║        • messages = []                                       ║
║        • ... (click para ver todos)                          ║
║                                                               ║
║  📄 templates/base_icts.html (inherited)                      ║
║     ├─ Template path: C:\Users\...\templates\base_icts.html  ║
║     ├─ Render time: 2.15 ms                                  ║
║     └─ Context: (inherited from child template)              ║
║                                                               ║
║  📄 includes/navbar.html (included)                           ║
║     ├─ Template path: C:\Users\...\includes\navbar.html      ║
║     ├─ Render time: 0.82 ms                                  ║
║     └─ Context: (shared from parent)                         ║
║                                                               ║
╚═══════════════════════════════════════════════════════════════╝
```

---

## 🔍 Detalles de un Template

Si haces click en cualquier nombre de template, se expande aún más:

```
╔═══════════════════════════════════════════════════════════════╗
║  📄 templates/portal/home.html                     [Click ✓]  ║
╠═══════════════════════════════════════════════════════════════╣
║                                                               ║
║  📍 Location:                                                 ║
║     C:\Users\marce\Desktop\SIGMA_FUSION\templates\portal\     ║
║     home.html                                                 ║
║                                                               ║
║  ⏱️  Render Time: 14.23 ms                                    ║
║                                                               ║
║  📦 Context Variables (12 total):                             ║
║  ┌─────────────────────────────────────────────────────────┐ ║
║  │ user                                                     │ ║
║  │   Type: django.contrib.auth.models.User                 │ ║
║  │   Value: <User: admin>                                  │ ║
║  │   ├─ username: "admin"                                  │ ║
║  │   ├─ email: "admin@example.com"                         │ ║
║  │   └─ is_authenticated: True                             │ ║
║  │                                                          │ ║
║  │ request                                                  │ ║
║  │   Type: django.core.handlers.wsgi.WSGIRequest           │ ║
║  │   Value: GET '/' from 127.0.0.1                         │ ║
║  │   ├─ method: "GET"                                      │ ║
║  │   ├─ path: "/"                                          │ ║
║  │   └─ GET: <QueryDict: {}>                               │ ║
║  │                                                          │ ║
║  │ equipos                                                  │ ║
║  │   Type: django.db.models.query.QuerySet                 │ ║
║  │   Value: [<Equipment: SEM>, <Equipment: Confocal>, ...] │ ║
║  │   Count: 15                                             │ ║
║  │                                                          │ ║
║  │ view                                                     │ ║
║  │   Type: portal.views.HomeView                           │ ║
║  │   Value: <HomeView object>                              │ ║
║  │                                                          │ ║
║  │ ... (click para expandir cada variable)                 │ ║
║  └─────────────────────────────────────────────────────────┘ ║
║                                                               ║
║  🔗 Template Inheritance:                                     ║
║     home.html                                                 ║
║       └─ extends base_icts.html                               ║
║            └─ extends base.html                               ║
║                                                               ║
║  📥 Template Includes:                                        ║
║     • includes/navbar.html                                    ║
║     • includes/footer.html                                    ║
║                                                               ║
╚═══════════════════════════════════════════════════════════════╝
```

---

## 💡 Casos de Uso Reales

### Caso 1: "¿Qué template se está usando aquí?"

**Antes** (sin Debug Toolbar):
1. Inspeccionar código HTML
2. Buscar algún texto único
3. Grep en toda la carpeta templates
4. Probar varios archivos
5. ❌ Perder 10 minutos

**Ahora** (con Debug Toolbar):
1. Mirar la toolbar → Templates
2. ✅ ¡Ahí está! `templates/portal/home.html`
3. ⏱️ 5 segundos

---

### Caso 2: "¿De dónde viene esta variable?"

**Antes**:
1. Buscar en la vista
2. Buscar en context processors
3. Buscar en middleware
4. ❌ No estás seguro

**Ahora**:
1. Debug Toolbar → Templates
2. Expandir template
3. Buscar la variable en el listado
4. ✅ Ver su valor, tipo y origen
5. ⏱️ 10 segundos

---

### Caso 3: "¿Por qué esta página es lenta?"

**Antes**:
1. ¿Es la vista?
2. ¿Es la base de datos?
3. ¿Es el template?
4. ❌ No lo sabes

**Ahora**:
1. Debug Toolbar → Time
   ```
   Total time: 245.67 ms
   ├─ View: 12.34 ms
   ├─ Template: 18.92 ms  
   └─ Database: 214.41 ms  ← ¡Aquí está el problema!
   ```
2. Debug Toolbar → SQL
   ```
   195 queries in 214.41 ms
   ⚠️ 190 similar queries detected (N+1 problem)
   ```
3. ✅ Identificado: problema de N+1
4. ⏱️ 30 segundos

---

## 🗄️ Otros Paneles Útiles

### Panel SQL
```
╔═══════════════════════════════════════════════════════════════╗
║  SQL queries (15 total)                        Time: 12.45 ms ║
╠═══════════════════════════════════════════════════════════════╣
║  1. SELECT * FROM auth_user WHERE id = 1          0.52 ms    ║
║     Stack trace: views.py:45 in get_context_data             ║
║                                                               ║
║  2. SELECT * FROM icts_equipment WHERE active = 1  1.23 ms   ║
║     Stack trace: views.py:47 in get_context_data             ║
║     ⚠️ Similar query repeated 10 times!                      ║
║                                                               ║
║  ... (click en cada query para ver detalles)                 ║
╚═══════════════════════════════════════════════════════════════╝
```

### Panel Time
```
╔═══════════════════════════════════════════════════════════════╗
║  ⏱️  Timeline                                                 ║
╠═══════════════════════════════════════════════════════════════╣
║  Total: 245.67 ms                                             ║
║  ├─ View: 12.34 ms (5%)                                       ║
║  ├─ Template: 18.92 ms (8%)                                   ║
║  └─ Database: 214.41 ms (87%) ⚠️                              ║
║                                                               ║
║  📊 Breakdown:                                                ║
║  ████████████████████████████████████████████ Database 87%   ║
║  ████ Template 8%                                             ║
║  ██ View 5%                                                   ║
╚═══════════════════════════════════════════════════════════════╝
```

---

## 🎮 Interactividad

La toolbar es **completamente interactiva**:

- ✅ Click para expandir/contraer paneles
- ✅ Click en nombres de templates para ver detalles
- ✅ Click en queries SQL para ver stacktrace
- ✅ Click en variables para ver su contenido completo
- ✅ Ocultar/mostrar la toolbar con un botón
- ✅ Navegar entre requests anteriores (History)

---

## 🎨 Apariencia

La toolbar tiene:
- 🎨 Diseño moderno y limpio
- 🌙 Fondo oscuro semi-transparente
- 📱 Responsive (se adapta al tamaño de pantalla)
- 🖱️ No interfiere con el contenido de la página
- ⌨️ Se puede ocultar/mostrar fácilmente
- 🎯 Información organizada en pestañas

---

## 📱 En pantallas pequeñas

En móvil o pantallas pequeñas, la toolbar se minimiza a un icono:

```
Tu Página
┌──────────────────────┐
│                      │
│  Contenido...        │
│                      │  [🛠️]  ← Click aquí
│                      │
│                      │
└──────────────────────┘
```

---

## 🚀 Primera Vez Usándola

Cuando arranques el servidor y visites una página:

1. **Aparecerá la toolbar** en la derecha
2. **No te asustes** - es normal, es parte del desarrollo
3. **Explora las pestañas** - especialmente "Templates"
4. **Disfruta** de la información útil

---

## ⚡ Tips Pro

1. **Mantén abierta la pestaña Templates** mientras desarrollas
2. **Usa el panel SQL** para detectar queries lentas
3. **Revisa el Time** si una página carga lento
4. **El panel History** te permite revisar requests anteriores
5. **Settings** te muestra toda la configuración de Django

---

## 🎯 Conclusión

La Django Debug Toolbar es como tener **rayos X de tu aplicación**.

Ya no tendrás que adivinar:
- ✅ Qué template se usa
- ✅ Qué variables están disponibles
- ✅ Cuántas queries se ejecutan
- ✅ Dónde está el cuello de botella
- ✅ Qué configuración está activa

Todo visible en tiempo real, mientras navegas tu app.

---

**¡Hora de probarlo!**

```bash
python manage.py runserver
```

Luego abre tu navegador en `http://127.0.0.1:8000/` y disfruta de tu nueva superpoder de desarrollo. 🦸‍♂️

---

## 📚 Documentación Visual

Para ver capturas de pantalla reales y ejemplos más detallados:
- https://django-debug-toolbar.readthedocs.io/en/latest/
- https://github.com/jazzband/django-debug-toolbar

---

**¡Feliz debugging!** 🐛🔨

