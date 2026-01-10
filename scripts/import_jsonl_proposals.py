"""
Script para importar propuestas desde requests.jsonl a AccessProposal
Uso: python manage.py shell < scripts/import_jsonl_proposals.py
"""
import json
import os
import sys
import re
from datetime import datetime

# Configurar Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'automatizacion.settings')
import django
django.setup()

from django.contrib.auth import get_user_model
from django.db import transaction
from icts.models import AccessProposal, Participant, ICTSUserProfile

User = get_user_model()

# Mapeo de nombres de facility a campos del modelo
FACILITY_MAP = {
    "Scanning Electron Microscopy": "facility_sem",
    "SEM Zeiss Auriga": "facility_sem",
    "SEM + Focus Ion Beam": "facility_sem_fib",
    "SEM-FIB": "facility_sem_fib",
    "Secondary Ion Mass Spectrometry": "facility_sims",
    "SIMS": "facility_sims",
    "Profilemeter": "facility_profilometer",
    "DektakXT": "facility_profilometer",
    "Confocal microscope": "facility_confocal",
    "Leica DCM8": "facility_confocal",
    "Van de Graaff": "facility_vdg",
    "Ion Implanter": "facility_imp",
    "Danfysik": "facility_imp",
    "Optical properties": "facility_optics",
}

# Mapeo de resolución a status
RESOLUTION_MAP = {
    "ACCEPT": "accepted",
    "REJECT": "rejected",
    "NOT ASSESSED": "submitted",
    None: "submitted",
}

# Mapeo de project_type
PROJECT_TYPE_MAP = {
    "international": "international",
    "european": "european",
    "national": "national",
    "regional": "regional",
    "internal": "national",  # Mapear internal a national
}


def parse_years(year_str):
    """Parsear cadenas como '2021-2028', '23-27', '2024' a (start, end)"""
    if not year_str:
        return None, None
    
    year_str = str(year_str).strip()
    
    # Buscar patrón XX-XX o XXXX-XXXX
    match = re.search(r'(\d{2,4})\s*[-–]\s*(\d{2,4})', year_str)
    if match:
        start, end = match.groups()
        # Convertir años de 2 dígitos a 4 dígitos
        if len(start) == 2:
            start = f"20{start}"
        if len(end) == 2:
            end = f"20{end}"
        return int(start), int(end)
    
    # Buscar un solo año
    match = re.search(r'(\d{4})', year_str)
    if match:
        year = int(match.group(1))
        return year, year
    
    return None, None


def map_facilities(facilities_list):
    """Mapear lista de facilities a diccionario de campos booleanos"""
    result = {
        "facility_sem": False,
        "facility_sem_fib": False,
        "facility_imp": False,
        "facility_sims": False,
        "facility_confocal": False,
        "facility_optics": False,
        "facility_vdg": False,
        "facility_profilometer": False,
        "facility_olmat": False,
    }
    
    for facility in facilities_list:
        if not facility.get("requested"):
            continue
        
        name = facility.get("facility_name", "")
        for key, field in FACILITY_MAP.items():
            if key.lower() in name.lower():
                result[field] = True
                break
    
    return result


def get_or_create_user(email, contact_person, center=None, phone=None, address=None):
    """Obtener o crear usuario basado en email"""
    if not email:
        email = f"unknown_{datetime.now().timestamp()}@example.com"
    
    email = email.lower().strip()
    
    try:
        user = User.objects.get(email=email)
    except User.DoesNotExist:
        # Crear username desde email
        username = email.split('@')[0]
        # Asegurar unicidad
        base_username = username
        counter = 1
        while User.objects.filter(username=username).exists():
            username = f"{base_username}_{counter}"
            counter += 1
        
        # Parsear nombre
        names = contact_person.split() if contact_person else ["Usuario"]
        first_name = names[0] if names else ""
        last_name = " ".join(names[1:]) if len(names) > 1 else ""
        
        user = User.objects.create_user(
            username=username,
            email=email,
            first_name=first_name,
            last_name=last_name,
            is_active=True,
        )
        
        # Crear perfil ICTS
        ICTSUserProfile.objects.create(
            user=user,
            center=center or "",
            phone=phone or "",
            address=address or "",
            validated=True,
        )
        print(f"  → Usuario creado: {username} ({email})")
    
    return user


