from django.urls import path
from . import views

urlpatterns = [
    path('catalogo/', views.catalogo_vehiculos, name='catalogo'),
    path('simular/<int:vehiculo_id>/', views.simular_prestamo, name='simular'),
    path('prestamo/<int:prestamo_id>/', views.detalle_prestamo, name='detalle_prestamo'),
    path('clientes/', views.lista_clientes, name='clientes'),
]