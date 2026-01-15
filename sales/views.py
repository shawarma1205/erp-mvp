# sales/views.py

from __future__ import annotations

from collections import defaultdict
from decimal import Decimal

from django.db.models import F, Sum, Count, ExpressionWrapper, DecimalField
from django.db.models.functions import Coalesce
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, render
from django.utils.dateparse import parse_date

from partners.models import Partner
from sales.models import SalesInvoice, SalesInvoiceLine
import csv
from django.shortcuts import get_object_or_404

from sales.models import SalesInvoice

def _csv_response_with_bom(filename: str) -> HttpResponse:
    """
    Excel에서 UTF-8 한글이 깨지지 않도록 BOM을 포함한 CSV 응답을 만든다.
    """
    response = HttpResponse(content_type="text/csv; charset=utf-8")
    response["Content-Disposition"] = f'attachment; filename="{filename}"'
    response.write("\ufeff")  # UTF-8 BOM
    return response


def sales_report(request):
    """
    Sales Report (ISSUED only)
    - 고객별 총매출 집계 (내림차순 정렬)
    - 최근 ISSUED 인보이스 리스트
    """
    date_from = parse_date(request.GET.get("date_from", "") or "")
    date_to = parse_date(request.GET.get("date_to", "") or "")

    qs = (
        SalesInvoice.objects
        .filter(status=SalesInvoice.ISSUED)
        .select_related("customer")
        .prefetch_related("lines", "lines__product")
        .order_by("-issue_date", "-id")
    )
    if date_from:
        qs = qs.filter(issue_date__gte=date_from)
    if date_to:
        qs = qs.filter(issue_date__lte=date_to)

    invoices = list(qs[:300])  # 화면 과부하 방지

    by_customer = defaultdict(lambda: {
        "customer_id": None,
        "customer_en": "",
        "customer_ko": "",
        "total_php": Decimal("0"),
    })
    grand_total = Decimal("0")

    for inv in invoices:
        ckey = inv.customer_id
        row = by_customer[ckey]
        row["customer_id"] = ckey
        # Partner 필드명은 프로젝트마다 다를 수 있어 fallback 처리
        row["customer_en"] = getattr(inv.customer, "name_en", "") or getattr(inv.customer, "name", "") or str(inv.customer)
        row["customer_ko"] = getattr(inv.customer, "name_ko", "") or ""

        inv_total = Decimal("0")
        for ln in inv.lines.all():
            if ln.final_unit_price_php is None:
                continue
            inv_total += (ln.final_unit_price_php * ln.qty_units)

        row["total_php"] += inv_total
        grand_total += inv_total

    # ✅ 1) 고객별 총매출 내림차순 정렬 (동점이면 이름으로)
    by_customer_list = sorted(
        by_customer.values(),
        key=lambda x: (-x["total_php"], (x["customer_en"] or "")),
    )

    context = {
        "date_from": request.GET.get("date_from", ""),
        "date_to": request.GET.get("date_to", ""),
        "by_customer": by_customer_list,
        "grand_total": grand_total,
        "invoices": invoices,
    }
    return render(request, "sales/sales_report.html", context)


def sales_report_export_csv(request):
    date_from = parse_date(request.GET.get("date_from", "") or "")
    date_to = parse_date(request.GET.get("date_to", "") or "")

    qs = (
        SalesInvoice.objects
        .filter(status=SalesInvoice.ISSUED)
        .select_related("customer")
        .prefetch_related("lines")
        .order_by("-issue_date", "-id")
    )
    if date_from:
        qs = qs.filter(issue_date__gte=date_from)
    if date_to:
        qs = qs.filter(issue_date__lte=date_to)

    by_customer = defaultdict(lambda: {
        "customer_id": None,
        "customer_en": "",
        "customer_ko": "",
        "total_php": Decimal("0"),
    })

    for inv in qs:
        ckey = inv.customer_id
        row = by_customer[ckey]
        row["customer_id"] = ckey
        row["customer_en"] = getattr(inv.customer, "name_en", "") or getattr(inv.customer, "name", "") or str(inv.customer)
        row["customer_ko"] = getattr(inv.customer, "name_ko", "") or ""
        for ln in inv.lines.all():
            if ln.final_unit_price_php is None:
                continue
            row["total_php"] += (ln.final_unit_price_php * ln.qty_units)

    # ✅ 1) CSV도 동일하게 내림차순
    sorted_rows = sorted(
        by_customer.values(),
        key=lambda x: (-x["total_php"], (x["customer_en"] or "")),
    )

    import csv
    response = _csv_response_with_bom("sales_report.csv")
    writer = csv.writer(response)
    writer.writerow(["Customer(EN)", "Customer(KO)", "Total Sales (PHP)"])

    for r in sorted_rows:
        writer.writerow([r["customer_en"], r["customer_ko"], str(r["total_php"])])

    return response