def import_proposal(data, dry_run=False):
    """Importar una propuesta desde diccionario JSON"""
    request_id = data.get("request_id", "")
    
    # Verificar si ya existe
    if AccessProposal.objects.filter(access_code=request_id).exists():
        print(f"  ⚠️ Ya existe: {request_id}")
        return None
    
    # Obtener o crear usuario
    user = get_or_create_user(
        email=data.get("email"),
        contact_person=data.get("contact_person"),
        center=data.get("center"),
        phone=data.get("phone"),
        address=data.get("address"),
    )
    
    # Parsear años
    start_year, end_year = parse_years(data.get("starting_ending_year"))
    
    # Mapear facilities
    facility_flags = map_facilities(data.get("facilities", []))
    
    # Mapear project_type
    raw_project_type = (data.get("project_type") or "").lower()
    project_type = ""
    for key, value in PROJECT_TYPE_MAP.items():
        if key in raw_project_type:
            project_type = value
            break
    
    # Mapear status
    resolution = data.get("committee_resolution")
    status = RESOLUTION_MAP.get(resolution, "submitted")
    
    # Parsear fecha
    proposal_date = data.get("proposal_date")
    submitted_at = None
    if proposal_date:
        try:
            submitted_at = datetime.strptime(proposal_date, "%Y-%m-%d")
        except ValueError:
            pass
    
    if dry_run:
        print(f"  [DRY RUN] Importaría: {data.get('proposal_title', '')[:50]}...")
        return None
    
    # Crear propuesta
    proposal = AccessProposal.objects.create(
        applicant=user,
        title=data.get("proposal_title", "")[:200],
        scope=data.get("proposal_description", ""),
        status=status,
        is_new_request=data.get("is_new_proposal", True),
        access_code=request_id,
        organization=data.get("center", "")[:200],
        contact_person=data.get("contact_person", "")[:200],
        email=data.get("email", ""),
        phone=data.get("phone", "")[:50] if data.get("phone") else "",
        project_name=data.get("project_name", "")[:200] if data.get("project_name") else "",
        project_type=project_type,
        funding_source=data.get("funding_source", "")[:200] if data.get("funding_source") else "",
        start_year=start_year,
        end_year=end_year,
        submitted_at=submitted_at,
        **facility_flags,
    )
    
    # Crear participantes
    participants_data = data.get("participants", [])
    for p in participants_data:
        Participant.objects.create(
            proposal=proposal,
            name=p.get("participant_name", "")[:100],
            affiliation=p.get("participant_address", "")[:200],
        )
    
    return proposal


def import_from_jsonl(filepath, limit=None, year_filter=None, dry_run=False):
    """Importar propuestas desde archivo JSONL"""
    imported = 0
    skipped = 0
    errors = 0
    
    with open(filepath, 'r', encoding='utf-8') as f:
        for line_num, line in enumerate(f, 1):
            if limit and imported >= limit:
                break
            
            try:
                data = json.loads(line.strip())
                
                # Filtrar por año si se especifica
                if year_filter:
                    proposal_date = data.get("proposal_date", "")
                    if not proposal_date or not proposal_date.startswith(str(year_filter)):
                        continue
                
                print(f"\n[{line_num}] Importando: {data.get('request_id', 'N/A')}")
                
                with transaction.atomic():
                    result = import_proposal(data, dry_run=dry_run)
                    if result:
                        imported += 1
                        print(f"  ✅ Importado: {result.title[:50]}...")
                    else:
                        skipped += 1
                        
            except json.JSONDecodeError as e:
                print(f"  ❌ Error JSON línea {line_num}: {e}")
                errors += 1
            except Exception as e:
                print(f"  ❌ Error línea {line_num}: {e}")
                errors += 1
    
    print(f"\n{'='*50}")
    print(f"Resumen: {imported} importados, {skipped} omitidos, {errors} errores")
    return imported, skipped, errors


if __name__ == "__main__":
    # Importar 5 propuestas de 2025
    filepath = "media/Datos/requests.jsonl"
    print("Importando 5 propuestas de 2025...")
    import_from_jsonl(filepath, limit=5, year_filter=2025, dry_run=False)
