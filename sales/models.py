from django.db import models


class Sale(models.Model):
    customer = models.ForeignKey("partners.Partner", on_delete=models.PROTECT)
    sale_date = models.DateField()

    memo = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-sale_date", "-created_at"]

    def __str__(self) -> str:
        return f"Sale({self.id}) {self.sale_date} to {self.customer}"


class SaleLine(models.Model):
    sale = models.ForeignKey("sales.Sale", on_delete=models.CASCADE, related_name="lines")
    product = models.ForeignKey("inventory.Product", on_delete=models.PROTECT)

    qty_units = models.DecimalField(max_digits=14, decimal_places=4)

    sell_price_php_per_unit = models.DecimalField(max_digits=14, decimal_places=4)
    cogs_php_per_unit_snapshot = models.DecimalField(max_digits=14, decimal_places=4)

    created_at = models.DateTimeField(auto_now_add=True)

    def sell_amount_php(self):
        return self.qty_units * self.sell_price_php_per_unit

    def cogs_total_php(self):
        return self.qty_units * self.cogs_php_per_unit_snapshot

    def gross_profit_php(self):
        return self.sell_amount_php() - self.cogs_total_php()

    def __str__(self) -> str:
        return f"SaleLine({self.product.sku_code}) qty={self.qty_units}"
