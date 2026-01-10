from django.contrib import admin

from .models import SIMSEquipment


@admin.register(SIMSEquipment)
class SIMSEquipmentAdmin(admin.ModelAdmin):
    list_display = (
        "code",
        "description",
        "is_reference",
        "responsible",
        "location",
        "received_date",
        "decommission_date",
        "updated_at",
    )
