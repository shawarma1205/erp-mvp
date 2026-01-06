from decimal import Decimal
from django.db import transaction
from django.utils import timezone

from inventory.models import InventoryBalance, Product, InventoryLot


def ceil_to_nearest(value: Decimal, unit: Decimal) -> Decimal:
    """
    올림 보조 함수 (참고용).
    지금은 평균원가에는 필요 없고, 나중에 견적 라운딩에서 쓸 예정.
    """
    if unit <= 0:
        return value
    q = (value / unit).to_integral_value(rounding="ROUND_CEILING")
    return q * unit


@transaction.atomic
def apply_receiving_to_balance(*, product: Product, in_qty: Decimal, in_unit_cost_php: Decimal) -> InventoryBalance:
    """
    입고가 발생했을 때 InventoryBalance(수량/평균원가)를 갱신한다.
    평균원가 공식:
      new_avg = (old_qty*old_avg + in_qty*in_cost) / (old_qty + in_qty)
    """
    balance, _ = InventoryBalance.objects.select_for_update().get_or_create(product=product)

    old_qty = balance.on_hand_qty_units
    old_avg = balance.avg_cost_php_per_unit

    new_qty = old_qty + in_qty
    if new_qty == 0:
        balance.on_hand_qty_units = Decimal("0")
        balance.avg_cost_php_per_unit = Decimal("0")
    else:
        new_avg = (old_qty * old_avg + in_qty * in_unit_cost_php) / new_qty
        balance.on_hand_qty_units = new_qty
        balance.avg_cost_php_per_unit = new_avg

    balance.last_updated_at = timezone.now()
    balance.save()
    return balance


@transaction.atomic
def create_inventory_lot(
    *,
    product: Product,
    supplier_id: int,
    received_date,
    qty_units_received: Decimal,
    fx_rate_snapshot: Decimal,
    supplier_cost_krw_per_unit: Decimal,
    supplier_markup_rate_snapshot: Decimal,
    transport_mode: str,
    transport_krw_per_kg_snapshot: Decimal,
    billable_weight_kg_total: Decimal,
    other_cost_php_total: Decimal = Decimal("0"),
    memo: str = "",
) -> InventoryLot:
    """
    입고 로트를 생성하고, 평균원가/재고를 갱신한다.
    - 여기서 landed_cost(입고 총원가)를 확정해 스냅샷으로 저장한다.
    """

    # 1) supplier pay KRW per unit = supplier_cost * (1 + markup)
    supplier_pay_krw_per_unit = supplier_cost_krw_per_unit * (Decimal("1") + supplier_markup_rate_snapshot)

    # 2) supplier pay PHP per unit
    supplier_pay_php_per_unit = supplier_pay_krw_per_unit * fx_rate_snapshot

    # 3) transport cost PHP total = (billable_weight * krw_per_kg) * fx
    transport_cost_php_total = (billable_weight_kg_total * transport_krw_per_kg_snapshot) * fx_rate_snapshot

    # 4) landed cost PHP total
    supplier_total_php = supplier_pay_php_per_unit * qty_units_received
    landed_cost_php_total = supplier_total_php + transport_cost_php_total + other_cost_php_total

    # 5) unit landed cost
    if qty_units_received == 0:
        raise ValueError("qty_units_received must be > 0")

    landed_cost_php_per_unit = landed_cost_php_total / qty_units_received

    lot = InventoryLot.objects.create(
        product=product,
        supplier_id=supplier_id,
        received_date=received_date,
        qty_units_received=qty_units_received,
        qty_units_remaining=qty_units_received,

        fx_rate_snapshot=fx_rate_snapshot,
        supplier_cost_krw_per_unit=supplier_cost_krw_per_unit,
        supplier_markup_rate_snapshot=supplier_markup_rate_snapshot,

        transport_mode=transport_mode,
        transport_krw_per_kg_snapshot=transport_krw_per_kg_snapshot,
        billable_weight_kg_total=billable_weight_kg_total,

        other_cost_php_total=other_cost_php_total,

        transport_cost_php_total_snapshot=transport_cost_php_total,
        landed_cost_php_total=landed_cost_php_total,
        landed_cost_php_per_unit=landed_cost_php_per_unit,

        memo=memo,
    )

    # 평균원가 반영
    apply_receiving_to_balance(product=product, in_qty=qty_units_received, in_unit_cost_php=landed_cost_php_per_unit)

    return lot
