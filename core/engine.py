"""
engine.py — Motor financiero de AutoFinance.

Implementa el plan de pagos del metodo "Compra Inteligente"
(Frances Vencido Ordinario, base 30/360) para credito vehicular en Peru.

Caracteristicas:
    - Tasa Efectiva Anual (TEA) o Tasa Nominal Anual (TNA) -> Tasa Efectiva Mensual (TEM).
    - Periodos de gracia: Total, Parcial o Ninguna.
    - Cuota Balon (Valor Futuro Minimo Garantizado).
    - Seguro de desgravamen mensual sobre el saldo inicial de cada mes.
    - Seguro vehicular sobre el precio del bien (monto fijo).
    - Indicadores SBS: TCEA, TIR mensual y VAN.

Dependencias:
    pip install numpy-financial

================================================================================
DOS DECISIONES DE MODELADO (prompt vs. mockups)
================================================================================
1) CUOTA BALON
   - Por defecto: cuota_balon_base="PRECIO"  (20% x precio = balon).
     Use cuota_balon_base="FINANCIADO" para basar el balon en el importe prestado.

2) SEGURO VEHICULAR
   - La tasa ingresada es siempre ANUAL; se divide entre 12 para el monto mensual.
     Formula: (precio_bien * tasa_anual) / 12.

================================================================================
ARQUITECTURA DE CALCULO: PMT DINAMICO + FLUJO REAL
================================================================================
PROBLEMA RESUELTO:
  El motor anterior usaba una CUOTA_BASE_UNIFICADA calculada una sola vez antes
  del bucle ordinario. Eso diverge de Excel porque:
    a) El saldo post-gracia acumula error de punto flotante.
    b) El redondeo de esa constante unica difiere del redondeo de Excel fila a fila.

SOLUCION: PMT dinamico por periodo
  En cada iteracion ordinaria se llama a npf.pmt(tasa_pmt, n_rest, saldo, -vf).
  Esto replica exactamente la funcion PAGO() de Excel (IEEE 754 double), y ademas
  es autocorrectivo: cualquier deriva de centimo en el saldo queda absorbida por
  el PMT del siguiente periodo.

  tasa_pmt = TEP + tasa_desgravamen  (tasa compuesta, misma que usa Excel)
  n_rest   = n_ord - j + 1           (periodos restantes incluyendo el actual)

FLUJO REAL PARA VAN/TIR:
  En Gracia Total la cuota_total es 0 (convencion contable), pero el deudor
  IGUALMENTE paga desgravamen + seguro vehicular. El campo flujo_caja_periodo
  captura ese desembolso real para alimentar npf.irr / npf.npv con precision.

PRECISION: MODELO DE DOBLE CAPA
  - PMT calculado en float IEEE 754 (= Excel). Convertido a Decimal via str().
  - Toda la aritmetica del periodo (interes, amort, saldo) en Decimal puro.
  - Sin ningun round() dentro del bucle.
  - redondear_excel() (ROUND_HALF_UP) SOLO en _fila() al escribir el dict.
"""
from __future__ import annotations

import calendar
from datetime import date
from decimal import Decimal, ROUND_HALF_UP

import numpy_financial as npf


