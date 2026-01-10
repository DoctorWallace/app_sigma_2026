"""Importar todas las propuestas de requests.jsonl"""
import json
import re
from datetime import datetime

import os
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'automatizacion.settings')

import django
django.setup()

from django.db import transaction
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.utils import timezone
from icts.models import AccessProposal, Participant, ICTSUserProfile

User = get_user_model()

FACILITY_MAP = {
    'Scanning Electron Microscopy': 'facility_sem',
    'SEM + Focus Ion Beam': 'facility_sem_fib',
    'Secondary Ion Mass Spectrometry': 'facility_sims',
    'Profilemeter': 'facility_profilometer',
    'Confocal microscope': 'facility_confocal',
    'Van de Graaff': 'facility_vdg',
    'Ion Implanter': 'facility_imp',
    'Danfysik': 'facility_imp',
    'Optical properties': 'facility_optics',
}

RESOLUTION_MAP = {
    'ACCEPT': 'accepted',
    'REJECT': 'rejected', 
    'NOT ASSESSED': 'submitted',
    None: 'submitted',
}

PROJECT_TYPE_MAP = {
    'international': 'international',
    'european': 'european',
    'national': 'national',
    'regional': 'regional',
}

def parse_years(year_str):
    if not year_str:
        return None, None
    match = re.search(r'(\d{2,4})\s*[-–]\s*(\d{2,4})', str(year_str))
    if match:
        start, end = match.groups()
        if len(start) == 2: start = f'20{start}'
        if len(end) == 2: end = f'20{end}'
        return int(start), int(end)
    match = re.search(r'(\d{4})', str(year_str))
    if match:
        return int(match.group(1)), int(match.group(1))
    return None, None

def map_facilities(facilities_list):
    result = {f: False for f in ['facility_sem','facility_sem_fib','facility_imp','facility_sims','facility_confocal','facility_optics','facility_vdg','facility_profilometer','facility_olmat']}
    for fac in facilities_list:
        if not fac.get('requested'):
            continue
        name = fac.get('facility_name', '')
        for key, field in FACILITY_MAP.items():
            if key.lower() in name.lower():
                result[field] = True
                break
    return result

def get_or_create_user(email, contact_person, center=None, phone=None, address=None):
    if not email:
        email = f'unknown_{datetime.now().timestamp()}@example.com'
    email = email.lower().strip()
    try:
        return User.objects.get(email=email)
    except User.DoesNotExist:
        username = email.split('@')[0]
        base = username
        c = 1
        while User.objects.filter(username=username).exists():
            username = f'{base}_{c}'
            c += 1
        names = contact_person.split() if contact_person else ['Usuario']
        user = User.objects.create_user(
            username=username,
            email=email,
            first_name=names[0],
            last_name=' '.join(names[1:]) if len(names) > 1 else '',
            is_active=True
        )
        user.set_password('u1627729')
        user.save()
        ICTSUserProfile.objects.create(
            user=user,
            center=center or '',
            phone=phone or '',
            address=address or '',
            validated=True
        )
        # Añadir a icts_users si es ciemat
        if '@ciemat' in email:
            icts_group, _ = Group.objects.get_or_create(name='icts_users')
            user.groups.add(icts_group)
        return user

def main():
    imported = 0
    skipped = 0
    errors = 0
    
    with open('media/Datos/requests.jsonl', 'r', encoding='utf-8') as f:
        for line_num, line in enumerate(f, 1):
            try:
                data = json.loads(line.strip())
                request_id = data.get('request_id', '')
                
                # Verificar si ya existe
                if AccessProposal.objects.filter(access_code=request_id).exists():
                    skipped += 1
                    continue
                
                with transaction.atomic():
                    user = get_or_create_user(
                        data.get('email'),
                        data.get('contact_person'),
                        data.get('center'),
                        data.get('phone'),
                        data.get('address')
                    )
                    
                    start_year, end_year = parse_years(data.get('starting_ending_year'))
                    fac = map_facilities(data.get('facilities', []))
                    
                    raw_pt = (data.get('project_type') or '').lower()
                    project_type = ''
                    for k, v in PROJECT_TYPE_MAP.items():
                        if k in raw_pt:
                            project_type = v
                            break
                    
                    status = RESOLUTION_MAP.get(data.get('committee_resolution'), 'submitted')
                    
                    submitted_at = None
                    if data.get('proposal_date'):
                        try:
                            submitted_at = timezone.make_aware(
                                datetime.strptime(data['proposal_date'], '%Y-%m-%d')
                            )
                        except:
                            pass
                    
                    proposal = AccessProposal.objects.create(
                        applicant=user,
                        title=data.get('proposal_title', '')[:200],
                        scope=data.get('proposal_description', ''),
                        status=status,
                        is_new_request=data.get('is_new_proposal', True),
                        access_code=request_id,
                        organization=data.get('center', '')[:200] if data.get('center') else '',
                        contact_person=data.get('contact_person', '')[:200] if data.get('contact_person') else '',
                        email=data.get('email', '') or '',
                        phone=str(data.get('phone', ''))[:50] if data.get('phone') else '',
                        project_name=data.get('project_name', '')[:200] if data.get('project_name') else '',
                        project_type=project_type,
                        funding_source=data.get('funding_source', '')[:200] if data.get('funding_source') else '',
                        start_year=start_year,
                        end_year=end_year,
                        submitted_at=submitted_at,
                        **fac
                    )
                    
                    # Crear participantes
                    for p in data.get('participants', []):
                        Participant.objects.create(
                            proposal=proposal,
                            name=p.get('participant_name', '')[:100],
                            address=p.get('participant_address', '')[:200]
                        )
                    
                    imported += 1
                    if imported % 20 == 0:
                        print(f'  ... {imported} importadas')
                        
            except Exception as e:
                print(f'Error linea {line_num}: {e}')
                errors += 1
    
    print(f'\n{"="*50}')
    print(f'Importadas: {imported}')
    print(f'Omitidas (ya existian): {skipped}')
    print(f'Errores: {errors}')
    print(f'Total propuestas en BD: {AccessProposal.objects.count()}')
    print(f'Total participantes en BD: {Participant.objects.count()}')

if __name__ == '__main__':
    main()
