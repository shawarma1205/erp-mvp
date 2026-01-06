from decimal import Decimal
from django.db import transaction
from django.utils import timezone

from inventory.models import InventoryBalance, Product
from partners.models import Partner
from sales.models import Sale, SaleLine


@transaction.atomic
def create_sale(
    *,
    customer: Partner,
    sale_date,
    product: Product,
    qty_units: Decimal,
    sell_price_php_per_unit: Decimal,
    memo: str = "",
) -> Sale:
    balance = InventoryBalance.objects.select_for_update().get(product=product)

    if qty_units <= 0:
        raise ValueError("qty_units must be > 0")

    if balance.on_hand_qty_units < qty_units:
        raise ValueError(f"Insufficient inventory: on_hand={balance.on_hand_qty_units}, request={qty_units}")

    cogs_snapshot = balance.avg_cost_php_per_unit

    sale = Sale.objects.create(
        customer=customer,
        sale_date=sale_date,
        memo=memo,
        created_at=timezone.now(),
    )

    SaleLine.objects.create(
        sale=sale,
        product=product,
        qty_units=qty_units,
        sell_price_php_per_unit=sell_price_php_per_unit,
        cogs_php_per_unit_snapshot=cogs_snapshot,
        created_at=timezone.now(),
    )

    balance.on_hand_qty_units = balance.on_hand_qty_units - qty_units
    balance.last_updated_at = timezone.now()
    balance.save()

    return sale
