"""
models.py — Esquema de base de datos de AutoFinance (Django + PostgreSQL).

Entidades:
    Usuario     -> AbstractUser extendido (DNI, nombre completo, rol).
    Vehiculo    -> Catalogo de autos.
    Prestamo    -> Configuracion del credito vehicular "Compra Inteligente".
    Cronograma  -> Detalle cuota por cuota generado por FinancialEngine.

Notas de configuracion:
    settings.py debe declarar:  AUTH_USER_MODEL = "core.Usuario"
    (reemplaza "core" por el nombre real de tu app).
"""
from decimal import Decimal

from django.conf import settings
from django.contrib.auth.models import AbstractUser
from django.core.exceptions import ValidationError
from django.core.validators import (
    MinValueValidator,
    MaxValueValidator,
    RegexValidator,
)
from django.db import models


# ---------------------------------------------------------------------------
# 1. USUARIO
# ---------------------------------------------------------------------------
class Usuario(AbstractUser):
    """Usuario del sistema. Extiende AbstractUser para sumar DNI y rol."""

    class Rol(models.TextChoices):
        ADMIN = "ADMIN", "Administrador"
        CLIENTE = "CLIENTE", "Cliente"

    dni = models.CharField(
        "DNI",
        max_length=8,
        unique=True,
        validators=[RegexValidator(r"^\d{8}$", "El DNI debe tener 8 digitos.")],
    )
    nombre_completo = models.CharField("Nombre completo", max_length=150)
    rol = models.CharField(max_length=10, choices=Rol.choices, default=Rol.CLIENTE)

    class Meta:
        verbose_name = "Usuario"
        verbose_name_plural = "Usuarios"

    def __str__(self):
        return f"{self.nombre_completo} ({self.dni})"


# ---------------------------------------------------------------------------
# 2. VEHICULO
# ---------------------------------------------------------------------------
class Vehiculo(models.Model):
    """Catalogo de vehiculos disponibles para financiar."""

    marca = models.CharField(max_length=60)
    modelo = models.CharField(max_length=60)
    anio = models.PositiveIntegerField(
        "Año",
        validators=[MinValueValidator(1990), MaxValueValidator(2100)],
    )
    descripcion = models.CharField(max_length=255, blank=True)
    precio_base = models.DecimalField(
        "Precio base (USD)",
        max_digits=12,
        decimal_places=2,
        validators=[MinValueValidator(Decimal("0.01"))],
    )
    imagen_url = models.URLField("Imagen (URL)", blank=True)

    class Meta:
        verbose_name = "Vehiculo"
        verbose_name_plural = "Vehiculos"
        ordering = ["marca", "modelo"]

    def __str__(self):
        return f"{self.anio} {self.marca} {self.modelo}"


