from datetime import date

from django.shortcuts import render, redirect, get_object_or_404

from .engine import FinancialEngine, guardar_cronograma
from .forms import SimuladorForm
from .models import Vehiculo, Prestamo, Usuario


def catalogo_vehiculos(request):
    vehiculos = Vehiculo.objects.all()
    return render(request, 'core/catalogo.html', {'vehiculos': vehiculos})


def simular_prestamo(request, vehiculo_id):
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

    # Valor ISO de la fecha para pre-rellenar el date picker sin depender de filtros de template
    if request.method == 'POST':
        fecha_inicio_val = request.POST.get('fecha_inicio', date.today().isoformat())
    else:
        fecha_inicio_val = date.today().isoformat()

    return render(request, 'core/simulador.html', {
        'vehiculo': vehiculo,
        'form': form,
        'fecha_inicio_val': fecha_inicio_val,
    })


def detalle_prestamo(request, prestamo_id):
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


def lista_clientes(request):
    prestamos = Prestamo.objects.all().order_by('-fecha_inicio')
    return render(request, 'core/clientes.html', {'prestamos': prestamos})
