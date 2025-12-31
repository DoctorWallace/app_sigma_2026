"""
Middleware para validar acceso entre módulos y sesiones.
Evita accesos cruzados por sesión huérfana.
"""
from django.shortcuts import redirect
from django.urls import reverse
from django.contrib import messages
from django.conf import settings
from django.utils import translation
from core.roles import user_can_access_icts, user_can_access_dtf


class ModuleAccessMiddleware:
    """
    Middleware que valida que los usuarios accedan solo a módulos apropiados
    según su rol y la sesión activa.
    """
    
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # Solo aplicar a rutas autenticadas
        if not request.user.is_authenticated:
            return self.get_response(request)
        
        # Obtener el módulo de la sesión
        session_module = request.session.get('module')
        current_path = request.path
        
        # Determinar el módulo actual basado en la URL
        current_module = self._get_module_from_path(current_path)
        
        # Si no hay módulo en sesión, establecerlo basado en el rol
        if not session_module and current_module:
            if current_module == 'icts' and user_can_access_icts(request.user):
                request.session['module'] = 'icts'
            elif current_module in ['dtf', 'sigmalab', 'sigmadp', 'mec', 'sigmaoptics'] and user_can_access_dtf(request.user):
                request.session['module'] = 'dtf'
        
        # Validar acceso cruzado solo si hay sesión y módulo actual
        if session_module and current_module and session_module != current_module:
            # Usuario intentando acceder a módulo diferente
            if self._is_cross_module_access(session_module, current_module, request.user):
                messages.warning(
                    request, 
                    f"No tienes permisos para acceder a {current_module.upper()} "
                    f"desde una sesión de {session_module.upper()}. "
                    "Por favor, cierra sesión y vuelve a iniciar sesión."
                )
                return redirect(self._get_redirect_url(session_module))
        
        return self.get_response(request)
    
    def _get_module_from_path(self, path):
        """Determinar el módulo basado en la URL."""
        if path.startswith('/icts/'):
            return 'icts'
        elif path.startswith('/dtf/') or path.startswith('/sigmalab/') or \
             path.startswith('/sigmadp/') or path.startswith('/mec/') or \
             path.startswith('/sigmaoptics/'):
            return 'dtf'
        return None
    
    def _is_cross_module_access(self, session_module, current_module, user):
        """Verificar si es un acceso cruzado no permitido."""
        # ICTS a DTF: no permitido
        if session_module == 'icts' and current_module == 'dtf':
            return True
        # DTF a ICTS: no permitido  
        if session_module == 'dtf' and current_module == 'icts':
            return True
        return False
    
    def _get_redirect_url(self, module):
        """Obtener URL de redirección apropiada."""
        if module == 'icts':
            return reverse('icts:dashboard')
        elif module == 'dtf':
            return reverse('dtf:dashboard')
        else:
            return reverse('portal:home')


class ForceSpanishForLabUrlsMiddleware:
    """Force Spanish for lab routes and default English on ICTS external pages."""

    LAB_PREFIXES = (
        "/sigmaconf/",
        "/sigmasem/",
        "/sigmavdg/",
        "/sigmaimp/",
        "/dtf/lab/",
        "/dtf/mec/",
        "/dtf/dp/",
        "/dtf/optics/",
        "/sigmalab/",
        "/sigmadp/",
        "/mec/",
    )

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        path = request.path or ""
        language_cookie = request.COOKIES.get(settings.LANGUAGE_COOKIE_NAME)

        if path.startswith(self.LAB_PREFIXES):
            translation.activate("es")
            request.LANGUAGE_CODE = "es"
        elif language_cookie and translation.check_for_language(language_cookie):
            translation.activate(language_cookie)
            request.LANGUAGE_CODE = language_cookie
        elif not language_cookie:
            translation.activate("en")
            request.LANGUAGE_CODE = "en"

        response = self.get_response(request)
        return response
