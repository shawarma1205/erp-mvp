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

    class SalesChannel(models.TextChoices):
        DIRECT = "DIRECT", "Direct"
        ONLINE = "ONLINE", "Online"
        AGENT = "AGENT", "Agent"
        OTHER = "OTHER", "Other"

    sales_channel = models.CharField(
        max_length=20,
        choices=SalesChannel.choices,
        default=SalesChannel.DIRECT,
        help_text="판매 출처(채널).", )

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

    def save(self, *args, **kwargs):
        """
        Draft 단계에서 가격 빈칸 방지:
        - suggested가 비어 있으면: invoice.quote_batch 기준으로 QuoteLine 최종가를 가져옴
        - manual(조정가)이 없으면: final = suggested
        - manual(조정가)이 있으면: final = manual
        """
        # 1) suggested 자동 채우기 (invoice에 quote_batch가 연결된 경우만)
        if self.suggested_unit_price_php is None and self.invoice_id and self.invoice.quote_batch_id:
            from pricing.models import QuoteLine

            ql = (
                QuoteLine.objects
                .filter(batch_id=self.invoice.quote_batch_id, product_id=self.product_id)
                .order_by("-created_at")
                .first()
            )
            if ql and ql.final_price_php_per_unit is not None:
                self.suggested_unit_price_php = ql.final_price_php_per_unit

        # 2) final 확정 (단, 재고/매출 잠금은 issue에서만)
        if self.manual_unit_price_php is not None:
            self.final_unit_price_php = self.manual_unit_price_php
        else:
            # suggested가 None이면 final도 None로 둔다(quote 없을 수 있으므로)
            self.final_unit_price_php = self.suggested_unit_price_php

        super().save(*args, **kwargs)


    def __str__(self) -> str:
        return f"{self.invoice.invoice_no} - {self.product.sku_code}"

