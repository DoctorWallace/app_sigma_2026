"""
Migración para crear todos los grupos canónicos necesarios.
Reemplaza la lógica de limpieza problemática con una fuente de verdad única.
"""
from django.db import migrations
from core.roles import CANONICAL_GROUP_NAMES


def create_canonical_groups(apps, schema_editor):
    """Crear todos los grupos canónicos necesarios."""
    Group = apps.get_model('auth', 'Group')
    
    created_groups = []
    for group_name in CANONICAL_GROUP_NAMES:
        group, created = Group.objects.get_or_create(name=group_name)
        if created:
            created_groups.append(group_name)
    
    if created_groups:
        print(f"✅ Grupos creados: {', '.join(created_groups)}")
    else:
        print("ℹ️  Todos los grupos canónicos ya existen")


def cleanup_legacy_groups(apps, schema_editor):
    """Limpiar grupos legados que no están en la lista canónica."""
    Group = apps.get_model('auth', 'Group')
    
    # Obtener todos los grupos existentes
    all_groups = Group.objects.all()
    canonical_set = set(CANONICAL_GROUP_NAMES)
    
    removed_groups = []
    for group in all_groups:
        if group.name not in canonical_set:
            removed_groups.append(group.name)
            group.delete()
    
    if removed_groups:
        print(f"🗑️  Grupos legados eliminados: {', '.join(removed_groups)}")
    else:
        print("ℹ️  No se encontraron grupos legados para eliminar")


class Migration(migrations.Migration):
    dependencies = [
        ('auth', '__latest__'),
    ]

    operations = [
        migrations.RunPython(create_canonical_groups, migrations.RunPython.noop),
        migrations.RunPython(cleanup_legacy_groups, migrations.RunPython.noop),
    ]
