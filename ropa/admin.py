from django.contrib import admin
from django_ratelimit.decorators import ratelimit

from .models import (
    DataCategory,
    DataRecipient,
    LegalBasis,
    ProcessingActivity,
    RetentionPeriod,
)

admin.site.site_header = "Data-Mapping-ROPA Administration"
admin.site.site_title = "Data-Mapping-ROPA Admin"
admin.site.index_title = "Manage processing activities & reference data"

# The login form is the one publicly reachable, unauthenticated endpoint
# in this app, so it's the one worth rate limiting against brute force.
# Wraps the existing admin site's bound login method directly (rather
# than swapping in a new AdminSite instance) so every @admin.register()
# call above keeps registering against the same site that urls.py serves.
admin.site.login = ratelimit(key="ip", rate="5/m", method="POST", block=True)(
    admin.site.login
)


@admin.register(DataCategory)
class DataCategoryAdmin(admin.ModelAdmin):
    list_display = ("name", "is_sensitive")
    list_filter = ("is_sensitive",)
    search_fields = ("name", "description")


@admin.register(LegalBasis)
class LegalBasisAdmin(admin.ModelAdmin):
    list_display = ("name",)
    search_fields = ("name", "description")


@admin.register(DataRecipient)
class DataRecipientAdmin(admin.ModelAdmin):
    list_display = ("name", "recipient_type", "country", "is_international_transfer")
    list_filter = ("recipient_type", "is_international_transfer")
    search_fields = ("name", "country", "notes")


@admin.register(RetentionPeriod)
class RetentionPeriodAdmin(admin.ModelAdmin):
    list_display = ("duration_label", "justification")
    search_fields = ("duration_label", "justification")


@admin.register(ProcessingActivity)
class ProcessingActivityAdmin(admin.ModelAdmin):
    list_display = (
        "name",
        "department",
        "legal_basis",
        "retention_period",
        "involves_sensitive_data",
        "involves_international_transfer",
        "is_high_risk",
    )
    list_filter = (
        "department",
        "data_categories",
        "legal_basis",
        "recipients__is_international_transfer",
    )
    search_fields = ("name", "description", "purpose", "department")
    filter_horizontal = ("data_categories", "recipients")

    fieldsets = (
        (None, {"fields": ("name", "description", "department", "purpose")}),
        (
            "Data mapping",
            {"fields": ("data_categories", "legal_basis", "recipients", "retention_period")},
        ),
    )

    @admin.display(boolean=True, description="Sensitive data")
    def involves_sensitive_data(self, obj):
        return obj.involves_sensitive_data

    @admin.display(boolean=True, description="Int'l transfer")
    def involves_international_transfer(self, obj):
        return obj.involves_international_transfer

    @admin.display(boolean=True, description="High risk")
    def is_high_risk(self, obj):
        return obj.is_high_risk
