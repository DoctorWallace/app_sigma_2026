from django.apps import AppConfig


class MecConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'mec'

    def ready(self):
        # Registrar señales (creación de grupos, etc.)
        try:
            from . import signals  # noqa: F401
        except Exception:
            pass
