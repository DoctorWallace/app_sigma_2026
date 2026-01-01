import pytest
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group

from core import roles


@pytest.mark.django_db
def test_is_sims_tech_true_for_sims_group():
    User = get_user_model()
    user = User.objects.create_user(username="sims_user", password="safe-pass")
    group, _ = Group.objects.get_or_create(name="tecnicos_sims")
    user.groups.add(group)

    assert roles.is_sims_tech(user) is True


@pytest.mark.django_db
def test_is_sims_tech_false_without_group():
    User = get_user_model()
    user = User.objects.create_user(username="plain_user", password="safe-pass")

    assert roles.is_sims_tech(user) is False
