from django.apps import AppConfig

class SigmalabConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "sigmalab"

    def ready(self):
        # Crea grupos tras migraciones
        from django.db.models.signals import post_migrate
        from .signals import create_sigmalab_groups
        post_migrate.connect(create_sigmalab_groups, sender=self)
