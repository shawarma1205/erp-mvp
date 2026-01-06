from django.urls import path
from . import views

app_name = "pricing"

urlpatterns = [
    path("quote/<int:batch_id>/", views.quote_batch_detail, name="quote_batch_detail"),
    path("quote/<int:batch_id>/export.csv", views.quote_batch_export_csv, name="quote_batch_export_csv"),
    path("quote/<int:batch_id>/line/<int:line_id>/delete/", views.quote_line_delete, name="quote_line_delete"),
]
