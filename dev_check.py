#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Script para verificar calidad del código antes de hacer commit.
Ejecuta: python dev_check.py
"""
import subprocess
import sys
import os
from pathlib import Path

# Configurar encoding para Windows
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')

# Colores para terminal
class Colors:
    HEADER = '\033[95m'
    OKBLUE = '\033[94m'
    OKCYAN = '\033[96m'
    OKGREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'


def print_header(text):
    """Imprime un encabezado llamativo."""
    print(f"\n{Colors.HEADER}{Colors.BOLD}{'='*70}{Colors.ENDC}")
    print(f"{Colors.HEADER}{Colors.BOLD}  {text}{Colors.ENDC}")
    print(f"{Colors.HEADER}{Colors.BOLD}{'='*70}{Colors.ENDC}\n")


def run_check(cmd, description, optional=False):
    """
    Ejecuta un comando y reporta el resultado.
    
    Args:
        cmd: Comando a ejecutar
        description: Descripción del check
        optional: Si es True, una falla no detiene el script
    
    Returns:
        bool: True si el check pasó, False si falló
    """
    print(f"{Colors.OKBLUE}>>> Ejecutando: {description}...{Colors.ENDC}")
    print(f"   Comando: {cmd}\n")
    
    result = subprocess.run(cmd, shell=True, capture_output=False)
    
    if result.returncode == 0:
        print(f"\n{Colors.OKGREEN}[OK] {description} - Pasado!{Colors.ENDC}\n")
        return True
    else:
        if optional:
            print(f"\n{Colors.WARNING}[WARN] {description} - Fallo (opcional){Colors.ENDC}\n")
            return True
        else:
            print(f"\n{Colors.FAIL}[FAIL] {description} - Fallo!{Colors.ENDC}\n")
            return False


def main():
    """Función principal."""
    print_header("VERIFICACION DE CODIGO - SIGMA FUSION")
    
    # Lista de checks a ejecutar
    checks = [
        # Django checks
        {
            "cmd": "python manage.py check",
            "description": "Django System Check",
            "optional": False
        },
        
        # Formateo de código
        {
            "cmd": "black --check .",
            "description": "Black - Formato de código",
            "optional": True  # No bloqueante, solo informativo
        },
        
        # Ordenar imports
        {
            "cmd": "isort --check-only --profile black .",
            "description": "isort - Orden de imports",
            "optional": True
        },
        
        # Linting
        {
            "cmd": "flake8 --max-line-length=88 --extend-ignore=E203,W503 --exclude=migrations,__pycache__,.git,venv,env",
            "description": "Flake8 - Análisis de código",
            "optional": True
        },
    ]
    
    # Ejecutar checks
    results = []
    for check in checks:
        result = run_check(
            check["cmd"],
            check["description"],
            check.get("optional", False)
        )
        results.append((check["description"], result, check.get("optional", False)))
    
    # Resumen final
    print_header("RESUMEN DE VERIFICACIONES")
    
    all_passed = True
    for desc, passed, optional in results:
        if passed:
            print(f"{Colors.OKGREEN}[OK] {desc}{Colors.ENDC}")
        else:
            print(f"{Colors.FAIL}[FAIL] {desc}{Colors.ENDC}")
            if not optional:
                all_passed = False
    
    # Mensaje final
    print(f"\n{Colors.BOLD}{'='*70}{Colors.ENDC}\n")
    
    if all_passed:
        print(f"{Colors.OKGREEN}{Colors.BOLD}TODAS LAS VERIFICACIONES PASARON!{Colors.ENDC}")
        print(f"{Colors.OKGREEN}   Tu codigo esta listo para commit.{Colors.ENDC}\n")
        return 0
    else:
        print(f"{Colors.FAIL}{Colors.BOLD}ALGUNAS VERIFICACIONES FALLARON{Colors.ENDC}")
        print(f"{Colors.WARNING}   Por favor, corrige los errores antes de hacer commit.{Colors.ENDC}\n")
        print(f"{Colors.OKCYAN}Sugerencias:{Colors.ENDC}")
        print(f"   - Para formatear codigo: {Colors.BOLD}black .{Colors.ENDC}")
        print(f"   - Para ordenar imports: {Colors.BOLD}isort --profile black .{Colors.ENDC}")
        print(f"   - Para ver detalles de flake8: {Colors.BOLD}flake8 --show-source{Colors.ENDC}\n")
        return 1


if __name__ == "__main__":
    sys.exit(main())

