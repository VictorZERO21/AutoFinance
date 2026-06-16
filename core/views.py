from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from datetime import date
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework_simplejwt.tokens import RefreshToken
from .models import Vehiculo, Prestamo, Usuario
from .engine import FinancialEngine, guardar_cronograma
from .serializers import LoginSerializer, CustomTokenObtainPairSerializer, UsuarioSerializer, RegisterSerializer

def login_view(request):
    """Vista de login"""
    if request.user.is_authenticated:
        return redirect('catalogo')
    
    if request.method == 'POST':
        email = request.POST.get('email')
        password = request.POST.get('password')
        
        try:
            # Buscar usuario por email
            user = Usuario.objects.get(email=email)
            # Autenticar con username (Django usa username por defecto)
            user = authenticate(request, username=user.username, password=password)
            
            if user is not None:
                login(request, user)
                return redirect('catalogo')
            else:
                messages.error(request, 'Email o contraseña incorrectos')
        except Usuario.DoesNotExist:
            messages.error(request, 'Email o contraseña incorrectos')
    
    return render(request, 'core/login.html')

def register_view(request):
    """Vista de registro - muestra el formulario de registro"""
    if request.user.is_authenticated:
        return redirect('catalogo')
    
    return render(request, 'core/register.html')

def logout_view(request):
    """Vista de logout - cierra sesión Django y redirige a login"""
    logout(request)
    return redirect('login')

# ============================================================================
# API VIEWS - JWT AUTHENTICATION
# ============================================================================

