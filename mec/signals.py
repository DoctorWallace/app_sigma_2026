from django.db.models.signals import post_migrate
from django.dispatch import receiver
from django.contrib.auth.models import Group


@receiver(post_migrate)
def ensure_mec_groups(sender, **kwargs):
    if sender.name != 'mec':
        return
    # Grupos canónicos para S-MEC (DTF)
    Group.objects.get_or_create(name="tecnico_responsable_s_mec")
