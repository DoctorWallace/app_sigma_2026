import pytest

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.urls import reverse

from icts.sigmasims.models import (
    SIMSAnnualPlan,
    SIMSAnnualPlanEntry,
    SIMSAnnualPlanChangeLog,
)


def _create_user(username, groups):
    User = get_user_model()
    user = User.objects.create_user(
        username=username,
        password="safe-pass",
        email=f"{username}@example.com",
    )
    for name in groups:
        group, _ = Group.objects.get_or_create(name=name)
        user.groups.add(group)
    return user


def _pick_unused_year(start_year=2100):
    """Devuelve un año no utilizado en SIMSAnnualPlan.

    La app incluye migraciones de seed (p.ej. plan 2024), por lo que no es
    seguro asumir que un año concreto está libre en tests.
    """
    year = start_year
    while SIMSAnnualPlan.objects.filter(year=year).exists():
        year += 1
    return year


def _pick_unused_year_pair(start_year=2100):
    """Devuelve (source_year, target_year) libres, con target_year = source_year + 1."""
    target_year = start_year
    while (
        SIMSAnnualPlan.objects.filter(year=target_year).exists()
        or SIMSAnnualPlan.objects.filter(year=target_year - 1).exists()
    ):
        target_year += 1
    return target_year - 1, target_year


@pytest.mark.django_db
def test_annual_plan_preview_when_year_missing(client):
    """Si no existe plan para el año solicitado, debe mostrarse plantilla (preview) del último plan anterior."""

    tech = _create_user("sims_tech_plan_preview", ["tecnicos_sims"])

    source_year, target_year = _pick_unused_year_pair(start_year=2100)
    source = SIMSAnnualPlan.objects.create(year=source_year)
    SIMSAnnualPlanEntry.objects.create(
        plan=source,
        equipment_code="EQ-DTF-L05-01",
        description="HIDEN SIMS WORKSTATION",
        activity=SIMSAnnualPlanEntry.ACTIVITY_MAINTENANCE,
        execution_type=SIMSAnnualPlanEntry.EXECUTION_INTERNAL,
        month_01=True,
    )

    client.force_login(tech)
    url = reverse("icts:sigmasims:annual_plan")
    r = client.get(url, {"year": target_year})
    assert r.status_code == 200

    body = r.content.decode("utf-8")
    assert str(target_year) in body
    assert "EQ-DTF-L05-01" in body
    assert "No existe plan para" in body


@pytest.mark.django_db
def test_annual_plan_copy_previous_creates_plan_months_cleared_and_logs(client):
    """Copiar del año anterior debe crear el plan destino, limpiar meses y generar logs."""

    resp = _create_user("sims_resp_plan_copy", ["tecnico_responsable_s_sims"])

    source_year, target_year = _pick_unused_year_pair(start_year=2150)
    source = SIMSAnnualPlan.objects.create(year=source_year)
    SIMSAnnualPlanEntry.objects.create(
        plan=source,
        equipment_code="EQ-DTF-L05-01",
        description="HIDEN SIMS WORKSTATION",
        activity=SIMSAnnualPlanEntry.ACTIVITY_MAINTENANCE,
        execution_type=SIMSAnnualPlanEntry.EXECUTION_INTERNAL,
        month_01=True,
        month_06=True,
    )

    client.force_login(resp)
    copy_url = reverse("icts:sigmasims:annual_plan_copy_previous")
    r = client.post(copy_url, data={"year": target_year})
    assert r.status_code == 302

    new_plan = SIMSAnnualPlan.objects.get(year=target_year)
    entries = list(SIMSAnnualPlanEntry.objects.filter(plan=new_plan))
    assert len(entries) == 1
    e = entries[0]

    # Meses deben estar todos en False tras copiar
    for m in range(1, 13):
        assert getattr(e, f"month_{m:02d}") is False

    # Debe haber logs: al menos un CREATE por entrada + un COPY para el plan
    assert SIMSAnnualPlanChangeLog.objects.filter(
        plan=new_plan,
        action=SIMSAnnualPlanChangeLog.ACTION_COPY,
    ).exists()
    assert SIMSAnnualPlanChangeLog.objects.filter(
        plan=new_plan,
        action=SIMSAnnualPlanChangeLog.ACTION_CREATE,
    ).exists()


@pytest.mark.django_db
def test_annual_plan_entry_update_creates_update_log(client):
    resp = _create_user("sims_resp_plan_update", ["tecnico_responsable_s_sims"])

    plan = SIMSAnnualPlan.objects.create(year=_pick_unused_year(start_year=2200))
    entry = SIMSAnnualPlanEntry.objects.create(
        plan=plan,
        equipment_code="EQ-1",
        description="Desc A",
        activity=SIMSAnnualPlanEntry.ACTIVITY_MAINTENANCE,
        execution_type=SIMSAnnualPlanEntry.EXECUTION_INTERNAL,
        month_01=False,
    )

    client.force_login(resp)
    edit_url = reverse("icts:sigmasims:annual_plan_entry_edit", args=[entry.pk])
    r = client.post(
        edit_url,
        data={
            "equipment_code": "EQ-1",
            "description": "Desc B",
            "activity": SIMSAnnualPlanEntry.ACTIVITY_MAINTENANCE,
            "execution_type": SIMSAnnualPlanEntry.EXECUTION_INTERNAL,
            "month_01": "on",
        },
    )
    assert r.status_code == 302

    entry.refresh_from_db()
    assert entry.description == "Desc B"
    assert entry.month_01 is True
    assert SIMSAnnualPlanChangeLog.objects.filter(
        plan=plan,
        entry=entry,
        action=SIMSAnnualPlanChangeLog.ACTION_UPDATE,
    ).exists()


