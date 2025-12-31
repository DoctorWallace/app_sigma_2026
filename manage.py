#!/usr/bin/env python
import os, sys
from pathlib import Path

# Cargar .env desde la raíz del proyecto
try:
    from dotenv import load_dotenv
    base_dir = Path(__file__).resolve().parent
    dotenv_path = base_dir / ".env"
    if dotenv_path.is_dir():
        dotenv_path = dotenv_path / ".env"
    load_dotenv(dotenv_path=dotenv_path)
except Exception:
    pass

def main():
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'automatizacion.settings')
    from django.core.management import execute_from_command_line
    execute_from_command_line(sys.argv)

if __name__ == '__main__':
    main()