def customer_detail_report(request, customer_id: int):
    """
    고객 1명에 대한 기간별 상세:
    - SKU별 수량/금액 집계
    - 기간 내 ISSUED 인보이스 리스트 (✅ 인보이스 상세 링크 제공)
    """
    date_from = parse_date(request.GET.get("date_from", "") or "")
    date_to = parse_date(request.GET.get("date_to", "") or "")

    customer = get_object_or_404(Partner, id=customer_id)

    inv_qs = (
        SalesInvoice.objects
        .filter(status=SalesInvoice.ISSUED, customer_id=customer_id)
        .order_by("-issue_date", "-id")
    )
    if date_from:
        inv_qs = inv_qs.filter(issue_date__gte=date_from)
    if date_to:
        inv_qs = inv_qs.filter(issue_date__lte=date_to)

    invoices = list(inv_qs[:500])

    line_qs = SalesInvoiceLine.objects.filter(
        invoice__status=SalesInvoice.ISSUED,
        invoice__customer_id=customer_id,
    )
    if date_from:
        line_qs = line_qs.filter(invoice__issue_date__gte=date_from)
    if date_to:
        line_qs = line_qs.filter(invoice__issue_date__lte=date_to)

    rows = (
        line_qs
        .values("product__sku_code", "product__name_en", "product__name_ko")
        .annotate(
            total_qty=Coalesce(Sum("qty_units"), Decimal("0")),
            total_amount=Coalesce(Sum(F("final_unit_price_php") * F("qty_units")), Decimal("0")),
        )
        .order_by("product__sku_code")
    )

    context = {
        "customer": customer,
        "date_from": request.GET.get("date_from", ""),
        "date_to": request.GET.get("date_to", ""),
        "rows": rows,
        "invoices": invoices,
    }
    return render(request, "sales/customer_detail_report.html", context)


def customer_detail_report_export_csv(request, customer_id: int):
    date_from = parse_date(request.GET.get("date_from", "") or "")
    date_to = parse_date(request.GET.get("date_to", "") or "")

    customer = get_object_or_404(Partner, id=customer_id)

    line_qs = SalesInvoiceLine.objects.filter(
        invoice__status=SalesInvoice.ISSUED,
        invoice__customer_id=customer_id,
    )
    if date_from:
        line_qs = line_qs.filter(invoice__issue_date__gte=date_from)
    if date_to:
        line_qs = line_qs.filter(invoice__issue_date__lte=date_to)

    rows = (
        line_qs
        .values("product__sku_code", "product__name_en", "product__name_ko")
        .annotate(
            total_qty=Coalesce(Sum("qty_units"), Decimal("0")),
            total_amount=Coalesce(Sum(F("final_unit_price_php") * F("qty_units")), Decimal("0")),
        )
        .order_by("product__sku_code")
    )

    import csv
    response = _csv_response_with_bom(f"customer_{customer_id}_purchase_report.csv")
    writer = csv.writer(response)

    writer.writerow(["Customer", str(customer)])
    writer.writerow(["Date from", request.GET.get("date_from", ""), "Date to", request.GET.get("date_to", "")])
    writer.writerow([])
    writer.writerow(["SKU", "Product(EN)", "Product(KO)", "Total Qty", "Total Amount (PHP)"])

    for r in rows:
        writer.writerow([
            r["product__sku_code"],
            r["product__name_en"],
            r["product__name_ko"],
            str(r["total_qty"]),
            str(r["total_amount"]),
        ])

    return response


