from django.db import models


class QuoteBatch(models.Model):
    name = models.CharField(max_length=120)

    fx_period = models.ForeignKey("fx.FXRatePeriod", on_delete=models.PROTECT)

    company_margin_rate = models.DecimalField(max_digits=6, decimal_places=4, default=0.2000)
    supplier_markup_rate = models.DecimalField(max_digits=6, decimal_places=4, default=0.0500)

    rounding_unit_php = models.DecimalField(max_digits=10, decimal_places=2, default=10)

    class TransportMode(models.TextChoices):
        OCEAN = "OCEAN", "Ocean"
        AIR = "AIR", "Air"

    transport_mode = models.CharField(max_length=10, choices=TransportMode.choices, default=TransportMode.OCEAN)
    transport_krw_per_kg = models.DecimalField(max_digits=14, decimal_places=2)

    memo = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)


class QuoteLine(models.Model):
    batch = models.ForeignKey("pricing.QuoteBatch", on_delete=models.CASCADE, related_name="lines")
    product = models.ForeignKey("inventory.Product", on_delete=models.PROTECT)

    qty_units = models.DecimalField(max_digits=14, decimal_places=4, default=1)
    supplier_cost_krw_per_unit = models.DecimalField(max_digits=14, decimal_places=2)
    billable_weight_kg_total = models.DecimalField(max_digits=14, decimal_places=4)
    other_cost_php_total = models.DecimalField(max_digits=14, decimal_places=2, default=0)

    fx_rate_snapshot = models.DecimalField(max_digits=12, decimal_places=6, null=True, blank=True)

    supplier_pay_php_per_unit = models.DecimalField(max_digits=14, decimal_places=4, null=True, blank=True)
    transport_php_total = models.DecimalField(max_digits=14, decimal_places=2, null=True, blank=True)
    transport_php_per_unit = models.DecimalField(max_digits=14, decimal_places=4, null=True, blank=True)

    base_price_php_per_unit = models.DecimalField(max_digits=14, decimal_places=4, null=True, blank=True)
    manual_price_php_per_unit = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="Optional manual override price per unit (PHP). If set, this becomes final price.",
    )

    final_price_php_per_unit = models.DecimalField(max_digits=14, decimal_places=4, null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    def save(self, *args, **kwargs):
        """
        Admin에서 저장될 때 자동으로 견적 계산.
        """
        from pricing.services.quoting import create_quote_line

        # 이미 계산된 경우(중복 계산 방지)
        if self.final_price_php_per_unit:
            super().save(*args, **kwargs)
            return

        line = create_quote_line(
            batch=self.batch,
            product=self.product,
            qty_units=self.qty_units,
            supplier_cost_krw_per_unit=self.supplier_cost_krw_per_unit,
            billable_weight_kg_total=self.billable_weight_kg_total,
            other_cost_php_total=self.other_cost_php_total,
        )

        # 같은 레코드를 다시 저장하지 않도록 pk 복사
        self.id = line.id
    def save(self, *args, **kwargs):
        # 계산 결과 필드가 비어있다면 자동 계산
        if self.final_price_php_per_unit is None:
            from pricing.services.quoting import compute_quote_line
            compute_quote_line(self)
        super().save(*args, **kwargs)