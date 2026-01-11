from django.urls import path
from . import views

app_name = "sales"

urlpatterns = [
    path("report/", views.sales_report, name="sales_report"),
    path("report/export.csv", views.sales_report_export_csv, name="sales_report_export_csv"),
]
