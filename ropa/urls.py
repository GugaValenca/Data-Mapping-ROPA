from django.urls import path

from . import views

app_name = "ropa"

urlpatterns = [
    path("", views.dashboard, name="dashboard"),
    path("about/", views.about, name="about"),
    path("export/csv/", views.export_csv, name="export_csv"),
    path("export/pdf/", views.export_pdf, name="export_pdf"),
]
