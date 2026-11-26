from django.db import models
from django.conf import settings
from django.contrib.auth.models import User
from core.models import Status, Currency
from materials.models import Material, Unit
from datetime import date
from accounting.models import CostCenter
from decimal import Decimal, ROUND_HALF_UP

class MovementType(models.Model):
    name = models.CharField(verbose_name="Name", max_length=50)
    symbol = models.CharField(verbose_name="Symbol", max_length=50)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True)

    class Meta:
        verbose_name = "Movement Type"
        verbose_name_plural = "Movement Types"

    def __str__(self):
        return f"{self.symbol} - {self.name}"


class LocationInventory(models.Model):

    id_location = models.CharField(verbose_name="Location ID", max_length=10, primary_key=True)
    name = models.CharField(verbose_name="Name", max_length=100)
    code = models.CharField(verbose_name="Code", max_length=20)
    main_location = models.BooleanField(verbose_name="Main Location", default=False)
    location = models.TextField(verbose_name="Address", blank=True)

    status = models.ForeignKey(Status, default=1, on_delete=models.SET_NULL, null=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True)

    class Meta:
        verbose_name = "Inventory Location"
        verbose_name_plural = "Inventory Locations"

    def __str__(self):
        return f"{self.code} - {self.name}"

class InventoryMovements(models.Model):

    id_inventory_movement = models.CharField(verbose_name="Inventory Movement ID", max_length=30, primary_key=True)
    id_location = models.ForeignKey(LocationInventory, on_delete=models.PROTECT, verbose_name="Location ID")
    id_material = models.ForeignKey(Material, on_delete=models.PROTECT, verbose_name="Material ID")
    quantity = models.IntegerField(verbose_name="Quantity")
    unit_type = models.ForeignKey(Unit, on_delete=models.PROTECT, verbose_name="Unit Type")

    price = models.FloatField(verbose_name="Price", default=0.0)
    currency = models.ForeignKey(Currency, on_delete=models.PROTECT, verbose_name="Currency")

    exchange_rate = models.DecimalField(max_digits=18, decimal_places=6, default=1.0, verbose_name='Exchange Rate')

    movement_type = models.ForeignKey(MovementType, on_delete=models.PROTECT, verbose_name="Movement ID")

    cost_center = models.ForeignKey(CostCenter, verbose_name='Cost Center', on_delete=models.PROTECT, null=True, blank=True)
    description = models.TextField(verbose_name='Description', blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True)

    class Meta:
        verbose_name = "Inventory Movement"
        verbose_name_plural = "Inventory Movements"

    def __str__(self):
        return f"{self.id_material} - {self.quantity} - {self.unit_type}"
    
class Stock(models.Model):

    id_location = models.ForeignKey(LocationInventory, on_delete=models.CASCADE)
    id_material = models.ForeignKey(Material, on_delete=models.CASCADE)
    date = models.DateField(verbose_name='Journal Date', default=date.today)
    quantity = models.IntegerField(verbose_name='Quantity', default=0)
    reserved_quantity = models.IntegerField(verbose_name='Reserved Quantity', default=0)
    unit_type = models.ForeignKey(Unit, on_delete=models.PROTECT, verbose_name="Unit Type")

    avg_price_usd = models.DecimalField(max_digits=18, decimal_places=6, default=0.0)
    total_value_usd = models.DecimalField(max_digits=18, decimal_places=4, default=0.0)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Stock"
        verbose_name_plural = "Stocks"
        unique_together = ('date', 'id_location', 'id_material')

    def save(self, *args, **kwargs):
        self.total_value_usd = (
            Decimal(str(self.quantity)) *
            Decimal(str(self.avg_price_usd))
        ).quantize(
            Decimal('0.0001'),
            rounding=ROUND_HALF_UP
        )

        if kwargs.get('update_fields') is not None:
            kwargs['update_fields'] = (
                set(kwargs['update_fields']) |
                {'total_value_usd'}
            )

        super().save(*args, **kwargs)
