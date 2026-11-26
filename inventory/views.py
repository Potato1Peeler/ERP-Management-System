import csv
from decimal import Decimal, ROUND_HALF_UP
from datetime import date, timedelta
from django.shortcuts import render, redirect
from django.http import HttpResponse
from django.db import transaction, models
from django.db.models import Sum, F
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.utils import timezone
from accounting.models import AccountAccount, Journal
from core.models import Currency
from users.models import UserRole
from materials.models import Unit
from sales.models import LinesSalesOrder
from .models import Stock, InventoryMovements, LocationInventory, MovementType
from .forms import InventoryMovementForm
from datetime import date, datetime, time, timedelta

def get_pmp_data(current_qty, current_pmp, qty_m, price, rate):
    price_unit_usd = Decimal(str(price)) / Decimal(str(rate))
    total_val_before = current_qty * current_pmp
    total_val_input = qty_m * price_unit_usd
    new_qty = current_qty + qty_m
    new_pmp = (total_val_before + total_val_input) / new_qty if new_qty > 0 else current_pmp

    return new_qty, new_pmp

def get_movement_quantity_change(movement):
    symbol = (movement.movement_type.symbol or '').upper()
    if symbol in {'GR', 'PUR'}:
        return Decimal(str(movement.quantity))
    if symbol in {'IM', 'IN', 'LO', 'LOSS', 'INT_USE', 'SALE', 'SAL'}:
        return -Decimal(str(movement.quantity))
    return Decimal('0')

def get_pending_reserved_quantity(material_id, location_id):
    pending_lines = LinesSalesOrder.objects.filter(
        id_material__id = material_id,
        id_location_id = location_id,
        id_sales_order__status__symbol__in = ['CONFIRMED', 'PARTIAL_SENT'],
    ).annotate(remaining=F('quantity') - F('shipped_quantity'))

    pending_lines = pending_lines.exclude(remaining__lte = 0)
    total_reserved = pending_lines.aggregate(total_res = Sum('remaining'))['total_res'] or 0
    return Decimal(str(total_reserved))


def sync_daily_stock_date(start_date = None):
    try:
        if not start_date:
            first_mov = InventoryMovements.objects.order_by('created_at').first()
            if not first_mov:
                return

            current_date = timezone.localdate(first_mov.created_at)
        else:
            current_date = start_date

        today, running_balances = timezone.localdate(), {}

        
        previus_day = current_date - timedelta(days=1)
        last_stocks = Stock.objects.filter(date = previus_day)
        for s in last_stocks:
            running_balances[(s.id_material_id, s.id_location_id)] = {
                'qty': Decimal(str(s.quantity)),
                'pmp': Decimal(str(s.avg_price_usd)),
                'unit': s.unit_type,
                'reserved': Decimal(str(s.reserved_quantity or 0))
                
            }

        while current_date <= today:
            with transaction.atomic():
                day_start = timezone.make_aware(datetime.combine(current_date, time.min), timezone.get_current_timezone())
                day_end = timezone.make_aware(datetime.combine(current_date + timedelta(days=1), time.min), timezone.get_current_timezone())
                daily_movs = InventoryMovements.objects.filter(created_at__gte = day_start, created_at__lt = day_end)
                materials_to_process = set(running_balances.keys()) | set(daily_movs.values_list('id_material_id', 'id_location_id'))

                materials_to_process = set(running_balances.keys()) | \
                                           set(daily_movs.values_list('id_material_id', 'id_location_id'))

                for mat_id, loc_id in materials_to_process:
                    key = (mat_id, loc_id)
                    prev_data= running_balances.get(key)
                    if prev_data is None:
                        previous_stock = Stock.objects.filter(
                            id_material_id=mat_id,
                            id_location_id=loc_id,
                            date__lt=current_date,
                        ).order_by('-date').first()

                        prev_data = {
                            'qty': Decimal(str(previous_stock.quantity))
                                if previous_stock else Decimal('0.0'),

                            'pmp': Decimal(str(previous_stock.avg_price_usd))
                                if previous_stock else Decimal('0.0'),

                            'unit': previous_stock.unit_type
                                if previous_stock else None,

                            'reserved': Decimal(str(previous_stock.reserved_quantity))
                                if previous_stock else Decimal('0.0'),
                        }

                    mat_movs = daily_movs.filter(id_material_id = mat_id, id_location_id = loc_id).order_by('created_at')

                    current_qty = prev_data['qty']
                    current_pmp = prev_data['pmp']
                    current_unit = prev_data['unit'] or (mat_movs.first().unit_type if mat_movs.exists() else None)

                    for m in mat_movs:
                        qty_m = get_movement_quantity_change(m)
                        if qty_m > 0:
                            current_qty, current_pmp = get_pmp_data(current_qty, current_pmp, qty_m, m.price, m.exchange_rate)
                        elif qty_m < 0:
                            current_qty += qty_m

                    if current_date == today:
                        current_reserved = get_pending_reserved_quantity(mat_id, loc_id)
                    else:
                        existing = Stock.objects.filter(date=current_date, id_material_id = mat_id, id_location_id = loc_id).first()
                        current_reserved = Decimal(str(existing.reserved_quantity)) if existing else prev_data['reserved']

                    pmp_rounded = current_pmp.quantize(Decimal('0.000001'), rounding=ROUND_HALF_UP)

                            
                    Stock.objects.update_or_create(
                        date = current_date,
                        id_location_id = loc_id,
                        id_material_id = mat_id,
                        defaults={
                            'quantity': int(max(current_qty, Decimal('0.0'))),
                            'reserved_quantity': int(current_reserved),
                            'avg_price_usd': pmp_rounded,
                            'unit_type': current_unit
                        }
                    )

                    running_balances[key] = {
                        'qty': current_qty, 
                        'pmp': current_pmp, 
                        'unit': current_unit,
                        'reserved': current_reserved,
                    }

                current_date += timedelta(days=1)

    except Exception as e:
        print(f"Error synchronizing: {e}")
        raise


