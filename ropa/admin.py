from django.contrib import admin
from django.db.models import QuerySet
from django.http import HttpRequest
from django_ratelimit.decorators import ratelimit

from .models import (
    DataCategory,
    DataRecipient,
    LegalBasis,
    ProcessingActivity,
    RetentionPeriod,
)
from .throttling import client_ip

admin.site.site_header = "Data-Mapping-ROPA Administration"
admin.site.site_title = "Data-Mapping-ROPA Admin"
admin.site.index_title = "Manage processing activities & reference data"

# The login form is the one publicly reachable, unauthenticated endpoint
# in this app, so it's the one worth rate limiting against brute force.
# Wraps the existing admin site's bound login method directly (rather
# than swapping in a new AdminSite instance) so every @admin.register()
# call above keeps registering against the same site that urls.py serves.
# Keyed by client_ip rather than django-ratelimit's built-in "ip" key: on
# Vercel, REMOTE_ADDR is the platform's proxy, not the visitor, so the
# built-in key would put every visitor's login attempts in one shared
# budget instead of one budget per visitor (see ropa/throttling.py).
# mypy sees this as reassigning a method on an instance, which its type
# model doesn't allow even though Python (and Django's own AdminSite,
# built to have its attributes overridden this way) allows it fine.
admin.site.login = ratelimit(  # type: ignore[method-assign]
    key=client_ip, rate="5/m", method="POST", block=True
)(admin.site.login)


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

    def get_queryset(self, request: HttpRequest) -> QuerySet[ProcessingActivity]:
        # The three boolean columns below each read data_categories and/or
        # recipients per row via the model properties they proxy — without
        # this, the changelist page runs two extra queries per row (an N+1
        # that's invisible in this demo's small seed data but would scale
        # badly on a real ROPA with hundreds of activities).
        return (
            super()
            .get_queryset(request)
            .prefetch_related("data_categories", "recipients")
            .select_related("legal_basis", "retention_period")
        )

    @admin.display(boolean=True, description="Sensitive data")
    def involves_sensitive_data(self, obj: ProcessingActivity) -> bool:
        return obj.involves_sensitive_data

    @admin.display(boolean=True, description="Int'l transfer")
    def involves_international_transfer(self, obj: ProcessingActivity) -> bool:
        return obj.involves_international_transfer

    @admin.display(boolean=True, description="High risk")
    def is_high_risk(self, obj: ProcessingActivity) -> bool:
        return obj.is_high_risk
