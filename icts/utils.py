# icts/utils.py
from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.utils import timezone
from django.urls import reverse
from django.db.models import Max
from .models import AccessProposal, ProposalReview, ICTSUserProfile

User = get_user_model()

def build_access_code(proposal, user_siglas=None, include_olmat=False):
    """Construye código de acceso único basado en técnicas seleccionadas."""

    techniques = []
    if proposal.facility_sem:
        techniques.append("SEM")
    if proposal.facility_sem_fib:
        techniques.append("FIB")
    if proposal.facility_imp:
        techniques.append("IMP")
    if proposal.facility_sims:
        techniques.append("SIMS")
    if proposal.facility_confocal:
        techniques.append("CONF")
    if proposal.facility_vdg:
        techniques.append("VDG")
    if proposal.facility_profilometer:
        techniques.append("PERF")
    if include_olmat and getattr(proposal, "facility_olmat", False):
        techniques.append("OLMAT")
    techniques = sorted(techniques)

    siglas = user_siglas or getattr(getattr(proposal.applicant, "icts_profile", None), "user_siglas", None)
    if not siglas:
        siglas = ensure_user_siglas(proposal.applicant)

    siglas = siglas.upper()

    submitted_at = proposal.submitted_at or timezone.now()
    month = submitted_at.month
    year = submitted_at.year % 100
    sequence = proposal.user_sequence_number or 0

    techniques_str = "_".join(techniques)
    if techniques_str:
        return f"{techniques_str}_{siglas}_{month:02d}_{year:02d}_{sequence}"
    return f"{siglas}_{month:02d}_{year:02d}_{sequence}"


def build_olmat_access_code(proposal, olmat_request=None, user_siglas=None):
    """Construye código independiente para solicitudes OLMAT (OLMAT + siglas + año + id)."""
    from django.utils import timezone

    siglas = user_siglas or getattr(getattr(proposal.applicant, 'icts_profile', None), 'user_siglas', None)
    if not siglas:
        siglas = ensure_user_siglas(proposal.applicant)

    siglas = siglas.upper()
    year = timezone.now().year % 100
    suffix = (olmat_request.pk if olmat_request and olmat_request.pk else proposal.pk) or "X"

    return f"OLMAT_{siglas}_{year:02d}_{suffix}"

def strip_accents(text):
    """Elimina tildes y acentos de un texto"""
    import unicodedata
    return ''.join(c for c in unicodedata.normalize('NFD', text) if unicodedata.category(c) != 'Mn')

def _normalize_name(value):
    return strip_accents(value or '').upper().strip()


def _generate_siglas_candidates(first_name, last_name):
    first = _normalize_name(first_name)
    surname_full = _normalize_name(last_name)
    surname = surname_full.split()[0] if surname_full else ''

    initial = first[0] if first else 'U'
    candidates = []

    if surname:
        letters = [c for c in surname if c.isalpha()]
        if len(letters) >= 2:
            candidates.append(f"{initial}{letters[0]}{letters[-1]}")
        elif letters:
            candidates.append(f"{initial}{letters[0]}X")
        else:
            candidates.append(f"{initial}XX")

        for idx in range(1, len(letters)):
            candidates.append(f"{initial}{letters[0]}{letters[idx]}")
    else:
        candidates.append(f"{initial}XX")

    normalized = []
    for cand in candidates:
        cand = cand.upper()
        if len(cand) < 3:
            cand = cand.ljust(3, 'X')
        else:
            cand = cand[:3]
        if cand not in normalized:
            normalized.append(cand)

    if not normalized:
        normalized = ['USR']
    return normalized


def generate_unique_user_siglas(first_name, last_name, exclude_user_id=None):
    candidates = _generate_siglas_candidates(first_name, last_name)

    for cand in candidates:
        qs = ICTSUserProfile.objects.filter(user_siglas__iexact=cand)
        if exclude_user_id:
            qs = qs.exclude(user_id=exclude_user_id)
        if not qs.exists():
            return cand

    base = candidates[0]
    counter = 1
    while True:
        candidate = f"{base}{counter}"
        if len(candidate) > 10:
            prefix = base[:max(1, 10 - len(str(counter)))]
            candidate = f"{prefix}{counter}"
        qs = ICTSUserProfile.objects.filter(user_siglas__iexact=candidate)
        if exclude_user_id:
            qs = qs.exclude(user_id=exclude_user_id)
        if not qs.exists():
            return candidate
        counter += 1


def assign_unique_user_siglas(profile):
    if profile is None or not getattr(profile, 'user', None):
        return None

    current = (profile.user_siglas or '').strip().upper()
    if current:
        conflict = ICTSUserProfile.objects.filter(user_siglas__iexact=current).exclude(pk=profile.pk).exists()
        if not conflict:
            if current != profile.user_siglas:
                profile.user_siglas = current
                profile.save(update_fields=['user_siglas'])
            return profile.user_siglas

    siglas = generate_unique_user_siglas(profile.user.first_name, profile.user.last_name, exclude_user_id=profile.user_id)
    profile.user_siglas = siglas
    profile.save(update_fields=['user_siglas'])
    return siglas


def ensure_user_siglas(user):
    if user is None:
        return generate_unique_user_siglas(None, None)

    profile = getattr(user, 'icts_profile', None)
    if profile is None:
        profile, _ = ICTSUserProfile.objects.get_or_create(user=user)
    return assign_unique_user_siglas(profile)


