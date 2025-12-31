# Dependencias pendientes de revisar

Listado actual (1 noviembre 2025) de paquetes presentes en `requirements.full.txt` que aún no se han movido a `requirements/base.txt` ni `requirements/dev.txt`. Revísalos en pequeños bloques:

1. Busca si el paquete se usa (`rg "nombre_paquete"`).
2. Decide si debe ir a `base.txt`, a `dev.txt` o eliminarse.
3. Actualiza los ficheros y valida con `pip install -r requirements.txt` y `pytest`.

## Paquetes a evaluar

- python-dateutil==2.9.0.post0; pytz==2024.1; tzdata==2024.1 - confirmar si queremos depender solo de `django` + `tzdata`.
- python3-openid==3.2.0 - llega con `django-allauth`; mantener si se usa login social.
- referencing==0.36.2 - transitivo de `jsonschema`; eliminar si se retira.
- xraylib==4.1.5 - librería específica de materiales; validar con apps científicas.
- scikit-image, scikit-learn, scipy, seaborn - decidir si forman parte del stack de análisis (probablemente sí).
- selenium==4.29.0 - mantener si existen tests/automatizaciones.
- six==1.16.0 - requerido por varias dependencias antiguas; verificar.
- sniffio==1.3.1; trio==0.29.0; trio-websocket==0.12.2 - llegan con selenium; revisar si son necesarios.
- sortedcontainers==2.4.0; soupsieve==2.5; tabulate==0.9.0; toolz==0.12.1; tqdm==4.66.4 - comprobar usos puntuales.
- SQLAlchemy==0.7.10 / sqlalchemy-migrate==0.11.0 - versiones muy antiguas; evaluar eliminación.
- statsmodels==0.14.4; symengine==0.14.0; sympy==1.12.1 - mantener solo si los laboratorios los necesitan.
- streamlit==1.43.1 - eliminar si no hay aplicaciones Streamlit.
- tenacity==9.0.0 - común en combinaciones con `requests`; confirmar uso.
- threadpoolctl==3.5.0 - transitivo de scikit-learn.
- tifffile==2024.7.2; tinydb==4.8.2 - revisar scripts específicos.
- toml==0.10.2 - tal vez necesario para `pre-commit`.
- traits==6.4.3 / traitsui==8.0.0 - usados por bibliotecas científicas; confirmar.
- typing_extensions==4.12.2 - mantener en base si es requisito de dependencias.
- uritemplate==4.1.1; urllib3==2.2.2 — transitivo de `requests`.
- watchdog==6.0.0; websocket-client==1.8.0; wsproto==1.2.0 — comprobar usos en automatización.
- xarray==2025.3.0; XlsxWriter==3.1.9; xlrd==0.7.1; xlwt==0.7.2 — validar con módulos de hojas de cálculo.
- zipp==3.19.2 — transitivo de importlib_metadata; se eliminará si limamos dependencias.
