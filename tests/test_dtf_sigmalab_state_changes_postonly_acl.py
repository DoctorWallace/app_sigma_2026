from datetime import timedelta

import pytest
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.test import Client as DjangoClient
from django.urls import reverse
from django.utils import timezone

from dtf.models import DTFUserProfile
from sigmalab.models import (
    EquipoLaboratorio,
    NotificacionPrestamo,
    PrestamoEquipo,
    Solicitud,
)


def _create_user(username, groups):
    User = get_user_model()
    user = User.objects.create_user(username=username, password="safe-pass")
    for name in groups:
        group, _ = Group.objects.get_or_create(name=name)
        user.groups.add(group)
    return user


def _set_module(client, module="dtf"):
    session = client.session
    session["module"] = module
    session.save()


def _create_notification(destinatario, tecnico, suffix):
    equipo = EquipoLaboratorio.objects.create(
        nombre=f"Equipo {suffix}",
        codigo=f"EQ-{suffix}",
        categoria="herramientas",
        creado_por=tecnico,
    )
    prestamo = PrestamoEquipo.objects.create(
        equipo=equipo,
        usuario=destinatario,
        tecnico_responsable=tecnico,
        fecha_devolucion_estimada=timezone.now() + timedelta(days=1),
        dias_prestamo=1,
    )
    return NotificacionPrestamo.objects.create(
        prestamo=prestamo,
        destinatario=destinatario,
        tipo="prestamo_realizado",
        mensaje="Mensaje",
    )


@pytest.mark.django_db
def test_sigmalab_state_actions_require_post(client):
    tech_slab = _create_user("slab_tech_post", ["tecnico_responsable_s_lab"])
    user = _create_user("slab_user_post", ["usuarios_dtf"])
    DTFUserProfile.objects.create(
        user=user,
        info_importante_completada=True,
        acceso_s_lab_restringido=False,
    )
    solicitud = Solicitud.objects.create(solicitante=user)
    notif = _create_notification(user, tech_slab, "post")

    client.force_login(tech_slab)
    _set_module(client)
    response = client.get(reverse("sigmalab:toggle-autonomia", args=[solicitud.pk]))
    assert response.status_code == 405

    response = client.get(
        reverse("sigmalab:restriccion-usuario", args=[user.pk, "s_lab", "aplicar"])
    )
    assert response.status_code == 405

    client.force_login(user)
    _set_module(client)
    response = client.get(reverse("sigmalab:notificacion_marcar_leida", args=[notif.pk]))
    assert response.status_code == 405


@pytest.mark.django_db
def test_sigmalab_state_actions_forbid_normal_user(client):
    user = _create_user("slab_user_forbid", ["usuarios_dtf"])
    target_user = _create_user("slab_target_forbid", ["usuarios_dtf"])
    DTFUserProfile.objects.create(
        user=user,
        info_importante_completada=True,
        acceso_s_lab_restringido=False,
    )
    DTFUserProfile.objects.create(
        user=target_user,
        info_importante_completada=True,
        acceso_s_lab_restringido=False,
    )
    solicitud = Solicitud.objects.create(solicitante=target_user)

    client.force_login(user)
    _set_module(client)
    response = client.post(reverse("sigmalab:toggle-autonomia", args=[solicitud.pk]))
    assert response.status_code == 403

    response = client.post(
        reverse("sigmalab:restriccion-usuario", args=[target_user.pk, "s_lab", "aplicar"])
    )
    assert response.status_code == 403


@pytest.mark.django_db
def test_sigmalab_state_actions_block_other_lab_tech(client):
    tech_mec = _create_user("slab_tech_mec", ["tecnico_responsable_s_mec"])
    target_user = _create_user("slab_target_mec", ["usuarios_dtf"])
    DTFUserProfile.objects.create(
        user=target_user,
        info_importante_completada=True,
        acceso_s_lab_restringido=False,
    )
    solicitud = Solicitud.objects.create(solicitante=target_user)

    client.force_login(tech_mec)
    _set_module(client)
    response = client.post(reverse("sigmalab:toggle-autonomia", args=[solicitud.pk]))
    assert response.status_code == 403

    response = client.post(
        reverse("sigmalab:restriccion-usuario", args=[target_user.pk, "s_lab", "aplicar"])
    )
    assert response.status_code == 403


@pytest.mark.django_db
def test_sigmalab_state_actions_enforce_csrf():
    tech_slab = _create_user("slab_tech_csrf", ["tecnico_responsable_s_lab"])
    target_user = _create_user("slab_target_csrf", ["usuarios_dtf"])
    DTFUserProfile.objects.create(
        user=target_user,
        info_importante_completada=True,
        acceso_s_lab_restringido=False,
    )
    solicitud = Solicitud.objects.create(solicitante=target_user)

    client = DjangoClient(enforce_csrf_checks=True)
    client.force_login(tech_slab)
    _set_module(client)
    response = client.post(reverse("sigmalab:toggle-autonomia", args=[solicitud.pk]))
    assert response.status_code == 403


@pytest.mark.django_db
def test_sigmalab_notificacion_mark_leida_scoped(client):
    tech_slab = _create_user("slab_tech_notif", ["tecnico_responsable_s_lab"])
    user = _create_user("slab_user_notif", ["usuarios_dtf"])
    target_user = _create_user("slab_target_notif", ["usuarios_dtf"])
    DTFUserProfile.objects.create(
        user=user,
        info_importante_completada=True,
        acceso_s_lab_restringido=False,
    )
    DTFUserProfile.objects.create(
        user=target_user,
        info_importante_completada=True,
        acceso_s_lab_restringido=False,
    )
    own_notif = _create_notification(user, tech_slab, "own")
    other_notif = _create_notification(target_user, tech_slab, "other")

    client.force_login(user)
    _set_module(client)
    response = client.post(reverse("sigmalab:notificacion_marcar_leida", args=[own_notif.pk]))
    assert response.status_code == 302
    own_notif.refresh_from_db()
    assert own_notif.enviada is True

    response = client.post(reverse("sigmalab:notificacion_marcar_leida", args=[other_notif.pk]))
    assert response.status_code == 404
    other_notif.refresh_from_db()
    assert other_notif.enviada is False
