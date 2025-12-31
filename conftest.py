import os

os.environ.setdefault("DJANGO_DEBUG", "1")
os.environ.setdefault("DJANGO_SECRET_KEY", "pytest-secret-key")
