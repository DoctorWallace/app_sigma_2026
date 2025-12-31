# icts/apps.py
from django.apps import AppConfig

class IctsConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "icts"          # ← correcto
    # no definas 'label' a menos que sepas por qué
    def ready(self):
        from . import signals  # si añadimos señales
