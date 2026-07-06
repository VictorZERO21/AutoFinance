from datetime import date
import random
from io import BytesIO

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Q
from django.http import HttpResponse

from reportlab.lib.pagesizes import letter, A4
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, PageBreak
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT

from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework_simplejwt.tokens import RefreshToken

from .models import Vehiculo, Prestamo, Usuario
from .engine import FinancialEngine, guardar_cronograma
from .forms import SimuladorForm
from .serializers import LoginSerializer, CustomTokenObtainPairSerializer, UsuarioSerializer, RegisterSerializer


NOMBRES_CLIENTE = [
    "Carlos", "Ana", "Luis", "Mariana", "Jorge", "Sofia", "Ricardo", "Camila", "Martin", "Nicole",
    "Miguel", "Valeria", "Diego", "Lucia", "Fernando", "Daniela", "Andres", "Paola", "Renato", "Victor"
]

APELLIDOS_CLIENTE = [
    "Garcia", "Rodriguez", "Fernandez", "Lopez", "Martinez", "Sanchez", "Perez", "Gomez", "Gonzales", "Velarde",
    "Diaz", "Torres", "Ramirez", "Flores", "Vargas", "Castro", "Rojas", "Mendoza", "Torres", "Cruz", "Huamani", "Sanchez"
]


def crear_cliente_aleatorio() -> Usuario:
    """Crea un usuario cliente con nombre completo y DNI aleatorios."""
    nombre = random.choice(NOMBRES_CLIENTE)
    apellido = random.choice(APELLIDOS_CLIENTE)
    nombre_completo = f"{nombre} {apellido}"

    # Reintenta ante colisiones de DNI/username para garantizar unicidad.
    for _ in range(20):
        dni = f"{random.randint(0, 99999999):08d}"
        username = f"cliente_{dni}"

        if Usuario.objects.filter(dni=dni).exists():
            continue

        usuario = Usuario(
            username=username,
            email="",
            nombre_completo=nombre_completo,
            dni=dni,
            rol=Usuario.Rol.CLIENTE,
        )
        usuario.set_unusable_password()
        usuario.save()
        return usuario

    raise RuntimeError("No se pudo generar un cliente aleatorio unico")


# ============================================================================
# WEB VIEWS - LOGIN & REGISTER (HTML)
# ============================================================================

def login_view(request):
    """Vista de login"""
    if request.user.is_authenticated:
        return redirect('catalog')
    
    if request.method == 'POST':
        email = request.POST.get('email')
        password = request.POST.get('password')
        
        try:
            user = Usuario.objects.get(email=email)
            user = authenticate(request, username=user.username, password=password)
            
            if user is not None:
                login(request, user)
                return redirect('catalog')
            else:
                messages.error(request, 'Email o contraseña incorrectos')
        except Usuario.DoesNotExist:
            messages.error(request, 'Email o contraseña incorrectos')
    
    return render(request, 'core/login.html')


def register_view(request):
    """Vista de registro - muestra el formulario de registro"""
    if request.user.is_authenticated:
        return redirect('catalog')
    
    return render(request, 'core/register.html')


def logout_view(request):
    """Vista de logout - cierra sesión Django y redirige a login"""
    logout(request)
    return redirect('login')


