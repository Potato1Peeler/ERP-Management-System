from django.urls import path
from . import views

app_name = 'sales'

urlpatterns = [
    path('', views.sales_order_list, name='sales_order_list'),

    path('create/', views.sales_order_create,
         name='sales_order_create'),

    path('api/customer/details/<str:customer_id>/',
         views.get_customer_details,
         name='get_customer_details'),

    path('api/stock/',
         views.get_stock_data,
         name='get_stock_data'),
]