# ---------------------------------------------------------------------------
# Redondeo compatible con Excel (ROUND_HALF_UP)
# ---------------------------------------------------------------------------
def redondear_excel(valor) -> Decimal:
    """Convierte `valor` a Decimal y redondea a 2 decimales con ROUND_HALF_UP.

    Normaliza -0.00 a 0.00 (artefacto de la ultima cuota cuando el saldo
    residual es un epsilon negativo infinitesimal).
    """
    result = Decimal(str(valor)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    return Decimal("0.00") if result == 0 else result


def _sumar_meses(fecha: date, meses: int) -> date:
    """Suma `meses` calendario a una fecha respetando el fin de mes."""
    indice = fecha.month - 1 + meses
    anio = fecha.year + indice // 12
    mes = indice % 12 + 1
    dia = min(fecha.day, calendar.monthrange(anio, mes)[1])
    return date(anio, mes, dia)


class FinancialEngine:
    """Genera el cronograma de pagos y los indicadores financieros."""

    GRACIA_TOTAL   = "GRACIA_TOTAL"
    GRACIA_PARCIAL = "GRACIA_PARCIAL"
    ORDINARIO      = "ORDINARIO"
    CUOTA_BALON    = "CUOTA_BALON"

    def __init__(
        self,
        precio_bien,
        cuota_inicial,
        cuota_balon_pct,
        tipo_tasa,                 # "EFECTIVA" | "NOMINAL"
        valor_tasa,                # en porcentaje, ej. 8.80
        plazo_meses,
        tipo_gracia,               # "TOTAL" | "PARCIAL" | "NINGUNA"
        meses_gracia,
        tasa_seguro_desgravamen,   # % mensual, ej. 0.077
        tasa_seguro_vehicular,     # %, ej. 0.4050
        cok_anual,                 # % anual, ej. 10
        fecha_inicio,              # datetime.date
        cuota_balon_base="PRECIO",         # "PRECIO" | "FINANCIADO"
        seguro_vehicular_es_anual=False,   # True -> tasa/12
        capitalizaciones_nominal=12,       # solo si tipo_tasa = "NOMINAL"
    ):
        self.precio_bien           = Decimal(str(precio_bien))
        self.cuota_inicial         = Decimal(str(cuota_inicial))
        self.cuota_balon_pct       = Decimal(str(cuota_balon_pct)) / Decimal("100")
        self.tipo_tasa             = str(tipo_tasa).upper()
        self.valor_tasa            = Decimal(str(valor_tasa)) / Decimal("100")
        self.plazo_meses           = int(plazo_meses)
        self.tipo_gracia           = str(tipo_gracia or "NINGUNA").upper()
        self.meses_gracia          = int(meses_gracia or 0)
        self.tasa_desgravamen      = Decimal(str(tasa_seguro_desgravamen)) / Decimal("100")
        self.tasa_seguro_vehicular = Decimal(str(tasa_seguro_vehicular)) / Decimal("100")
        self.cok_anual             = Decimal(str(cok_anual)) / Decimal("100")
        self.fecha_inicio          = fecha_inicio
        self.cuota_balon_base      = str(cuota_balon_base).upper()
        self.seguro_vehicular_es_anual = bool(seguro_vehicular_es_anual)
        self.m_nominal             = int(capitalizaciones_nominal)

        self.importe_financiado = self.precio_bien - self.cuota_inicial

        if self.tipo_gracia == "NINGUNA":
            self.meses_gracia = 0

    # ------------------------------------------------------------------ #
    # Conversiones de tasa
    # ------------------------------------------------------------------ #
    def tem(self) -> Decimal:
        """Tasa Efectiva Mensual.

        La potencia fraccional (^1/12) se calcula en float IEEE 754 y se
        convierte a Decimal via str() para preservar todos los digitos
        significativos sin artefactos de la representacion binaria interna.
        """
        if self.tipo_tasa == "EFECTIVA":
            tem_float = (1 + float(self.valor_tasa)) ** (1 / 12) - 1
            return Decimal(str(tem_float))
        return self.valor_tasa / self.m_nominal

    def cok_mensual(self) -> Decimal:
        """COK efectivo mensual (TDP) para descontar el VAN."""
        cok_float = (1 + float(self.cok_anual)) ** (1 / 12) - 1
        return Decimal(str(cok_float))

    # ------------------------------------------------------------------ #
    # Componentes auxiliares
    # ------------------------------------------------------------------ #
    def _monto_balon(self) -> Decimal:
        base = self.precio_bien if self.cuota_balon_base == "PRECIO" else self.importe_financiado
        return base * self.cuota_balon_pct

    def _seguro_vehicular_mensual(self) -> Decimal:
        # Tasa siempre anual → cuotas_por_año = 360/30 = 12
        return (self.tasa_seguro_vehicular * self.precio_bien) / Decimal("12")

    # ------------------------------------------------------------------ #
    # Cronograma
    # ------------------------------------------------------------------ #
    def generar_cronograma(self) -> list[dict]:
        """Devuelve el cronograma completo como lista de diccionarios.

        Cada fila incluye 'flujo_caja_periodo': el desembolso real del deudor
        para ese mes. Difiere de 'cuota_total' en Gracia Total, donde la cuota
        contable es 0 pero el deudor efectivamente paga desgravamen + seg.veh.
        """
        i       = self.tem()
        vf      = self._monto_balon()
        seg_veh = self._seguro_vehicular_mensual()
        tasa_dg = self.tasa_desgravamen

        # Tasa compuesta para PMT = TEP + desgravamen (replica PAGO() de Excel)
        tasa_pmt_f = float(i) + float(tasa_dg)
        vf_f       = float(vf)
        n_ord      = self.plazo_meses - self.meses_gracia

        filas: list[dict] = []
        saldo = self.importe_financiado   # Decimal puro; NUNCA se redondea

        D0 = Decimal("0")

        # ── Fase de Gracia ───────────────────────────────────────────────
        for k in range(1, self.meses_gracia + 1):
            interes     = saldo * i
            desgravamen = saldo * tasa_dg

            if self.tipo_gracia == "TOTAL":
                # Cuota contable = 0. Solo el interes capitaliza al saldo.
                # Flujo real: el deudor paga desgravamen + seguro vehicular
                # (no capitalizan; salen de su bolsillo y forman parte del VAN).
                cuota_base   = D0
                amortizacion = D0
                saldo_final  = saldo + interes
                cuota_total  = D0
                flujo        = desgravamen + seg_veh
                tipo         = self.GRACIA_TOTAL
            else:  # PARCIAL
                cuota_base   = interes
                amortizacion = D0
                saldo_final  = saldo
                cuota_total  = cuota_base + desgravamen + seg_veh
                flujo        = cuota_total
                tipo         = self.GRACIA_PARCIAL

            filas.append(self._fila(
                k, tipo, interes, amortizacion, desgravamen,
                seg_veh, cuota_total, flujo, saldo, saldo_final, cuota_base,
            ))
            saldo = saldo_final

        # ── Fase Ordinaria: PMT dinamico en cada periodo ──────────────────
        #
        # Por que dinamico en vez de constante?
        #   npf.pmt(tasa_pmt_f, n_rest, saldo, -vf) reproduce exactamente
        #   la celda PAGO() de Excel. Al recalcular con el saldo real de cada
        #   periodo, cualquier centimo de deriva queda absorbido automaticamente,
        #   y la cuota converge a la que Excel mostraria en esa misma celda.
        for j in range(1, n_ord + 1):
            k        = self.meses_gracia + j
            n_rest   = n_ord - j + 1        # periodos restantes incluyendo este
            es_balon = (j == n_ord) and (vf > D0)

            # PMT en IEEE 754 float (identico a Excel PAGO).
            # npf.pmt devuelve negativo (desembolso); negamos -> positivo.
            # fv = -vf: al final de n_rest periodos el saldo residual es vf
            # (se amortiza hasta vf, luego se paga el balon por separado).
            if tasa_pmt_f != 0 and n_rest > 0:
                cuota_pmt_f = -float(npf.pmt(tasa_pmt_f, n_rest, float(saldo), -vf_f))
            else:
                cuota_pmt_f = (float(saldo) - vf_f) / max(n_rest, 1)

            # Aritmetica del periodo en Decimal puro (sin redondeo intermedio)
            cuota_base_raw = Decimal(str(cuota_pmt_f))
            interes        = saldo * i
            desgravamen    = saldo * tasa_dg
            amortizacion   = cuota_base_raw - interes - desgravamen
            saldo_final    = saldo - amortizacion

            if es_balon:
                # El deudor paga la cuota ordinaria + el globo residual.
                # Matematicamente saldo_final ≈ vf antes de este bloque;
                # restar vf cierra el saldo en 0.00.
                cuota_total = cuota_base_raw + seg_veh + vf
                saldo_final = saldo_final - vf
                tipo        = self.CUOTA_BALON
            else:
                cuota_total = cuota_base_raw + seg_veh
                tipo        = self.ORDINARIO

            flujo = cuota_total

            filas.append(self._fila(
                k, tipo, interes, amortizacion, desgravamen,
                seg_veh, cuota_total, flujo, saldo, saldo_final, cuota_base_raw,
            ))
            saldo = saldo_final

        return filas

    def _fila(
        self, nro, tipo, interes, amort, desg, seg_veh,
        cuota, flujo, saldo_ini, saldo_fin, cb_ex,
    ) -> dict:
        """Aplica ROUND_HALF_UP UNICAMENTE aqui, al escribir el dict de salida."""
        R = redondear_excel
        return {
            "nro_cuota":          nro,
            "tipo_periodo":       tipo,
            "fecha_vencimiento":  _sumar_meses(self.fecha_inicio, nro),
            "saldo_inicial":      R(saldo_ini),
            "interes":            R(interes),
            "amortizacion":       R(amort),
            "cuota_base":         R(cb_ex),
            "seguro_desgravamen": R(desg),
            "seguro_vehicular":   R(seg_veh),
            "cuota_total":        R(cuota),
            "flujo_caja_periodo": R(flujo),   # desembolso real para VAN/TIR
            "saldo_final":        R(saldo_fin),
        }

    # ------------------------------------------------------------------ #
    # Indicadores SBS
    # ------------------------------------------------------------------ #
    def calcular_indicadores(self, cronograma: list[dict]) -> dict:
        """Calcula importe financiado, cuota ordinaria, TCEA, TIR mensual y VAN.

        CONVENCION DE SIGNOS (replica Celda T26 del Excel del usuario):
        ┌─────────────────────────────────────────────────────────────────┐
        │  t = 0  :  +importe_financiado  (dinero QUE RECIBE el deudor)  │
        │  t > 0  :  -desembolso_real     (dinero QUE PAGA el deudor)    │
        │                                                                 │
        │  desembolso_real = cuota_base + seg_desgravamen + seg_vehicular │
        │                    [+ balon en el periodo balón]                │
        │                                                                 │
        │  GRACIA TOTAL: cuota contable = 0, pero desembolso_real > 0    │
        │  porque el deudor sí paga desgravamen + seguro vehicular.      │
        │  Por eso se usa flujo_caja_periodo (no cuota_total).           │
        └─────────────────────────────────────────────────────────────────┘

        NOTA SOBRE EL VAN:
        La formula Excel del usuario es:  prestamo + VNA(TDP, pagos_negativos)
        Excel VNA descuenta desde el periodo 1:
            VNA_excel(r, [-f1, ..., -fN]) = -f1/(1+r)^1 + ... + -fN/(1+r)^N

        numpy_financial.npv descuenta desde el periodo 0 (no el 1), por lo que
        npf.npv(r, [-f1,...,-fN]) != Excel_VNA(r, [-f1,...,-fN]).
        El equivalente CORRECTO de 'prestamo + VNA_excel(TDP, pagos)' en numpy es:
            npf.npv(TDP, [+prestamo, -f1, ..., -fN])
        Esto garantiza que f1 se descuenta en (1+TDP)^1, no en (1+TDP)^0.
        """
        # ── t=0: dinero que el banco entrega al deudor (POSITIVO) ────────
        flujo_t0 = float(self.importe_financiado)

        # ── t=1..N: desembolsos reales del deudor (ESTRICTAMENTE NEGATIVOS)
        # -abs() garantiza el signo correcto aunque flujo_caja_periodo
        # llegara con signo incorrecto por un bug futuro.
        flujos_periodos = [
            -abs(float(f["flujo_caja_periodo"])) for f in cronograma
        ]

        # Array completo [+prestamo, -pago_1, -pago_2, ..., -pago_N]
        flujo_van = [flujo_t0] + flujos_periodos

        try:
            tir_mensual = float(npf.irr(flujo_van))
        except Exception:
            tir_mensual = float("nan")

        # TCEA base 30/360: (1 + TIR_mensual)^(360/30) - 1
        tcea = (1 + tir_mensual) ** (360 / 30) - 1

        # TDP = COK efectivo mensual base 30/360  = (1+COK_anual)^(30/360) - 1
        tdp = float(self.cok_mensual())

        # VAN = prestamo + VNA(TDP, pagos_negativos)
        # Implementado como npf.npv del array completo:
        #   npf.npv(TDP, [p, -f1, ..., -fN])
        #   = p + (-f1)/(1+TDP)^1 + ... + (-fN)/(1+TDP)^N   [correcto]
        van = float(npf.npv(tdp, flujo_van))

        ordinarias = [
            f["cuota_total"]
            for f in cronograma
            if f["tipo_periodo"] in (self.ORDINARIO, self.CUOTA_BALON)
        ]
        cuota_ordinaria = ordinarias[0] if ordinarias else Decimal("0")

        bases_ord = [
            f["cuota_base"]
            for f in cronograma
            if f["tipo_periodo"] == self.ORDINARIO
        ]
        cuota_base_ordinaria = bases_ord[0] if bases_ord else Decimal("0")

        return {
            "importe_financiado":   redondear_excel(self.importe_financiado),
            "cuota_ordinaria":      cuota_ordinaria,       # con seguro veh.
            "cuota_base_ordinaria": cuota_base_ordinaria,  # sin seguro veh.
            "duracion_meses":       self.plazo_meses,
            "tem":                  round(float(self.tem()), 8),
            "tcea":                 round(tcea, 6),
            "tcea_pct":             round(tcea * 100, 4),
            "tir_mensual":          round(tir_mensual, 6),
            "tir_mensual_pct":      round(tir_mensual * 100, 4),
            "van":                  redondear_excel(van),
            "flujo_caja":           [round(x, 2) for x in flujo_van],
        }

    # ------------------------------------------------------------------ #
    # Punto de entrada
    # ------------------------------------------------------------------ #
    def procesar(self) -> tuple[list[dict], dict]:
        """Devuelve (cronograma, indicadores)."""
        cronograma  = self.generar_cronograma()
        indicadores = self.calcular_indicadores(cronograma)
        return cronograma, indicadores


# ---------------------------------------------------------------------------
# Integracion con Django
# ---------------------------------------------------------------------------
def engine_desde_prestamo(prestamo) -> FinancialEngine:
    """Crea un FinancialEngine a partir de una instancia del modelo Prestamo."""
    return FinancialEngine(
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


def guardar_cronograma(prestamo, cronograma: list[dict]):
    """
    Persiste el cronograma en la BD (modelo Cronograma).
    Reemplaza cualquier cronograma previo del prestamo.
    Los valores son Decimal (ROUND_HALF_UP), compatibles con DecimalField.
    flujo_caja_periodo es un campo de calculo; no se persiste en la BD.
    """
    from .models import Cronograma  # import diferido para evitar ciclos

    Cronograma.objects.filter(prestamo=prestamo).delete()
    objetos = [
        Cronograma(
            prestamo=prestamo,
            nro_cuota=f["nro_cuota"],
            tipo_periodo=f["tipo_periodo"],
            fecha_vencimiento=f["fecha_vencimiento"],
            saldo_inicial=f["saldo_inicial"],
            interes=f["interes"],
            amortizacion=f["amortizacion"],
            seguro_desgravamen=f["seguro_desgravamen"],
            seguro_vehicular=f["seguro_vehicular"],
            cuota_total=f["cuota_total"],
            saldo_final=f["saldo_final"],
        )
        for f in cronograma
    ]
    return Cronograma.objects.bulk_create(objetos)


# ---------------------------------------------------------------------------
# Prueba rapida en consola (replica el escenario de los mockups)
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    motor = FinancialEngine(
        precio_bien=25000,
        cuota_inicial=5000,
        cuota_balon_pct=20,
        tipo_tasa="EFECTIVA",
        valor_tasa=8.80,
        plazo_meses=18,
        tipo_gracia="PARCIAL",
        meses_gracia=2,
        tasa_seguro_desgravamen=0.077,
        tasa_seguro_vehicular=0.4050,
        cok_anual=10.0,
        fecha_inicio=date(2026, 4, 7),
    )
    cronograma, indicadores = motor.procesar()

    header = (
        f"{'N':>3} {'TIPO':<14} {'SALDO_INI':>11} {'INTERES':>9} "
        f"{'AMORT':>10} {'CUOTA_BASE':>11} {'DESGR':>8} "
        f"{'SEG_VEH':>9} {'CUOTA_TOT':>11} {'FLUJO':>11} {'SALDO_FIN':>11}"
    )
    print(header)
    print("-" * len(header))
    for f in cronograma:
        print(
            f"{f['nro_cuota']:>3} {f['tipo_periodo']:<14} "
            f"{f['saldo_inicial']:>11} {f['interes']:>9} "
            f"{f['amortizacion']:>10} {f['cuota_base']:>11} "
            f"{f['seguro_desgravamen']:>8} {f['seguro_vehicular']:>9} "
            f"{f['cuota_total']:>11} {f['flujo_caja_periodo']:>11} "
            f"{f['saldo_final']:>11}"
        )

    print("\nINDICADORES:")
    for clave, valor in indicadores.items():
        if clave != "flujo_caja":
            print(f"  {clave}: {valor}")