# ---------------------------------------------------------------------------
# 3. PRESTAMO
# ---------------------------------------------------------------------------
class Prestamo(models.Model):
    """
    Configuracion de un credito vehicular bajo el metodo "Compra Inteligente".
    Guarda todos los parametros de entrada que consume FinancialEngine.
    """

    class Moneda(models.TextChoices):
        USD = "USD", "Dolares (USD)"

    class TipoTasa(models.TextChoices):
        EFECTIVA = "EFECTIVA", "Tasa Efectiva Anual (TEA)"
        NOMINAL = "NOMINAL", "Tasa Nominal Anual (TNA)"

    class TipoGracia(models.TextChoices):
        NINGUNA = "NINGUNA", "Ninguna"
        TOTAL = "TOTAL", "Gracia Total"
        PARCIAL = "PARCIAL", "Gracia Parcial"

    class Estado(models.TextChoices):
        ACTIVO = "ACTIVO", "Activo"
        CANCELADO = "CANCELADO", "Cancelado"

    # Relaciones
    usuario = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="prestamos"
    )
    vehiculo = models.ForeignKey(
        Vehiculo, on_delete=models.PROTECT, related_name="prestamos"
    )

    # Datos economicos del bien
    moneda = models.CharField(max_length=3, choices=Moneda.choices, default=Moneda.USD)
    precio_bien = models.DecimalField(max_digits=12, decimal_places=2)
    cuota_inicial_monto = models.DecimalField(max_digits=12, decimal_places=2)
    cuota_inicial_pct = models.DecimalField(
        "Cuota inicial (%)",
        max_digits=5,
        decimal_places=2,
        validators=[MinValueValidator(Decimal("10")), MaxValueValidator(Decimal("30"))],
    )
    cuota_balon_pct = models.DecimalField(
        "Cuota balon (%)",
        max_digits=5,
        decimal_places=2,
        default=Decimal("0"),
        validators=[MinValueValidator(Decimal("0")), MaxValueValidator(Decimal("30"))],
    )

    # Tasa de interes
    tipo_tasa = models.CharField(
        max_length=10, choices=TipoTasa.choices, default=TipoTasa.EFECTIVA
    )
    valor_tasa = models.DecimalField(
        "Valor de la tasa (%)",
        max_digits=6,
        decimal_places=4,
        validators=[MinValueValidator(Decimal("0"))],
    )

    # Plazo y gracia
    plazo_meses = models.PositiveIntegerField(
        validators=[MinValueValidator(12), MaxValueValidator(72)]
    )
    tipo_gracia = models.CharField(
        max_length=10, choices=TipoGracia.choices, default=TipoGracia.NINGUNA
    )
    meses_gracia = models.PositiveIntegerField(default=0)

    # Seguros (porcentajes; ver convenciones en FinancialEngine)
    tasa_seguro_desgravamen = models.DecimalField(
        "Seguro desgravamen (% mensual)", max_digits=7, decimal_places=4
    )
    tasa_seguro_vehicular = models.DecimalField(
        "Seguro vehicular (%)", max_digits=7, decimal_places=4
    )

    # Costo de oportunidad para el VAN
    cok = models.DecimalField(
        "COK del usuario (% anual)", max_digits=6, decimal_places=4
    )

    # Metadatos
    fecha_inicio = models.DateField()
    estado = models.CharField(max_length=10, choices=Estado.choices, default=Estado.ACTIVO)
    creado_en = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Prestamo"
        verbose_name_plural = "Prestamos"
        ordering = ["-creado_en"]

    def __str__(self):
        return f"Prestamo #{self.pk} - {self.usuario} - {self.vehiculo}"

    @property
    def importe_financiado(self):
        """Monto liquido prestado = precio del bien - cuota inicial."""
        return self.precio_bien - self.cuota_inicial_monto

    def clean(self):
        """Validaciones de negocio que cruzan varios campos."""
        errores = {}

        # Coherencia cuota inicial monto vs %
        if self.precio_bien and self.cuota_inicial_pct is not None:
            esperado = self.precio_bien * self.cuota_inicial_pct / Decimal("100")
            if self.cuota_inicial_monto is not None:
                if abs(self.cuota_inicial_monto - esperado) > Decimal("1.00"):
                    errores["cuota_inicial_monto"] = (
                        "No coincide con el porcentaje de cuota inicial."
                    )

        # Cuota balon: si es > 0 debe estar entre 10% y 30%
        if self.cuota_balon_pct and self.cuota_balon_pct > 0:
            if not (Decimal("10") <= self.cuota_balon_pct <= Decimal("30")):
                errores["cuota_balon_pct"] = "La cuota balon debe estar entre 10% y 30%."

        # Meses de gracia: maximo 20% del plazo
        if self.plazo_meses and self.meses_gracia:
            maximo = int(self.plazo_meses * 0.20)
            if self.tipo_gracia == self.TipoGracia.NINGUNA and self.meses_gracia > 0:
                errores["meses_gracia"] = "Sin periodo de gracia los meses deben ser 0."
            elif self.meses_gracia > maximo:
                errores["meses_gracia"] = (
                    f"Los meses de gracia no pueden exceder el 20% del plazo ({maximo})."
                )

        # Coherencia tipo de gracia / meses
        if self.tipo_gracia != self.TipoGracia.NINGUNA and not self.meses_gracia:
            errores["meses_gracia"] = "Debe indicar la cantidad de meses de gracia."

        if errores:
            raise ValidationError(errores)


# ---------------------------------------------------------------------------
# 4. CRONOGRAMA
# ---------------------------------------------------------------------------
class Cronograma(models.Model):
    """Fila del cronograma de pagos (una por cuota) asociada a un Prestamo."""

    class TipoPeriodo(models.TextChoices):
        GRACIA_TOTAL = "GRACIA_TOTAL", "Gracia Total"
        GRACIA_PARCIAL = "GRACIA_PARCIAL", "Gracia Parcial"
        ORDINARIO = "ORDINARIO", "Ordinario"
        CUOTA_BALON = "CUOTA_BALON", "Cuota Balon"

    prestamo = models.ForeignKey(
        Prestamo, on_delete=models.CASCADE, related_name="cronograma"
    )
    nro_cuota = models.PositiveIntegerField()
    tipo_periodo = models.CharField(max_length=15, choices=TipoPeriodo.choices)
    fecha_vencimiento = models.DateField()

    saldo_inicial = models.DecimalField(max_digits=14, decimal_places=2)
    interes = models.DecimalField(max_digits=14, decimal_places=2)
    amortizacion = models.DecimalField(max_digits=14, decimal_places=2)
    seguro_desgravamen = models.DecimalField(max_digits=14, decimal_places=2)
    seguro_vehicular = models.DecimalField(max_digits=14, decimal_places=2)
    cuota_total = models.DecimalField(max_digits=14, decimal_places=2)
    saldo_final = models.DecimalField(max_digits=14, decimal_places=2)

    class Meta:
        verbose_name = "Cronograma"
        verbose_name_plural = "Cronogramas"
        ordering = ["prestamo", "nro_cuota"]
        unique_together = ("prestamo", "nro_cuota")

    def __str__(self):
        return f"Prestamo #{self.prestamo_id} - Cuota {self.nro_cuota}"