def home(request):
    """Redirige a catálogo si está autenticado, sino a login"""
    if request.user.is_authenticated:
        return redirect('catalog')
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
            cliente = crear_cliente_aleatorio()

            prestamo = Prestamo.objects.create(
                usuario=cliente,
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

            return redirect('loan', prestamo_id=prestamo.id)

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
def exportar_cronograma_pdf(request, prestamo_id):
    """Genera y descarga el cronograma como PDF"""
    prestamo = get_object_or_404(Prestamo, id=prestamo_id)
    cronograma = prestamo.cronograma.all().order_by('nro_cuota')
    
    # Crear el PDF en memoria
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter, rightMargin=0.5*inch, leftMargin=0.5*inch,
                           topMargin=0.5*inch, bottomMargin=0.5*inch)
    
    # Estilos
    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Heading1'],
        fontSize=16,
        textColor=colors.HexColor('#5a1829'),
        spaceAfter=12,
        alignment=TA_CENTER,
        fontName='Helvetica-Bold'
    )
    
    heading_style = ParagraphStyle(
        'CustomHeading',
        parent=styles['Heading2'],
        fontSize=11,
        textColor=colors.HexColor('#5a1829'),
        spaceAfter=8,
        fontName='Helvetica-Bold'
    )
    
    normal_style = styles['Normal']
    normal_style.fontSize = 9
    normal_style.alignment = TA_LEFT
    
    # Contenido
    elementos = []
    
    # Título
    elementos.append(Paragraph("CRONOGRAMA DE PAGOS", title_style))
    elementos.append(Spacer(1, 0.2*inch))
    
    # Información del préstamo
    info_text = f"""
    <b>Cliente:</b> {prestamo.usuario.nombre_completo} (DNI: {prestamo.usuario.dni})<br/>
    <b>Vehículo:</b> {prestamo.vehiculo.anio} {prestamo.vehiculo.marca} {prestamo.vehiculo.modelo}<br/>
    <b>Precio del Bien:</b> USD {prestamo.precio_bien:,.2f}<br/>
    <b>Cuota Inicial:</b> USD {prestamo.cuota_inicial_monto:,.2f} ({prestamo.cuota_inicial_pct}%)<br/>
    <b>Importe Financiado:</b> USD {prestamo.importe_financiado:,.2f}<br/>
    <b>Tasa de Interés:</b> {prestamo.valor_tasa}% ({prestamo.tipo_tasa})<br/>
    <b>Plazo:</b> {prestamo.plazo_meses} meses<br/>
    <b>Fecha de Inicio:</b> {prestamo.fecha_inicio.strftime('%d/%m/%Y')}<br/>
    <b>Estado:</b> {prestamo.get_estado_display()}
    """
    elementos.append(Paragraph(info_text, normal_style))
    elementos.append(Spacer(1, 0.2*inch))
    
    # Tabla del cronograma
    elementos.append(Paragraph("DETALLE DEL CRONOGRAMA", heading_style))
    
    # Preparar datos para la tabla
    datos_tabla = [
        ['Cuota', 'Fecha', 'Tipo', 'Saldo Inicial', 'Interés', 'Amortización', 
         'Desgravamen', 'Seguro', 'Cuota Total', 'Saldo Final']
    ]
    
    for fila in cronograma:
        tipo_display = dict(Prestamo.Cronograma.TipoPeriodo.choices).get(fila.tipo_periodo, fila.tipo_periodo) if hasattr(Prestamo, 'Cronograma') else fila.tipo_periodo
        # Si el modelo está bien estructurado, usamos el nombre corto del tipo
        tipo_corto = {
            'GRACIA_TOTAL': 'G.Total',
            'GRACIA_PARCIAL': 'G.Parc',
            'ORDINARIO': 'Ord',
            'CUOTA_BALON': 'Balón'
        }.get(fila.tipo_periodo, fila.tipo_periodo[:3])
        
        datos_tabla.append([
            str(fila.nro_cuota),
            fila.fecha_vencimiento.strftime('%d/%m/%Y'),
            tipo_corto,
            f"${fila.saldo_inicial:,.2f}",
            f"${fila.interes:,.2f}",
            f"${fila.amortizacion:,.2f}",
            f"${fila.seguro_desgravamen:,.2f}",
            f"${fila.seguro_vehicular:,.2f}",
            f"${fila.cuota_total:,.2f}",
            f"${fila.saldo_final:,.2f}",
        ])
    
    # Crear tabla con estilos
    tabla = Table(datos_tabla, colWidths=[0.5*inch, 0.65*inch, 0.5*inch, 0.7*inch, 
                                          0.6*inch, 0.65*inch, 0.65*inch, 0.6*inch, 
                                          0.65*inch, 0.65*inch])
    
    tabla.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#5a1829')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 8),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 8),
        ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
        ('GRID', (0, 0), (-1, -1), 1, colors.grey),
        ('FONTSIZE', (0, 1), (-1, -1), 7),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#f5f5f5')]),
    ]))
    
    elementos.append(tabla)
    
    # Construcción del PDF
    doc.build(elementos)
    
    # Preparar respuesta
    buffer.seek(0)
    response = HttpResponse(buffer.getvalue(), content_type='application/pdf')
    filename = f"cronograma_prestamo_{prestamo.id}_{prestamo.usuario.dni}.pdf"
    response['Content-Disposition'] = f'attachment; filename="{filename}"'
    
    return response


