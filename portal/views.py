from django.shortcuts import redirect, render

from .forms import DirectServiceRequestForm

def home(request):
    return render(request, "portal/home.html")

def faq(request):
    return render(request, "portal/faq.html")


def icts_access(request):
    tariffs = [
        {
            "facility": "Microscopía electrónica EDX y EBSD",
            "reference": "FUSION-002",
            "price": "77,67",
            "unit": "€/hora",
            "notes": "Tarificación por hora de análisis",
        },
        {
            "facility": "Microscopía confocal",
            "reference": "FUSION-003",
            "price": "82,17",
            "unit": "€/hora",
            "notes": "Tarificación por hora de análisis",
        },
        {
            "facility": "Medida de propiedades dieléctricas",
            "reference": "FUSION-004",
            "price": "74,62",
            "unit": "€/hora",
            "notes": "Tarificación por hora de análisis",
        },
        {
            "facility": "SIMS — espectrometría de masas (espectro de masas)",
            "reference": "FUSION-005",
            "price": "75,84",
            "unit": "€/hora",
            "notes": "Tarificación por hora de análisis",
        },
        {
            "facility": "SIMS — perfil de masas en profundidad",
            "reference": "FUSION-006",
            "price": "92,36",
            "unit": "€/hora",
            "notes": "Tarificación por hora de análisis",
        },
        {
            "facility": "Irradiación con electrones de 2 MeV",
            "reference": "FUSION-007",
            "price": "1.095,26",
            "unit": "€/día",
            "notes": "Tarificación por día de análisis",
        },
        {
            "facility": "Perfilometría con Bruker Dektak XT",
            "reference": "FUSION-008",
            "price": "44,77",
            "unit": "€/hora",
            "notes": "Tarificación por hora de análisis",
        },
        {
            "facility": "OLMAT",
            "reference": "OLMAT-2024",
            "price": "5.000",
            "unit": "€",
            "notes": "Servicio técnico: operación del dispositivo y preparación de muestras",
        },
        {
            "facility": "OLMAT",
            "reference": "OLMAT-2024",
            "price": "10.305",
            "unit": "€",
            "notes": "Servicio de investigación: soporte científico, análisis e interpretación",
        },
        {
            "facility": "LML (metales líquidos)",
            "reference": "",
            "price": None,
            "unit": "",
            "notes": "Coste por definir",
        },
        {
            "facility": "Implantador 60 keV",
            "reference": "",
            "price": None,
            "unit": "",
            "notes": "Coste por definir",
        },
    ]
    return render(request, "portal/icts_access.html", {"tariffs": tariffs})


def direct_request_create(request):
    if request.method == "POST":
        form = DirectServiceRequestForm(request.POST, request.FILES)
        if form.is_valid():
            form.save()
            return redirect("portal:direct_request_success")
    else:
        form = DirectServiceRequestForm()
    return render(request, "portal/direct_request_form.html", {"form": form})


def direct_request_success(request):
    return render(request, "portal/direct_request_success.html")
