class NoCacheMiddleware:
    """Añade encabezados para evitar caché en respuestas HTML.

    Aplicable a todo el sitio para facilitar la iteración de plantillas.
    """
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)
        try:
            if 'text/html' in response.get('Content-Type', ''):
                response['Cache-Control'] = 'no-store, no-cache, must-revalidate, max-age=0'
                response['Pragma'] = 'no-cache'
                response['Expires'] = '0'
        except Exception:
            pass
        return response

