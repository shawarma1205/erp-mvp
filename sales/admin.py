# sales/admin.py

from django.contrib import admin, messages
from django.db import transaction

from sales.models import SalesInvoice, SalesInvoiceLine
from sales.services.invoicing import issue_invoice, cancel_invoice  # ✅ cancel_invoice 추가


class SalesInvoiceLineInline(admin.TabularInline):
    model = SalesInvoiceLine
    extra = 0


@admin.action(description="ISSUE selected invoices (deduct stock + lock revenue)")
def issue_selected_invoices(modeladmin, request, queryset):
    ok = 0
    failed = 0

    for inv in queryset:
        try:
            with transaction.atomic():
                issue_invoice(inv.id)
            ok += 1
        except Exception as e:
            failed += 1
            messages.error(request, f"[{inv.invoice_no}] ISSUE failed: {e}")

    if ok:
        messages.success(request, f"ISSUED: {ok}")
    if failed:
        messages.warning(request, f"FAILED: {failed}")


@admin.action(description="CANCEL selected invoices (restore stock)")
def cancel_selected_invoices(modeladmin, request, queryset):
    ok = 0
    failed = 0

    for inv in queryset:
        try:
            with transaction.atomic():
                cancel_invoice(inv.id)
            ok += 1
        except Exception as e:
            failed += 1
            messages.error(request, f"[{inv.invoice_no}] CANCEL failed: {e}")

    if ok:
        messages.success(request, f"CANCELLED: {ok}")
    if failed:
        messages.warning(request, f"FAILED: {failed}")


@admin.register(SalesInvoice)
class SalesInvoiceAdmin(admin.ModelAdmin):
    list_display = ("invoice_no", "customer", "issue_date", "status", "total_php", "quote_batch", "created_at")
    list_filter = ("status", "issue_date", "customer")
    search_fields = ("invoice_no", "customer__name", "customer__name_ko")
    inlines = [SalesInvoiceLineInline]
    actions = [issue_selected_invoices, cancel_selected_invoices]  # ✅ cancel 액션 추가


@admin.register(SalesInvoiceLine)
class SalesInvoiceLineAdmin(admin.ModelAdmin):
    list_display = ("invoice", "product", "qty_units", "suggested_unit_price_php", "manual_unit_price_php", "final_unit_price_php", "created_at")
    search_fields = ("invoice__invoice_no", "product__sku_code", "product__name_en", "product__name_ko")
