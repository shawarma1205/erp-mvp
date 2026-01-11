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

        manual_raw = request.POST.get("manual_price_php_per_unit", "").strip()
        manual_price = Decimal(manual_raw) if manual_raw else None

        product = get_object_or_404(Product, sku_code=sku)

        line = QuoteLine(
            batch=batch,
            product=product,
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
        .order_by("-created_at")
    )
    display_lines = []
    for ln in lines:
        suggested = ln.base_price_php_per_unit  # suggested 기준: base price
        manual = ln.manual_price_php_per_unit

        diff_pct = None
        if manual is not None and suggested not in (None, 0):
            diff_pct = (manual - suggested) / suggested * Decimal("100")

        display_lines.append({
            "obj": ln,  # 원래 QuoteLine 객체
            "suggested_price": suggested,
            "diff_pct": diff_pct,
        })

    lang = request.GET.get("lang","ko")
    TEXT = {
        "ko": {
            "company_margin_rate": "회사 마진율 (예: 0.20)",
            "supplier_markup_rate": "공급사 마크업율 (예: 0.05)",
            "transport_mode": "운송 방식",
            "transport_krw_per_kg": "운송비 (KRW/kg)",
            "rounding_unit_php": "라운딩 단위 (PHP)",

            "sku_code": "SKU 코드",
            "qty_units": "수량 (단위 기준)",
            "supplier_cost_krw_per_unit": "공급가 (KRW/단위)",
            "billable_weight_kg_total": "청구중량 (KG, 총합)",
            "other_cost_php_total": "기타비용 (PHP, 총합)",

            "language": "언어",
            "download_csv": "CSV 다운로드",
            "batch_settings": "배치 설정",
            "update_batch": "배치 업데이트",
            "add_quote_line": "견적 라인 추가",
            "create": "생성",
            "lines": "라인 목록",
            "delete": "삭제",
            "no_lines": "아직 라인이 없습니다.",
            "created": "생성일",
            "sku": "SKU",
            "name": "품목명",
            "qty": "수량",
            "supplier_cost": "공급가 (KRW/단위)",
            "weight": "청구중량 (KG)",
            "base_price": "기준가 (PHP/단위)",
            "final_price": "최종가 (PHP/단위)",
            "action": "작업",
            "fx_period": "환율 기간",
            "fx_rate": "환율 (KRW→PHP)",
            "margin": "회사 마진",
            "supplier_markup": "공급사 마크업",
            "transport": "운송",
            "round": "라운딩",

            "suggested_price": "권장가(자동)",
            "manual_price": "수동가",
            "manual_price_php_per_unit": "수동 판매가 (PHP/단위, 선택)",
            "price_diff_pct": "자동가 대비 차이(%)",

        },
        "en": {
            "company_margin_rate": "Company margin rate (e.g. 0.20)",
            "supplier_markup_rate": "Supplier markup rate (e.g. 0.05)",
            "transport_mode": "Transport mode",
            "transport_krw_per_kg": "Transport (KRW/kg)",
            "rounding_unit_php": "Rounding unit (PHP)",

            "sku_code": "SKU Code",
            "qty_units": "Qty Units",
            "supplier_cost_krw_per_unit": "Supplier Cost (KRW per unit)",
            "billable_weight_kg_total": "Billable Weight (KG total)",
            "other_cost_php_total": "Other Cost (PHP total)",

            "language": "Language",
            "download_csv": "Download CSV",
            "batch_settings": "Batch Settings",
            "update_batch": "Update Batch",
            "add_quote_line": "Add Quote Line",
            "create": "Create",
            "lines": "Lines",
            "delete": "Delete",
            "no_lines": "No lines yet.",
            "created": "Created",
            "sku": "SKU",
            "name": "Name",
            "qty": "Qty",
            "supplier_cost": "Supplier Cost (KRW/unit)",
            "weight": "Billable Weight (KG)",
            "base_price": "Base Price (PHP/unit)",
            "final_price": "Final Price (PHP/unit)",
            "action": "Action",
            "fx_period": "FX Period",
            "fx_rate": "FX (KRW→PHP)",
            "margin": "Margin",
            "supplier_markup": "Supplier markup",
            "transport": "Transport",
            "round": "Round",

            "suggested_price": "Suggested (auto)",
            "manual_price": "Manual",
            "manual_price_php_per_unit": "Manual price (PHP/unit, optional)",
            "price_diff_pct": "Diff vs suggested (%)",

        },
    }

    T = TEXT.get(lang, TEXT["ko"])

    context = {
        "batch": batch,
        "lines": display_lines,
        "lang": lang,
        "T": T,
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