def invoice_detail(request, invoice_id: int):
    """
    ✅ 인보이스 상세 조회:
    - 헤더(고객/날짜/상태)
    - 라인(SKU/이름/수량/단가/금액)
    """
    invoice = get_object_or_404(
        SalesInvoice.objects.select_related("customer").prefetch_related("lines", "lines__product"),
        id=invoice_id,
    )

    # 라인 합계 계산(모델 property가 있으면 그걸 써도 됨)
    total_php = Decimal("0")
    for ln in invoice.lines.all():
        if ln.final_unit_price_php is None:
            continue
        total_php += (ln.final_unit_price_php * ln.qty_units)

    context = {
        "invoice": invoice,
        "lines": invoice.lines.all(),
        "total_php": total_php,
    }
    return render(request, "sales/invoice_detail.html", context)

def invoice_detail_export_csv(request, invoice_id: int):
    """
    Invoice Detail CSV export (UTF-8 BOM 포함)
    - 인보이스 헤더
    - 라인 상세
    """
    invoice = get_object_or_404(
        SalesInvoice.objects.select_related("customer").prefetch_related("lines", "lines__product"),
        id=invoice_id,
    )

    # ✅ BOM 포함 CSV 응답 (이미 프로젝트에 _csv_response_with_bom()이 있으면 그걸 그대로 사용)
    try:
        response = _csv_response_with_bom(f"invoice_{invoice.invoice_no}.csv")  # type: ignore
    except NameError:
        # fallback (혹시 함수명이 다르거나 없는 경우)
        from django.http import HttpResponse
        response = HttpResponse(content_type="text/csv; charset=utf-8")
        response["Content-Disposition"] = f'attachment; filename="invoice_{invoice.invoice_no}.csv"'
        response.write("\ufeff")

    writer = csv.writer(response)

    # Header block
    writer.writerow(["Invoice No", invoice.invoice_no])
    writer.writerow(["Customer", str(invoice.customer)])
    writer.writerow(["Issue Date", str(invoice.issue_date)])
    writer.writerow(["Status", invoice.status])
    writer.writerow([])

    # Line header
    writer.writerow(["SKU", "Product(EN)", "Product(KO)", "Qty", "Final Unit Price(PHP)", "Line Total(PHP)"])

    total_php = Decimal("0")
    for ln in invoice.lines.all():
        unit = ln.final_unit_price_php or Decimal("0")
        qty = ln.qty_units or Decimal("0")
        line_total = unit * qty
        total_php += line_total

        writer.writerow([
            ln.product.sku_code,
            ln.product.name_en,
            ln.product.name_ko,
            str(qty),
            str(unit),
            str(line_total),
        ])

    writer.writerow([])
    writer.writerow(["TOTAL (PHP)", str(total_php)])

    return response

def _csv_response_with_bom(filename: str) -> HttpResponse:
    """
    Excel UTF-8 한글 깨짐 방지용 BOM 포함 CSV
    """
    response = HttpResponse(content_type="text/csv; charset=utf-8")
    response["Content-Disposition"] = f'attachment; filename="{filename}"'
    response.write("\ufeff")
    return response


def _parse_date(s: str):
    # 이미 프로젝트에 날짜 파서가 있으면 그걸 사용하세요.
    # 여기서는 단순히 string 그대로 필터에 넣는 방식(YYYY-MM-DD)을 전제로 합니다.
    return s.strip() if s else ""


