"""
engine.py — Motor financiero de AutoFinance.

Implementa el plan de pagos del metodo "Compra Inteligente"
(Frances Vencido Ordinario, base 30/360) para credito vehicular en Peru.
Replica al centavo el modelo financiero auditado en Excel del usuario.

Reglas de negocio:
    - Tasa Efectiva Mensual (TEM) a partir de la TEA por interes compuesto:
          TEM = (1 + TEA) ** (1/12) - 1
      (TNA -> TEM simple: TNA / capitalizaciones_nominal).
    - COK mensual a partir del COK anual por interes compuesto:
          COK_mensual = (1 + COK_anual) ** (1/12) - 1

    - Seguro de desgravamen: monto FIJO, NO se recalcula sobre el saldo vivo
      mensual. Se calcula una sola vez sobre el saldo inicial neto financiado
      del periodo 1 (precio_bien - cuota_inicial) y se repite constante en
      todo el cronograma.
    - Seguro vehicular: monto FIJO sobre el valor completo del bien
      (precio_bien), constante en todo el cronograma.

    - Gracia Parcial: el cliente paga interes + desgravamen + seguro del bien;
      la amortizacion es 0 y el saldo no cambia.
    - Gracia Total: el cliente no paga nada; interes + desgravamen + seguro
      del bien se CAPITALIZAN integramente al saldo del periodo.

    - Cuota Balon: Monto_Balon = Valor_del_Bien (precio_bien) * %balon.
      Se descuenta su valor presente (a la TEM, sobre los meses ordinarios)
      del saldo capitalizado con el que arranca la fase ordinaria para
      obtener el monto neto a amortizar (Ma), y sobre Ma se calcula la cuota
      neta constante (R) con el metodo frances ordinario. Al aplicar R sobre
      el saldo capitalizado completo (no sobre Ma) durante n_ord periodos, el
      saldo remanente al final coincide exactamente con el Monto_Balon, que
      se liquida en la ultima cuota junto con el saldo contable restante.

PRECISION: MODELO DE DOBLE CAPA
    - Toda la matematica financiera (tasas, saldo, cuotas) se hace con
      floats de alta precision (IEEE 754), igual que las formulas nativas de
      Excel y numpy-financial, evitando descalces de redondeo intermedio.
    - Decimal (ROUND_HALF_UP) se usa UNICAMENTE en _fila(), al empacar cada
      valor en el diccionario de salida que alimenta la base de datos.
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
        cuota_balon_base="PRECIO",     # "FINANCIADO" | "PRECIO"
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
        self.m_nominal             = int(capitalizaciones_nominal)

        # Saldo inicial neto financiado del periodo 1 = precio_bien - cuota_inicial
        self.importe_financiado = self.precio_bien - self.cuota_inicial

        # Flujo de caja RAW (sin redondear); lo llena generar_cronograma().
        self._flujos_brutos: list[float] | None = None

        if self.tipo_gracia == "NINGUNA":
            self.meses_gracia = 0

    # ------------------------------------------------------------------ #
    # Conversiones de tasa
    # ------------------------------------------------------------------ #
    def tem(self) -> Decimal:
        """Tasa Efectiva Mensual = (1 + TEA) ** (1/12) - 1 (interes compuesto).

        La potencia fraccional se calcula en float IEEE 754 y se convierte a
        Decimal via str() para preservar todos los digitos significativos
        sin artefactos de la representacion binaria interna.
        """
        if self.tipo_tasa == "EFECTIVA":
            tem_float = (1 + float(self.valor_tasa)) ** (1 / 12) - 1
            return Decimal(str(tem_float))
        return self.valor_tasa / self.m_nominal

    def cok_mensual(self) -> Decimal:
        """COK mensual = (1 + COK_anual) ** (1/12) - 1 (interes compuesto)."""
        cok_float = (1 + float(self.cok_anual)) ** (1 / 12) - 1
        return Decimal(str(cok_float))

    # ------------------------------------------------------------------ #
    # Componentes fijos (constantes en todo el cronograma)
    # ------------------------------------------------------------------ #
    def _monto_balon(self) -> Decimal:
        """Monto_Balon = Valor_del_Bien (precio_bien) * %balon."""
        base = self.precio_bien if self.cuota_balon_base == "PRECIO" else self.importe_financiado
        return base * self.cuota_balon_pct

    def _desgravamen_fijo(self) -> Decimal:
        """Seguro de desgravamen FIJO: tasa * saldo inicial neto financiado."""
        return self.importe_financiado * self.tasa_desgravamen

    def _seguro_vehicular_fijo(self) -> Decimal:
        """Seguro vehicular FIJO: tasa * valor completo del bien."""
        return self.precio_bien * self.tasa_seguro_vehicular

    # ------------------------------------------------------------------ #
    # Cronograma
    # ------------------------------------------------------------------ #
    def generar_cronograma(self) -> list[dict]:
        """Devuelve el cronograma completo como lista de diccionarios.

        De paso, guarda en `self._flujos_brutos` el flujo de caja SIN
        redondear (RAW float) de cada periodo, incluyendo t=0. Estos son los
        flujos que deben alimentar npf.irr / npf.npv para que TIR, TCEA y VAN
        sean un espejo exacto de Excel — los valores del dict de cada fila
        solo sirven para mostrarse/persistirse y ya vienen redondeados.
        """
        i           = float(self.tem())
        monto_balon = float(self._monto_balon())
        desgravamen = float(self._desgravamen_fijo())
        seg_veh     = float(self._seguro_vehicular_fijo())
        n_ord       = self.plazo_meses - self.meses_gracia

        filas: list[dict] = []
        flujos_base:  list[float] = [float(self.importe_financiado)]
        flujos_final: list[float] = [float(self.importe_financiado)]
        saldo = float(self.importe_financiado)   # saldo en alta precision

        # ── Fase de Gracia ───────────────────────────────────────────────
        for k in range(1, self.meses_gracia + 1):
            interes = saldo * i

            if self.tipo_gracia == "TOTAL":
                # El cliente no paga nada: todo se capitaliza al saldo.
                amortizacion = 0.0
                cuota_base   = 0.0
                cuota_total  = 0.0
                flujo        = 0.0
                saldo_final  = saldo + interes + desgravamen + seg_veh
                tipo         = self.GRACIA_TOTAL
                fb           = 0.0
            else:  # PARCIAL — el cliente paga solo el interés; seguros capitalizan
                amortizacion = 0.0
                cuota_base   = interes
                cuota_total  = interes
                flujo        = cuota_total
                saldo_final  = saldo + desgravamen + seg_veh
                tipo         = self.GRACIA_PARCIAL
                fb           = interes

            filas.append(self._fila(
                k, tipo, interes, amortizacion, desgravamen,
                seg_veh, cuota_total, flujo, saldo, saldo_final, cuota_base, fb,
            ))
            flujos_base.append(-fb)
            flujos_final.append(-cuota_total)
            saldo = saldo_final

        # ── Cuota neta ordinaria (R) sobre el Saldo Capitalizado ──────────
        # Saldo_Capitalizado = saldo con el que arranca la fase ordinaria
        # (ya incluye lo capitalizado en Gracia Total, si aplica).
        saldo_capitalizado = saldo

        if n_ord > 0:
            va_balon = monto_balon / ((1 + i) ** n_ord)
            ma       = saldo_capitalizado - va_balon
            if i != 0:
                r = ma * (i / (1 - (1 + i) ** (-n_ord)))
            else:
                r = ma / n_ord
        else:
            r = 0.0

        # ── Fase Ordinaria (incluye la cuota balon en el ultimo mes) ──────
        for j in range(1, n_ord + 1):
            k          = self.meses_gracia + j
            es_ultimo  = (j == n_ord)

            interes      = saldo * i
            amortizacion = r - interes
            cuota_base   = r

            if es_ultimo:
                # Se liquida el Monto_Balon junto con el saldo remanente;
                # el saldo final cierra exactamente en 0.
                amortizacion += monto_balon
                cuota_base   += monto_balon
                saldo_final   = 0.0
            else:
                saldo_final = saldo - amortizacion

            cuota_total = cuota_base + desgravamen + seg_veh
            flujo       = cuota_total
            tipo        = self.CUOTA_BALON if (es_ultimo and monto_balon > 0) else self.ORDINARIO

            fb = cuota_base  # flujo_base: R puro (o R + balón), sin seguros
            filas.append(self._fila(
                k, tipo, interes, amortizacion, desgravamen,
                seg_veh, cuota_total, flujo, saldo, saldo_final, cuota_base, fb,
            ))
            flujos_base.append(-fb)
            flujos_final.append(-cuota_total)
            saldo = saldo_final

        self._flujos_base  = flujos_base
        self._flujos_final = flujos_final
        return filas

    def _fila(
        self, nro, tipo, interes, amort, desg, seg_veh,
        cuota, flujo, saldo_ini, saldo_fin, cb_ex, flujo_base_val=0.0,
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
            "flujo_base":         R(flujo_base_val),
            "flujo_final":        R(flujo),
            "saldo_final":        R(saldo_fin),
        }

    # ------------------------------------------------------------------ #
    # Indicadores SBS
    # ------------------------------------------------------------------ #
    def calcular_indicadores(self, cronograma: list[dict]) -> dict:
        """Calcula importe financiado, cuota ordinaria, TIR, TCEA y VAN.

        Dos flujos de caja RAW (sin redondear), generados en generar_cronograma():

        flujo_base (SIN seguros) — para TIR mensual y VAN:
            t = 0       -> +Importe_Financiado
            Gracia Total:   0
            Gracia Parcial: -Interes
            Ordinario:      -R
            Ultima cuota:   -(R + Monto_Balon)

        flujo_final (CON seguros, cuota real del cliente) — para TCEA:
            t = 0       -> +Importe_Financiado
            t = 1..N    -> -Cuota_Total del periodo

        TIR mensual: npf.irr(flujo_base).
        TCEA: (1 + npf.irr(flujo_final))^12 - 1.
        VAN:  npf.npv(COK_mensual, flujo_base).
        """
        flujos_base  = self._flujos_base
        flujos_final = self._flujos_final

        try:
            tir_mensual = float(npf.irr(flujos_base))
        except Exception:
            tir_mensual = float("nan")

        try:
            tir_tcea_mensual = float(npf.irr(flujos_final))
        except Exception:
            tir_tcea_mensual = float("nan")

        tcea = (1 + tir_tcea_mensual) ** 12 - 1

        cok_mensual = float(self.cok_mensual())
        van = npf.npv(cok_mensual, flujos_base)

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
            "monto_balon":          redondear_excel(self._monto_balon()),
            "duracion_meses":       self.plazo_meses,
            "tem":                   round(float(self.tem()), 8),
            "tcea":                  round(tcea, 6),
            "tcea_pct":              round(tcea * 100, 4),
            "tir_mensual":           round(tir_mensual, 6),
            "tir_mensual_pct":       round(tir_mensual * 100, 4),
            "tir_tcea_mensual":      round(tir_tcea_mensual, 6),
            "tir_tcea_mensual_pct":  round(tir_tcea_mensual * 100, 4),
            "van":                   redondear_excel(van),
            "flujo_base":            [round(x, 2) for x in flujos_base],
            "flujo_final":           [round(x, 2) for x in flujos_final],
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
        cuota_balon_base="PRECIO",
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
        f"{'SEG_VEH':>9} {'CUOTA_TOT':>11} {'F_BASE':>11} {'F_FINAL':>11} {'SALDO_FIN':>11}"
    )
    print(header)
    print("-" * len(header))
    for f in cronograma:
        print(
            f"{f['nro_cuota']:>3} {f['tipo_periodo']:<14} "
            f"{f['saldo_inicial']:>11} {f['interes']:>9} "
            f"{f['amortizacion']:>10} {f['cuota_base']:>11} "
            f"{f['seguro_desgravamen']:>8} {f['seguro_vehicular']:>9} "
            f"{f['cuota_total']:>11} {f['flujo_base']:>11} {f['flujo_final']:>11} "
            f"{f['saldo_final']:>11}"
        )

    print("\nINDICADORES:")
    for clave, valor in indicadores.items():
        if clave not in ("flujo_base", "flujo_final"):
            print(f"  {clave}: {valor}")

    saldo_final_ultimo = cronograma[-1]["saldo_final"]
    print(f"\nSaldo final del ultimo periodo (debe ser 0.00): {saldo_final_ultimo}")
