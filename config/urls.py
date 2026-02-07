
from django.contrib import admin
from django.urls import path, include
from core.views import dashboard

urlpatterns = [
    path('admin/', admin.site.urls),
    path("", dashboard, name="dashboard"),
    path("pricing/", include("pricing.urls")),
    path("sales/", include("sales.urls")),
    path("inventory/", include("inventory.urls")),

]
