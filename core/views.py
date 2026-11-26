from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from users.models import UserRole
from .models import ExchangeRate, Currency
from django.conf import settings
from datetime import date, timedelta
import requests
import threading
from inventory.views import sync_daily_stock_date

def run_maintenance_tasks():

    update_exchange_rates_background()
    sync_daily_stock_date()

@login_required
def dashboard_view(request):

    #threading.Thread(target=run_maintenance_tasks, daemon=True).start()


    user_roles = UserRole.objects.filter(user_id=request.user)
    permissions = {
        'customers': 0,
        'suppliers': 0,
        'materials': 0,
        'purchases': 0,
        'sales': 0,
        'inventory': 0,
        'accounting': 0,
        'reporting': 0,
    }

    for user_role in user_roles:
        role = user_role.role
        for module in permissions.keys():
            current_permission = getattr(role, module)
            if current_permission > permissions[module]:
                permissions[module] = current_permission

    context = {
        'user': request.user,
        'permissions': permissions,
        'roles': [ur.role.role_name for ur in user_roles]
    }

    return render(request, 'core/dashboard.html', context)

def update_exchange_rates_background():
    try:
        base_currency_code = getattr(settings, 'BASE_CURRENCY', 'USD')
        last_rate = ExchangeRate.objects.all().first()

        if not last_rate:
            start_date = (date.today() - timedelta(days =1)).isoformat()
            url = f"http://api.frankfurter.dev/v1/{start_date}?base={base_currency_code}"

        else:

            start_date_obj = last_rate.date + timedelta(days=1)
            if start_date_obj > date.today():
                return

            if start_date_obj == date.today():
                url = f"http://api.frankfurter.dev/v1/{start_date_obj.isoformat()}?base={base_currency_code}"

            else:
                url = f"http://api.frankfurter.dev/v1/{start_date_obj.isoformat()}..{date.today().isoformat()}?base={base_currency_code}"

        response = requests.get(url, timeout=10)
        if response.status_code == 200:
            data = response.json()
            rates_data = data.get('rates', {})
            curriencies_in_erp = {c.symbol: c for c in Currency.objects.all()}

            is_range = isinstance(next(iter(rates_data.values())), dict) if rates_data else False

            if not is_range:
                target_date = data.get('date')
                for symbol, rate_value in rates_data.items():
                    if symbol in curriencies_in_erp:
                        ExchangeRate.objects.update_or_create(
                            currency = curriencies_in_erp[symbol],
                            date = target_date,
                            defaults= {'rate':rate_value}
                        )

                if base_currency_code in curriencies_in_erp:
                    ExchangeRate.objects.update_or_create(
                        currency = curriencies_in_erp[base_currency_code],
                        date = target_date,
                        defaults={'rate':1.0}
                    )

            else:
                for date_str, rates in rates_data.items():
                    for symbol, rate_value in rates.items():
                        if symbol in curriencies_in_erp:
                            ExchangeRate.objects.update_or_create(
                                currency=curriencies_in_erp[symbol],
                                date=date_str,
                                defaults={'rate':rate_value}
                            )
                if base_currency_code in curriencies_in_erp:
                    ExchangeRate.objects.update_or_create(
                        currency = curriencies_in_erp[base_currency_code],
                        date = date_str,
                        defaults={'rate':1.0}
                    )

    except Exception as e:
        print(f"Error updating exchange rates: {e}")