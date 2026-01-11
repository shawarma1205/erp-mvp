# inventory/urls.py
from django.urls import path
from . import views

app_name = "inventory"

urlpatterns = [
    path("overview/", views.inventory_overview, name="inventory_overview"),
    path("overview/balances.csv", views.export_balances_csv, name="export_balances_csv"),
    path("overview/movements.csv", views.export_movements_csv, name="export_movements_csv"),
]
