from django.contrib import admin
from .models import Sale, SaleLine


class SaleLineInline(admin.TabularInline):
    model = SaleLine
    extra = 0
    readonly_fields = ("cogs_php_per_unit_snapshot",)


@admin.register(Sale)
class SaleAdmin(admin.ModelAdmin):
    list_display = ("id", "sale_date", "customer", "created_at")
    search_fields = ("customer__name", "customer__name_ko")
    inlines = [SaleLineInline]


@admin.register(SaleLine)
class SaleLineAdmin(admin.ModelAdmin):
    list_display = ("sale", "product", "qty_units", "sell_price_php_per_unit", "cogs_php_per_unit_snapshot", "created_at")
    search_fields = ("product__sku_code", "sale__customer__name", "sale__customer__name_ko")
