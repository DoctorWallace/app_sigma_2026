"""
Comando de gestión para verificar préstamos vencidos y enviar notificaciones.
Este comando debe ejecutarse periódicamente (por ejemplo, diariamente) para:
1. Marcar préstamos como vencidos
2. Enviar notificaciones a usuarios y técnicos
3. Bloquear cuentas de usuarios con préstamos muy vencidos
"""

from django.core.management.base import BaseCommand
from django.utils import timezone
from django.contrib.auth.models import User
from django.db.models import Q
from datetime import timedelta
from sigmalab.models import PrestamoEquipo, NotificacionPrestamo


class Command(BaseCommand):
    help = 'Verifica préstamos vencidos y envía notificaciones'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dias-bloqueo',
            type=int,
            default=7,
            help='Días de retraso después de los cuales se bloquea la cuenta del usuario'
        )
        parser.add_argument(
            '--dias-notificacion',
            type=int,
            default=1,
            help='Días antes del vencimiento para enviar notificación de recordatorio'
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Ejecutar en modo de prueba sin realizar cambios'
        )

    def handle(self, *args, **options):
        dias_bloqueo = options['dias_bloqueo']
        dias_notificacion = options['dias_notificacion']
        dry_run = options['dry_run']
        
        self.stdout.write(
            self.style.SUCCESS(f'Iniciando verificación de préstamos vencidos...')
        )
        
        # Obtener fecha actual
        ahora = timezone.now()
        
        # 1. Marcar préstamos como vencidos
        prestamos_para_vencer = PrestamoEquipo.objects.filter(
            estado='activo',
            fecha_devolucion_estimada__lt=ahora
        )
        
        prestamos_vencidos_count = 0
        for prestamo in prestamos_para_vencer:
            if not dry_run:
                prestamo.marcar_como_vencido()
                prestamos_vencidos_count += 1
                
                # Crear notificación para el usuario
                NotificacionPrestamo.objects.create(
                    prestamo=prestamo,
                    destinatario=prestamo.usuario,
                    tipo='equipo_vencido',
                    mensaje=f'Tu préstamo del equipo {prestamo.equipo.nombre} ha vencido. Por favor, devuélvelo lo antes posible.'
                )
                
                # Crear notificación para el técnico
                NotificacionPrestamo.objects.create(
                    prestamo=prestamo,
                    destinatario=prestamo.tecnico_responsable,
                    tipo='equipo_vencido',
                    mensaje=f'El préstamo del equipo {prestamo.equipo.nombre} por {prestamo.usuario.get_full_name()} ha vencido.'
                )
        
        if prestamos_vencidos_count > 0:
            self.stdout.write(
                self.style.WARNING(f'Marcados {prestamos_vencidos_count} préstamos como vencidos')
            )
        
        # 2. Enviar notificaciones de recordatorio
        fecha_recordatorio = ahora + timedelta(days=dias_notificacion)
        prestamos_para_recordar = PrestamoEquipo.objects.filter(
            estado='activo',
            fecha_devolucion_estimada__lte=fecha_recordatorio,
            fecha_devolucion_estimada__gt=ahora,
            notificacion_enviada_vencimiento=False
        )
        
        recordatorios_enviados = 0
        for prestamo in prestamos_para_recordar:
            if not dry_run:
                # Crear notificación de recordatorio para el usuario
                NotificacionPrestamo.objects.create(
                    prestamo=prestamo,
                    destinatario=prestamo.usuario,
                    tipo='recordatorio_vencimiento',
                    mensaje=f'Recordatorio: Tu préstamo del equipo {prestamo.equipo.nombre} vence en {prestamo.dias_restantes} días.'
                )
                
                prestamo.notificacion_enviada_vencimiento = True
                prestamo.save()
                recordatorios_enviados += 1
        
        if recordatorios_enviados > 0:
            self.stdout.write(
                self.style.SUCCESS(f'Enviados {recordatorios_enviados} recordatorios de vencimiento')
            )
        
        # 3. Bloquear cuentas de usuarios con préstamos muy vencidos
        fecha_bloqueo = ahora - timedelta(days=dias_bloqueo)
        prestamos_muy_vencidos = PrestamoEquipo.objects.filter(
            estado='vencido',
            fecha_devolucion_estimada__lt=fecha_bloqueo,
            notificacion_enviada_retraso=False
        )
        
        cuentas_bloqueadas = 0
        for prestamo in prestamos_muy_vencidos:
            if not dry_run:
                # Bloquear cuenta del usuario
                prestamo.usuario.is_active = False
                prestamo.usuario.save()
                
                # Marcar notificación como enviada
                prestamo.notificacion_enviada_retraso = True
                prestamo.save()
                
                # Crear notificación para el técnico sobre el bloqueo
                NotificacionPrestamo.objects.create(
                    prestamo=prestamo,
                    destinatario=prestamo.tecnico_responsable,
                    tipo='equipo_vencido',
                    mensaje=f'La cuenta del usuario {prestamo.usuario.get_full_name()} ha sido bloqueada por préstamo vencido del equipo {prestamo.equipo.nombre} ({prestamo.dias_vencido} días de retraso).'
                )
                
                cuentas_bloqueadas += 1
        
        if cuentas_bloqueadas > 0:
            self.stdout.write(
                self.style.ERROR(f'Bloqueadas {cuentas_bloqueadas} cuentas por préstamos muy vencidos')
            )
        
        # 4. Estadísticas finales
        prestamos_activos = PrestamoEquipo.objects.filter(estado='activo').count()
        prestamos_vencidos = PrestamoEquipo.objects.filter(estado='vencido').count()
        prestamos_devueltos = PrestamoEquipo.objects.filter(estado='devuelto').count()
        
        self.stdout.write(
            self.style.SUCCESS(
                f'Verificación completada. '
                f'Activos: {prestamos_activos}, '
                f'Vencidos: {prestamos_vencidos}, '
                f'Devueltos: {prestamos_devueltos}'
            )
        )
        
        if dry_run:
            self.stdout.write(
                self.style.WARNING('Modo de prueba activado - No se realizaron cambios reales')
            )
