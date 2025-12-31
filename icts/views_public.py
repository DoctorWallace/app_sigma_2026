# icts/views_public.py
from django.views.generic import TemplateView
from django.shortcuts import redirect
from django.contrib.auth.mixins import LoginRequiredMixin

class ICTSHomeView(TemplateView):
    template_name = "icts/home.html"
    
    def dispatch(self, request, *args, **kwargs):
        # Si el usuario está autenticado, redirigir al orquestador de dashboard (según rol)
        if request.user.is_authenticated:
            return redirect('icts:dashboard')
        return super().dispatch(request, *args, **kwargs)
