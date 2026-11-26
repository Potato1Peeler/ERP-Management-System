from django.shortcuts import render, get_object_or_404
import json
import logging
import csv
from django.http import HttpResponse, JsonResponse
from django.db import transaction, models
from django.db.models import Max
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_POST
from django.core.paginator import Paginator
from django.shortcuts import redirect
from django.utils import timezone

from .models import SalesOrder, LinesSalesOrder, SalesOrderStatus
from inventory.models import Stock, LocationInventory
from materials.models import Material
from customers.models import Customer
from core.models import Currency
from datetime import date
from users.models import UserRole



logger = logging.getLogger(__name__)

@login_required
def sales_order_list(request):
    max_permission = UserRole.objects.filter(
        user_id=request.user
    ).aggregate(
        max_permission=models.Max('role__sales')
    )['max_permission'] or 0

    if max_permission == 0:
        return redirect('dashboard')


    orders_list = SalesOrder.objects.select_related('id_customer', 'status').all().order_by('-created_at')

    id_so = request.GET.get ('id_sales_order')
    customer_id= request.GET.get('id_customer__id_customer')
    status_symbol = request.GET.get('status__symbol')

    if id_so:
        orders_list = orders_list.filter(id_sales_order__icontains=id_so)
    if customer_id:
        orders_list = orders_list.filter(id_customer__id_customer__icontains=customer_id)
    if status_symbol:
        orders_list = orders_list.filter(status__symbol__iexact = status_symbol)
 
    if request.GET.get('export') == 'csv':
        response = HttpResponse(content_type = 'text/csv')
        response['Content-Disposition'] = 'attachment; filename="sales_orders.csv"'

        response.write('\ufeff'.encode('utf-8'))
        writer = csv.writer(response)
        writer.writerow(['ID SO', 'Customer ID', 'Customer Name', 'Status', 'Date'])

        for so in orders_list:
            writer.writerow([
                so.id_sales_order,
                so.id_customer.id_customer,
                so.id_customer.name,
                so.status.symbol,
                so.created_at.strftime('%Y-%m-%d'),

                #getattr(so, 'total_amount', 0) TODO: Total amount
            ])
        return response

    paginator = Paginator(orders_list, 10)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    all_statuses = SalesOrderStatus.objects.all().order_by('symbol')

    query_params = request.GET.copy()
    query_params.pop('page', None)
    query_params.pop('export', None)

    context = {
        'page_obj': page_obj,
        'all_statuses_so': all_statuses,
        'query_string': query_params.urlencode(),
    }
    return render(request, 'sales/sales_order_list.html', context)

@login_required
def get_stock_data(request):
    max_permission = UserRole.objects.filter(
        user_id=request.user
    ).aggregate(
        max_permission=models.Max('role__sales')
    )['max_permission'] or 0

    if max_permission == 0:
        return redirect('dashboard')

    material_code = request.GET.get('material_id')
    location_id = request.GET.get('location_id')

    stock_record = Stock.objects.filter(
        id_material__id_material = material_code,
        id_location_id = location_id,
    ).order_by('-date').first()

    if stock_record:
        physical = float(stock_record.quantity)
        reserved = float(stock_record.reserved_quantity)
        avaible = physical -reserved

        return JsonResponse({
            'avaible': avaible,
            'wac': float(stock_record.avg_price_usd),
            'unit': stock_record.unit_type.symbol if stock_record.unit_type else 'UN'
        })

    return JsonResponse({'avaible': 0, 'wac': 0.0, 'unit': 'N/A'})

@login_required
def get_customer_details(request, customer_id):

    max_permission = UserRole.objects.filter(
        user_id=request.user
    ).aggregate(
        max_permission=models.Max('role__sales')
    )['max_permission'] or 0

    if max_permission == 0:
        return redirect('dashboard')

    customer = get_object_or_404(Customer, id_customer = customer_id)
    data = {
        'id_customer': customer.id_customer,
        'name': customer.name,
        'address': customer.address,
        'city': customer.city,
        'country': str(customer.country),
    }

    return JsonResponse(data)

