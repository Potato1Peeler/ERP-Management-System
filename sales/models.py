from django.db import models
from django.conf import settings
from customers.models import Customer
from materials.models import Material, Unit
from core.models import Currency
from inventory.models import LocationInventory

class SalesOrderStatus(models.Model):
    name = models.CharField(max_length=200, verbose_name="Name")
    symbol = models.CharField(max_length=100, blank= True, verbose_name="Symbol")

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now= True)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True)
    
    class Meta:
        verbose_name = "Sales Order Status"
        verbose_name_plural = "Sales Order Status"

    def __str__(self):
        return self.symbol

class SalesOrder(models.Model):
    id_sales_order = models.CharField(max_length=10, verbose_name="ID Sales Order")
    id_customer= models.ForeignKey(Customer, default=1, on_delete=models.PROTECT, verbose_name="Customer")
    issue_date = models.DateField(auto_now_add=True)
    estimulated_delivery_date = models.DateField(verbose_name="Estimated delivery date")
    status = models.ForeignKey(SalesOrderStatus, default=1, on_delete=models.PROTECT, verbose_name="Status")

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now= True)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True)
    
    class Meta:
        verbose_name = "Sales Order"
        verbose_name_plural = "Sales Orders"

    def __str__(self):
        return self.id_sales_order

class LinesSalesOrder(models.Model):
    id_sales_order_line = models.CharField(max_length=30, verbose_name="ID Sales Order Live")
    id_sales_order = models.ForeignKey(SalesOrder, default=1, on_delete=models.PROTECT, verbose_name="Sales Order")
    id_material = models.ForeignKey(Material, default=1, on_delete=models.PROTECT, verbose_name="Material", related_name="Material")
    id_location = models.ForeignKey(LocationInventory, on_delete=models.PROTECT, verbose_name="Storage")
    position = models.IntegerField(default=1, verbose_name="Position")
    quantity = models.IntegerField(default=0, verbose_name="Quantity")
    unit_material = models.ForeignKey(Unit, on_delete=models.PROTECT, verbose_name="Unit")
    price = models.FloatField(verbose_name="Price")
    wac = models.FloatField(verbose_name= "WAC")
    margin = models.FloatField(verbose_name="Margin (%)")

    currency = models.ForeignKey(Currency, on_delete=models.PROTECT)

    shipped_quantity = models.IntegerField(default=0, verbose_name="Shipped Quantity")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now= True)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True)

    def save(self, *args, **kwargs):
        if self.price and self.price > 0:
            self.margin = round(((self.price - self.wac) / self.price) * 100, 2)
        else:
            self.margin = -100 if self.wac > 0 else 0
        super().save(*args, **kwargs)
    
    class Meta:
        verbose_name = "Lines Sales Order"
        verbose_name_plural = "Line Sales Orders"

    def __str__(self):
        return self.id_sales_order_line

