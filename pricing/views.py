# pricing/views.py

from decimal import Decimal
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_http_methods, require_POST

from pricing.models import QuoteBatch, QuoteLine
from pricing.exports.quote_csv import export_quote_batch_csv
from pricing.services.quoting import compute_quote_line
from inventory.models import Product


@require_http_methods(["GET", "POST"])
def quote_batch_detail(request, batch_id: int):
    batch = get_object_or_404(QuoteBatch, id=batch_id)

    if request.method == "POST":
        form_type = request.POST.get("form_type", "").strip()

        # 1) Batch Settings 업데이트
        if form_type == "batch_settings":
            batch.company_margin_rate = Decimal(request.POST["company_margin_rate"])
            batch.supplier_markup_rate = Decimal(request.POST["supplier_markup_rate"])
            batch.ocean_krw_per_kg = Decimal(request.POST["ocean_krw_per_kg"])
            batch.air_krw_per_kg = Decimal(request.POST["air_krw_per_kg"])
            batch.rounding_unit_php = Decimal(request.POST["rounding_unit_php"])
            batch.save()
            return redirect("pricing:quote_batch_detail", batch_id=batch.id)

        # 2) QuoteLine 생성
        sku = request.POST.get("sku_code", "").strip()
        qty_units = Decimal(request.POST.get("qty_units", "1"))
        supplier_cost_krw_per_unit = Decimal(request.POST.get("supplier_cost_krw_per_unit", "0"))
        billable_weight_kg_total = Decimal(request.POST.get("billable_weight_kg_total", "0"))
        other_cost_php_total = Decimal(request.POST.get("other_cost_php_total", "0"))

        transport_mode_raw = request.POST.get("transport_mode", "").strip()
        transport_mode = transport_mode_raw if transport_mode_raw else None

        manual_raw = request.POST.get("manual_price_php_per_unit", "").strip()
        manual_price = Decimal(manual_raw) if manual_raw else None

        product = get_object_or_404(Product, sku_code=sku)

        line = QuoteLine(
            batch=batch,
            product=product,
            transport_mode=transport_mode,
            qty_units=qty_units,
            supplier_cost_krw_per_unit=supplier_cost_krw_per_unit,
            billable_weight_kg_total=billable_weight_kg_total,
            other_cost_php_total=other_cost_php_total,
            manual_price_php_per_unit=manual_price,
        )

        compute_quote_line(line)
        line.save()
        return redirect("pricing:quote_batch_detail", batch_id=batch.id)

    lines = (
        QuoteLine.objects
        .filter(batch=batch)
        .select_related("product")
        .order_by("product__sku_code", "id")
    )

    display_lines = []
    for ln in lines:
        suggested = ln.base_price_php_per_unit
        manual = ln.manual_price_php_per_unit

        diff_pct = None
        if manual is not None and suggested not in (None, 0):
            diff_pct = (manual - suggested) / suggested * Decimal("100")

        display_lines.append({
            "obj": ln,
            "suggested_price": suggested,
            "diff_pct": diff_pct,
        })

    lang = request.GET.get("lang", "ko")
    TEXT = {
        "ko": {
            "language": "Language",
            "download_csv": "CSV 다운로드",
            "batch_settings": "배치 설정",
            "company_margin_rate": "회사 마진율 (예: 0.20)",
            "supplier_markup_rate": "공급사 마크업율 (예: 0.05)",
            "ocean_krw_per_kg": "해상 운송비 (KRW/kg)",
            "air_krw_per_kg": "항공 운송비 (KRW/kg)",
            "rounding_unit_php": "라운딩 단위 (PHP)",

            "add_quote_line": "라인 추가",
            "sku_code": "SKU",
            "qty_units": "수량",
            "supplier_cost_krw_per_unit": "공급 원가 (KRW/unit)",
            "billable_weight_kg_total": "청구중량 합계 (KG)",
            "other_cost_php_total": "조정금액 (PHP total)",
            "transport_mode": "운송모드(옵션)",
            "manual_price_php_per_unit": "조정가 (PHP/unit, 옵션)",
            "lines": "라인",
            "suggested_price": "제안가",
            "manual_price": "조정가",
            "price_diff_pct": "차이(%)",
        },
        "en": {
            "language": "Language",
            "download_csv": "Download CSV",
            "batch_settings": "Batch Settings",
            "company_margin_rate": "Company margin rate (e.g. 0.20)",
            "supplier_markup_rate": "Supplier markup rate (e.g. 0.05)",
            "ocean_krw_per_kg": "Ocean transport (KRW/kg)",
            "air_krw_per_kg": "Air transport (KRW/kg)",
            "rounding_unit_php": "Rounding unit (PHP)",

            "add_quote_line": "Add Quote Line",
            "sku_code": "SKU Code",
            "qty_units": "Qty Units",
            "supplier_cost_krw_per_unit": "Supplier cost (KRW/unit)",
            "billable_weight_kg_total": "Billable weight (KG total)",
            "other_cost_php_total": "Adjustments (PHP total)",
            "transport_mode": "Transport mode (optional)",
            "manual_price_php_per_unit": "Adjusted price (PHP/unit, optional)",
            "lines": "Lines",
            "suggested_price": "Suggested price",
            "manual_price": "Adjusted price",
            "price_diff_pct": "Diff (%)",
        }
    }

    T = TEXT.get(lang, TEXT["ko"])

    return render(request, "pricing/quote_batch_detail.html", {
        "batch": batch,
        "lines": display_lines,
        "lang": lang,
        "T": T,
    })


def quote_batch_export_csv(request, batch_id: int):
    return export_quote_batch_csv(batch_id)


@require_POST
def quote_line_delete(request, batch_id: int, line_id: int):
    batch = get_object_or_404(QuoteBatch, id=batch_id)
    line = get_object_or_404(QuoteLine, id=line_id, batch=batch)
    line.delete()
    return redirect("pricing:quote_batch_detail", batch_id=batch.id)

def quote_batch_list(request):
    batches = QuoteBatch.objects.select_related("fx_period").order_by("-id")
    return render(request, "pricing/quote_batch_list.html", {"batches": batches})