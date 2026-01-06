from django.db import models


class InventoryLot(models.Model):
    """
    입고 로트(한 번의 입고 기록).
    평균원가를 계산하려면 '입고 당시 총원가(PHP)'가 확정되어 있어야 한다.
    """

    class TransportMode(models.TextChoices):
        OCEAN = "OCEAN", "Ocean"
        AIR = "AIR", "Air"

    product = models.ForeignKey("inventory.Product", on_delete=models.PROTECT)
    supplier = models.ForeignKey("partners.Partner", on_delete=models.PROTECT)

    received_date = models.DateField()

    qty_units_received = models.DecimalField(max_digits=14, decimal_places=4)
    qty_units_remaining = models.DecimalField(max_digits=14, decimal_places=4)

    # FX snapshot
    fx_rate_snapshot = models.DecimalField(max_digits=12, decimal_places=6)

    # Supplier cost KRW per unit (manual input)
    supplier_cost_krw_per_unit = models.DecimalField(max_digits=14, decimal_places=2)
    supplier_markup_rate_snapshot = models.DecimalField(max_digits=6, decimal_places=4, default=0.0500)

    # Transport snapshots
    transport_mode = models.CharField(max_length=10, choices=TransportMode.choices)
    transport_krw_per_kg_snapshot = models.DecimalField(max_digits=14, decimal_places=2)

    billable_weight_kg_total = models.DecimalField(max_digits=14, decimal_places=4)

    # optional other costs in PHP
    other_cost_php_total = models.DecimalField(max_digits=14, decimal_places=2, default=0)

    # Derived totals (snapshots)
    transport_cost_php_total_snapshot = models.DecimalField(max_digits=14, decimal_places=2)
    landed_cost_php_total = models.DecimalField(max_digits=14, decimal_places=2)
    landed_cost_php_per_unit = models.DecimalField(max_digits=14, decimal_places=4)

    memo = models.TextField(blank=True)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-received_date", "-created_at"]

    def __str__(self) -> str:
        return f"Lot({self.product.sku_code}) {self.received_date} qty={self.qty_units_received} cost={self.landed_cost_php_per_unit}"
