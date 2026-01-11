from decimal import Decimal
from collections import defaultdict

from django.http import HttpResponse
from django.shortcuts import render
from django.utils.dateparse import parse_date

from sales.models import SalesInvoice


def sales_report(request):
    date_from = parse_date(request.GET.get("date_from", "") or "")
    date_to = parse_date(request.GET.get("date_to", "") or "")
    customer_id = request.GET.get("customer_id", "") or ""

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
    if customer_id:
        qs = qs.filter(customer_id=customer_id)

    # 고객별 누적
    by_customer = defaultdict(lambda: {"customer_en": "", "customer_ko": "", "total_php": Decimal("0")})
    grand_total = Decimal("0")

    invoices = list(qs[:300])  # 화면 과부하 방지 (최근 300건)

    for inv in invoices:
        ckey = inv.customer_id
        by_customer[ckey]["customer_en"] = inv.customer.name
        by_customer[ckey]["customer_ko"] = getattr(inv.customer, "name_ko", "") or ""
        # 인보이스 총액 = 라인 합계
        inv_total = Decimal("0")
        for ln in inv.lines.all():
            if ln.final_unit_price_php is None:
                continue
            inv_total += (ln.final_unit_price_php * ln.qty_units)
        by_customer[ckey]["total_php"] += inv_total
        grand_total += inv_total

    # 템플릿에서 쓰기 좋은 list로 변환 + 정렬
    by_customer_list = sorted(by_customer.values(), key=lambda x: (x["customer_en"] or ""))

    context = {
        "date_from": request.GET.get("date_from", ""),
        "date_to": request.GET.get("date_to", ""),
        "customer_id": customer_id,
        "by_customer": by_customer_list,
        "grand_total": grand_total,
        "invoices": invoices,
    }
    return render(request, "sales/sales_report.html", context)


def sales_report_export_csv(request):
    date_from = parse_date(request.GET.get("date_from", "") or "")
    date_to = parse_date(request.GET.get("date_to", "") or "")
    customer_id = request.GET.get("customer_id", "") or ""

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
    if customer_id:
        qs = qs.filter(customer_id=customer_id)

    from collections import defaultdict
    by_customer = defaultdict(lambda: {"customer_en": "", "customer_ko": "", "total_php": Decimal("0")})

    for inv in qs:
        ckey = inv.customer_id
        by_customer[ckey]["customer_en"] = inv.customer.name
        by_customer[ckey]["customer_ko"] = getattr(inv.customer, "name_ko", "") or ""
        for ln in inv.lines.all():
            if ln.final_unit_price_php is None:
                continue
            by_customer[ckey]["total_php"] += (ln.final_unit_price_php * ln.qty_units)

    import csv
    response = HttpResponse(content_type="text/csv; charset=utf-8")
    response["Content-Disposition"] = 'attachment; filename="sales_report.csv"'

    writer = csv.writer(response)
    writer.writerow(["Customer(EN)", "Customer(KO)", "Total Sales (PHP)"])

    for row in sorted(by_customer.values(), key=lambda x: (x["customer_en"] or "")):
        writer.writerow([row["customer_en"], row["customer_ko"], str(row["total_php"])])

    return response
