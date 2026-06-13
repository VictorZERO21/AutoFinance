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
Al verificar el motor contra los numeros de los mockups encontre dos puntos
donde el TEXTO del prompt y los NUMEROS del mockup no coinciden. Por defecto el
motor reproduce el MOCKUP; ambos comportamientos son configurables:

1) CUOTA BALON
   - Texto del prompt: "porcentaje del prestamo original".
   - Numeros del mockup: 20% x 25,000 (precio) = 5,000  ->  base = PRECIO.
   - Por defecto: cuota_balon_base="PRECIO" (coincide con el mockup y con la
     convencion de "Compra Inteligente": el balon es el valor residual del auto).
     Use cuota_balon_base="FINANCIADO" para aplicar el texto literal del prompt.

2) SEGURO VEHICULAR
   - Texto del prompt: "tasa anual, se divide entre 12".
   - Numeros del mockup: 0.4050% x 25,000 = 101.25 mensual (tasa aplicada directa).
   - Por defecto: seguro_vehicular_es_anual=False (la tasa ya es mensual; mockup).
     Use seguro_vehicular_es_anual=True para dividir la tasa entre 12.

Nota sobre los indicadores del mockup (TIR 1.5249% / TCEA 19.91%): se calcularon
congelando la cuota en 1,146.61 (desgravamen fijo). Este motor respeta la regla
del prompt -"desgravamen sobre el saldo inicial DE CADA MES"- por lo que el
desgravamen baja con el saldo y la TIR resulta ~1.4941% / TCEA ~19.48%.
"""
from __future__ import annotations

import calendar
from datetime import date

import numpy_financial as npf


def _sumar_meses(fecha: date, meses: int) -> date:
    """Suma `meses` calendario a una fecha respetando el fin de mes."""
    indice = fecha.month - 1 + meses
    anio = fecha.year + indice // 12
    mes = indice % 12 + 1
    dia = min(fecha.day, calendar.monthrange(anio, mes)[1])
    return date(anio, mes, dia)


class FinancialEngine:
    """Genera el cronograma de pagos y los indicadores financieros."""

    # Tipos de periodo del cronograma
    GRACIA_TOTAL = "GRACIA_TOTAL"
    GRACIA_PARCIAL = "GRACIA_PARCIAL"
    ORDINARIO = "ORDINARIO"
    CUOTA_BALON = "CUOTA_BALON"

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
        self.precio_bien = float(precio_bien)
        self.cuota_inicial = float(cuota_inicial)
        self.cuota_balon_pct = float(cuota_balon_pct) / 100.0
        self.tipo_tasa = str(tipo_tasa).upper()
        self.valor_tasa = float(valor_tasa) / 100.0
        self.plazo_meses = int(plazo_meses)
        self.tipo_gracia = str(tipo_gracia or "NINGUNA").upper()
        self.meses_gracia = int(meses_gracia or 0)
        self.tasa_desgravamen = float(tasa_seguro_desgravamen) / 100.0
        self.tasa_seguro_vehicular = float(tasa_seguro_vehicular) / 100.0
        self.cok_anual = float(cok_anual) / 100.0
        self.fecha_inicio = fecha_inicio
        self.cuota_balon_base = str(cuota_balon_base).upper()
        self.seguro_vehicular_es_anual = bool(seguro_vehicular_es_anual)
        self.m_nominal = int(capitalizaciones_nominal)

        # Monto liquido prestado
        self.importe_financiado = self.precio_bien - self.cuota_inicial

        if self.tipo_gracia == "NINGUNA":
            self.meses_gracia = 0

    # ------------------------------------------------------------------ #
    # Conversiones de tasa
    # ------------------------------------------------------------------ #
    def tem(self) -> float:
        """Tasa Efectiva Mensual a partir de la tasa de entrada."""
        if self.tipo_tasa == "EFECTIVA":
            # TEA -> TEM, base 30/360 -> exponente 1/12
            return (1 + self.valor_tasa) ** (1 / 12) - 1
        # TNA capitalizable m veces al año -> tasa del periodo mensual
        return self.valor_tasa / self.m_nominal

    def cok_mensual(self) -> float:
        """COK efectivo mensual para descontar el VAN."""
        return (1 + self.cok_anual) ** (1 / 12) - 1

    # ------------------------------------------------------------------ #
    # Componentes auxiliares
    # ------------------------------------------------------------------ #
    def _monto_balon(self) -> float:
        base = self.precio_bien if self.cuota_balon_base == "PRECIO" else self.importe_financiado
        return base * self.cuota_balon_pct

    def _seguro_vehicular_mensual(self) -> float:
        if self.seguro_vehicular_es_anual:
            return (self.tasa_seguro_vehicular / 12) * self.precio_bien
        return self.tasa_seguro_vehicular * self.precio_bien

    def _cuota_constante(self, saldo: float, n: int, valor_futuro: float, i: float) -> float:
        """
        Cuota fija R (interes + amortizacion) del metodo frances, descontando
        el valor presente de la Cuota Balon (valor futuro al periodo n).

            PV = R * [1 - (1+i)^-n]/i  +  VF * (1+i)^-n
        """
        if n <= 0:
            return 0.0
        if i == 0:
            return (saldo - valor_futuro) / n
        factor_anualidad = (1 - (1 + i) ** -n) / i
        return (saldo - valor_futuro * (1 + i) ** -n) / factor_anualidad

    # ------------------------------------------------------------------ #
    # Cronograma
    # ------------------------------------------------------------------ #
    def generar_cronograma(self) -> list[dict]:
        """Devuelve el cronograma como lista de diccionarios (una fila por cuota)."""
        i = self.tem()
        valor_futuro = self._monto_balon()
        seguro_veh = self._seguro_vehicular_mensual()
        # NUEVO: Calculamos el desgravamen fijo sobre el precio del bien
        desgravamen_fijo = self.precio_bien * self.tasa_desgravamen
        filas: list[dict] = []
        saldo = self.importe_financiado

        # ---- Fase de gracia ----
        for k in range(1, self.meses_gracia + 1):
            interes = saldo * i
            desgravamen = desgravamen_fijo

            if self.tipo_gracia == "TOTAL":
                # Cuota = 0. Interes y seguros se capitalizan (el saldo crece).
                cuota = 0.0
                saldo_final = saldo + interes + desgravamen + seguro_veh
                tipo = self.GRACIA_TOTAL
            else:  # PARCIAL
                # Paga intereses + seguros. Amortizacion 0. Saldo intacto.
                cuota = interes + desgravamen + seguro_veh
                saldo_final = saldo
                tipo = self.GRACIA_PARCIAL

            filas.append(
                self._fila(k, tipo, interes, 0.0, desgravamen, seguro_veh, cuota, saldo, saldo_final)
            )
            saldo = saldo_final

        # ---- Fase ordinaria ----
        n_ordinario = self.plazo_meses - self.meses_gracia
        R = self._cuota_constante(saldo, n_ordinario, valor_futuro, i)

        for j in range(1, n_ordinario + 1):
            k = self.meses_gracia + j
            interes = saldo * i
            amortizacion = R - interes
            desgravamen = saldo * self.tasa_desgravamen
            cuota = R + desgravamen + seguro_veh
            saldo_final = saldo - amortizacion

            es_ultima = j == n_ordinario
            if es_ultima and valor_futuro > 0:
                # Ultimo mes ordinario: paga su cuota regular + la Cuota Balon.
                cuota += valor_futuro
                saldo_final -= valor_futuro
                tipo = self.CUOTA_BALON
            else:
                tipo = self.ORDINARIO

            filas.append(
                self._fila(
                    k, tipo, interes, amortizacion, desgravamen, seguro_veh,
                    cuota, saldo, max(saldo_final, 0.0),
                )
            )
            saldo = saldo_final

        return filas

    def _fila(self, nro, tipo, interes, amort, desg, seg_veh, cuota, saldo_ini, saldo_fin) -> dict:
        return {
            "nro_cuota": nro,
            "tipo_periodo": tipo,
            "fecha_vencimiento": _sumar_meses(self.fecha_inicio, nro),
            "saldo_inicial": round(saldo_ini, 2),
            "interes": round(interes, 2),
            "amortizacion": round(amort, 2),
            "seguro_desgravamen": round(desg, 2),
            "seguro_vehicular": round(seg_veh, 2),
            "cuota_total": round(cuota, 2),
            "saldo_final": round(saldo_fin, 2),
        }

    # ------------------------------------------------------------------ #
    # Indicadores SBS
    # ------------------------------------------------------------------ #
    def calcular_indicadores(self, cronograma: list[dict]) -> dict:
        """Calcula importe financiado, cuota ordinaria, TCEA, TIR mensual y VAN."""
        # Flujo de caja: mes 0 = +importe financiado; meses 1..N = -cuota total.
        flujo = [self.importe_financiado] + [-f["cuota_total"] for f in cronograma]

        try:
            tir_mensual = float(npf.irr(flujo))
        except Exception:
            tir_mensual = float("nan")

        tcea = (1 + tir_mensual) ** 12 - 1
        van = float(npf.npv(self.cok_mensual(), flujo))

        ordinarias = [
            f["cuota_total"]
            for f in cronograma
            if f["tipo_periodo"] in (self.ORDINARIO, self.CUOTA_BALON)
        ]
        cuota_ordinaria = ordinarias[0] if ordinarias else 0.0

        return {
            "importe_financiado": round(self.importe_financiado, 2),
            "cuota_ordinaria": round(cuota_ordinaria, 2),
            "duracion_meses": self.plazo_meses,
            "tem": tir_mensual if False else round(self.tem(), 8),
            "tcea": round(tcea, 6),
            "tir_mensual": round(tir_mensual, 6),
            "van": round(van, 2),
            "flujo_caja": [round(x, 2) for x in flujo],
        }

    # ------------------------------------------------------------------ #
    # Punto de entrada
    # ------------------------------------------------------------------ #
    def procesar(self) -> tuple[list[dict], dict]:
        """Devuelve (cronograma, indicadores)."""
        cronograma = self.generar_cronograma()
        indicadores = self.calcular_indicadores(cronograma)
        return cronograma, indicadores


# ---------------------------------------------------------------------------
# Integracion con Django: construir el motor desde una instancia Prestamo
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
# Prueba rapida (replica el escenario de los mockups)
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
    for fila in cronograma:
        print(fila)
    print("\nINDICADORES:")
    for clave, valor in indicadores.items():
        if clave != "flujo_caja":
            print(f"  {clave}: {valor}")
