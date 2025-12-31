from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from django.utils import timezone
from datetime import datetime, timedelta
import random

from icts.models import AccessProposal, ProposalReview, Participant

User = get_user_model()

class Command(BaseCommand):
    help = 'Corrige la propiedad de las propuestas para que solo los usuarios las envíen'

    def add_arguments(self, parser):
        parser.add_argument(
            '--delete-existing',
            action='store_true',
            help='Eliminar propuestas existentes antes de crear las nuevas',
        )

    def handle(self, *args, **options):
        if options['delete_existing']:
            self.stdout.write('Eliminando propuestas existentes...')
            AccessProposal.objects.all().delete()
            ProposalReview.objects.all().delete()
            self.stdout.write(self.style.SUCCESS('Propuestas existentes eliminadas.'))

        # Obtener usuarios, revisores y responsable
        users = User.objects.filter(username__startswith='ictsdemo_u')
        reviewers = User.objects.filter(username__startswith='ictsdemo_r')
        responsible = User.objects.filter(username='ictsdemo_resp01').first()

        if not users.exists():
            self.stdout.write(self.style.ERROR('No se encontraron usuarios ictsdemo_u.'))
            return

        if not reviewers.exists():
            self.stdout.write(self.style.ERROR('No se encontraron revisores ictsdemo_r.'))
            return

        if not responsible:
            self.stdout.write(self.style.ERROR('No se encontró el responsable ictsdemo_resp01.'))
            return

        self.stdout.write(f'Generando propuestas para {users.count()} usuarios...')
        self.stdout.write(f'Revisores disponibles: {reviewers.count()}')
        self.stdout.write(f'Responsable: {responsible.username}')

        # Datos de prueba
        titles = [
            "Análisis de microestructura de aleaciones de titanio",
            "Caracterización de nanopartículas de óxido de zinc",
            "Estudio de interfaces en materiales compuestos",
            "Análisis de defectos en semiconductores",
            "Caracterización de recubrimientos protectores",
            "Estudio de corrosión en aceros inoxidables",
            "Análisis de fases en cerámicas avanzadas",
            "Caracterización de materiales biomédicos",
            "Estudio de propiedades magnéticas",
            "Análisis de superficies funcionalizadas",
            "Caracterización de catalizadores",
            "Estudio de materiales para energía solar",
            "Análisis de polímeros conductores",
            "Caracterización de materiales 2D",
            "Estudio de interfaces metal-óxido"
        ]

        scopes = [
            "El objetivo de este proyecto es caracterizar la microestructura y propiedades de materiales avanzados mediante técnicas de análisis de superficie y volumen.",
            "Este estudio se centra en el análisis de la estructura cristalina y defectos en materiales semiconductores.",
            "La investigación tiene como objetivo principal el desarrollo y caracterización de nuevos materiales compuestos con propiedades mejoradas.",
            "Este proyecto se enfoca en el estudio de la corrosión y degradación de materiales en condiciones ambientales específicas.",
            "La caracterización de materiales biomédicos requiere un análisis detallado de su biocompatibilidad y propiedades mecánicas."
        ]

        organizations = [
            "Universidad Complutense de Madrid",
            "Universidad Politécnica de Madrid", 
            "Universidad Autónoma de Madrid",
            "Universidad Carlos III de Madrid",
            "Universidad Rey Juan Carlos",
            "Universidad de Alcalá",
            "CSIC - Instituto de Ciencia de Materiales",
            "CSIC - Instituto de Cerámica y Vidrio",
            "CIEMAT - Centro de Investigaciones Energéticas",
            "IMDEA Materiales"
        ]

        project_names = [
            "MATERIALS-2024",
            "NANOTECH-2023", 
            "ADVANCED-MATERIALS-2025",
            "BIOMATERIALS-2024",
            "ENERGY-MATERIALS-2023",
            "COMPOSITES-2025",
            "CERAMICS-2024",
            "METALS-2023",
            "POLYMERS-2025",
            "CATALYSTS-2024"
        ]

        funding_sources = [
            "Ministerio de Ciencia e Innovación",
            "Comunidad de Madrid",
            "Horizon Europe",
            "FEDER",
            "Fundación BBVA",
            "CSIC",
            "Universidad",
            "Empresa privada"
        ]

        # Técnicas disponibles
        techniques = [
            ('facility_sem', 'SEM/EDX'),
            ('facility_sem_fib', 'FIB'),
            ('facility_sims', 'SIMS'),
            ('facility_confocal', 'Confocal'),
            ('facility_imp', 'Ion Implanter'),
            ('facility_vdg', 'VDG'),
            ('facility_profilometer', 'Profilometer')
        ]

        # Generar propuestas para cada usuario
        total_created = 0
        
        for user in users:
            # Crear entre 3-6 propuestas por usuario
            num_proposals = random.randint(3, 6)
            
            for i in range(num_proposals):
                # Fechas aleatorias entre 2023-2025 con distribución
                year_weights = {2023: 0.3, 2024: 0.4, 2025: 0.3}
                year = random.choices(list(year_weights.keys()), weights=list(year_weights.values()))[0]
                month = random.randint(1, 12)
                day = random.randint(1, 28)
                created_date = datetime(year, month, day)
                
                # Estado aleatorio con distribución realista
                status_weights = {
                    'draft': 0.15,
                    'submitted': 0.25, 
                    'accepted': 0.45,
                    'rejected': 0.15
                }
                status = random.choices(
                    list(status_weights.keys()),
                    weights=list(status_weights.values())
                )[0]

                # Seleccionar técnicas aleatorias (1-3 técnicas por propuesta)
                selected_techniques = random.sample(techniques, random.randint(1, 3))
                
                # Crear propuesta
                proposal = AccessProposal.objects.create(
                    applicant=user,  # Solo usuarios pueden ser solicitantes
                    title=random.choice(titles),
                    scope=random.choice(scopes),
                    status=status,
                    
                    # Información del solicitante
                    organization=random.choice(organizations),
                    contact_person=user.get_full_name() or user.username,
                    email=user.email,
                    phone=f"+34 {random.randint(600000000, 699999999)}",
                    
                    # Información del proyecto
                    project_name=random.choice(project_names),
                    project_type=random.choice(['international', 'european', 'national', 'regional']),
                    funding_source=random.choice(funding_sources),
                    start_year=year,
                    end_year=year + random.randint(1, 3),
                    
                    # Experimentos y referencias
                    previous_experiments=f"Experimentos previos realizados en {random.choice(['2022', '2023', '2024'])} con resultados prometedores.",
                    references=f"Referencias: {random.choice(['Nature Materials', 'Advanced Materials', 'Materials Science', 'Journal of Materials Science'])} (2023)",
                    
                    # Técnicas seleccionadas
                    **{tech[0]: True for tech in selected_techniques},
                    
                    # Datos específicos por técnica
                    facility_data=self.generate_facility_data(selected_techniques)
                )

                # Actualizar fecha de creación
                AccessProposal.objects.filter(id=proposal.id).update(created_at=created_date)
                
                # Generar código de acceso si está aprobada
                if status == 'accepted':
                    from icts.utils import build_access_code
                    proposal.access_code = build_access_code(proposal)
                    proposal.save()

                # Crear participantes (0-2 por propuesta)
                num_participants = random.randint(0, 2)
                for j in range(num_participants):
                    Participant.objects.create(
                        proposal=proposal,
                        name=f"Participante {j+1} {user.last_name}",
                        center=random.choice(organizations),
                        address=f"Calle {random.randint(1, 100)}, Madrid, España"
                    )

                # Crear revisiones si está enviada, aceptada o rechazada
                if status in ['submitted', 'accepted', 'rejected']:
                    self.create_reviews(proposal, status, reviewers, responsible)

                total_created += 1

        self.stdout.write(
            self.style.SUCCESS(
                f'Se crearon {total_created} propuestas correctamente asignadas.'
            )
        )

    def generate_facility_data(self, selected_techniques):
        """Genera datos específicos para cada técnica"""
        facility_data = {}
        
        for tech_field, tech_name in selected_techniques:
            if tech_name == 'SEM/EDX':
                facility_data['sem'] = {
                    'sample_0_identification': f'SEM-{random.randint(1000, 9999)}',
                    'sample_0_name': f'Muestra SEM {random.randint(1, 10)}',
                    'sample_0_details': f'Detalles de la muestra para análisis SEM: composición {random.choice(["aleación", "cerámica", "polímero"])}'
                }
            elif tech_name == 'FIB':
                facility_data['fib'] = {
                    'sample_0_identification': f'FIB-{random.randint(1000, 9999)}',
                    'sample_0_name': f'Muestra FIB {random.randint(1, 10)}',
                    'sample_0_details': f'Preparación de muestra para FIB: espesor {random.randint(50, 200)}nm'
                }
            elif tech_name == 'SIMS':
                facility_data['sims'] = {
                    'sample_0_identification': f'SIMS-{random.randint(1000, 9999)}',
                    'sample_0_name': f'Muestra SIMS {random.randint(1, 10)}',
                    'sample_0_details': f'Análisis SIMS de elementos traza en {random.choice(["silicio", "germanio", "carburo de silicio"])}'
                }
            elif tech_name == 'Confocal':
                facility_data['confocal'] = {
                    'sample_0_identification': f'CONF-{random.randint(1000, 9999)}',
                    'sample_0_name': f'Muestra Confocal {random.randint(1, 10)}',
                    'sample_0_details': f'Microscopía confocal de {random.choice(["fluorescencia", "reflexión", "transmisión"])}'
                }
            elif tech_name == 'Ion Implanter':
                facility_data['imp'] = {
                    'num_samples': random.randint(1, 5),
                    'species': random.choice(['B+', 'P+', 'As+', 'N+']),
                    'dose': f'{random.randint(1, 10)}e{random.randint(14, 16)} cm-2'
                }
            elif tech_name == 'VDG':
                facility_data['vdg'] = {
                    'code': f'VDG-{random.randint(100, 999)}',
                    'material': random.choice(['Si', 'Ge', 'GaAs', 'InP']),
                    'experiment_description': f'Experimento VDG para {random.choice(["dopado", "implantación", "recocido"])}'
                }
            elif tech_name == 'Profilometer':
                facility_data['profilometer'] = {
                    'num_samples': random.randint(1, 3),
                    'range_um': random.randint(1, 10),
                    'resolution_nm': random.randint(1, 10)
                }
        
        return facility_data

    def create_reviews(self, proposal, status, reviewers, responsible):
        """Crea revisiones para la propuesta"""
        # Asignar 2-3 revisores aleatorios
        selected_reviewers = random.sample(list(reviewers), min(3, reviewers.count()))
        
        for reviewer in selected_reviewers:
            if status == 'accepted':
                decision = 'approve'
                scores = {
                    'score_scientific_quality': random.randint(4, 5),
                    'score_need_infrastructure': random.randint(3, 5),
                    'score_industrial_potential': random.randint(3, 5)
                }
                comments = f"Excelente propuesta con {random.choice(['alta calidad científica', 'buen potencial industrial', 'metodología sólida'])}"
            elif status == 'rejected':
                decision = 'reject'
                scores = {
                    'score_scientific_quality': random.randint(1, 3),
                    'score_need_infrastructure': random.randint(1, 3),
                    'score_industrial_potential': random.randint(1, 3)
                }
                comments = f"Propuesta que necesita {random.choice(['mayor justificación científica', 'mejoras metodológicas', 'clarificación de objetivos'])}"
            else:  # submitted
                decision = 'pending'
                scores = {}
                comments = "Propuesta pendiente de revisión"

            ProposalReview.objects.create(
                proposal=proposal,
                reviewer=reviewer,
                decision=decision,
                comments=comments,
                **scores
            )

