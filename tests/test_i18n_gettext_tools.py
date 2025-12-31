import shutil

from django.core.management import call_command


def test_gettext_tools_available():
    missing = [tool for tool in ("msgfmt", "msguniq") if shutil.which(tool) is None]
    assert not missing, f"Missing gettext tools in PATH: {', '.join(missing)}"


def test_compilemessages_runs():
    call_command("compilemessages", verbosity=0)
