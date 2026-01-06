from decimal import Decimal
from datetime import date

from inventory.models import Product, InventoryBalance
from partners.models import Partner
from sales.services.selling import create_sale

product = Product.objects.get(sku_code="SALMON-001")

customer, _ = Partner.objects.get_or_create(
    partner_type="CUSTOMER",
    name="Sample Customer",
    defaults={"name_ko": "샘플고객", "is_active": True},
)

balance_before = InventoryBalance.objects.get(product=product)
print("BEFORE qty:", balance_before.on_hand_qty_units, "avg:", balance_before.avg_cost_php_per_unit)

sale = create_sale(
    customer=customer,
    sale_date=date(2026, 1, 7),
    product=product,
    qty_units=Decimal("5"),
    sell_price_php_per_unit=Decimal("1800"),
    memo="TEST SALE",
)

balance_after = InventoryBalance.objects.get(product=product)
print("AFTER qty:", balance_after.on_hand_qty_units, "avg:", balance_after.avg_cost_php_per_unit)
print("Created sale id:", sale.id)
