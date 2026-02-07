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


def _ensure_balance_locked(product_id: int) -> InventoryBalance:
    """
    InventoryBalance를 '락 걸고' 가져온다.
    - 존재하면: select_for_update()로 row lock
    - 없으면: 생성 후 다시 select_for_update()로 가져옴
    """
    try:
        return InventoryBalance.objects.select_for_update().get(product_id=product_id)
    except InventoryBalance.DoesNotExist:
        InventoryBalance.objects.create(
            product_id=product_id,
            on_hand_qty_units=Decimal("0"),
            avg_cost_php_per_unit=Decimal("0"),
            last_updated_at=timezone.now(),
        )
        return InventoryBalance.objects.select_for_update().get(product_id=product_id)


@transaction.atomic
def issue_invoice(invoice_id: int) -> SalesInvoice:
    # invoice row lock
    invoice = SalesInvoice.objects.select_for_update().get(id=invoice_id)

    # 이미 발행/취소된 경우는 그대로 반환 (idempotent)
    if invoice.status != SalesInvoice.DRAFT:
        return invoice

    # ✅ 방어막: status는 DRAFT인데, 과거에 OUT이 이미 생긴 경우 (데이터 꼬임/중복 클릭 흔적)
    already_out = StockMovement.objects.filter(
        movement_type=StockMovement.OUT,
        ref_table="sales_salesinvoice",
        ref_id=invoice.id,
    ).exists()
    if already_out:
        raise ValueError(
            f"Invoice {invoice.invoice_no} already has OUT stock movements. "
            f"ISSUE is blocked to prevent double deduction."
        )

    # 라인 lock
    lines = list(invoice.lines.select_related("product").select_for_update())

    if not lines:
        raise ValueError("Invoice has no lines.")

    # 1) 가격 확정(락) — final_unit_price_php가 없으면 ISSUE 불가
    for ln in lines:
        if ln.suggested_unit_price_php is None:
            ln.suggested_unit_price_php = _suggested_price_from_quote(invoice, ln.product_id)

        if ln.manual_unit_price_php is not None:
            ln.final_unit_price_php = ln.manual_unit_price_php
        else:
            ln.final_unit_price_php = ln.suggested_unit_price_php

        if ln.final_unit_price_php is None:
            raise ValueError(
                f"Missing final unit price for {ln.product.sku_code}. "
                f"Set Adjusted(manual) price or ensure QuoteBatch has QuoteLine for this product."
            )

        ln.save(update_fields=["suggested_unit_price_php", "final_unit_price_php"])

    # 2) 재고 차감(OUT) — balance도 row lock
    for ln in lines:
        if not ln.qty_units or ln.qty_units <= 0:
            continue

        bal = _ensure_balance_locked(ln.product_id)

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

    # 3) invoice 상태 변경 (같은 트랜잭션 안에서)
    invoice.status = SalesInvoice.ISSUED
    invoice.save(update_fields=["status"])
    return invoice

def cancel_invoice(invoice: SalesInvoice):
    """
    Cancel an ISSUED sales invoice and restore inventory.

    Rules:
    - Only ISSUED invoices can be cancelled
    - Inventory is restored via IN StockMovement
    - Original OUT movements are NEVER deleted
    - Duplicate cancel is blocked
    """

    if invoice.status != SalesInvoice.ISSUED:
        raise ValueError("Only ISSUED invoices can be cancelled.")

    with transaction.atomic():
        # 1. Invoice 상태 변경
        invoice.status = SalesInvoice.CANCELLED
        invoice.save(update_fields=["status"])

        # 2. 재고 원복 (IN movement 생성)
        for line in invoice.lines.all():
            StockMovement.objects.create(
                movement_type=StockMovement.IN,
                product=line.product,
                qty_units=line.qty_units,
                ref_table="sales_salesinvoice",
                ref_id=invoice.id,
                memo=f"Invoice {invoice.invoice_no} cancelled – stock restored",
                created_at=timezone.now(),
            )

# sales/services/invoicing.py (맨 아래에 추가)

@transaction.atomic
def cancel_invoice(invoice_id: int) -> SalesInvoice:
    """
    CANCEL an ISSUED invoice and restore inventory via IN StockMovement.
    - Only ISSUED can be cancelled
    - Duplicate cancel is blocked
    - Original OUT movements are NEVER deleted
    """
    invoice = SalesInvoice.objects.select_for_update().get(id=invoice_id)

    if invoice.status != SalesInvoice.ISSUED:
        raise ValueError("Only ISSUED invoices can be cancelled.")

    # ✅ 방어막: 이미 cancel용 IN movement가 있으면 중복 복구 방지
    already_restored = StockMovement.objects.filter(
        movement_type=StockMovement.IN,
        ref_table="sales_salesinvoice",
        ref_id=invoice.id,
    ).exists()
    if already_restored:
        raise ValueError(
            f"Invoice {invoice.invoice_no} already has IN stock movements (restored). "
            f"Cancel is blocked to prevent double restore."
        )

    lines = list(invoice.lines.select_related("product").select_for_update())
    if not lines:
        raise ValueError("Invoice has no lines.")

    # 1) 재고 원복 (balance row lock + qty add)
    for ln in lines:
        if not ln.qty_units or ln.qty_units <= 0:
            continue

        bal = _ensure_balance_locked(ln.product_id)
        bal.on_hand_qty_units = bal.on_hand_qty_units + ln.qty_units
        bal.last_updated_at = timezone.now()
        bal.save(update_fields=["on_hand_qty_units", "last_updated_at"])

        StockMovement.objects.create(
            product_id=ln.product_id,
            movement_type=StockMovement.IN,
            qty_units=ln.qty_units,
            ref_table="sales_salesinvoice",
            ref_id=invoice.id,
            memo=f"Invoice {invoice.invoice_no} cancelled – stock restored",
        )

    # 2) invoice 상태 변경
    invoice.status = SalesInvoice.CANCELLED
    invoice.save(update_fields=["status"])
    return invoice
