# dtf/views_public.py
from django.views.generic import TemplateView
from django.shortcuts import render
from django.conf import settings
from django.urls import reverse
import os


class DTFHomeView(TemplateView):
    template_name = "dtf/welcome.html"

    def dispatch(self, request, *args, **kwargs):
        # Si está autenticado, mostrar la página de usuario DTF
        if request.user.is_authenticated:
            self.template_name = "dtf/home_login_dtf.html"
        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["labs"] = [
            {
                "slug": "lab",
                "name": "Σ-LAB",
                "description": "Laboratorio avanzado de preparación metalográfica, corte y tratamientos térmicos.",
                "logo": "/media/Logos/sigma_lab.png",
                "url": reverse("dtf:lab_info", args=["lab"]),
            },
            {
                "slug": "mec",
                "name": "Σ-MEC",
                "description": "Laboratorio de caracterización mecánica de materiales estructurales.",
                "logo": "/media/Logos/logo_sigma_mec.png",
                "url": reverse("dtf:lab_info", args=["mec"]),
            },
            {
                "slug": "sims-implant",
                "name": "Σ-SIMS·Implant",
                "description": "Implantación de precisión con iones de baja tensión.",
                "logo": "/media/Logos/logo_sigma_imp_sims.png",
                "url": reverse("dtf:lab_info", args=["sims-implant"]),
            },
            {
                "slug": "optics",
                "name": "Σ-OPTIC",
                "description": "Caracterizaciones de propiedades ópticas.",
                "logo": "/media/Logos/sigma_optics.png",
                "url": reverse("dtf:lab_info", args=["optics"]),
            },
            {
                "slug": "dp",
                "name": "Σ-DP",
                "description": "Estudios de permeación y desorción térmicapara materiales avanzados.",
                "logo": "/media/Logos/sigma_DP3.png",
                "url": reverse("dtf:lab_info", args=["dp"]),
            },
        ]
        ctx["cta_links"] = {
            "login": reverse("accounts:login_dtf"),
            "register": reverse("accounts:register_dtf"),
            "portal": reverse("portal:home"),
        }
        return ctx


LAB_LABELS = {
    "lab": {
        "name": "Σ-LAB",
        "logo": "/media/Logos/sigma_lab.png",
        "email": "montserrat.martin@ciemat.es",
        "responsable": "Montserrat Martín Laso",
        "description": "Laboratorio avanzado de caracterización y análisis de materiales con equipamiento de última generación.",
        "services": [
            "Preparación y análisis de muestras",
            "Caracterización microestructural",
            "Análisis de composición",
            "Ensayos de materiales",
        ],
    },
    "mec": {
        "name": "Σ-MEC",
        "logo": "/media/Logos/logo_sigma_mec.png",
        "email": "nerea.garcia@ciemat.es",
        "description": "Caracterización de propiedades mecánicas de materiales estrucutrales.",
        "services": [
            "Ensayos de tracción desde nitrógeno líquido a 700ºC",
            "Ensayos de fatiga y creep-fatiga",
            "Tenacidad de fractura y crecimiento de grieta",
            "Ensayos estandarizados",
        ],
    },
    "sims-implant": {
        "name": "Σ-SIMS·Implant",
        "logo": "/media/Logos/logo_sigma_imp_sims.png",
        "email": "maria.gonzalez@ciemat.es",
        "description": "Implantación de iones de baja energía de precisión.",
        "services": [
            "Implantación superficial ionica",
            "Dose-rate variable y controlado",
            "Implantación de thin foils",
            "Mapeo de concentración de especie implantada",
        ],
    },
    "dp": {
        "name": "Σ-DP",
        "logo": "/media/Logos/sigma_DP3.png",
        "email": "marta.malo@ciemat.es",
        "description": "Estudios de permeación y desorción térmica de gases.",
        "services": [
            "Ensayos de permeación térmica",
            "Estudios de desorción térmica",
            "Análisis de difusión",
            "Caracterización de barreras",
        ],
    },
    "optics": {
        "name": "Σ-OPTIC",
        "logo": "/media/Logos/sigma_optics.png",
        "email": "rafael.vila@ciemat.es",
        "description": "Caracterización de propiedades ópticas de materiales funcionales para fusión.",
        "services": [
            "Absorción óptica",
            "UV - IR",
            "Medidas de reflectancia y transmitancia",
            "Caracterización de superficies",
            
        ],
    },
}


def lab_info(request, slug):
    info = LAB_LABELS.get(slug)
    if not info:
        return render(request, "dtf/under_construction.html", {"slug": slug})

    gallery_rows = []
    if slug == "lab":
        # Buscar imágenes en MEDIA_ROOT/lab con patrón Lab_(XX).jpg o variantes similares
        lab_dir = os.path.join(settings.MEDIA_ROOT, "lab")
        images = []
        try:
            if os.path.isdir(lab_dir):
                for fn in sorted(os.listdir(lab_dir)):
                    low = fn.lower()
                    if low.endswith('.jpg') and (low.startswith('lab_') or low.startswith('lab (') or low.startswith('lab')):
                        images.append(settings.MEDIA_URL.rstrip('/') + '/lab/' + fn)
        except Exception:
            images = []

        # Agrupar de 3 en 3 y calcular huecos para completar la cuadrícula
        for i in range(0, len(images), 3):
            chunk = images[i:i+3]
            filler = max(0, 3 - len(chunk))
            gallery_rows.append({
                "images": chunk,
                "filler_str": "x" * filler,  # iterar sobre string para añadir huecos
            })

    ctx = {"lab": info, "slug": slug, "gallery_rows": gallery_rows}
    return render(request, "dtf/lab_info.html", ctx)
