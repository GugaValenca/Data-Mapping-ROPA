from django.db.models import Q, QuerySet
from django.http import HttpRequest
from django.shortcuts import render

from . import exports
from .models import DataCategory, LegalBasis, ProcessingActivity

INTERNATIONAL_CHOICES = (
    ("yes", "Yes — international transfer"),
    ("no", "No — domestic only"),
)


def _filtered_activities(request: HttpRequest) -> QuerySet[ProcessingActivity]:
    """Apply the dashboard's filter/search query params to the base queryset.

    Shared by the dashboard view and both export views so that exporting
    "the current view" and browsing it always mean the same set of rows.
    """
    activities = ProcessingActivity.objects.all().prefetch_related(
        "data_categories", "recipients"
    ).select_related("legal_basis", "retention_period")

    category_id = request.GET.get("data_category") or ""
    legal_basis_id = request.GET.get("legal_basis") or ""
    international = request.GET.get("international") or ""
    query = request.GET.get("q") or ""

    if category_id:
        activities = activities.filter(data_categories__id=category_id)
    if legal_basis_id:
        activities = activities.filter(legal_basis__id=legal_basis_id)
    if international == "yes":
        activities = activities.filter(recipients__is_international_transfer=True)
    elif international == "no":
        activities = activities.exclude(recipients__is_international_transfer=True)
    if query:
        activities = activities.filter(
            Q(name__icontains=query)
            | Q(description__icontains=query)
            | Q(department__icontains=query)
            | Q(purpose__icontains=query)
        )

    return activities.distinct()


def dashboard(request: HttpRequest):
    activities = list(_filtered_activities(request))
    high_risk_count = sum(1 for a in activities if a.is_high_risk)

    context = {
        "activities": activities,
        "total_count": len(activities),
        "high_risk_count": high_risk_count,
        "data_categories": DataCategory.objects.all(),
        "legal_bases": LegalBasis.objects.all(),
        "international_choices": INTERNATIONAL_CHOICES,
        "selected_category": request.GET.get("data_category") or "",
        "selected_legal_basis": request.GET.get("legal_basis") or "",
        "selected_international": request.GET.get("international") or "",
        "query": request.GET.get("q") or "",
        "filters_active": any(
            request.GET.get(key) for key in ("data_category", "legal_basis", "international", "q")
        ),
    }
    return render(request, "ropa/dashboard.html", context)


def about(request: HttpRequest):
    return render(request, "ropa/about.html")


def export_csv(request: HttpRequest):
    return exports.export_csv(_filtered_activities(request))


def export_pdf(request: HttpRequest):
    return exports.export_pdf(_filtered_activities(request))
