# inventory/signals.py

from decimal import Decimal
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.utils import timezone

from inventory.models import InventoryLot, InventoryBalance, StockMovement


@receiver(post_save, sender=InventoryLot)
def create_inbound_movement(sender, instance: InventoryLot, created, **kwargs):
    """
    InventoryLot이 처음 생성될 때:
    - StockMovement(IN) 생성
    - InventoryBalance 증가
    """
    if not created:
        return  # 수정 시에는 아무것도 안 함

    qty = instance.qty_units_received
    if not qty or qty <= 0:
        return

    # 1) Balance 확보
    balance, _ = InventoryBalance.objects.get_or_create(
        product=instance.product,
        defaults={"on_hand_qty_units": Decimal("0")},
    )

    # 2) 재고 증가
    balance.on_hand_qty_units += qty
    balance.last_updated_at = timezone.now()
    balance.save(update_fields=["on_hand_qty_units", "last_updated_at"])

    # 3) IN movement 기록
    StockMovement.objects.create(
        product=instance.product,
        movement_type=StockMovement.IN,
        qty_units=qty,
        ref_table="inventory_inventorylot",
        ref_id=instance.id,
        memo=f"Received from {instance.supplier}",
    )
