# sales/urls.py

from django.urls import path
from . import views

app_name = "sales"

urlpatterns = [
    path("report/", views.sales_report, name="sales_report"),
    path("report/export.csv", views.sales_report_export_csv, name="sales_report_export_csv"),

    path("customer/<int:customer_id>/report/", views.customer_detail_report, name="customer_detail_report"),
    path("customer/<int:customer_id>/report/export.csv", views.customer_detail_report_export_csv, name="customer_detail_report_export_csv"),

    # ✅ 추가: 인보이스 상세
    path("invoice/<int:invoice_id>/", views.invoice_detail, name="invoice_detail"),
    # sales/urls.py
    path("invoice/<int:invoice_id>/", views.invoice_detail, name="invoice_detail"),
    path("invoice/<int:invoice_id>/export.csv", views.invoice_detail_export_csv, name="invoice_detail_export_csv"),
    path("product-performance/", views.product_performance_overview, name="product_performance_overview"),
    path("product-performance/export.csv", views.product_performance_export_csv, name="product_performance_export_csv"),
]
