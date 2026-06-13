from django.shortcuts import render, redirect, get_object_or_404
from datetime import date
from .models import Vehiculo, Prestamo, Usuario
from .engine import FinancialEngine, guardar_cronograma

def catalogo_vehiculos(request):
    vehiculos = Vehiculo.objects.all()
    return render(request, 'core/catalogo.html', {'vehiculos': vehiculos})

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

def lista_clientes(request):
    """Muestra la tabla de todos los clientes con préstamos"""
    prestamos = Prestamo.objects.all().order_by('-fecha_inicio')
    return render(request, 'core/clientes.html', {'prestamos': prestamos})