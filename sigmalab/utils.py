# sigmalab/utils.py
from django.db import transaction
from django.shortcuts import get_object_or_404
from django.utils import timezone

from .models import SampleCodeSequence
from core.roles import is_slab_tech

def is_tecnico(user):
    """
    Alias para is_technician para mantener compatibilidad
    """
    return user.is_authenticated and (user.is_superuser or is_slab_tech(user))

def get_solicitud_for_user_or_404(user, pk, queryset=None, allow_tecnico=True):
    """Return a solicitud ensuring the requester has access.

    When allow_tecnico is True, technician users keep their broader access,
    otherwise the queryset is always filtered by the requester.
    """
    if queryset is None:
        from .models import Solicitud
        queryset = Solicitud.objects.all()
    if allow_tecnico and is_tecnico(user):
        return get_object_or_404(queryset, pk=pk)
    return get_object_or_404(queryset.filter(solicitante=user), pk=pk)

def generate_sample_code():
    """
    Genera un código de muestra único en formato YY-XXX
    Ejemplo: 25-001, 25-002, etc.
    """
    now = timezone.now()
    current_year = now.year % 100

    with transaction.atomic():
        next_counter = SampleCodeSequence.next_counter(now.year)

    return f"{current_year:02d}-{next_counter:03d}"

def assign_sample_code(solicitud):
    """
    Asigna un código de muestra a una solicitud si no lo tiene
    """
    if not solicitud.codigo_muestra:
        code = generate_sample_code()
        solicitud.codigo_muestra = code
        solicitud.save(update_fields=['codigo_muestra'])
        return code
    return solicitud.codigo_muestra

def get_sample_code_display(solicitud):
    """
    Obtiene el código de muestra para mostrar, generándolo si es necesario
    """
    if solicitud.codigo_muestra:
        return solicitud.codigo_muestra
    now = timezone.now()
    next_value = SampleCodeSequence.peek_next(now.year)
    return f"{now.year % 100:02d}-{next_value:03d}"
