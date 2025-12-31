from django.contrib.auth.models import Group


def create_sigmalab_groups(sender, **kwargs):
    """Crea grupos canónicos para DTF con nombres homogéneos (ASCII)."""
    names = [
        # DTF comunes
        "usuarios_dtf",
        # Responsables por laboratorio
        "tecnico_responsable_s_lab",
        "tecnico_responsable_s_mec",
        "tecnico_responsable_s_dp",
        # Usuarios especiales
        "usuarios_autonomo_s_lab",
    ]
    for name in names:
        Group.objects.get_or_create(name=name)