@api_view(['POST'])
@permission_classes([AllowAny])
def api_login(request):
    """
    Endpoint de login que retorna JWT tokens
    POST /api/login/
    {
        "email": "usuario@email.com",
        "password": "contraseña"
    }
    """
    serializer = LoginSerializer(data=request.data)
    if serializer.is_valid():
        user = serializer.validated_data['user']
        
        # Crear sesión Django (para web)
        login(request, user)
        
        # Crear tokens JWT (para API)
        refresh = RefreshToken.for_user(user)
        
        return Response({
            'access': str(refresh.access_token),
            'refresh': str(refresh),
            'usuario': {
                'id': user.id,
                'username': user.username,
                'email': user.email,
                'nombre_completo': user.nombre_completo,
                'dni': user.dni,
                'rol': user.rol,
                'is_staff': user.is_staff,
            }
        }, status=status.HTTP_200_OK)
    
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(['POST'])
@permission_classes([AllowAny])
def api_refresh_token(request):
    """
    Endpoint para refrescar el JWT access token
    POST /api/refresh-token/
    {
        "refresh": "token_de_refresh"
    }
    """
    refresh_token = request.data.get('refresh')
    
    if not refresh_token:
        return Response(
            {'error': 'Refresh token is required'},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    try:
        refresh = RefreshToken(refresh_token)
        return Response({
            'access': str(refresh.access_token),
        }, status=status.HTTP_200_OK)
    except Exception as e:
        return Response(
            {'error': 'Invalid refresh token'},
            status=status.HTTP_401_UNAUTHORIZED
        )


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def api_me(request):
    """
    Endpoint para obtener información del usuario autenticado
    GET /api/me/
    Headers: Authorization: Bearer <access_token>
    """
    serializer = UsuarioSerializer(request.user)
    return Response(serializer.data, status=status.HTTP_200_OK)


@api_view(['POST'])
@permission_classes([AllowAny])
def api_logout(request):
    """
    Endpoint para logout (invalida el refresh token)
    POST /api/logout/
    {
        "refresh": "token_de_refresh"
    }
    """
    refresh_token = request.data.get('refresh')
    
    if not refresh_token:
        return Response(
            {'error': 'Refresh token is required'},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    try:
        refresh = RefreshToken(refresh_token)
        refresh.blacklist()
        return Response(
            {'message': 'Successfully logged out'},
            status=status.HTTP_200_OK
        )
    except Exception as e:
        return Response(
            {'error': 'Invalid refresh token'},
            status=status.HTTP_400_BAD_REQUEST
        )


@api_view(['POST'])
@permission_classes([AllowAny])
def api_register(request):
    """
    Endpoint para registro de nuevos usuarios
    POST /api/register/
    {
        "email": "nuevo@email.com",
        "password": "contraseña",
        "password_confirm": "contraseña"
    }
    """
    serializer = RegisterSerializer(data=request.data)
    if serializer.is_valid():
        usuario = serializer.save()
        return Response({
            'message': 'Usuario registrado exitosamente',
            'usuario': {
                'id': usuario.id,
                'username': usuario.username,
                'email': usuario.email,
            }
        }, status=status.HTTP_201_CREATED)
    
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

def home(request):
    if request.user.is_authenticated:
        return redirect('catalogo')
    return redirect('login')

@login_required(login_url='login')
def catalogo_vehiculos(request):
    vehiculos = Vehiculo.objects.all()
    return render(request, 'core/catalogo.html', {'vehiculos': vehiculos})

@login_required(login_url='login')
def simular_prestamo(request, vehiculo_id):
    vehiculo = get_object_or_404(Vehiculo, id=vehiculo_id)
    
    if request.method == 'POST':
        # Instanciamos el motor
        motor = FinancialEngine(
            precio_bien=vehiculo.precio_base,
            cuota_inicial=request.POST.get('cuota_inicial'),
            cuota_balon_pct=request.POST.get('cuota_balon_pct'),
            tipo_tasa="EFECTIVA",
            valor_tasa=request.POST.get('valor_tasa'),
            plazo_meses=request.POST.get('plazo_meses'),
            tipo_gracia=request.POST.get('tipo_gracia', 'NINGUNA'),
            meses_gracia=request.POST.get('meses_gracia', 0),
            tasa_seguro_desgravamen=request.POST.get('tasa_desgravamen'),
            tasa_seguro_vehicular=request.POST.get('tasa_vehicular'),
            cok_anual=3.0, 
            fecha_inicio=date.today(),
            cuota_balon_base="PRECIO"
        )
        cronograma, indicadores = motor.procesar()
        
        # GUARDAMOS EN BASE DE DATOS
        vendedor = Usuario.objects.first() # Temporal: asume el primer usuario
        prestamo = Prestamo.objects.create(
            usuario=vendedor,
            vehiculo=vehiculo,
            moneda='USD',
            precio_bien=vehiculo.precio_base,
            cuota_inicial_monto=request.POST.get('cuota_inicial'),
            cuota_inicial_pct=20.0, # Valor por defecto seguro
            cuota_balon_pct=request.POST.get('cuota_balon_pct'),
            tipo_tasa="EFECTIVA",
            valor_tasa=request.POST.get('valor_tasa'),
            plazo_meses=request.POST.get('plazo_meses'),
            tipo_gracia=request.POST.get('tipo_gracia', 'NINGUNA'),
            meses_gracia=request.POST.get('meses_gracia', 0),
            tasa_seguro_desgravamen=request.POST.get('tasa_desgravamen'),
            tasa_seguro_vehicular=request.POST.get('tasa_vehicular'),
            cok=3.0,
            fecha_inicio=date.today()
        )
        guardar_cronograma(prestamo, cronograma)
        
        # TRANSPORTA A LA NUEVA PANTALLA
        return redirect('detalle_prestamo', prestamo_id=prestamo.id)

    return render(request, 'core/simulador.html', {'vehiculo': vehiculo})

@login_required(login_url='login')
def detalle_prestamo(request, prestamo_id):
    """Muestra el dashboard rojo con el cronograma del préstamo guardado"""
    prestamo = get_object_or_404(Prestamo, id=prestamo_id)
    # Recalculamos los indicadores para mostrarlos en la vista
    motor = FinancialEngine(
        precio_bien=prestamo.precio_bien, cuota_inicial=prestamo.cuota_inicial_monto,
        cuota_balon_pct=prestamo.cuota_balon_pct, tipo_tasa=prestamo.tipo_tasa,
        valor_tasa=prestamo.valor_tasa, plazo_meses=prestamo.plazo_meses,
        tipo_gracia=prestamo.tipo_gracia, meses_gracia=prestamo.meses_gracia,
        tasa_seguro_desgravamen=prestamo.tasa_seguro_desgravamen, tasa_seguro_vehicular=prestamo.tasa_seguro_vehicular,
        cok_anual=prestamo.cok, fecha_inicio=prestamo.fecha_inicio
    )
    _, indicadores = motor.procesar()
    
    return render(request, 'core/detalle.html', {
        'prestamo': prestamo,
        'cronograma': prestamo.cronograma.all(),
        'indicadores': indicadores
    })

@login_required(login_url='login')
def lista_clientes(request):
    """Muestra la tabla de todos los clientes con préstamos"""
    prestamos = Prestamo.objects.all().order_by('-fecha_inicio')
    return render(request, 'core/clientes.html', {'prestamos': prestamos})