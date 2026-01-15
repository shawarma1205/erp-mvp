from decimal import Decimal, ROUND_CEILING

from pricing.models import QuoteLine


def ceil_to_nearest(value: Decimal, unit: Decimal) -> Decimal:
    """
    unit 단위로 올림.
    unit=10이면 3621.94 -> 3630
    """
    if unit is None or unit <= 0:
        return value
    q = (value / unit).to_integral_value(rounding=ROUND_CEILING)
    return q * unit


def compute_quote_line(line: QuoteLine) -> None:
    """
    ✅ 의도한 계산식:
    (공급지불액 * (1+마진)) + 운송비 + 조정금액
    그리고 라운딩
    """

    if line.qty_units is None or line.qty_units <= 0:
        raise ValueError("qty_units must be > 0")

    batch = line.batch
    product = line.product

    fx = batch.fx_period.krw_to_php
    fx = Decimal(str(fx))

    # 1) 공급사 지불액 (KRW -> PHP) : 원가에 공급사 마크업 적용 후 환전
    supplier_pay_krw_per_unit = Decimal(str(line.supplier_cost_krw_per_unit)) * (
        Decimal("1") + Decimal(str(batch.supplier_markup_rate))
    )
    supplier_pay_php_per_unit = supplier_pay_krw_per_unit * fx

    # 2) 운송 모드 결정: line.transport_mode가 있으면 그걸 쓰고,
    #    없으면 product.default_transport_mode 사용
    mode = getattr(line, "transport_mode", None)
    if not mode:
        mode = getattr(product, "default_transport_mode", None) or "OCEAN"

    # 3) 운송비 (KRW/kg) 선택
    if mode == "AIR":
        rate_krw_per_kg = Decimal(str(batch.air_krw_per_kg))
    else:
        rate_krw_per_kg = Decimal(str(batch.ocean_krw_per_kg))

    transport_krw_total = rate_krw_per_kg * Decimal(str(line.billable_weight_kg_total))
    transport_php_total = transport_krw_total * fx
    transport_php_per_unit = transport_php_total / Decimal(str(line.qty_units))

    # 4) 조정금액(기타비용) per unit
    other_php_per_unit = (Decimal(str(line.other_cost_php_total or 0))) / Decimal(str(line.qty_units))

    # ✅ 5) 핵심: 마진은 공급지불액에만 적용, 운송/조정금액은 뒤에 더함
    base_price_php_per_unit = (
        supplier_pay_php_per_unit * (Decimal("1") + Decimal(str(batch.company_margin_rate)))
        + transport_php_per_unit
        + other_php_per_unit
    )

    # 6) 라운딩은 최종가에만 적용
    rounded_final = ceil_to_nearest(base_price_php_per_unit, Decimal(str(batch.rounding_unit_php)))

    # 스냅샷 및 계산결과 저장
    line.fx_rate_snapshot = fx
    line.supplier_pay_php_per_unit = supplier_pay_php_per_unit
    line.transport_php_total = transport_php_total
    line.transport_php_per_unit = transport_php_per_unit
    line.base_price_php_per_unit = base_price_php_per_unit  # ✅ 올림 전(예: 3621.94)
    line.final_price_php_per_unit = rounded_final           # ✅ 올림 후(예: 3630)

    # manual(조정가)가 있으면 최종가 override
    if line.manual_price_php_per_unit is not None:
        line.final_price_php_per_unit = line.manual_price_php_per_unit
