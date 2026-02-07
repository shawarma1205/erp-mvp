from django.db import models


class Partner(models.Model):
    class PartnerType(models.TextChoices):
        SUPPLIER = "SUPPLIER", "Supplier"
        CUSTOMER = "CUSTOMER", "Customer"

    partner_type = models.CharField(max_length=20, choices=PartnerType.choices)
    name = models.CharField(max_length=120)
    name_ko = models.CharField(max_length=120, blank=True)

    contact = models.CharField(max_length=200, blank=True)
    address = models.CharField(max_length=200, blank=True)
    memo = models.TextField(blank=True)

    is_active = models.BooleanField(default=True)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["name"]

    def __str__(self) -> str:
        return self.name
