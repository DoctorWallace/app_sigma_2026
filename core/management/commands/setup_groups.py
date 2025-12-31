"""
Comando de gestión para crear y verificar grupos de usuarios.
Reemplaza los scripts ad hoc con una fuente de verdad única.
"""
from django.core.management.base import BaseCommand, CommandError
from django.contrib.auth.models import Group, User
from core.roles import CANONICAL_GROUP_NAMES, get_normalized_user_groups


class Command(BaseCommand):
    help = 'Crear y verificar grupos de usuarios canónicos'

    def add_arguments(self, parser):
        parser.add_argument(
            '--check',
            action='store_true',
            help='Solo verificar grupos existentes sin crear nuevos',
        )
        parser.add_argument(
            '--cleanup',
            action='store_true',
            help='Eliminar grupos que no están en la lista canónica',
        )
        parser.add_argument(
            '--list-users',
            action='store_true',
            help='Mostrar usuarios en cada grupo',
        )

    def handle(self, *args, **options):
        if options['check']:
            self.check_groups()
        elif options['cleanup']:
            self.cleanup_groups()
        elif options['list_users']:
            self.list_users_in_groups()
        else:
            self.create_groups()

    def create_groups(self):
        """Crear todos los grupos canónicos."""
        self.stdout.write("🔧 Creando grupos canónicos...")
        
        created_count = 0
        for group_name in CANONICAL_GROUP_NAMES:
            group, created = Group.objects.get_or_create(name=group_name)
            if created:
                created_count += 1
                self.stdout.write(
                    self.style.SUCCESS(f"✅ Grupo creado: {group_name}")
                )
            else:
                self.stdout.write(f"ℹ️  Grupo ya existe: {group_name}")
        
        self.stdout.write(
            self.style.SUCCESS(f"\n📊 Resumen: {created_count} grupos creados")
        )

    def check_groups(self):
        """Verificar qué grupos existen."""
        self.stdout.write("🔍 Verificando grupos existentes...")
        
        existing_groups = set(Group.objects.values_list('name', flat=True))
        canonical_set = set(CANONICAL_GROUP_NAMES)
        
        missing = canonical_set - existing_groups
        extra = existing_groups - canonical_set
        
        if missing:
            self.stdout.write(
                self.style.WARNING(f"❌ Grupos faltantes: {', '.join(missing)}")
            )
        else:
            self.stdout.write(self.style.SUCCESS("✅ Todos los grupos canónicos existen"))
        
        if extra:
            self.stdout.write(
                self.style.WARNING(f"⚠️  Grupos extra: {', '.join(extra)}")
            )

    def cleanup_groups(self):
        """Eliminar grupos que no están en la lista canónica."""
        self.stdout.write("🗑️  Limpiando grupos legados...")
        
        all_groups = Group.objects.all()
        canonical_set = set(CANONICAL_GROUP_NAMES)
        
        removed_count = 0
        for group in all_groups:
            if group.name not in canonical_set:
                self.stdout.write(f"🗑️  Eliminando: {group.name}")
                group.delete()
                removed_count += 1
        
        self.stdout.write(
            self.style.SUCCESS(f"\n📊 Resumen: {removed_count} grupos eliminados")
        )

    def list_users_in_groups(self):
        """Mostrar usuarios en cada grupo."""
        self.stdout.write("👥 Usuarios en grupos:\n")
        
        for group_name in CANONICAL_GROUP_NAMES:
            try:
                group = Group.objects.get(name=group_name)
                users = group.user_set.all()
                
                self.stdout.write(f"📋 {group_name}:")
                if users.exists():
                    for user in users:
                        full_name = user.get_full_name() or "Sin nombre"
                        self.stdout.write(f"   - {user.username} ({full_name})")
                else:
                    self.stdout.write("   (Sin usuarios)")
                self.stdout.write("")
                
            except Group.DoesNotExist:
                self.stdout.write(
                    self.style.WARNING(f"❌ Grupo no existe: {group_name}")
                )
