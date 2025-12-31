from django.core.mail import EmailMessage
from django.template.loader import render_to_string
from django.conf import settings
import os


def enviar_resultados_termicos(solicitud, resultado):
    """
    Envía los resultados del análisis térmico por email al solicitante
    """
    try:
        # Preparar el asunto del email
        asunto = f"Resultados del análisis térmico DP-T#{solicitud.pk} - {solicitud.nombre_muestra}"
        
        # Preparar el contenido del email
        contexto = {
            'solicitud': solicitud,
            'resultado': resultado,
            'solicitante': solicitud.solicitante,
        }
        
        # Renderizar el template del email
        contenido_html = render_to_string('sigmadp/emails/resultados_termicos.html', contexto)
        contenido_texto = render_to_string('sigmadp/emails/resultados_termicos.txt', contexto)
        
        # Crear el mensaje de email
        email = EmailMessage(
            subject=asunto,
            body=contenido_html,
            from_email=settings.DEFAULT_FROM_EMAIL,
            to=[solicitud.solicitante.email],
            reply_to=[settings.DEFAULT_FROM_EMAIL],
        )
        
        # Configurar como HTML
        email.content_subtype = "html"
        
        # Adjuntar archivos de resultados
        if resultado.archivo_resultado:
            email.attach_file(resultado.archivo_resultado.path)
        
        if resultado.archivo_resultado_2:
            email.attach_file(resultado.archivo_resultado_2.path)
        
        # Enviar el email
        email.send()
        
        # Marcar como enviado
        resultado.enviado_por_email = True
        resultado.save()
        
        return True
        
    except Exception as e:
        print(f"Error enviando email: {e}")
        return False


def enviar_notificacion_aceptacion(solicitud):
    """
    Envía notificación de aceptación de solicitud térmica
    """
    try:
        asunto = f"Solicitud térmica DP-T#{solicitud.pk} aceptada - {solicitud.nombre_muestra}"
        
        contexto = {
            'solicitud': solicitud,
            'solicitante': solicitud.solicitante,
        }
        
        contenido_html = render_to_string('sigmadp/emails/solicitud_aceptada.html', contexto)
        
        email = EmailMessage(
            subject=asunto,
            body=contenido_html,
            from_email=settings.DEFAULT_FROM_EMAIL,
            to=[solicitud.solicitante.email],
            reply_to=[settings.DEFAULT_FROM_EMAIL],
        )
        
        email.content_subtype = "html"
        email.send()
        
        return True
        
    except Exception as e:
        print(f"Error enviando notificación de aceptación: {e}")
        return False


def enviar_notificacion_rechazo(solicitud):
    """
    Envía notificación de rechazo de solicitud térmica
    """
    try:
        asunto = f"Solicitud térmica DP-T#{solicitud.pk} rechazada - {solicitud.nombre_muestra}"
        
        contexto = {
            'solicitud': solicitud,
            'solicitante': solicitud.solicitante,
        }
        
        contenido_html = render_to_string('sigmadp/emails/solicitud_rechazada.html', contexto)
        
        email = EmailMessage(
            subject=asunto,
            body=contenido_html,
            from_email=settings.DEFAULT_FROM_EMAIL,
            to=[solicitud.solicitante.email],
            reply_to=[settings.DEFAULT_FROM_EMAIL],
        )
        
        email.content_subtype = "html"
        email.send()
        
        return True
        
    except Exception as e:
        print(f"Error enviando notificación de rechazo: {e}")
        return False