@login_required
def movement_list(request):

    max_permission = UserRole.objects.filter(
        user_id=request.user
    ).aggregate(
        max_permission=models.Max('role__inventory')
    )['max_permission'] or 0

    if max_permission == 0:
        return redirect('dashboard')

    movements = InventoryMovements.objects.select_related(
        'id_location',
        'id_material',
        'unit_type',
        'currency',
        'movement_type',
        'created_by'
    ).all().order_by('-created_at', '-pk')

    material_id = request.GET.get('id_material', '').strip()
    location_id = request.GET.get('location', '').strip()
    movement_type = request.GET.get('type', '').strip()

    if material_id:
        movements = movements.filter(
            id_material__id_material__icontains=material_id
        )

    if location_id:
        movements = movements.filter(
            id_location_id=location_id
        )

    if movement_type:
        movements = movements.filter(
            movement_type_id=movement_type
        )

    if request.GET.get('export') == 'csv':

        response = HttpResponse(content_type='text/csv')

        response['Content-Disposition'] = (
            'attachment; filename="inventory_movements.csv"'
        )

        response.write('\ufeff'.encode('utf-8'))

        writer = csv.writer(response)

        writer.writerow([
            'ID Movement',
            'Date',
            'Location',
            'ID Material',
            'Material Name',
            'Movement Type',
            'Quantity',
            'Unit',
            'Price',
            'Currency',
            'Exchange Rate',
            'User'
        ])

        for m in movements:
            writer.writerow([
                m.id_inventory_movement,
                timezone.localtime(m.created_at).strftime('%Y-%m-%d %H:%M:%S'),
                m.id_location.name,
                m.id_material.id_material,
                m.id_material.name,
                m.movement_type.name,
                m.quantity,
                m.unit_type.symbol,
                m.price,
                m.currency.symbol,
                m.exchange_rate,
                m.created_by.username if m.created_by else 'N/A'
            ])

        return response

    paginator = Paginator(movements, 10)
    page_obj = paginator.get_page(request.GET.get('page'))

    query_params = request.GET.copy()
    query_params.pop('page', None)
    query_params.pop('export', None)

    context = {
        'page_obj': page_obj,
        'locations': LocationInventory.objects.all().order_by('name'),
        'mov_types': MovementType.objects.all().order_by('name'),
        'permissions': {'inventory': max_permission},
        'query_string': query_params.urlencode(),
    }

    return render(request, 'inventory/movement_list.html', context)


@login_required
def stock_list(request):

    max_permission = UserRole.objects.filter(
        user_id=request.user
    ).aggregate(
        max_permission=models.Max('role__inventory')
    )['max_permission'] or 0

    if max_permission == 0:
        return redirect('dashboard')

    stocks = Stock.objects.select_related(
        'id_location',
        'id_material',
        'unit_type'
    ).annotate(
        available_quantity=F('quantity') - F('reserved_quantity')
    ).order_by('-date', 'id_location', 'id_material')

    date_filter = request.GET.get('date', '')
    material_id = request.GET.get('id_material', '').strip()
    location_id = request.GET.get('location', '').strip()

    if date_filter:
        stocks = stocks.filter(date=date_filter)

    if material_id:
        stocks = stocks.filter(
            id_material__id_material__icontains=material_id
        )

    if location_id:
        stocks = stocks.filter(
            id_location_id=location_id
        )

    if request.GET.get('export') == 'csv':

        response = HttpResponse(content_type='text/csv')

        response['Content-Disposition'] = (
            'attachment; filename="inventory_stock.csv"'
        )

        response.write('\ufeff'.encode('utf-8'))

        writer = csv.writer(response)

        writer.writerow([
            'Date',
            'Location',
            'ID Material',
            'Material Name',
            'On Hand',
            'Reserved',
            'Avaible',
            'Unit',
            'WAC USD',
            'Total USD'
        ])

        for s in stocks:
            writer.writerow([
                s.date.strftime('%Y-%m-%d'),
                s.id_location.name,
                s.id_material.id_material,
                s.id_material.name,
                s.quantity,
                s.reserved_quantity,
                s.avaible_quantity,
                s.unit_type.symbol,
                s.avg_price_usd,
                s.total_value_usd
            ])

        return response

    paginator = Paginator(stocks, 10)
    page_obj = paginator.get_page(request.GET.get('page'))

    query_params = request.GET.copy()
    query_params.pop('page', None)
    query_params.pop('export', None)
    query_params['date'] = date_filter

    context = {
        'page_obj': page_obj,
        'locations': LocationInventory.objects.all().order_by('name'),
        'current_date': date_filter,
        'permissions': {'inventory': max_permission},
        'query_string': query_params.urlencode(),
    }

    return render(request, 'inventory/stock_list.html', context)


