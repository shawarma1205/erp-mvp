# sales/models.py

from decimal import Decimal
from django.db import models
from django.utils import timezone

class SalesInvoice(models.Model):
    DRAFT = "DRAFT"
    ISSUED = "ISSUED"
    CANCELLED = "CANCELLED"
    STATUS_CHOICES = [
        (DRAFT, "DRAFT"),
        (ISSUED, "ISSUED"),
        (CANCELLED, "CANCELLED"),
    ]

    invoice_no = models.CharField(max_length=30, unique=True)
    customer = models.ForeignKey("partners.Partner", on_delete=models.PROTECT, related_name="sales_invoices")
    issue_date = models.DateField(default=timezone.now)
    status = models.CharField(max_length=12, choices=STATUS_CHOICES, default=DRAFT)

    # 어떤 견적 배치(QuoteBatch) 기준으로 자동 제안가를 뽑을지 연결
    quote_batch = models.ForeignKey(
        "pricing.QuoteBatch",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="sales_invoices",
        help_text="자동 제안가를 뽑을 견적 배치(선택).",
    )

    memo = models.TextField(blank=True, default="")
    created_at = models.DateTimeField(default=timezone.now)

    def __str__(self) -> str:
        return f"{self.invoice_no} ({self.customer})"

    @property
    def total_php(self) -> Decimal:
        total = Decimal("0")
        for ln in self.lines.all():
            total += ln.line_total_php
        return total


class SalesInvoiceLine(models.Model):
    invoice = models.ForeignKey(SalesInvoice, on_delete=models.CASCADE, related_name="lines")
    product = models.ForeignKey("inventory.Product", on_delete=models.PROTECT)
    qty_units = models.DecimalField(max_digits=12, decimal_places=4)

    # suggested / manual / final 구조
    suggested_unit_price_php = models.DecimalField(max_digits=12, decimal_places=4, null=True, blank=True)
    manual_unit_price_php = models.DecimalField(max_digits=12, decimal_places=4, null=True, blank=True)
    final_unit_price_php = models.DecimalField(max_digits=12, decimal_places=4, null=True, blank=True)

    created_at = models.DateTimeField(default=timezone.now)

    @property
    def line_total_php(self) -> Decimal:
        if not self.final_unit_price_php:
            return Decimal("0")
        return (self.final_unit_price_php * self.qty_units)

    def __str__(self) -> str:
        return f"{self.invoice.invoice_no} - {self.product.sku_code}"

