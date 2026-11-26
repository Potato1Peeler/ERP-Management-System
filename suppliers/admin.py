from django.contrib import admin

from .models import Supplier

@admin.register(Supplier)
class SupplierAdmin(admin.ModelAdmin):
    list_display = ('id_supplier', 'name', 'country', 'status')