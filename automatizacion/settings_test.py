import os

os.environ.setdefault("DJANGO_SECRET_KEY", "pytest-secret-key")
os.environ.setdefault("DJANGO_DEBUG", "1")

from .settings import *  # noqa: F401,F403

INSTALLED_APPS = [app for app in INSTALLED_APPS if app != "debug_toolbar"]  # type: ignore[name-defined]
MIDDLEWARE = [
    mw
    for mw in MIDDLEWARE  # type: ignore[name-defined]
    if mw != "debug_toolbar.middleware.DebugToolbarMiddleware"
]
if not DEBUG and SECRET_KEY == "dev-unsafe-secret-key":
    raise ImproperlyConfigured("Production deployments must define DJANGO_SECRET_KEY.")