def product_performance_overview(request):
    date_from = _parse_date(request.GET.get("date_from", ""))
    date_to = _parse_date(request.GET.get("date_to", ""))
    channel = request.GET.get("channel", "").strip()  # optional

    # ISSUED만 집계
    qs = (
        SalesInvoiceLine.objects
        .select_related("product", "invoice")
        .filter(invoice__status="ISSUED")
    )

    if date_from:
        qs = qs.filter(invoice__issue_date__gte=date_from)
    if date_to:
        qs = qs.filter(invoice__issue_date__lte=date_to)
    if channel:
        qs = qs.filter(invoice__sales_channel=channel)

    # line_total = final_unit_price * qty
    line_total_expr = ExpressionWrapper(
        Coalesce(F("final_unit_price_php"), Decimal("0")) * Coalesce(F("qty_units"), Decimal("0")),
        output_field=DecimalField(max_digits=18, decimal_places=4),
    )

    grouped = (
        qs.values(
            "product_id",
            "product__sku_code",
            "product__name_en",
            "product__name_ko",
        )
        .annotate(
            qty_sold=Coalesce(Sum("qty_units"), Decimal("0")),
            sales_php=Coalesce(Sum(line_total_expr), Decimal("0")),
            invoice_count=Count("invoice_id", distinct=True),
        )
        .order_by("-sales_php", "-qty_sold")
    )

    rows = []
    for r in grouped:
        qty = Decimal(str(r["qty_sold"] or 0))
        sales = Decimal(str(r["sales_php"] or 0))
        avg = (sales / qty) if qty > 0 else Decimal("0")
        rows.append({
            "sku": r["product__sku_code"],
            "name_en": r["product__name_en"],
            "name_ko": r["product__name_ko"],
            "qty_sold": qty,
            "sales_php": sales,
            "invoice_count": r["invoice_count"],
            "avg_unit_price": avg,
        })

    return render(request, "sales/product_performance_overview.html", {
        "date_from": date_from,
        "date_to": date_to,
        "channel": channel,
        "rows": rows,
    })


def product_performance_export_csv(request):
    date_from = _parse_date(request.GET.get("date_from", ""))
    date_to = _parse_date(request.GET.get("date_to", ""))
    channel = request.GET.get("channel", "").strip()

    # view와 동일 로직 재사용(중복 최소화 위해 여기서 다시 계산)
    qs = (
        SalesInvoiceLine.objects
        .select_related("product", "invoice")
        .filter(invoice__status="ISSUED")
    )
    if date_from:
        qs = qs.filter(invoice__issue_date__gte=date_from)
    if date_to:
        qs = qs.filter(invoice__issue_date__lte=date_to)
    if channel:
        qs = qs.filter(invoice__sales_channel=channel)

    line_total_expr = ExpressionWrapper(
        Coalesce(F("final_unit_price_php"), Decimal("0")) * Coalesce(F("qty_units"), Decimal("0")),
        output_field=DecimalField(max_digits=18, decimal_places=4),
    )

    grouped = (
        qs.values(
            "product__sku_code",
            "product__name_en",
            "product__name_ko",
        )
        .annotate(
            qty_sold=Coalesce(Sum("qty_units"), Decimal("0")),
            sales_php=Coalesce(Sum(line_total_expr), Decimal("0")),
            invoice_count=Count("invoice_id", distinct=True),
        )
        .order_by("-sales_php", "-qty_sold")
    )

    response = _csv_response_with_bom("product_performance.csv")
    w = csv.writer(response)

    w.writerow(["Date from", date_from])
    w.writerow(["Date to", date_to])
    w.writerow(["Channel", channel or "ALL"])
    w.writerow([])

    w.writerow(["SKU", "Name(EN)", "Name(KO)", "Qty Sold", "Sales (PHP)", "#Invoices", "Avg Unit Price (PHP)"])

    for r in grouped:
        qty = Decimal(str(r["qty_sold"] or 0))
        sales = Decimal(str(r["sales_php"] or 0))
        avg = (sales / qty) if qty > 0 else Decimal("0")
        w.writerow([
            r["product__sku_code"],
            r["product__name_en"],
            r["product__name_ko"],
            str(qty),
            str(sales),
            str(r["invoice_count"]),
            str(avg),
        ])

    return response