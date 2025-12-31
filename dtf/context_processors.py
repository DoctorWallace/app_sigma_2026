# dtf/context_processors.py
"""
Context processor para proporcionar enlaces comunes de DTF en todos los templates.
"""
from django.urls import reverse


def dtf_cta_links(request):
    """
    Proporciona enlaces comunes de DTF (login, register, portal) en todos los templates.
    """
    try:
        return {
            "cta_links": {
                "login": reverse("accounts:login_dtf"),
                "register": reverse("accounts:register_dtf"),
                "portal": reverse("portal:home"),
            }
        }
    except Exception:
        # En caso de que aún no existan las rutas (migraciones/parciales), devolver vacío
        return {"cta_links": {}}

