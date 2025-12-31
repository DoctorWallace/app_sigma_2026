from django.apps import AppConfig


class SigmadpConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'sigmadp'
    verbose_name = 'SIGMA DP - Desorción y Permeación'
    
    def ready(self):
        import sigmadp.signals

