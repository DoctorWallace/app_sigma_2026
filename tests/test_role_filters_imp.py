import pytest
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group

from core.templatetags import role_filters


def _create_user(username, group_name):
    User = get_user_model()
    user = User.objects.create_user(
        username=username,
        password="safe-pass",
        email=f"{username}@example.com",
    )
    group, _ = Group.objects.get_or_create(name=group_name)
    user.groups.add(group)
    return user


@pytest.mark.django_db
def test_role_filter_imp_technician_canonical():
    user = _create_user("imp_role", "implant_technicians")
    assert role_filters.is_imp_technician(user) is True


@pytest.mark.django_db
def test_role_filter_imp_technician_alias():
    user = _create_user("imp_role_alias", "tecnico_imp")
    assert role_filters.is_imp_technician(user) is True
