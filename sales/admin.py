from django.contrib import admin
from .models import SalesOrderStatus, SalesOrder, LinesSalesOrder

@admin.register(SalesOrderStatus)
class SalesOrderStatusAdmin(admin.ModelAdmin):
    list_display=('name', 'symbol')

@admin.register(SalesOrder)
class SalesOrderAdmin(admin.ModelAdmin):
    list_display= ('id_sales_order', 'id_customer', 'issue_date', 'estimulated_delivery_date', 'status')

@admin.register(LinesSalesOrder)
class LinesSalesOrderAdmin(admin.ModelAdmin):
    list_display=('id_sales_order_line', 'id_sales_order', 'id_material', 'id_location', 'quantity', 'unit_material', 'price', 'wac', 'margin', 'currency', 'shipped_quantity')


