# sigmadp/views.py
from django.shortcuts import render
from django.views.decorators.http import require_http_methods
from .utils_detect import detect_and_preview

@require_http_methods(["GET","POST"])
def previsualizar_archivo(request):
    if request.method == "GET":
        return render(request, "sigmadp/previsualizar_archivo.html", {})  # o la variante que uses
    f = request.FILES.get("archivo_datos")
    if not f:
        return render(request, "sigmadp/previsualizar_archivo.html", {"error":"No se recibió archivo"})
    props = detect_and_preview(f)
    info_archivo = {
        "nombre": getattr(f, "name", "archivo"),
        "tamaño": getattr(f, "size", 0),
        "filas_totales": props["rows"],
        "columnas": props["ncols"],
        "separador_detectado": props["separator"],
        "decimal_detectado": props["decimal"],
        "auto_detectado": True,
    }
    ctx = {
        "info_archivo": info_archivo,
        "columnas": props["columns"],
        "datos_tabla": props["preview_rows"],
    }
    return render(request, "sigmadp/previsualizar_archivo.html", ctx)
