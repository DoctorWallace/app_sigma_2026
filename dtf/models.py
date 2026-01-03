from django.db import models
from django.conf import settings


class DTFUserProfile(models.Model):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="dtf_profile")
    is_ciemat = models.BooleanField(default=False)
    departamento = models.CharField(max_length=50, blank=True)
    division_unidad = models.CharField(max_length=200, blank=True)
    matricula = models.CharField(max_length=50, blank=True)
    telefono_interno = models.CharField(max_length=20, blank=True)
    
    # Seguimiento de acceso a información importante
    info_importante_completada = models.BooleanField(default=False, help_text="Ha completado la lectura de información importante")
    info_importante_inicio = models.DateTimeField(null=True, blank=True, help_text="Hora de inicio de acceso a información importante")
    info_importante_fin = models.DateTimeField(null=True, blank=True, help_text="Hora de finalización de acceso a información importante")
    
    # Gestión de accesos por técnicos
    acceso_s_lab_restringido = models.BooleanField(default=False, help_text="Acceso a S-LAB restringido por técnico")
    acceso_s_mec_restringido = models.BooleanField(default=False, help_text="Acceso a S-MEC restringido por técnico")
    acceso_s_dp_restringido = models.BooleanField(default=False, help_text="Acceso a S-DP restringido por técnico")
    acceso_s_optics_restringido = models.BooleanField(default=False, help_text="Acceso a S-OPTICS restringido por tecnico")
    motivo_restriccion = models.TextField(blank=True, help_text="Motivo de la restricción de acceso")
    restriccion_fecha = models.DateTimeField(null=True, blank=True, help_text="Fecha de aplicación de la restricción")
    restriccion_por = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name="restricciones_aplicadas", help_text="Técnico que aplicó la restricción")

    def __str__(self):
        return f"DTFProfile({self.user_id})"


class InfoImportanteAcceso(models.Model):
    """Registra el acceso a cada sección de información importante"""
    SECCIONES = [
        ('seguridad', 'Seguridad'),
        ('uso_equipos', 'Uso de Equipos'),
        ('normas_obligatorias', 'Normas Obligatorias'),
    ]
    
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="accesos_info_importante")
    seccion = models.CharField(max_length=20, choices=SECCIONES)
    accedido_en = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        unique_together = ('user', 'seccion')
        ordering = ['-accedido_en']
    
    def __str__(self):
        return f"{self.user.username} - {self.get_seccion_display()} ({self.accedido_en})"
