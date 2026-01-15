# pricing/models.py

from django.db import models


class QuoteBatch(models.Model):
    name = models.CharField(max_length=120)

    fx_period = models.ForeignKey("fx.FXRatePeriod", on_delete=models.PROTECT)

    company_margin_rate = models.DecimalField(max_digits=6, decimal_places=4, default=0.2000)
    supplier_markup_rate = models.DecimalField(max_digits=6, decimal_places=4, default=0.0500)

    rounding_unit_php = models.DecimalField(max_digits=10, decimal_places=2, default=10)

    # ✅ 운송비를 모드별로 2개 보관 (Batch를 AIR/SEA로 쪼개지 않음)
    ocean_krw_per_kg = models.DecimalField(max_digits=14, decimal_places=2, default=2200)
    air_krw_per_kg = models.DecimalField(max_digits=14, decimal_places=2, default=14000)

    memo = models.TextField(blank=True, default="")
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self) -> str:
        return self.name


class QuoteLine(models.Model):
    class TransportMode(models.TextChoices):
        OCEAN = "OCEAN", "Ocean"
        AIR = "AIR", "Air"

    batch = models.ForeignKey("pricing.QuoteBatch", on_delete=models.CASCADE, related_name="lines")
    product = models.ForeignKey("inventory.Product", on_delete=models.PROTECT)

    # ✅ 라인에서 override 가능 (없으면 Product.default_transport_mode 사용)
    transport_mode = models.CharField(
        max_length=10,
        choices=TransportMode.choices,
        null=True,
        blank=True,
        help_text="Optional override. If blank, uses product default transport mode.",
    )

    qty_units = models.DecimalField(max_digits=14, decimal_places=4, default=1)
    supplier_cost_krw_per_unit = models.DecimalField(max_digits=14, decimal_places=2)
    billable_weight_kg_total = models.DecimalField(max_digits=14, decimal_places=4)
    other_cost_php_total = models.DecimalField(max_digits=14, decimal_places=2, default=0)

    # snapshot
    fx_rate_snapshot = models.DecimalField(max_digits=12, decimal_places=6, null=True, blank=True)

    # computed fields
    supplier_pay_php_per_unit = models.DecimalField(max_digits=14, decimal_places=4, null=True, blank=True)
    transport_php_total = models.DecimalField(max_digits=14, decimal_places=2, null=True, blank=True)
    transport_php_per_unit = models.DecimalField(max_digits=14, decimal_places=4, null=True, blank=True)

    base_price_php_per_unit = models.DecimalField(max_digits=14, decimal_places=4, null=True, blank=True)

    manual_price_php_per_unit = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="Adjusted price per unit (PHP). If set, this becomes final price.",
    )

    final_price_php_per_unit = models.DecimalField(max_digits=14, decimal_places=4, null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)

    def save(self, *args, **kwargs):
        # 계산 결과가 비어있다면 자동 계산
        if self.final_price_php_per_unit is None:
            from pricing.services.quoting import compute_quote_line
            compute_quote_line(self)
        super().save(*args, **kwargs)

    def __str__(self) -> str:
        return f"{self.batch.name} - {self.product.sku_code}"
