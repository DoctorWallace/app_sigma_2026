from django.contrib import admin
from .models import DTFUserProfile


@admin.register(DTFUserProfile)
class DTFUserProfileAdmin(admin.ModelAdmin):
    list_display = ("user", "is_ciemat", "departamento", "matricula", "telefono_interno")
    list_filter = ("is_ciemat", "departamento")
    search_fields = ("user__username", "user__email", "matricula")

