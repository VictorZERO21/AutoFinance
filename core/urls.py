from django.urls import path
from . import views

urlpatterns = [
    # Web views (con sesiones)
    path('', views.home, name='home'),
    path('login/', views.login_view, name='login'),
    path('register/', views.register_view, name='register'),
    path('logout/', views.logout_view, name='logout'),
    path('catalogo/', views.catalogo_vehiculos, name='catalogo'),
    path('simular/<int:vehiculo_id>/', views.simular_prestamo, name='simular'),
    path('prestamo/<int:prestamo_id>/', views.detalle_prestamo, name='detalle_prestamo'),
    path('clientes/', views.lista_clientes, name='clientes'),
    
    # API endpoints (con JWT)
    path('api/login/', views.api_login, name='api_login'),
    path('api/register/', views.api_register, name='api_register'),
    path('api/refresh-token/', views.api_refresh_token, name='api_refresh_token'),
    path('api/me/', views.api_me, name='api_me'),
    path('api/logout/', views.api_logout, name='api_logout'),
]