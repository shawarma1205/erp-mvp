# sales/services/invoicing.py

from decimal import Decimal
from django.db import transaction
from django.utils import timezone

from sales.models import SalesInvoice
from inventory.models import InventoryBalance, StockMovement

def _suggested_price_from_quote(invoice: SalesInvoice, product_id: int):
    """
    invoice.quote_batch가 지정되어 있고,
    해당 배치에 product에 대한 QuoteLine이 있으면
    최신 QuoteLine의 final_price_php_per_unit을 suggested로 사용.
    """
    if not invoice.quote_batch_id:
        return None

    from pricing.models import QuoteLine  # 지연 import (순환 방지)

    ql = (
        QuoteLine.objects
        .filter(batch_id=invoice.quote_batch_id, product_id=product_id)
        .order_by("-created_at")
        .first()
    )
    if not ql:
        return None
    return ql.final_price_php_per_unit


def _ensure_balance(product_id: int) -> InventoryBalance:
    bal, _ = InventoryBalance.objects.get_or_create(product_id=product_id, defaults={"on_hand_qty_units": Decimal("0")})
    return bal


@transaction.atomic
def issue_invoice(invoice_id: int) -> SalesInvoice:
    invoice = SalesInvoice.objects.select_for_update().get(id=invoice_id)

    if invoice.status != SalesInvoice.DRAFT:
        return invoice  # 이미 발행/취소된 경우는 그대로 반환

    # 1) 라인별로 suggested/final 확정 + 재고 차감
    lines = list(invoice.lines.select_related("product").select_for_update())

    # (안전) 라인 없으면 발행 막기
    if not lines:
        raise ValueError("Invoice has no lines.")

    # 1-A) 먼저 가격 확정
    for ln in lines:
        if ln.suggested_unit_price_php is None:
            ln.suggested_unit_price_php = _suggested_price_from_quote(invoice, ln.product_id)

        # manual이 있으면 manual이 final, 없으면 suggested가 final
        if ln.manual_unit_price_php is not None:
            ln.final_unit_price_php = ln.manual_unit_price_php
        else:
            ln.final_unit_price_php = ln.suggested_unit_price_php

        ln.save(update_fields=["suggested_unit_price_php", "final_unit_price_php"])

    # 1-B) 재고 차감 (OUT)
    for ln in lines:
        if not ln.qty_units or ln.qty_units <= 0:
            continue

        bal = _ensure_balance(ln.product_id)

        # 재고 부족 방지 (원하면 나중에 '마이너스 허용' 옵션 추가 가능)
        if bal.on_hand_qty_units < ln.qty_units:
            raise ValueError(
                f"Insufficient stock for {ln.product.sku_code}. "
                f"On hand={bal.on_hand_qty_units}, required={ln.qty_units}"
            )

        bal.on_hand_qty_units = bal.on_hand_qty_units - ln.qty_units
        bal.last_updated_at = timezone.now()
        bal.save(update_fields=["on_hand_qty_units", "last_updated_at"])

        StockMovement.objects.create(
            product_id=ln.product_id,
            movement_type=StockMovement.OUT,
            qty_units=ln.qty_units,
            ref_table="sales_salesinvoice",
            ref_id=invoice.id,
            memo=f"Invoice {invoice.invoice_no} issued",
        )

    # 2) invoice 상태 변경
    invoice.status = SalesInvoice.ISSUED
    invoice.save(update_fields=["status"])
    return invoice