def get_next_user_sequence(user):
    profile, _ = ICTSUserProfile.objects.get_or_create(user=user)
    max_seq = (
        AccessProposal.objects.filter(
            applicant=user, user_sequence_number__isnull=False
        )
        .aggregate(max_seq=Max("user_sequence_number"))
        .get("max_seq")
        or 0
    )
    count_no_draft = (
        AccessProposal.objects.filter(applicant=user)
        .exclude(status="draft")
        .count()
    )
    base = max(profile.proposal_counter or 0, max_seq, count_no_draft)
    return base + 1

def generate_user_siglas_algorithm(first_name, last_name, exclude_user_id=None):
    """Genera siglas candidatas garantizando unicidad en perfiles ICTS."""
    return generate_unique_user_siglas(first_name, last_name, exclude_user_id=exclude_user_id)

def generate_user_siglas_new(first_name, last_name):
    """Genera siglas garantizando formato estándar (compatible con versiones anteriores)."""
    return generate_unique_user_siglas(first_name, last_name)

def generate_user_siglas(first_name, last_name):
    """Genera siglas del usuario (compatibilidad hacia atrás)."""
    return generate_unique_user_siglas(first_name, last_name)

def send_proposal_notification(proposal, action, recipient=None):
    """Envía notificación por email sobre cambios en propuestas"""
    if not settings.EMAIL_HOST_USER:
        return  # No enviar si no hay configuración de email
    
    context = {
        'proposal': proposal,
        'action': action,
        'site_url': getattr(settings, 'SITE_URL', 'http://localhost:8000'),
    }
    
    if action == 'submitted':
        subject = f'Propuesta enviada: {proposal.title}'
        template = 'icts/emails/proposal_submitted.html'
        recipients = [proposal.applicant.email]
        
    elif action == 'review_assigned':
        subject = f'Nueva propuesta para revisar: {proposal.title}'
        template = 'icts/emails/review_assigned.html'
        # Enviar a todos los revisores
        reviewers = User.objects.filter(groups__name='revisores')
        recipients = [r.email for r in reviewers if r.email]
        
    elif action == 'review_completed':
        subject = f'Revisión completada: {proposal.title}'
        template = 'icts/emails/review_completed.html'
        recipients = [proposal.applicant.email]
        
    elif action == 'decision_made':
        subject = f'Decisión sobre propuesta: {proposal.title}'
        template = 'icts/emails/proposal_decision.html'
        recipients = [proposal.applicant.email]
        
    else:
        return
    
    if recipient:
        recipients = [recipient]
    
    try:
        html_message = render_to_string(template, context)
        send_mail(
            subject=subject,
            message='',  # Versión texto plano (opcional)
            html_message=html_message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=recipients,
            fail_silently=False,
        )
    except Exception as e:
        # Log el error pero no fallar la aplicación
        import logging
        logger = logging.getLogger(__name__)
        logger.error(f"Error enviando email: {e}")

def send_user_approval_notification(user):
    """Envía notificación cuando un usuario es aprobado"""
    if not settings.EMAIL_HOST_USER or not user.email:
        return
        
    context = {
        'user': user,
        'site_url': getattr(settings, 'SITE_URL', 'http://localhost:8000'),
    }
    
    try:
        html_message = render_to_string('icts/emails/user_approved.html', context)
        send_mail(
            subject='Cuenta aprobada - SIGMA ICTS',
            message='',
            html_message=html_message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[user.email],
            fail_silently=False,
        )
    except Exception as e:
        import logging
        logger = logging.getLogger(__name__)
        logger.error(f"Error enviando email de aprobación: {e}")



def send_new_user_registration_notification(user):
    """Notifica a responsables/managers cuando se registra un nuevo usuario ICTS."""
    import logging
    from core.roles import MANAGER_GROUPS, RESPONSABLE_GROUPS, normalize_group_name

    logger = logging.getLogger(__name__)
    if not settings.EMAIL_HOST_USER:
        logger.info("EMAIL_HOST_USER no configurado; se omite aviso de nuevo usuario.")
        return
    if user is None:
        return

    target_groups = RESPONSABLE_GROUPS | MANAGER_GROUPS
    group_ids = [
        group.id
        for group in Group.objects.all()
        if normalize_group_name(group.name) in target_groups
    ]
    if not group_ids:
        return

    recipients = list(
        User.objects.filter(groups__in=group_ids, is_active=True)
        .exclude(email="")
        .values_list("email", flat=True)
        .distinct()
    )
    if not recipients:
        return

    site_url = getattr(settings, "SITE_URL", "http://localhost:8000").rstrip("/")
    pending_url = f"{site_url}{reverse('icts:pending_users')}"
    registered_at = timezone.localtime(getattr(user, "date_joined", timezone.now()))

    subject = "Nuevo usuario ICTS registrado"
    message = (
        "Se ha registrado un nuevo usuario ICTS.\n\n"
        f"Usuario: {user.username}\n"
        f"Email: {user.email}\n"
        f"Fecha: {registered_at:%Y-%m-%d %H:%M}\n\n"
        f"Revisar pendientes: {pending_url}\n"
    )
    try:
        send_mail(
            subject=subject,
            message=message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=recipients,
            fail_silently=False,
        )
    except Exception as exc:
        logger.error(f"Error enviando aviso de nuevo usuario: {exc}")
