from datetime import date, timedelta
from decimal import Decimal
from django import forms

GRACIA_CHOICES = [
    ("SI", "Sí"),
    ("NO", "No"),
]

TIPO_GRACIA_CHOICES = [
    ("PARCIAL", "Gracia Parcial"),
    ("TOTAL", "Gracia Total"),
]

# El valor de cada opción es el porcentaje mensual tal como lo recibe el engine
# (el engine lo divide /100 internamente para obtener la tasa decimal).
DESGRAVAMEN_CHOICES = [
    ("0.077", "BBVA - Crédito Vehicular Inteligente (0.077%)"),
    ("0.050", "Interbank - Préstamo Vehicular (0.050%)"),
    ("0.060", "BCP - Préstamo Vehicular (0.060%)"),
    ("OTRO", "Otro — ingresar manualmente"),
]

VEHICULAR_CHOICES = [
    ("0.4050", "BCP - (0.4050%)"),
    ("0.3500", "BBVA - (0.3500%)"),
    ("0.4200", "Rímac - (0.4200%)"),
    ("OTRO", "Otro — ingresar manualmente"),
]


class SimuladorForm(forms.Form):

    # ── PASO 1: Datos del bien ────────────────────────────────────────────
    precio_bien = forms.DecimalField(
        label="Valor del bien ($/)",
        min_value=Decimal("1"),
        decimal_places=2,
        widget=forms.NumberInput(attrs={
            "step": "0.01", "min": "1",
            "class": "form-control bg-light text-center fw-bold fs-5",
        }),
    )

    # ── PASO 1: Condiciones del préstamo ─────────────────────────────────
    cuota_inicial_pct = forms.DecimalField(
        label="Cuota Inicial (%)",
        min_value=Decimal("0"),
        max_value=Decimal("40"),
        decimal_places=2,
        initial=Decimal("20"),
        widget=forms.NumberInput(attrs={
            "step": "0.01", "min": "0", "max": "40",
            "class": "form-control bg-light text-center fw-bold fs-5",
        }),
    )
    cuota_balon_pct = forms.DecimalField(
        label="Cuota Balón (%)",
        min_value=Decimal("0"),
        max_value=Decimal("40"),
        decimal_places=2,
        initial=Decimal("20"),
        widget=forms.NumberInput(attrs={
            "step": "0.01", "min": "0", "max": "40",
            "class": "form-control bg-light text-center fw-bold fs-5",
        }),
    )
    valor_tasa = forms.DecimalField(
        label="Tasa de Interés (TEA %)",
        min_value=Decimal("8"),
        max_value=Decimal("25"),
        decimal_places=4,
        initial=Decimal("8.80"),
        widget=forms.NumberInput(attrs={
            "step": "0.01", "min": "8", "max": "25",
            "class": "form-control bg-light text-center fw-bold fs-5",
        }),
    )
    cok = forms.DecimalField(
        label="COK — Costo de Oportunidad (% anual)",
        min_value=Decimal("1"),
        max_value=Decimal("100"),
        decimal_places=4,
        initial=Decimal("15.00"),
        widget=forms.NumberInput(attrs={
            "step": "0.01", "min": "1", "max": "100",
            "class": "form-control bg-light text-center fw-bold fs-5",
        }),
    )
    plazo_meses = forms.IntegerField(
        label="Plazo (meses)",
        min_value=12,
        max_value=120,
        initial=18,
    )

    # ── PASO 2: Período de gracia ─────────────────────────────────────────
    desea_gracia = forms.ChoiceField(
        choices=GRACIA_CHOICES,
        initial="SI",
        widget=forms.RadioSelect,
    )
    tipo_gracia = forms.ChoiceField(
        choices=TIPO_GRACIA_CHOICES,
        required=False,
        initial="PARCIAL",
    )
    meses_gracia = forms.IntegerField(
        label="N° de meses de Gracia",
        min_value=0,
        max_value=4,
        required=False,
        initial=2,
        widget=forms.NumberInput(attrs={
            "min": "0", "max": "4",
            "class": "form-control bg-light text-center fw-bold fs-5",
        }),
    )

    # ── PASO 2: Seguros ───────────────────────────────────────────────────
    tasa_desgravamen = forms.ChoiceField(
        label="Seguro de Desgravamen ($/)",
        choices=DESGRAVAMEN_CHOICES,
    )
    tasa_desgravamen_custom = forms.DecimalField(
        label="Desgravamen personalizado (%)",
        min_value=Decimal("0.04"),
        max_value=Decimal("0.07"),
        decimal_places=4,
        required=False,
        widget=forms.NumberInput(attrs={
            "step": "0.001", "min": "0.04", "max": "0.07",
            "class": "form-control bg-light text-center fw-bold",
            "placeholder": "ej. 0.055",
        }),
    )
    tasa_vehicular = forms.ChoiceField(
        label="Seguro del Bien",
        choices=VEHICULAR_CHOICES,
    )
    tasa_vehicular_custom = forms.DecimalField(
        label="Seguro del bien personalizado (%)",
        min_value=Decimal("0.35"),
        max_value=Decimal("8.5"),
        decimal_places=4,
        required=False,
        widget=forms.NumberInput(attrs={
            "step": "0.01", "min": "0.35", "max": "8.5",
            "class": "form-control bg-light text-center fw-bold",
            "placeholder": "ej. 0.40",
        }),
    )

    # ── PASO 2: Fecha de inicio ───────────────────────────────────────────
    fecha_inicio = forms.DateField(
        label="Fecha de inicio",
        initial=date.today,
        widget=forms.DateInput(attrs={
            "type": "date",
            "class": "form-control bg-light fw-bold fs-5",
        }),
    )

    # ── Validaciones cruzadas ─────────────────────────────────────────────
    def clean(self):
        cleaned = super().clean()

        # Gracia
        if cleaned.get("desea_gracia") == "SI":
            if not cleaned.get("tipo_gracia"):
                self.add_error("tipo_gracia", "Seleccione el tipo de gracia.")
            meses = cleaned.get("meses_gracia")
            if meses is None or meses <= 0:
                self.add_error("meses_gracia", "Ingrese al menos 1 mes de gracia (máx. 4).")

        # Seguro desgravamen personalizado
        if cleaned.get("tasa_desgravamen") == "OTRO":
            td = cleaned.get("tasa_desgravamen_custom")
            if td is None:
                self.add_error(
                    "tasa_desgravamen_custom",
                    "Ingrese el porcentaje del seguro de desgravamen.",
                )
            elif not (Decimal("0.04") <= td <= Decimal("0.07")):
                self.add_error(
                    "tasa_desgravamen_custom",
                    "El desgravamen personalizado debe estar entre 0.04 % y 0.07 %.",
                )

        # Seguro vehicular personalizado
        if cleaned.get("tasa_vehicular") == "OTRO":
            tv = cleaned.get("tasa_vehicular_custom")
            if tv is None:
                self.add_error(
                    "tasa_vehicular_custom",
                    "Ingrese el porcentaje del seguro del bien.",
                )
            elif not (Decimal("0.35") <= tv <= Decimal("8.5")):
                self.add_error(
                    "tasa_vehicular_custom",
                    "El seguro del bien personalizado debe estar entre 0.35 % y 8.5 %.",
                )

        # Fecha de inicio: mínimo hoy, máximo un año a partir de hoy
        fi = cleaned.get("fecha_inicio")
        if fi:
            hoy = date.today()
            max_fecha = hoy + timedelta(days=365)
            if fi < hoy:
                self.add_error("fecha_inicio", "La fecha de inicio no puede ser anterior a hoy.")
            elif fi > max_fecha:
                self.add_error(
                    "fecha_inicio",
                    f"La fecha no puede superar un año desde hoy ({max_fecha.strftime('%d/%m/%Y')}).",
                )

        return cleaned