def self_Accounting(mov, usd, user):

    acc_map = {'INT_USE':  ('6020', 'Internal Use'), 'LOSS':('6590', 'Inventory Loss')}
    code_dr, ref_text = acc_map[mov.movement_type.symbol]
    value = float(mov.quantity) * float(mov.price)

    entries = [
        (code_dr, value, 0.0, f"{ref_text}: {mov.description[:50]}", "D1"),
        ('1200', 0.0, value, f"Stock Out - {mov.id_inventory_movement}", "C1")
    ]

    for code, db, cr, ref, suffix in entries:
        Journal.objects.create(
            id_journal = f"IM-{mov.id_inventory_movement}-{suffix}",
            group_journal = f"IM-{mov.id_inventory_movement}",
            reference=ref,
            id_account = AccountAccount.objects.get(code=code),
            debit=db, credit=cr, currency=usd, cost_center=mov.cost_center, description=mov.description, created_by=user
        )

@login_required
def create_movement(request):
    max_permission = UserRole.objects.filter(
    user_id=request.user
    ).aggregate(
        max_permission=models.Max('role__inventory')
    )['max_permission'] or 0

    if max_permission < 2:
        return redirect('inventory:movement_list')

    if request.method == 'POST':
        form = InventoryMovementForm(request.POST)
        if form.is_valid():
            try:
                with transaction.atomic():
                    mov = form.save(commit=False)
                    mov.created_by = request.user
                    mov.unit_type = mov.id_material.unit

                    usd =Currency.objects.get(symbol='USD')
                    mov.currency = usd
                    prefix = mov.movement_type.symbol[:2].upper()
                    count = InventoryMovements.objects.filter(movement_type = mov.movement_type).count()
                    mov.id_inventory_movement = f"{prefix}-{(count + 1):07d}"

                    last_stock = Stock.objects.filter(
                        id_material=mov.id_material,
                        id_location=mov.id_location
                    ).order_by('-date').first()

                    mov.price = last_stock.avg_price_usd if last_stock else 0

                    stock_today, _ = Stock.objects.get_or_create(
                        id_material=mov.id_material,
                        id_location=mov.id_location,
                        date=timezone.localdate(),
                        defaults={
                            'quantity': last_stock.quantity if last_stock else 0,
                            'avg_price_usd': mov.price,
                            'unit_type': mov.unit_type,
                            'reserved_quantity': int(
                                get_pending_reserved_quantity(
                                    mov.id_material_id,
                                    mov.id_location_id
                                )
                            ),
                        }
                    )
                    stock_today.reserved_quantity = int(
                        get_pending_reserved_quantity(
                            mov.id_material_id,
                            mov.id_location_id
                        )
                    )
                    qty_change = -mov.quantity if mov.movement_type.symbol in ['LOSS', 'INT_USE', 'SALE', 'SAL'] else mov.quantity
                    available_quantity = stock_today.quantity - stock_today.reserved_quantity
                    if qty_change < 0 and available_quantity < mov.quantity:
                        raise ValueError(f"Not enough available stock: {available_quantity}")

                    stock_today.quantity += qty_change
                    stock_today.total_value_usd = float(stock_today.quantity) * float(stock_today.avg_price_usd)
                    stock_today.save()
                    mov.save()

                    if mov.movement_type.symbol in ['INT_USE', 'LOSS'] and (float(mov.quantity)*float(mov.price)) > 0:
                        self_Accounting(mov, usd, request.user)

                    messages.success(request, f"Movement {mov.id_inventory_movement} registered")
                    return redirect('inventory:movement_list')
            except Exception as e:
                print(f"Process error: {str(e)}")
                messages.error(request, f"Process error: {str(e)}")
        
        else:
            for field, errors in form.errors.items():
                for error in errors:
                    field_label = form.fields[field].label if field in form.fields else field
                    messages.error(request, f"Error in {field_label}:{error}")
    else:
        form = InventoryMovementForm()

    return render(request, 'inventory/movement_form.html', {'form':form})



