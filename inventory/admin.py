from django.contrib import admin
from .models import Product, InventoryBalance, InventoryLot, StockMovement


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = (
        "sku_code",
        "name_en",
        "name_ko",
        "base_unit",
        "net_weight_kg_per_unit",
        "origin_country",
        "origin_name",
        "is_active",
    )
    list_filter = ("is_active", "base_unit", "origin_country")
    search_fields = ("sku_code", "name_en", "name_ko", "origin_country", "origin_name")
    ordering = ("sku_code",)
    list_per_page = 50


@admin.register(InventoryBalance)
class InventoryBalanceAdmin(admin.ModelAdmin):
    list_display = ("product", "on_hand_qty_units", "avg_cost_php_per_unit", "last_updated_at")
    search_fields = ("product__sku_code", "product__name_en", "product__name_ko")
    list_per_page = 50


@admin.register(InventoryLot)
class InventoryLotAdmin(admin.ModelAdmin):
    list_display = (
        "received_date",
        "product",
        "supplier",
        "qty_units_received",
        "landed_cost_php_per_unit",
        "transport_mode",
    )
    list_filter = ("transport_mode", "received_date")
    search_fields = ("product__sku_code", "supplier__name", "supplier__name_ko")
    list_per_page = 50

@admin.register(StockMovement)
class StockMovementAdmin(admin.ModelAdmin):
    list_display = ("created_at", "movement_type", "product", "qty_units", "ref_table", "ref_id", "memo")
    list_filter = ("movement_type", "created_at")
    search_fields = ("product__sku_code", "product__name_en", "product__name_ko", "ref_table", "memo")