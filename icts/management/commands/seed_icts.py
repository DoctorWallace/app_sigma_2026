from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.db import transaction

from icts.models import (
    ICTSUserProfile,
    Facility,
    AccessProposal,
    Participant,
    ProposalReview,
)


PASSWORD = "u1627729"


class Command(BaseCommand):
    help = (
        "Crea datos de ejemplo para ICTS (grupos, facilities, usuarios, propuestas) "
        "y establece la contraseña de TODOS los usuarios a 'u1627729'."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--no-reset-all-passwords",
            action="store_true",
            help="No restablecer la contraseña de todos los usuarios (por defecto se restablece)",
        )

    @transaction.atomic
    def handle(self, *args, **options):
        self.stdout.write(self.style.MIGRATE_HEADING("[ICTS] Sembrando datos de ejemplo..."))

        # 1) Grupos
        groups = ["icts_users", "revisores", "responsables", "managers"]
        for gname in groups:
            Group.objects.get_or_create(name=gname)
        self.stdout.write(self.style.SUCCESS("Grupos creados/verificados."))

        # 2) Facilities
        facilities = [
            ("SEM/EDX", "sem"),
            ("FIB", "fib"),
            ("Ion Implanter", "imp"),
            ("SIMS", "sims"),
            ("Confocal", "confocal"),
            ("VDG", "vdg"),
            ("Profilometer", "profilometer"),
        ]
        for name, code in facilities:
            Facility.objects.get_or_create(name=name, code=code)
        self.stdout.write(self.style.SUCCESS("Facilities creadas/verificadas."))

        # 3) Usuarios
        User = get_user_model()

        def ensure_user(username, first, last, email, group_name=None, is_superuser=False):
            u, created = User.objects.get_or_create(
                username=username,
                defaults={
                    "first_name": first,
                    "last_name": last,
                    "email": email,
                    "is_staff": is_superuser,
                    "is_superuser": is_superuser,
                },
            )
            # Mantener nombres/emails actualizados por si ya existían
            u.first_name = first
            u.last_name = last
            u.email = email
            if is_superuser:
                u.is_staff = True
                u.is_superuser = True
            u.set_password(PASSWORD)
            u.save()

            # Perfil ICTS
            ICTSUserProfile.objects.get_or_create(
                user=u,
                defaults={
                    "center": "CIEMAT",
                    "phone": "+34 000 000 000",
                    "address": "Av. Complutense 40, Madrid",
                    "validated": True,
                },
            )

            # Grupo
            if group_name:
                g = Group.objects.get(name=group_name)
                u.groups.add(g)

            return u

        # Superusuario demo (si no lo hubiera ya)
        admin = ensure_user("ictsdemo_admin", "Admin", "Demo", "ictsdemo_admin@example.com", None, True)

        # Plain ICTS users
        plain_users = [
            ensure_user("ictsdemo_u01", "Ana", "Álvarez", "ictsdemo_u01@example.com", "icts_users"),
            ensure_user("ictsdemo_u02", "Bruno", "Bleda", "ictsdemo_u02@example.com", "icts_users"),
            ensure_user("ictsdemo_u03", "Carla", "Cruz", "ictsdemo_u03@example.com", "icts_users"),
        ]

        # Revisores
        reviewers = [
            ensure_user("ictsdemo_r01", "Rita", "Ribas", "ictsdemo_r01@example.com", "revisores"),
            ensure_user("ictsdemo_r02", "Raúl", "Rico", "ictsdemo_r02@example.com", "revisores"),
            ensure_user("ictsdemo_r03", "Rocío", "Ríos", "ictsdemo_r03@example.com", "revisores"),
            ensure_user("ictsdemo_r04", "Rafa", "Roma", "ictsdemo_r04@example.com", "revisores"),
        ]

        # Responsables
        responsables = [
            ensure_user("ictsdemo_resp01", "Laura", "Lara", "ictsdemo_resp01@example.com", "responsables"),
        ]

        # Managers
        managers = [
            ensure_user("ictsdemo_mgr01", "Miguel", "Mena", "ictsdemo_mgr01@example.com", "managers"),
        ]

        self.stdout.write(self.style.SUCCESS("Usuarios/perfiles creados/actualizados."))

        # 4) Propuestas de ejemplo
        all_facilities = list(Facility.objects.all())
        statuses = ["draft", "submitted", "accepted", "rejected"]

        def mk_proposal(user, idx, status):
            p, _ = AccessProposal.objects.get_or_create(
                applicant=user,
                title=f"Propuesta Demo {user.username.upper()} #{idx}",
                defaults={
                    "scope": "Pruebas de acceso a instalaciones ICTS.",
                    "status": status,
                    "project_name": "Proyecto Demo",
                    "project_type": "national",
                },
            )
            # asegurar estado
            if p.status != status:
                p.status = status
                p.save(update_fields=["status"])
            # facilities: asociar 2-3
            if p.facilities.count() == 0 and all_facilities:
                for f in all_facilities[:3]:
                    p.facilities.add(f)
            # participantes
            if not p.participants.exists():
                Participant.objects.create(
                    proposal=p, name=f"Participante {idx} {user.first_name}", center="CIEMAT"
                )
            return p

        created_props = []
        for i, user in enumerate(plain_users, start=1):
            for j, st in enumerate(statuses, start=1):
                created_props.append(mk_proposal(user, j, st))

        # 5) Revisiones para las 'submitted' y 'accepted'/'rejected'
        for p in created_props:
            if p.status in {"submitted", "accepted", "rejected"}:
                for r in reviewers:
                    rev, _ = ProposalReview.objects.get_or_create(
                        proposal=p, reviewer=r
                    )
                    # dar decisiones a algunas para simular histórico
                    if p.status == "accepted":
                        rev.decision = "approve"
                        rev.comments = "Aprobada por calidad científica."
                        rev.save()
                    elif p.status == "rejected":
                        rev.decision = "reject"
                        rev.comments = "No cumple requisitos."
                        rev.save()

        self.stdout.write(self.style.SUCCESS("Propuestas y revisiones de ejemplo creadas/actualizadas."))

        # 6) Passwords de todos los usuarios (opcional, por defecto sí)
        if not options.get("no_reset_all_passwords"):
            for u in get_user_model().objects.all():
                u.set_password(PASSWORD)
                u.save(update_fields=["password"])
            self.stdout.write(self.style.WARNING("Contraseñas de TODOS los usuarios establecidas a 'u1627729'."))

        self.stdout.write(self.style.SUCCESS("[ICTS] Datos demo OK."))
