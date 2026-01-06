from decimal import Decimal
from datetime import date

from fx.models import FXRatePeriod
from inventory.models import Product
from pricing.models import QuoteBatch
from pricing.services.quoting import create_quote_line

# 1) FX 기간(기존에 만들어둔 FXRatePeriod를 사용)
fx = FXRatePeriod.objects.get(start_date=date(2026, 1, 1), end_date=None)

# 2) 테스트 상품(기존에 만들어둔 Product 사용)
product = Product.objects.get(sku_code="SALMON-001")

# 3) 견적 배치(이번 견적 설정 묶음 1개 생성)
batch = QuoteBatch.objects.create(
    name="W01 Quote",
    fx_period=fx,
    company_margin_rate=Decimal("0.20"),
    supplier_markup_rate=Decimal("0.05"),
    rounding_unit_php=Decimal("10"),
    transport_mode="OCEAN",
    transport_krw_per_kg=Decimal("2200"),
    memo="TEST BATCH",
)

# 4) 품목 1줄 견적 계산 + 저장
line = create_quote_line(
    batch=batch,
    product=product,
    qty_units=Decimal("10"),
    supplier_cost_krw_per_unit=Decimal("14000"),
    billable_weight_kg_total=Decimal("12.0"),
    other_cost_php_total=Decimal("0"),
)

print("Quote final PHP/unit:", line.final_price_php_per_unit)
print("Base PHP/unit:", line.base_price_php_per_unit)
print("Transport PHP/unit:", line.transport_php_per_unit)
