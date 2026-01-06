import csv
from decimal import Decimal
from django.http import HttpResponse

from pricing.models import QuoteBatch, QuoteLine


def _d(v):
    # Decimal/None 안전 처리
    if v is None:
        return ""
    if isinstance(v, Decimal):
        return str(v)
    return v


def export_quote_batch_csv(batch_id: int) -> HttpResponse:
    batch = QuoteBatch.objects.get(id=batch_id)

    lines = (
        QuoteLine.objects
        .filter(batch=batch)
        .select_related("product")
        .order_by("id")
    )

    filename = f"quote_batch_{batch.id}_{batch.name}.csv".replace(" ", "_")

    response = HttpResponse(content_type="text/csv; charset=utf-8")
    response["Content-Disposition"] = f'attachment; filename="{filename}"'

    # 엑셀 한글 깨짐 방지용 BOM
    response.write("\ufeff")

    writer = csv.writer(response)

    # 헤더(필요하면 나중에 더 추가)
    writer.writerow([
        "BatchName",
        "ProductSKU",
        "ProductName",
        "QtyUnits",
        "SupplierCostKRWPerUnit",
        "BillableWeightKgTotal",
        "FXRateSnapshot",
        "SupplierPayPHPPerUnit",
        "TransportPHPTotal",
        "TransportPHPPerUnit",
        "BasePricePHPPerUnit",
        "FinalPricePHPPerUnit",
        "CreatedAt",
    ])

    for ln in lines:
        writer.writerow([
            batch.name,
            ln.product.sku_code,
            getattr(ln.product, "name_ko", "") or getattr(ln.product, "name_en", ""),
            _d(ln.qty_units),
            _d(ln.supplier_cost_krw_per_unit),
            _d(ln.billable_weight_kg_total),
            _d(ln.fx_rate_snapshot),
            _d(ln.supplier_pay_php_per_unit),
            _d(ln.transport_php_total),
            _d(ln.transport_php_per_unit),
            _d(ln.base_price_php_per_unit),
            _d(ln.final_price_php_per_unit),
            ln.created_at.isoformat() if ln.created_at else "",
        ])

    return response
