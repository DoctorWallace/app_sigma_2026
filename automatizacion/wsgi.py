import os
from pathlib import Path
try:
    from dotenv import load_dotenv
    base_dir = Path(__file__).resolve().parent.parent
    dotenv_path = base_dir / ".env"
    if dotenv_path.is_dir():
        dotenv_path = dotenv_path / ".env"
    load_dotenv(dotenv_path=dotenv_path)
except Exception:
    pass

from django.core.wsgi import get_wsgi_application
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'automatizacion.settings')
application = get_wsgi_application()