@login_required
def sales_order_create(request):

    max_permission = UserRole.objects.filter(
        user_id=request.user
    ).aggregate(
        max_permission=models.Max('role__sales')
    )['max_permission'] or 0

    if max_permission == 0:
        return redirect('dashboard')


    if request.method == 'POST':
        try:
            with transaction.atomic():
                data = json.loads(request.body)
                customer_id = data.get('id_customer')
                est_delivery = data.get('estimulated_delivery_date')
                lines_data = data.get('lines', [])

                if not customer_id or not est_delivery or not lines_data:
                    return JsonResponse({'success': False, 'error': 'There are required fields missing'}, status= 400)
                customer = get_object_or_404(Customer, id_customer = customer_id)
                status = get_object_or_404(SalesOrderStatus, symbol = 'CONFIRMED')

                max_id_result = SalesOrder.objects.aggregate(max_id=Max('id_sales_order'))
                last_id_str = max_id_result.get('max_id')

                next_number = 1
                if last_id_str and '-' in last_id_str:
                    try:
                        next_number = int(last_id_str.split('-')[1]) + 1
                    except (ValueError, IndexError):
                        next_number = 1

                next_so_id = f"SO-{str(next_number).zfill(5)}"

                so = SalesOrder.objects.create(
                    id_sales_order = next_so_id,
                    id_customer = customer,
                    estimulated_delivery_date = est_delivery,
                    status = status,
                    created_by= request.user,
                )

                for position, line in enumerate(lines_data, start=1):
                    material = get_object_or_404(Material, id_material = line['id_material'])
                    location = get_object_or_404(LocationInventory, id_location = line['id_location'])

                    today = timezone.localdate()

                    last_stock = Stock.objects.select_for_update().filter(
                        id_material=material,
                        id_location=location,
                        date__lte=today
                    ).order_by('-date').first()

                    if not last_stock:
                        raise ValueError(
                            f"There are no stock records for {material.name}"
                        )

                    stock_record, created = Stock.objects.select_for_update().get_or_create(
                        id_material=material,
                        id_location=location,
                        date=today,
                        defaults={
                            'quantity': last_stock.quantity,
                            'reserved_quantity': last_stock.reserved_quantity,
                            'avg_price_usd': last_stock.avg_price_usd,
                            'unit_type': last_stock.unit_type,
                        }
                    )

                    qty_requested = int(line['quantity'])
                    if qty_requested <= 0:
                        raise ValueError("Quantity must be greater than zero.")
                    avaible = stock_record.quantity - stock_record.reserved_quantity
                    if avaible < qty_requested:
                        raise ValueError(f"Not avaible. Stock: {avaible}")
                    stock_record.reserved_quantity += qty_requested
                    stock_record.save()

                    LinesSalesOrder.objects.create(
                        id_sales_order_line=f"{so.id_sales_order}-{position}",
                        id_sales_order = so,
                        id_material = material,
                        id_location = location,
                        position = position,
                        quantity = qty_requested,
                        unit_material = material.unit,
                        price = float(line['price']),
                        wac = float(stock_record.avg_price_usd),
                        currency=Currency.objects.get(
                            id=line['currency_id'],
                            symbol='USD'
                        ), #TODO Add more currencies
                        created_by = request.user
                    )
                return JsonResponse({
                    'success': True,
                    'id': so.id_sales_order,
                    'message': f"Order {so.id_sales_order} successfully created. Stock has been compromised"
                })
            
        except ValueError as e:
            return JsonResponse({
                'success': False,
                'error': str(e)
            }, status=400)

        except Exception as e:
            return JsonResponse({
                'success': False,
                'error': str(e)
            }, status=500)

    context= {
        'customers': Customer.objects.all(),
        'materials': Material.objects.all(),
        'locations': LocationInventory.objects.all(),
        'currencies': Currency.objects.filter(symbol='USD'), #TODO: For now USD only
        'title': 'New Sales Order'
    }

    return render(request, 'sales/sales_order_form.html', context)