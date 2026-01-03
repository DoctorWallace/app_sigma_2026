import pytest

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.urls import reverse

from dtf.models import DTFUserProfile
from sigmaoptics.models import OpticsSolicitud


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


@pytest.mark.django_db
def test_sigmaoptics_blocks_other_lab_tech(client):
    tech_mec = _create_user("optics_tech_mec", ["tecnico_responsable_s_mec"])

    client.force_login(tech_mec)
    _set_module(client)
    response = client.get(reverse("sigmaoptics:solicitud_list"))

    assert response.status_code == 403


@pytest.mark.django_db
def test_sigmaoptics_redirects_info_importante(client):
    user = _create_user("optics_info", ["usuarios_dtf"])
    DTFUserProfile.objects.create(
        user=user,
        info_importante_completada=False,
        acceso_s_optics_restringido=False,
    )

    client.force_login(user)
    _set_module(client)
    response = client.get(reverse("sigmaoptics:solicitud_list"))

    assert response.status_code == 302
    assert response.url == reverse("dtf:info-importante")


@pytest.mark.django_db
def test_sigmaoptics_redirects_restricted_user(client):
    user = _create_user("optics_restricted", ["usuarios_dtf"])
    DTFUserProfile.objects.create(
        user=user,
        info_importante_completada=True,
        acceso_s_optics_restringido=True,
    )

    client.force_login(user)
    _set_module(client)
    response = client.get(reverse("sigmaoptics:solicitud_list"))

    assert response.status_code == 302
    assert response.url == reverse("dtf:dashboard")


@pytest.mark.django_db
def test_sigmaoptics_list_scopes_to_user(client):
    user_a = _create_user("optics_user_a", ["usuarios_dtf"])
    user_b = _create_user("optics_user_b", ["usuarios_dtf"])
    DTFUserProfile.objects.create(
        user=user_a,
        info_importante_completada=True,
        acceso_s_optics_restringido=False,
    )
    DTFUserProfile.objects.create(
        user=user_b,
        info_importante_completada=True,
        acceso_s_optics_restringido=False,
    )

    s1 = OpticsSolicitud.objects.create(
        solicitante=user_a,
        material="Mat A",
        medidas_realizar=OpticsSolicitud.TipoMedida.UV_VIS,
        codigo_analisis="OPT-A-1",
    )
    OpticsSolicitud.objects.create(
        solicitante=user_b,
        material="Mat B",
        medidas_realizar=OpticsSolicitud.TipoMedida.FTIR,
        codigo_analisis="OPT-B-1",
    )

    client.force_login(user_a)
    _set_module(client)
    response = client.get(reverse("sigmaoptics:solicitud_list"))

    assert response.status_code == 200
    page_obj = response.context["page_obj"]
    assert page_obj.paginator.count == 1
    assert page_obj.object_list[0].pk == s1.pk


@pytest.mark.django_db
def test_sigmaoptics_detail_scoped_to_owner(client):
    user_a = _create_user("optics_user_a2", ["usuarios_dtf"])
    user_b = _create_user("optics_user_b2", ["usuarios_dtf"])
    DTFUserProfile.objects.create(
        user=user_a,
        info_importante_completada=True,
        acceso_s_optics_restringido=False,
    )
    DTFUserProfile.objects.create(
        user=user_b,
        info_importante_completada=True,
        acceso_s_optics_restringido=False,
    )

    s1 = OpticsSolicitud.objects.create(
        solicitante=user_a,
        material="Mat A2",
        medidas_realizar=OpticsSolicitud.TipoMedida.UV_VIS,
        codigo_analisis="OPT-A-2",
    )
    s2 = OpticsSolicitud.objects.create(
        solicitante=user_b,
        material="Mat B2",
        medidas_realizar=OpticsSolicitud.TipoMedida.FTIR,
        codigo_analisis="OPT-B-2",
    )

    client.force_login(user_a)
    _set_module(client)
    response = client.get(reverse("sigmaoptics:solicitud_detail", args=[s2.pk]))

    assert response.status_code == 404


@pytest.mark.django_db
def test_sigmaoptics_tech_can_view_any_detail(client):
    user_a = _create_user("optics_user_a3", ["usuarios_dtf"])
    user_b = _create_user("optics_user_b3", ["usuarios_dtf"])
    tech_optics = _create_user("optics_tech", ["tecnico_responsable_s_optics"])
    DTFUserProfile.objects.create(
        user=user_a,
        info_importante_completada=True,
        acceso_s_optics_restringido=False,
    )
    DTFUserProfile.objects.create(
        user=user_b,
        info_importante_completada=True,
        acceso_s_optics_restringido=False,
    )

    s1 = OpticsSolicitud.objects.create(
        solicitante=user_a,
        material="Mat A3",
        medidas_realizar=OpticsSolicitud.TipoMedida.UV_VIS,
        codigo_analisis="OPT-A-3",
    )
    s2 = OpticsSolicitud.objects.create(
        solicitante=user_b,
        material="Mat B3",
        medidas_realizar=OpticsSolicitud.TipoMedida.FTIR,
        codigo_analisis="OPT-B-3",
    )

    client.force_login(tech_optics)
    _set_module(client)
    response = client.get(reverse("sigmaoptics:solicitud_detail", args=[s1.pk]))
    assert response.status_code == 200

    response = client.get(reverse("sigmaoptics:solicitud_detail", args=[s2.pk]))
    assert response.status_code == 200
