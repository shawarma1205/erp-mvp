# inventory/views.py
from django.db.models import Q

from django.shortcuts import render
from django.http import HttpResponse
from django.utils.dateparse import parse_date

from inventory.models import InventoryBalance, StockMovement


def inventory_overview(request):
    """
    GET params (optional):
      - q: 검색어 (SKU / EN / KO)
      - move_from=YYYY-MM-DD
      - move_to=YYYY-MM-DD
      - move_type=IN/OUT/ADJ
    """
    q = (request.GET.get("q") or "").strip()
    move_from = parse_date(request.GET.get("move_from", "") or "")
    move_to = parse_date(request.GET.get("move_to", "") or "")
    move_type = (request.GET.get("move_type") or "").strip()

    balances = InventoryBalance.objects.select_related("product").order_by("product__sku_code")
    if q:
        balances = balances.filter(
            Q(product__sku_code__icontains=q) |
            Q(product__name_en__icontains=q) |
            Q(product__name_ko__icontains=q)
        )

    movements = StockMovement.objects.select_related("product").order_by("-created_at")
    if move_type in {"IN", "OUT", "ADJ"}:
        movements = movements.filter(movement_type=move_type)
    if move_from:
        movements = movements.filter(created_at__date__gte=move_from)
    if move_to:
        movements = movements.filter(created_at__date__lte=move_to)

    # 너무 길어지는 것 방지: 화면에는 최근 300개만
    movements = movements[:300]

    context = {
        "q": q,
        "move_from": request.GET.get("move_from", ""),
        "move_to": request.GET.get("move_to", ""),
        "move_type": move_type,
        "balances": balances,
        "movements": movements,
    }
    return render(request, "inventory/inventory_overview.html", context)


def export_balances_csv(request):
    q = (request.GET.get("q") or "").strip()

    balances = InventoryBalance.objects.select_related("product").order_by("product__sku_code")
    if q:
        balances = balances.filter(
            product__sku_code__icontains=q
        ) | balances.filter(product__name_en__icontains=q) | balances.filter(product__name_ko__icontains=q)

    import csv
    response = HttpResponse(content_type="text/csv; charset=utf-8")
    response["Content-Disposition"] = 'attachment; filename="inventory_balances.csv"'

    w = csv.writer(response)
    w.writerow(["SKU", "Name(EN)", "Name(KO)", "Base Unit", "On Hand Qty"])

    for b in balances:
        p = b.product
        w.writerow([p.sku_code, p.name_en, p.name_ko, p.base_unit, str(b.on_hand_qty_units)])

    return response


def export_movements_csv(request):
    move_from = parse_date(request.GET.get("move_from", "") or "")
    move_to = parse_date(request.GET.get("move_to", "") or "")
    move_type = (request.GET.get("move_type") or "").strip()

    movements = StockMovement.objects.select_related("product").order_by("-created_at")
    if move_type in {"IN", "OUT", "ADJ"}:
        movements = movements.filter(movement_type=move_type)
    if move_from:
        movements = movements.filter(created_at__date__gte=move_from)
    if move_to:
        movements = movements.filter(created_at__date__lte=move_to)

    import csv
    response = HttpResponse(content_type="text/csv; charset=utf-8")
    response["Content-Disposition"] = 'attachment; filename="stock_movements.csv"'

    w = csv.writer(response)
    w.writerow(["Created At", "Type", "SKU", "Product Name(EN)", "Product Name(KO)", "Qty", "Ref Table", "Ref ID", "Memo"])

    for m in movements[:2000]:  # CSV는 최근 2000개 제한(초기 안전장치)
        p = m.product
        w.writerow([m.created_at, m.movement_type, p.sku_code, p.name_en, p.name_ko, str(m.qty_units), m.ref_table, m.ref_id, m.memo])

    return response
