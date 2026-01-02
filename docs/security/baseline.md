# Baseline (Prompt 00)

Date: 2026-01-02

## Commands
- pytest (DJANGO_SETTINGS_MODULE=automatizacion.settings_test from pytest.ini)
- python manage.py check
- python manage.py check --deploy

## Results summary
pytest: 167 tests, 3 failures
- tests/test_icts_access_control.py::test_load_technique_draft_forbids_reviewer -> got 200, expected 302/403
- tests/test_portal_access_mode_regression.py::test_portal_access_mode_regression -> "FUSION-005" missing from portal:icts_access
- tests/test_portal_icts_access_protocol.py::test_icts_access_page_includes_tariffs -> "FUSION-005" missing from portal:icts_access
python manage.py check: OK (0 issues)
python manage.py check --deploy: warnings W004, W008, W009, W012, W016, W018
- W004: SECURE_HSTS_SECONDS not set
- W008: SECURE_SSL_REDIRECT not True
- W009: SECRET_KEY not strong / django-insecure
- W012: SESSION_COOKIE_SECURE not True
- W016: CSRF_COOKIE_SECURE not True
- W018: DEBUG True

## Repo hygiene
- db.sqlite3 exists at repo root; git ls-files reports it is not tracked.
- __pycache__ dirs found across apps (accounts, automatizacion, core, dtf, icts, mec, sigmadp, sigmalab, sigmaoptics, sigmavdg, tests, etc); removed.
- *.pyc files found under __pycache__ in many apps; removed.
- .pytest_cache removed.
- .gitignore updated to include sqlite journal/shm/wal files.

## Demo data (if needed)
- If db.sqlite3 is required for a demo, generate a sanitized fixture from a local DB, then remove secrets.
  Example:
  python manage.py dumpdata --exclude auth.permission --exclude contenttypes --exclude sessions --indent 2 > fixtures/dev_sanitized.json
