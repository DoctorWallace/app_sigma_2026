# Gestión de dependencias

- `base.txt`: paquetes necesarios para ejecutar la aplicación SIGMA en producción (Django, librerías de tratamiento de archivos y generación de informes).
- `dev.txt`: utilidades solo usadas durante el desarrollo (pytest, black, django-debug-toolbar, etc.).
- `requirements.txt`: incluye ambos mediante `-r`.
- `requirements.full.txt`: copia del listado original para revisar con calma qué otros paquetes siguen siendo necesarios. Cuando confirmes un paquete, muévelo a `base.txt` o `dev.txt`; si no se usa, elimínalo y guarda una nota del motivo.

Flujo sugerido cuando quieras podar dependencias:

1. Busca en el código si el paquete se importa (`rg "import <paquete>"`).
2. Si lo usas en producción, colócalo en `base.txt`. Si solo te ayuda en desarrollo o scripts de mantenimiento, pásalo a `dev.txt`.
3. Ejecuta `pip install -r requirements.txt` y lanza las pruebas (`pytest`) para asegurarte de que todo sigue funcionando.
4. Haz commit del cambio y actualiza esta nota si hace falta.
