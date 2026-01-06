from decimal import Decimal
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_http_methods

from pricing.models import QuoteBatch, QuoteLine
from pricing.exports.quote_csv import export_quote_batch_csv
from pricing.services.quoting import compute_quote_line
from inventory.models import Product
from django.views.decorators.http import require_POST


@require_http_methods(["GET", "POST"])
def quote_batch_detail(request, batch_id: int):
    batch = get_object_or_404(QuoteBatch, id=batch_id)

    if request.method == "POST":
        form_type = request.POST.get("form_type", "").strip()

        # 1) Batch Settings 업데이트
        if form_type == "batch_settings":
            batch.company_margin_rate = Decimal(request.POST["company_margin_rate"])
            batch.supplier_markup_rate = Decimal(request.POST["supplier_markup_rate"])
            batch.transport_mode = request.POST["transport_mode"]
            batch.transport_krw_per_kg = Decimal(request.POST["transport_krw_per_kg"])
            batch.rounding_unit_php = Decimal(request.POST["rounding_unit_php"])
            batch.save()
            return redirect("pricing:quote_batch_detail", batch_id=batch.id)

        # 2) (기본) QuoteLine 생성
        sku = request.POST.get("sku_code", "").strip()
        qty_units = Decimal(request.POST.get("qty_units", "1"))
        supplier_cost_krw_per_unit = Decimal(request.POST.get("supplier_cost_krw_per_unit", "0"))
        billable_weight_kg_total = Decimal(request.POST.get("billable_weight_kg_total", "0"))
        other_cost_php_total = Decimal(request.POST.get("other_cost_php_total", "0"))

        product = get_object_or_404(Product, sku_code=sku)

        line = QuoteLine(
            batch=batch,
            product=product,
            qty_units=qty_units,
            supplier_cost_krw_per_unit=supplier_cost_krw_per_unit,
            billable_weight_kg_total=billable_weight_kg_total,
            other_cost_php_total=other_cost_php_total,
        )
        compute_quote_line(line)
        line.save()

        return redirect("pricing:quote_batch_detail", batch_id=batch.id)


    lines = (
        QuoteLine.objects
        .filter(batch=batch)
        .select_related("product")
        .order_by("-created_at")
    )
    lang = request.GET.get("lang","ko")

    context = {
        "batch": batch,
        "lines": lines,
        "lang": lang,
    }
    return render(request, "pricing/quote_batch_detail.html", context)


def quote_batch_export_csv(request, batch_id: int):
    return export_quote_batch_csv(batch_id)

@require_POST
def quote_line_delete(request, batch_id: int, line_id: int):
    batch = get_object_or_404(QuoteBatch, id=batch_id)
    line = get_object_or_404(QuoteLine, id=line_id, batch=batch)
    line.delete()
    return redirect("pricing:quote_batch_detail", batch_id=batch.id)
