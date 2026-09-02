from dataclasses import dataclass

from django.db.models import Q, QuerySet
from django.http import HttpRequest, HttpResponse
from django.shortcuts import render

from . import exports
from .models import DataCategory, LegalBasis, ProcessingActivity

INTERNATIONAL_CHOICES = (
    ("yes", "Yes — international transfer"),
    ("no", "No — domestic only"),
)


@dataclass(frozen=True)
class DashboardFilters:
    """Parsed, validated query params from the dashboard's filter form.

    Parsed once per request and passed down to `_filtered_activities`,
    the dashboard's own template context, and both export views, so
    "what am I filtering on" is computed in exactly one place.
    """

    category_id: str
    legal_basis_id: str
    international: str
    query: str

    @property
    def is_active(self) -> bool:
        return bool(self.category_id or self.legal_basis_id or self.international or self.query)


def _parse_filters(request: HttpRequest) -> DashboardFilters:
    # category_id/legal_basis_id feed straight into `.filter(id=...)` below,
    # so a non-numeric value (someone editing the URL by hand) is dropped
    # here rather than reaching the ORM, where it would raise instead of
    # just matching nothing.
    category_id = request.GET.get("data_category") or ""
    legal_basis_id = request.GET.get("legal_basis") or ""
    return DashboardFilters(
        category_id=category_id if category_id.isdigit() else "",
        legal_basis_id=legal_basis_id if legal_basis_id.isdigit() else "",
        international=request.GET.get("international") or "",
        query=request.GET.get("q") or "",
    )


def _filtered_activities(filters: DashboardFilters) -> QuerySet[ProcessingActivity]:
    """Apply the dashboard's filters to the base queryset.

    Shared by the dashboard view and both export views so that exporting
    "the current view" and browsing it always mean the same set of rows.
    """
    activities = (
        ProcessingActivity.objects.all()
        .prefetch_related("data_categories", "recipients")
        .select_related("legal_basis", "retention_period")
    )

    if filters.category_id:
        activities = activities.filter(data_categories__id=filters.category_id)
    if filters.legal_basis_id:
        activities = activities.filter(legal_basis__id=filters.legal_basis_id)
    if filters.international == "yes":
        activities = activities.filter(recipients__is_international_transfer=True)
    elif filters.international == "no":
        activities = activities.exclude(recipients__is_international_transfer=True)
    if filters.query:
        activities = activities.filter(
            Q(name__icontains=filters.query)
            | Q(description__icontains=filters.query)
            | Q(department__icontains=filters.query)
            | Q(purpose__icontains=filters.query)
        )

    return activities.distinct()


def dashboard(request: HttpRequest) -> HttpResponse:
    filters = _parse_filters(request)
    activities = list(_filtered_activities(filters))
    high_risk_count = sum(1 for a in activities if a.is_high_risk)

    context = {
        "activities": activities,
        "total_count": len(activities),
        "high_risk_count": high_risk_count,
        "data_categories": DataCategory.objects.all(),
        "legal_bases": LegalBasis.objects.all(),
        "international_choices": INTERNATIONAL_CHOICES,
        "selected_category": filters.category_id,
        "selected_legal_basis": filters.legal_basis_id,
        "selected_international": filters.international,
        "query": filters.query,
        "filters_active": filters.is_active,
    }
    return render(request, "ropa/dashboard.html", context)


def about(request: HttpRequest) -> HttpResponse:
    return render(request, "ropa/about.html")


def export_csv(request: HttpRequest) -> HttpResponse:
    return exports.export_csv(_filtered_activities(_parse_filters(request)))


def export_pdf(request: HttpRequest) -> HttpResponse:
    return exports.export_pdf(_filtered_activities(_parse_filters(request)))
