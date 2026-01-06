from decimal import Decimal
from datetime import date

from inventory.services.costing import create_inventory_lot
from inventory.models import Product, InventoryBalance
from partners.models import Partner
from fx.models import FXRatePeriod

fx = FXRatePeriod.objects.get(start_date=date(2026, 1, 1), end_date=None)
supplier = Partner.objects.get(partner_type="SUPPLIER", name="Sample Supplier")
product = Product.objects.get(sku_code="SALMON-001")

# 입고 전 balance 출력
balance_before = InventoryBalance.objects.get(product=product)
print("BEFORE qty:", balance_before.on_hand_qty_units, "avg:", balance_before.avg_cost_php_per_unit)

# 2번째 입고: 단가가 더 비싸다고 가정
lot2 = create_inventory_lot(
    product=product,
    supplier_id=supplier.id,
    received_date=date(2026, 1, 6),

    qty_units_received=Decimal("10"),

    fx_rate_snapshot=fx.krw_to_php,

    supplier_cost_krw_per_unit=Decimal("14000"),  # 더 비싼 원가
    supplier_markup_rate_snapshot=Decimal("0.05"),

    transport_mode="AIR",
    transport_krw_per_kg_snapshot=Decimal("14000"),

    billable_weight_kg_total=Decimal("12.0"),

    other_cost_php_total=Decimal("0"),
    memo="TEST RECEIVING 2",
)

print("Created lot2:", lot2)

# 입고 후 balance 출력
balance_after = InventoryBalance.objects.get(product=product)
print("AFTER qty:", balance_after.on_hand_qty_units, "avg:", balance_after.avg_cost_php_per_unit)
