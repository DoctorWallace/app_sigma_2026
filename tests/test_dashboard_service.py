import pytest
from django.contrib.auth import get_user_model
from django.utils import timezone

from dtf.services import dashboard as svc
from sigmalab.models import Solicitud as SlabSolicitud
from mec.models import MecSolicitud
from sigmadp.models import DpSolicitudTermica
from sigmaoptics.models import OpticsSolicitud


def _set_created(obj, days_offset: int):
    obj.creado_en = timezone.now() - timezone.timedelta(days=days_offset)
    obj.save(update_fields=["creado_en"])
    return obj


@pytest.mark.django_db
def test_build_dashboard_data_with_real_models():
    """El servicio agrega correctamente los datos reales de cada laboratorio."""
    User = get_user_model()
    user = User.objects.create_user(
        username="dashboard-user",
        password="safe-password",
        email="user@example.com",
    )

    def create_sigmalab(estado, offset):
        solicitud = SlabSolicitud.objects.create(
            solicitante=user,
            estado=estado,
            material="Acero",
            numero_muestras=1,
        )
        return _set_created(solicitud, offset)

    def create_mec(estado, offset):
        solicitud = MecSolicitud.objects.create(
            solicitante=user,
            estado=estado,
            material="Aleacion",
            numero_muestras=1,
        )
        return _set_created(solicitud, offset)

    def create_dp(estado, offset):
        solicitud = DpSolicitudTermica.objects.create(
            solicitante=user,
            estado=estado,
            nombre_muestra=f"Muestra DP {estado}",
            material="Material DP",
            temperatura_maxima=500,
            tasa_calentamiento=10,
            tasa_enfriamiento=10,
            tiempo_permanencia=15,
            masa_registrar=DpSolicitudTermica.MasaChoices.MASA_2,
            espesor_muestra=1.0,
            **{"tamaño_muestra": 1.5},
            geometria_muestra="circular",
        )
        return _set_created(solicitud, offset)

    def create_optics(estado, offset):
        solicitud = OpticsSolicitud.objects.create(
            solicitante=user,
            estado=estado,
            material="Vidrio",
            numero_muestras=2,
            medidas_realizar=OpticsSolicitud.TipoMedida.UV_VIS,
            formato_resultado=OpticsSolicitud.FormatoResultado.IMAGEN,
            tipo_tamano="diametro",
            diametro_muestra=2.0,
            codigo_analisis=f"OPT-{estado}-{offset}",
        )
        return _set_created(solicitud, offset)

    estados = [
        SlabSolicitud.Estado.PENDIENTE,
        SlabSolicitud.Estado.EN_CURSO,
        SlabSolicitud.Estado.FINALIZADA,
    ]

    for offset, estado in enumerate(estados):
        create_sigmalab(estado, offset)
        create_mec(estado, offset)
        create_dp(estado, offset)
        create_optics(estado, offset)

    data = svc.build_dashboard_data(user)

    totals = data["totals"]
    assert totals["total_solicitudes"] == 12
    assert totals["pendientes"] == 4
    assert totals["en_curso"] == 4
    assert totals["finalizadas"] == 4

    labs = data["labs"]

    sigmalab_summary = labs["sigmalab"]
    assert sigmalab_summary.counts[SlabSolicitud.Estado.PENDIENTE] == 1
    assert sigmalab_summary.latest[0].estado == SlabSolicitud.Estado.PENDIENTE

    mec_stats = data["stats"]["mec"]
    assert mec_stats["total"] == 3
    assert mec_stats["finalizadas"] == 1

    sigmadp_latest = labs["sigmadp"].latest
    assert len(sigmadp_latest) == 3
    assert sigmadp_latest[0].estado == DpSolicitudTermica.Estado.PENDIENTE
