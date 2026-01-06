from django.contrib import admin
from .models import Product


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ("sku_code", "name_en", "name_ko", "base_unit", "net_weight_kg_per_unit", "is_active")
    list_filter = ("is_active", "base_unit")
    search_fields = ("sku_code", "name_en", "name_ko")

from .models import InventoryBalance, InventoryLot


@admin.register(InventoryBalance)
class InventoryBalanceAdmin(admin.ModelAdmin):
    list_display = ("product", "on_hand_qty_units", "avg_cost_php_per_unit", "last_updated_at")
    search_fields = ("product__sku_code", "product__name_en", "product__name_ko")


@admin.register(InventoryLot)
class InventoryLotAdmin(admin.ModelAdmin):
    list_display = ("received_date", "product", "supplier", "qty_units_received", "landed_cost_php_per_unit", "transport_mode")
    list_filter = ("transport_mode", "received_date")
    search_fields = ("product__sku_code", "supplier__name", "supplier__name_ko")
