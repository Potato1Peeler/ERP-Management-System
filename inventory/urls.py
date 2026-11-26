from django.urls import path
from . import views

app_name = 'inventory'

urlpatterns = [
    path('movements/', views.movement_list, name='movement_list'),
    path('stock/', views.stock_list, name='stock_list'),
    path('movements/create/', views.create_movement, name='create_movement'),
]