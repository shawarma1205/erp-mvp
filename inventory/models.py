from django.db import models
from django.utils import timezone


class Product(models.Model):
    sku_code = models.CharField(max_length=50, unique=True)  # 품목번호
    name_en = models.CharField(max_length=120)
    name_ko = models.CharField(max_length=120, blank=True)

    base_unit = models.CharField(max_length=30)  # pack, kg, 500g 등 (문자열로 시작)
    net_weight_kg_per_unit = models.DecimalField(max_digits=10, decimal_places=2)  # 내용물 기준 kg
    origin_country = models.CharField(
        max_length=2,
        null=True,
        blank=True,
        help_text="Country of origin (ISO code, e.g. KR, NO, CL)",
    )

    origin_name = models.CharField(
        max_length=50,
        null=True,
        blank=True,
        help_text="Origin name (e.g. Korea, Norway, Chile)",
    )

    packaging_note = models.CharField(max_length=200, blank=True)
    memo = models.TextField(blank=True)

    is_active = models.BooleanField(default=True)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["sku_code"]

    def __str__(self) -> str:
        return f"{self.sku_code} - {self.name_ko or self.name_en}"

class InventoryBalance(models.Model):
    """
    품목별 현재 재고 상태(캐시).
    - on_hand_qty_units: 현재 수량
    - avg_cost_php_per_unit: 현재 평균원가(PHP/단위)
    """
    product = models.OneToOneField("inventory.Product", on_delete=models.CASCADE, related_name="balance")

    on_hand_qty_units = models.DecimalField(max_digits=14, decimal_places=4, default=0)
    avg_cost_php_per_unit = models.DecimalField(max_digits=14, decimal_places=4, default=0)

    last_updated_at = models.DateTimeField(default=timezone.now)

    def inventory_value_php(self):
        return self.on_hand_qty_units * self.avg_cost_php_per_unit

    def __str__(self) -> str:
        return f"Balance({self.product.sku_code}) qty={self.on_hand_qty_units} avg={self.avg_cost_php_per_unit}"

from .receiving_models import InventoryLot  # noqa: F401

# inventory/models.py

from django.db import models
from django.utils import timezone

class StockMovement(models.Model):
    IN = "IN"
    OUT = "OUT"
    ADJ = "ADJ"
    MOVE_TYPES = [
        (IN, "IN"),
        (OUT, "OUT"),
        (ADJ, "ADJ"),
    ]

    product = models.ForeignKey("inventory.Product", on_delete=models.PROTECT)
    movement_type = models.CharField(max_length=3, choices=MOVE_TYPES)
    qty_units = models.DecimalField(max_digits=12, decimal_places=4)
    ref_table = models.CharField(max_length=50, blank=True, default="")
    ref_id = models.PositiveIntegerField(null=True, blank=True)
    memo = models.CharField(max_length=200, blank=True, default="")
    created_at = models.DateTimeField(default=timezone.now)

    class Meta:
        ordering = ["-created_at"]
