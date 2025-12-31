# sigmadp/signals.py
from django.db.models.signals import post_save, pre_save
from django.dispatch import receiver
from django.utils import timezone
from .models import DpSolicitud, DpIndicadorCalidad


@receiver(post_save, sender=DpSolicitud)
def actualizar_indicadores_solicitud(sender, instance, created, **kwargs):
    """Actualizar indicadores cuando cambie el estado de una solicitud"""
    
    # Obtener o crear el indicador para esta solicitud
    indicador, created = DpIndicadorCalidad.objects.get_or_create(
        solicitud=instance,
        defaults={'fecha_recepcion': instance.creado_en}
    )
    
    # Si se creó un nuevo indicador, establecer la fecha de recepción
    if created:
        indicador.fecha_recepcion = instance.creado_en
        indicador.save()
    
    # Actualizar fechas según el estado
    if instance.estado == DpSolicitud.Estado.FINALIZADA:
        # Si se finaliza la solicitud, establecer fecha de finalización
        if not indicador.fecha_finalizacion_analisis:
            indicador.fecha_finalizacion_analisis = timezone.now()
            indicador.actualizar_indicadores()
    
    # Si ya tiene fecha de finalización y se entrega el informe
    elif instance.estado == DpSolicitud.Estado.FINALIZADA and indicador.fecha_finalizacion_analisis:
        # Aquí se podría agregar lógica para detectar cuando se entrega el informe
        # Por ejemplo, si hay un campo específico o evento que indique la entrega
        pass


@receiver(pre_save, sender=DpSolicitud)
def detectar_cambio_estado(sender, instance, **kwargs):
    """Detectar cambios de estado para actualizar indicadores"""
    
    if instance.pk:  # Solo para instancias existentes
        try:
            old_instance = DpSolicitud.objects.get(pk=instance.pk)
            
            # Si cambió el estado a FINALIZADA
            if (old_instance.estado != DpSolicitud.Estado.FINALIZADA and 
                instance.estado == DpSolicitud.Estado.FINALIZADA):
                
                # Actualizar indicador
                try:
                    indicador = DpIndicadorCalidad.objects.get(solicitud=instance)
                    if not indicador.fecha_finalizacion_analisis:
                        indicador.fecha_finalizacion_analisis = timezone.now()
                        indicador.actualizar_indicadores()
                except DpIndicadorCalidad.DoesNotExist:
                    # Crear nuevo indicador si no existe
                    indicador = DpIndicadorCalidad.objects.create(
                        solicitud=instance,
                        fecha_recepcion=instance.creado_en,
                        fecha_finalizacion_analisis=timezone.now()
                    )
                    indicador.actualizar_indicadores()
                    
        except DpSolicitud.DoesNotExist:
            pass  # Es una nueva instancia