def _score_riesgo_cumplimiento(prestamo):
    """Calcula un score simple de riesgo de cumplimiento en escala 0-100."""
    cuota_inicial_pct = float(prestamo.cuota_inicial_pct or 0)
    valor_tasa = float(prestamo.valor_tasa or 0)
    plazo_meses = int(prestamo.plazo_meses or 12)
    meses_gracia = int(prestamo.meses_gracia or 0)
    cuota_balon_pct = float(prestamo.cuota_balon_pct or 0)

    riesgo_plazo = min(max((plazo_meses - 12) / 60, 0), 1) * 25
    riesgo_tasa = min(max(valor_tasa / 30, 0), 1) * 25
    riesgo_inicial = min(max((40 - cuota_inicial_pct) / 40, 0), 1) * 20
    riesgo_gracia = min(max(meses_gracia / 12, 0), 1) * 15
    riesgo_balon = min(max(cuota_balon_pct / 30, 0), 1) * 15

    score = riesgo_plazo + riesgo_tasa + riesgo_inicial + riesgo_gracia + riesgo_balon
    return round(min(score, 100), 1)


@login_required(login_url='login')
def lista_clientes(request):
    """Muestra la tabla de préstamos y un resumen de riesgo de cumplimiento."""
    busqueda = request.GET.get('q', '').strip()
    estado = request.GET.get('estado', '').strip()
    fecha_desde = request.GET.get('fecha_desde', '').strip()
    fecha_hasta = request.GET.get('fecha_hasta', '').strip()

    prestamos_qs = Prestamo.objects.select_related('usuario', 'vehiculo').all()

    if busqueda:
        prestamos_qs = prestamos_qs.filter(
            Q(usuario__nombre_completo__icontains=busqueda)
            | Q(usuario__dni__icontains=busqueda)
            | Q(usuario__email__icontains=busqueda)
            | Q(vehiculo__marca__icontains=busqueda)
            | Q(vehiculo__modelo__icontains=busqueda)
        )

    if estado and estado != 'TODOS':
        prestamos_qs = prestamos_qs.filter(estado=estado)

    if fecha_desde:
        prestamos_qs = prestamos_qs.filter(fecha_inicio__gte=fecha_desde)

    if fecha_hasta:
        prestamos_qs = prestamos_qs.filter(fecha_inicio__lte=fecha_hasta)

    prestamos = list(prestamos_qs.order_by('-fecha_inicio'))

    estadisticas_riesgo = []
    for prestamo in prestamos:
        score = _score_riesgo_cumplimiento(prestamo)
        estadisticas_riesgo.append({
            'prestamo': prestamo,
            'score': score,
        })

    estadisticas_riesgo.sort(key=lambda item: item['score'], reverse=True)
    top_riesgo = estadisticas_riesgo[0] if estadisticas_riesgo else None
    promedio_riesgo = round(
        sum(item['score'] for item in estadisticas_riesgo) / len(estadisticas_riesgo), 1
    ) if estadisticas_riesgo else 0

    return render(request, 'core/clientes.html', {
        'prestamos': prestamos,
        'top_riesgo': top_riesgo,
        'ranking_riesgo': estadisticas_riesgo[:5],
        'promedio_riesgo': promedio_riesgo,
        'total_clientes_riesgo': len(estadisticas_riesgo),
        'filtros': {
            'q': busqueda,
            'estado': estado or 'TODOS',
            'fecha_desde': fecha_desde,
            'fecha_hasta': fecha_hasta,
        },
        'estados_prestamo': Prestamo.Estado.choices,
    })
