from django.urls import path
from . import views

urlpatterns = [
    # Web views (con sesiones)
    path('', views.home, name='home'),
    path('login/', views.login_view, name='login'),
    path('signup/', views.register_view, name='signup'),
    path('logout/', views.logout_view, name='logout'),
    
    # Catálogo y simulador
    path('catalog/', views.catalogo_vehiculos, name='catalog'),
    path('simulate/<int:vehiculo_id>/', views.simular_prestamo, name='simulate'),
    path('loan/<int:prestamo_id>/', views.detalle_prestamo, name='loan'),
    path('clients/', views.lista_clientes, name='clients'),
    
    # API endpoints (con JWT)
    path('api/login/', views.api_login, name='api_login'),
    path('api/register/', views.api_register, name='api_register'),
    path('api/refresh-token/', views.api_refresh_token, name='api_refresh_token'),
    path('api/me/', views.api_me, name='api_me'),
    path('api/logout/', views.api_logout, name='api_logout'),
]