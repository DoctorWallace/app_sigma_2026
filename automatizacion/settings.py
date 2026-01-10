

import os
from pathlib import Path
from django.core.exceptions import ImproperlyConfigured

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent


# Quick-start development settings - unsuitable for production
# See https://docs.djangoproject.com/en/5.0/howto/deployment/checklist/

def _get_env_bool(name: str, default: bool) -> bool:
    """Return boolean environment flag supporting common truthy strings."""
    raw = os.environ.get(name)
    if raw is None:
        return default
    return raw.strip().lower() in {"1", "true", "yes", "on"}


# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = _get_env_bool("DJANGO_DEBUG", True)


def _get_env(name: str, *, default: str | None = None, required: bool = False) -> str:
    """Fetch environment setting with optional requirement enforcement."""
    value = os.environ.get(name, default)
    if required and (value is None or value == ""):
        raise ImproperlyConfigured(f"Missing required environment variable: {name}")
    return value


# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = _get_env(
    "DJANGO_SECRET_KEY",
    default="dev-unsafe-secret-key",
    required=not DEBUG,
)

if not DEBUG and SECRET_KEY == "dev-unsafe-secret-key":
    raise ImproperlyConfigured("Production deployments must define DJANGO_SECRET_KEY.")


def _parse_allowed_hosts(raw: str | None) -> list[str]:
    if not raw:
        return []
    return [host.strip() for host in raw.split(",") if host.strip()]


def _parse_path_list(env_name: str, default: list[Path]) -> list[Path]:
    raw = os.environ.get(env_name)
    if not raw:
        return [Path(path).expanduser().resolve(strict=False) for path in default]
    paths: list[Path] = []
    for chunk in raw.split(os.pathsep):
        cleaned = chunk.strip()
        if not cleaned:
            continue
        paths.append(Path(cleaned).expanduser().resolve(strict=False))
    return paths


_allowed_hosts_raw = _get_env(
    "DJANGO_ALLOWED_HOSTS",
    default="localhost,127.0.0.1" if DEBUG else None,
    required=not DEBUG,
)
ALLOWED_HOSTS = _parse_allowed_hosts(_allowed_hosts_raw)


# Application definition

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",  # ← coma necesaria aquí
    "portal",
    "dtf",
    "labtemp",
    "accounts",
    "mec",
    "core",
    "sigmalab.apps.SigmalabConfig",
    "icts.apps.IctsConfig",
    "icts.sigmasem.apps.SigmasemConfig",
    "icts.sigmasims.apps.SigmaSimsConfig",
    "sigmadp.apps.SigmadpConfig",
    "sigmaconf.apps.SigmaconfConfig",
    "sigmaimp.apps.SigmaimpConfig",
    "sigmavdg.apps.SigmavdgConfig",
    "sigmaoptics.apps.SigmaopticsConfig",
    "sigmaoptics_icts.apps.SigmaOpticsICTSConfig",
    "sigmaprofilometer.apps.SigmaprofilometerConfig",
    "widget_tweaks",
]

# Development tools (only active when DEBUG=True)
if DEBUG:
    INSTALLED_APPS += [
        "debug_toolbar",
        "django_extensions",
    ]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'automatizacion.middleware.NoCacheMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.locale.LocaleMiddleware',
    'core.middleware.ForceSpanishForLabUrlsMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    # 'core.middleware.ModuleAccessMiddleware',  # Temporalmente deshabilitado para debug
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

# Add Debug Toolbar middleware when DEBUG=True
if DEBUG:
    MIDDLEWARE.insert(0, 'debug_toolbar.middleware.DebugToolbarMiddleware')

ROOT_URLCONF = 'automatizacion.urls'

TEMPLATES = [{
    "BACKEND": "django.template.backends.django.DjangoTemplates",
    "DIRS": [BASE_DIR / "templates"],
    "APP_DIRS": True,
    "OPTIONS": {
        "context_processors": [
        "django.template.context_processors.debug",
        "django.template.context_processors.request",
        "django.contrib.auth.context_processors.auth",
        "django.contrib.messages.context_processors.messages",
        "django.template.context_processors.i18n",
        "dtf.context_processors.dtf_cta_links",
        "sigmalab.context_processors.lab_role",
        "mec.context_processors.mec_role",
            "sigmadp.context_processors.dp_role",
            "icts.context_processors.icts_ui",
        ],
    },
}]


MEDIA_URL = "/media/"
MEDIA_ROOT = BASE_DIR / "media"
STATIC_URL = "static/"
STATICFILES_DIRS = [BASE_DIR/"static"]

SIGMASEM_ALLOWED_BROWSE_ROOTS = _parse_path_list(
    "SIGMASEM_ALLOWED_BROWSE_ROOTS",
    [MEDIA_ROOT / "sem_files"],
)


WSGI_APPLICATION = 'automatizacion.wsgi.application'


# Database
# https://docs.djangoproject.com/en/5.0/ref/settings/#databases

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': BASE_DIR / 'db.sqlite3',
    }
}


# Password validation
# https://docs.djangoproject.com/en/5.0/ref/settings/#auth-password-validators

AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
]


# Internationalization
# https://docs.djangoproject.com/en/5.0/topics/i18n/

LANGUAGE_CODE = 'es-es'
LANGUAGES = [
    ("en", "English"),
    ("fr", "Français"),
    ("es", "Español"),
]
LOCALE_PATHS = [BASE_DIR / "locale"]

TIME_ZONE = 'Europe/Madrid'

USE_I18N = True

USE_TZ = True


# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/5.0/howto/static-files/

# Default primary key field type
# https://docs.djangoproject.com/en/5.0/ref/settings/#default-auto-field

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'



LOGIN_URL = "/accounts/login/"          # ← router que decide ICTS o DTF
LOGIN_REDIRECT_URL = "/"                # ← valor neutro (las vistas de login ya redirigen bien)
LOGOUT_REDIRECT_URL = "/"

EMAIL_BACKEND = "django.core.mail.backends.console.EmailBackend"
DEFAULT_FROM_EMAIL = "sigma-dtf@localhost"

# ICTS review threshold (fallback used by views if overridden elsewhere).
ICTS_MIN_REVIEWS_REQUIRED = 4

# Optional LO3 notice signature overrides (leave name empty to fallback to technician).
LO3_RESPONSIBLE_NAME = ""
LO3_RESPONSIBLE_TITLE = "Responsable de LO3 Metrolog\u00eda de superficies \u00f3pticas 3D."

# ============================================================================
# DEVELOPMENT TOOLS CONFIGURATION (only active when DEBUG=True)
# ============================================================================

if DEBUG:
    # Django Debug Toolbar - Show which templates are being used
    INTERNAL_IPS = [
        "127.0.0.1",
        "localhost",
    ]
    
    # Debug Toolbar configuration
    DEBUG_TOOLBAR_CONFIG = {
        "SHOW_TOOLBAR_CALLBACK": lambda request: DEBUG,
        "SHOW_TEMPLATE_CONTEXT": True,
    }
    
    # Django Extensions configuration
    # Enables useful management commands like:
    # - shell_plus: Enhanced shell with all models auto-imported
    # - show_urls: List all URL patterns
    # - runserver_plus: Enhanced dev server with Werkzeug debugger
    SHELL_PLUS_PRINT_SQL = True  # Show SQL queries in shell_plus
