from datetime import date

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.contrib import messages

from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework_simplejwt.tokens import RefreshToken

from .models import Vehiculo, Prestamo, Usuario
from .engine import FinancialEngine, guardar_cronograma
from .forms import SimuladorForm
from .serializers import LoginSerializer, CustomTokenObtainPairSerializer, UsuarioSerializer, RegisterSerializer


# ============================================================================
# WEB VIEWS - LOGIN & REGISTER (HTML)
# ============================================================================

def login_view(request):
    """Vista de login"""
    if request.user.is_authenticated:
        return redirect('catalogo')
    
    if request.method == 'POST':
        email = request.POST.get('email')
        password = request.POST.get('password')
        
        try:
            user = Usuario.objects.get(email=email)
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


def home(request):
    """Redirige a catálogo si está autenticado, sino a login"""
    if request.user.is_authenticated:
        return redirect('catalogo')
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


# ============================================================================
# WEB VIEWS - CATALOGO & SIMULADOR
# ============================================================================

@login_required(login_url='login')
def catalogo_vehiculos(request):
    """Lista de vehículos disponibles para financiar"""
    vehiculos = Vehiculo.objects.all()
    return render(request, 'core/catalogo.html', {'vehiculos': vehiculos})


@login_required(login_url='login')
def simular_prestamo(request, vehiculo_id):
    """Simulador de préstamo con formulario"""
    vehiculo = get_object_or_404(Vehiculo, id=vehiculo_id)

    if request.method == 'POST':
        form = SimuladorForm(request.POST)
        if form.is_valid():
            cd = form.cleaned_data

            # ── Precio del bien (ahora editable en el formulario) ─────────
            precio_bien = cd['precio_bien']

            # ── Cuota inicial: convertir % → monto ────────────────────────
            ci_pct   = cd['cuota_inicial_pct']
            ci_monto = precio_bien * ci_pct / 100

            # ── Gracia ────────────────────────────────────────────────────
            if cd['desea_gracia'] == 'SI':
                tipo_gracia  = cd['tipo_gracia']
                meses_gracia = cd['meses_gracia'] or 0
            else:
                tipo_gracia  = 'NINGUNA'
                meses_gracia = 0

            # ── Tasas de seguros (predefinidas o "Otro") ──────────────────
            if cd['tasa_desgravamen'] == 'OTRO':
                tasa_desgravamen = float(cd['tasa_desgravamen_custom'])
            else:
                tasa_desgravamen = float(cd['tasa_desgravamen'])

            if cd['tasa_vehicular'] == 'OTRO':
                tasa_vehicular = float(cd['tasa_vehicular_custom'])
            else:
                tasa_vehicular = float(cd['tasa_vehicular'])

            # ── Fecha de inicio (date object del form) ────────────────────
            fecha_inicio = cd['fecha_inicio']

            # ── Motor financiero ──────────────────────────────────────────
            motor = FinancialEngine(
                precio_bien=precio_bien,
                cuota_inicial=ci_monto,
                cuota_balon_pct=cd['cuota_balon_pct'],
                tipo_tasa="EFECTIVA",
                valor_tasa=cd['valor_tasa'],
                plazo_meses=int(cd['plazo_meses']),
                tipo_gracia=tipo_gracia,
                meses_gracia=meses_gracia,
                tasa_seguro_desgravamen=tasa_desgravamen,
                tasa_seguro_vehicular=tasa_vehicular,
                cok_anual=float(cd['cok']),
                fecha_inicio=fecha_inicio,
                cuota_balon_base="PRECIO",
            )
            cronograma, _ = motor.procesar()

            # ── Persistencia ──────────────────────────────────────────────
            vendedor = (
                Usuario.objects.filter(username="vendedor_demo").first()
                or Usuario.objects.first()
            )

            prestamo = Prestamo.objects.create(
                usuario=vendedor,
                vehiculo=vehiculo,
                moneda='USD',
                precio_bien=precio_bien,
                cuota_inicial_monto=ci_monto,
                cuota_inicial_pct=ci_pct,
                cuota_balon_pct=cd['cuota_balon_pct'],
                tipo_tasa="EFECTIVA",
                valor_tasa=cd['valor_tasa'],
                plazo_meses=int(cd['plazo_meses']),
                tipo_gracia=tipo_gracia,
                meses_gracia=meses_gracia,
                tasa_seguro_desgravamen=tasa_desgravamen,
                tasa_seguro_vehicular=tasa_vehicular,
                cok=cd['cok'],
                fecha_inicio=fecha_inicio,
            )
            guardar_cronograma(prestamo, cronograma)

            return redirect('detalle_prestamo', prestamo_id=prestamo.id)

    else:
        # El precio del bien se pre-rellena con el precio del catálogo
        form = SimuladorForm(initial={'precio_bien': vehiculo.precio_base})

    # Valor ISO de la fecha para pre-rellenar el date picker
    if request.method == 'POST':
        fecha_inicio_val = request.POST.get('fecha_inicio', date.today().isoformat())
    else:
        fecha_inicio_val = date.today().isoformat()

    return render(request, 'core/simulador.html', {
        'vehiculo': vehiculo,
        'form': form,
        'fecha_inicio_val': fecha_inicio_val,
    })


@login_required(login_url='login')
def detalle_prestamo(request, prestamo_id):
    """Muestra el dashboard del préstamo con cronograma"""
    prestamo = get_object_or_404(Prestamo, id=prestamo_id)
    motor = FinancialEngine(
        precio_bien=prestamo.precio_bien,
        cuota_inicial=prestamo.cuota_inicial_monto,
        cuota_balon_pct=prestamo.cuota_balon_pct,
        tipo_tasa=prestamo.tipo_tasa,
        valor_tasa=prestamo.valor_tasa,
        plazo_meses=prestamo.plazo_meses,
        tipo_gracia=prestamo.tipo_gracia,
        meses_gracia=prestamo.meses_gracia,
        tasa_seguro_desgravamen=prestamo.tasa_seguro_desgravamen,
        tasa_seguro_vehicular=prestamo.tasa_seguro_vehicular,
        cok_anual=prestamo.cok,
        fecha_inicio=prestamo.fecha_inicio,
    )
    _, indicadores = motor.procesar()

    return render(request, 'core/detalle.html', {
        'prestamo': prestamo,
        'cronograma': prestamo.cronograma.all(),
        'indicadores': indicadores,
    })


@login_required(login_url='login')
def lista_clientes(request):
    """Muestra la tabla de todos los préstamos"""
    prestamos = Prestamo.objects.all().order_by('-fecha_inicio')
    return render(request, 'core/clientes.html', {'prestamos': prestamos})