@pytest.mark.django_db
def test_annual_plan_copy_denied_for_tech(client):
    """Un técnico (no responsable) NO debe poder copiar planes."""

    tech = _create_user("sims_tech_plan_denied", ["tecnicos_sims"])

    source_year, target_year = _pick_unused_year_pair(start_year=2250)
    source = SIMSAnnualPlan.objects.create(year=source_year)
    SIMSAnnualPlanEntry.objects.create(
        plan=source,
        equipment_code="EQ-DTF-L05-01",
        description="HIDEN SIMS WORKSTATION",
        activity=SIMSAnnualPlanEntry.ACTIVITY_MAINTENANCE,
        execution_type=SIMSAnnualPlanEntry.EXECUTION_INTERNAL,
        month_01=True,
    )

    client.force_login(tech)
    copy_url = reverse("icts:sigmasims:annual_plan_copy_previous")
    r = client.post(copy_url, data={"year": target_year})
    assert r.status_code in {302, 403}

    assert not SIMSAnnualPlan.objects.filter(year=target_year).exists()
    assert not SIMSAnnualPlanChangeLog.objects.filter(plan__year=target_year).exists()


@pytest.mark.django_db
def test_annual_plan_entry_delete_creates_log(client):
    resp = _create_user("sims_resp_plan_delete", ["tecnico_responsable_s_sims"])

    plan = SIMSAnnualPlan.objects.create(year=_pick_unused_year(start_year=2300))
    entry = SIMSAnnualPlanEntry.objects.create(
        plan=plan,
        equipment_code="EQ-DEL-1",
        description="Desc",
        activity=SIMSAnnualPlanEntry.ACTIVITY_MAINTENANCE,
        execution_type=SIMSAnnualPlanEntry.EXECUTION_INTERNAL,
    )

    client.force_login(resp)
    delete_url = reverse("icts:sigmasims:annual_plan_entry_delete", args=[entry.pk])
    r = client.post(delete_url)
    assert r.status_code == 302
    assert not SIMSAnnualPlanEntry.objects.filter(pk=entry.pk).exists()
    assert SIMSAnnualPlanChangeLog.objects.filter(
        plan=plan,
        action=SIMSAnnualPlanChangeLog.ACTION_DELETE,
    ).exists()


@pytest.mark.django_db
def test_annual_plan_entry_create_edit_delete_denied_for_tech(client):
    """CRUD del plan anual debe estar denegado para técnicos no responsables."""

    tech = _create_user("sims_tech_plan_crud", ["tecnicos_sims"])

    plan_year = _pick_unused_year(start_year=2350)
    plan = SIMSAnnualPlan.objects.create(year=plan_year)
    entry = SIMSAnnualPlanEntry.objects.create(
        plan=plan,
        equipment_code="EQ-CR-1",
        description="Desc",
        activity=SIMSAnnualPlanEntry.ACTIVITY_MAINTENANCE,
        execution_type=SIMSAnnualPlanEntry.EXECUTION_INTERNAL,
    )

    client.force_login(tech)

    # CREATE (la vista decide el plan por ?year=...)
    create_url = reverse("icts:sigmasims:annual_plan_entry_create") + f"?year={plan_year}"
    r = client.post(
        create_url,
        data={
            "equipment_code": "EQ-NEW",
            "description": "Nueva",
            "activity": SIMSAnnualPlanEntry.ACTIVITY_MAINTENANCE,
            "execution_type": SIMSAnnualPlanEntry.EXECUTION_INTERNAL,
        },
    )
    assert r.status_code in {302, 403}
    assert SIMSAnnualPlanEntry.objects.filter(plan=plan).count() == 1
    assert not SIMSAnnualPlanChangeLog.objects.filter(plan=plan).exists()

    # EDIT
    edit_url = reverse("icts:sigmasims:annual_plan_entry_edit", args=[entry.pk])
    r = client.post(
        edit_url,
        data={
            "equipment_code": "EQ-CR-1",
            "description": "Cambio",
            "activity": SIMSAnnualPlanEntry.ACTIVITY_MAINTENANCE,
            "execution_type": SIMSAnnualPlanEntry.EXECUTION_INTERNAL,
        },
    )
    assert r.status_code in {302, 403}
    entry.refresh_from_db()
    assert entry.description == "Desc"
    assert not SIMSAnnualPlanChangeLog.objects.filter(plan=plan).exists()

    # DELETE
    delete_url = reverse("icts:sigmasims:annual_plan_entry_delete", args=[entry.pk])
    r = client.post(delete_url)
    assert r.status_code in {302, 403}
    assert SIMSAnnualPlanEntry.objects.filter(pk=entry.pk).exists()
    assert not SIMSAnnualPlanChangeLog.objects.filter(plan=plan).exists()
