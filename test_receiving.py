from decimal import Decimal
from datetime import date

from inventory.services.costing import create_inventory_lot
from inventory.models import Product
from partners.models import Partner
from fx.models import FXRatePeriod


# 1) FXRatePeriod: 없으면 생성
fx, _ = FXRatePeriod.objects.get_or_create(
    start_date=date(2026, 1, 1),
    end_date=None,
    defaults={
        "krw_to_php": Decimal("0.045000"),
        "memo": "AUTO CREATED FX",
        "is_locked": False,
    },
)

# 2) Supplier Partner: 없으면 생성
supplier, _ = Partner.objects.get_or_create(
    partner_type="SUPPLIER",
    name="Sample Supplier",
    defaults={
        "name_ko": "샘플공급사",
        "is_active": True,
    },
)

# 3) Product: 없으면 생성
product, _ = Product.objects.get_or_create(
    sku_code="SALMON-001",
    defaults={
        "name_en": "Salmon Fillet",
        "name_ko": "연어 필렛",
        "base_unit": "pack",
        "net_weight_kg_per_unit": Decimal("1.0000"),
        "is_active": True,
    },
)

# 4) 입고 1건 생성
lot = create_inventory_lot(
    product=product,
    supplier_id=supplier.id,
    received_date=date(2026, 1, 5),

    qty_units_received=Decimal("10"),

    fx_rate_snapshot=fx.krw_to_php,

    supplier_cost_krw_per_unit=Decimal("10000"),
    supplier_markup_rate_snapshot=Decimal("0.05"),

    transport_mode="OCEAN",
    transport_krw_per_kg_snapshot=Decimal("2200"),

    billable_weight_kg_total=Decimal("12.0"),

    other_cost_php_total=Decimal("0"),
    memo="TEST RECEIVING",
)

print("Created lot:", lot)
