import pytest
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.urls import reverse
from django.utils import timezone

from sigmaconf.models import LO3Calibration, LO3Equipment


def _create_user(username, groups=None):
    User = get_user_model()
    user = User.objects.create_user(
        username=username,
        password="safe-pass",
        email=f"{username}@example.com",
    )
    for name in groups or []:
        group, _ = Group.objects.get_or_create(name=name)
        user.groups.add(group)
    return user


def _set_icts_session(client):
    session = client.session
    session["module"] = "icts"
    session.save()


@pytest.mark.django_db
def test_lo3_calibration_filter_by_type(client):
    technician = _create_user("lo3_tech_cal", ["confocal_technicians"])
    equipment = LO3Equipment.objects.create(name="DCM8")
    LO3Calibration.objects.create(
        equipment=equipment,
        calibration_type="internal",
        performed_at=timezone.localdate(),
    )
    LO3Calibration.objects.create(
        equipment=equipment,
        calibration_type="external",
        performed_at=timezone.localdate(),
    )

    client.force_login(technician)
    _set_icts_session(client)

    response = client.get(reverse("sigmaconf:lo3_calibration_list", args=["interna"]))
    assert response.status_code == 200
    internal_list = response.context["calibrations"]
    assert internal_list
    assert all(cal.calibration_type == "internal" for cal in internal_list)

    response = client.get(reverse("sigmaconf:lo3_calibration_list", args=["externa"]))
    assert response.status_code == 200
    external_list = response.context["calibrations"]
    assert external_list
    assert all(cal.calibration_type == "external" for cal in external_list)


@pytest.mark.django_db
def test_lo3_calibration_due_status_flags(client):
    technician = _create_user("lo3_tech_due", ["confocal_technicians"])
    equipment = LO3Equipment.objects.create(name="DCM8")
    today = timezone.localdate()

    overdue = LO3Calibration.objects.create(
        equipment=equipment,
        calibration_type="internal",
        performed_at=today,
        due_at=today - timezone.timedelta(days=1),
    )
    due_soon = LO3Calibration.objects.create(
        equipment=equipment,
        calibration_type="internal",
        performed_at=today,
        due_at=today + timezone.timedelta(days=10),
    )
    ok = LO3Calibration.objects.create(
        equipment=equipment,
        calibration_type="internal",
        performed_at=today,
        due_at=today + timezone.timedelta(days=40),
    )

    client.force_login(technician)
    _set_icts_session(client)

    response = client.get(reverse("sigmaconf:lo3_calibration_list", args=["interna"]))
    assert response.status_code == 200
    calibrations = response.context["calibrations"]
    status_map = {cal.pk: cal.due_status for cal in calibrations}
    assert status_map[overdue.pk] == "overdue"
    assert status_map[due_soon.pk] == "due_soon"
    assert status_map[ok.pk] == "ok"
