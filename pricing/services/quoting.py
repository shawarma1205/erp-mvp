from decimal import Decimal, ROUND_CEILING

from pricing.models import QuoteLine


def ceil_to_nearest(value: Decimal, unit: Decimal) -> Decimal:
    if unit <= 0:
        return value
    q = (value / unit).to_integral_value(rounding=ROUND_CEILING)
    return q * unit


def compute_quote_line(line: QuoteLine) -> None:
    """
    line에 입력된 값(수량/원가/청구중량/기타비용)을 기반으로
    계산 결과 필드를 채웁니다. (DB 저장은 호출자가 담당)
    """
    if line.qty_units is None or line.qty_units <= 0:
        raise ValueError("qty_units must be > 0")

    batch = line.batch
    fx = batch.fx_period.krw_to_php

    # 1) supplier pay per unit
    supplier_pay_krw_per_unit = line.supplier_cost_krw_per_unit * (Decimal("1") + batch.supplier_markup_rate)
    supplier_pay_php_per_unit = supplier_pay_krw_per_unit * fx

    # 2) transport total + per unit
    transport_krw_total = line.billable_weight_kg_total * batch.transport_krw_per_kg
    transport_php_total = transport_krw_total * fx
    transport_php_per_unit = transport_php_total / line.qty_units

    # 3) other cost per unit
    other_php_per_unit = (line.other_cost_php_total or Decimal("0")) / line.qty_units

    # 4) base + rounding
    base_price_php_per_unit = (
        (supplier_pay_php_per_unit * (Decimal("1") + batch.company_margin_rate))
        + transport_php_per_unit
        + other_php_per_unit
    )
    final_price_php_per_unit = ceil_to_nearest(base_price_php_per_unit, batch.rounding_unit_php)

    # 스냅샷 저장
    line.fx_rate_snapshot = fx
    line.supplier_pay_php_per_unit = supplier_pay_php_per_unit
    line.transport_php_total = transport_php_total
    line.transport_php_per_unit = transport_php_per_unit
    line.base_price_php_per_unit = base_price_php_per_unit
    line.final_price_php_per_unit = final_price_php_per_unit
