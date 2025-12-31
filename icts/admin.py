from django.contrib import admin
from .models import (
    Facility,
    AccessProposal,
    Participant,
    ProposalReview,
    ICTSUserProfile,
    OLMATRequest,
)


class ParticipantInline(admin.TabularInline):
    model = Participant
    extra = 0


@admin.register(AccessProposal)
class AccessProposalAdmin(admin.ModelAdmin):
    list_display = ("title", "applicant", "status", "created_at")
    list_filter = ("status", "created_at")
    search_fields = ("title", "applicant__username", "applicant__email")
    inlines = [ParticipantInline]
    filter_horizontal = ("facilities",)


@admin.register(ICTSUserProfile)
class ICTSUserProfileAdmin(admin.ModelAdmin):
    list_display = ("user", "user_siglas", "center", "phone", "validated", "created_at")
    search_fields = ("user__username", "user__email", "center", "phone")
    list_filter = ("validated", "created_at")


@admin.register(Facility)
class FacilityAdmin(admin.ModelAdmin):
    list_display = ("name", "code")
    search_fields = ("name", "code")


@admin.register(ProposalReview)
class ProposalReviewAdmin(admin.ModelAdmin):
    list_display = ("proposal", "reviewer", "decision", "updated_at")
    list_filter = ("decision", "updated_at")
    search_fields = ("proposal__title", "reviewer__username", "reviewer__email")


@admin.register(OLMATRequest)
class OLMATRequestAdmin(admin.ModelAdmin):
    list_display = ("proposal", "proponent_name", "service_type", "status", "access_code", "base_cost", "estimated_cost", "created_at")
    list_filter = ("service_type", "status", "created_at")
    search_fields = (
        "proposal__title",
        "proposal__applicant__username",
        "proposal__applicant__email",
        "proponent_name",
        "proponent_affiliation",
    )
    readonly_fields = ("base_cost", "access_code", "created_at", "updated_at")

    fieldsets = (
        ("Informacion basica", {
            "fields": ("proposal", "proponent_name", "proponent_affiliation", "entity_type", "service_type", "status", "access_code")
        }),
        ("Detalles tecnicos", {
            "fields": ("activity_description", "irradiation_requirements", "diagnostics_needed", "sample_preparation", "beam_usage")
        }),
        ("Planificacion", {
            "fields": ("preferred_dates", "flexibility", "additional_requirements")
        }),
        ("Evaluacion", {
            "fields": ("evaluation_notes", "estimated_cost", "base_cost")
        }),
        ("Timestamps", {
            "fields": ("created_at", "updated_at", "evaluated_at"),
            "classes": ("collapse",)
        }),
    )
