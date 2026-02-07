from django.urls import path
from . import views

app_name = "pricing"

urlpatterns = [
    # ✅ /pricing/  (QuoteBatch 목록)
    path("", views.quote_batch_list, name="quote_batch_list"),

    # 기존: batch detail
    path("quote/<int:batch_id>/", views.quote_batch_detail, name="quote_batch_detail"),
    path("quote/<int:batch_id>/export.csv", views.quote_batch_export_csv, name="quote_batch_export_csv"),
    path("quote/<int:batch_id>/line/<int:line_id>/delete/", views.quote_line_delete, name="quote_line_delete"),
]
