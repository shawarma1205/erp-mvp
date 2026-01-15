from django.contrib import admin
from .models import QuoteBatch, QuoteLine


class QuoteLineInline(admin.TabularInline):
    model = QuoteLine
    extra = 0


@admin.register(QuoteBatch)
class QuoteBatchAdmin(admin.ModelAdmin):
    list_display = (
        "name",
        "fx_period",
        "company_margin_rate",
        "supplier_markup_rate",
        "ocean_krw_per_kg",
        "air_krw_per_kg",
        "rounding_unit_php",
        "created_at",
    )
    actions = ["export_selected_batches_csv"]
    def export_selected_batches_csv(self, request, queryset):
        """
        여러 개 선택하면: 첫 번째 배치만 우선 다운로드(단순화).
        다음 단계에서 zip으로 확장 가능.
        """
        from pricing.exports.quote_csv import export_quote_batch_csv

        batch = queryset.order_by("id").first()
        return export_quote_batch_csv(batch.id)

    export_selected_batches_csv.short_description = "Export selected QuoteBatch to CSV"

    inlines = [QuoteLineInline]

@admin.register(QuoteLine)
class QuoteLineAdmin(admin.ModelAdmin):
    list_display = (
        "batch",
        "product",
        "qty_units",
        "final_price_php_per_unit",
        "created_at",
    )
