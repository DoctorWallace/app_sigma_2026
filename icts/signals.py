from django.db.models.signals import post_migrate
from django.dispatch import receiver
from django.contrib.auth.models import Group

@receiver(post_migrate)
def ensure_icts_groups(sender, **kwargs):
    # Solo cuando migra la app 'icts' o 'auth'
    if sender.name not in {"icts", "django.contrib.auth"}:
        return
    for name in ("icts_users", "revisores", "responsables", "managers"):
        Group.objects.get_or_create(name=name)
