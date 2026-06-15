from django.db import migrations


VEHICULOS = [
    {
        "marca": "Toyota",
        "modelo": "Corolla",
        "anio": 2024,
        "precio_base": "25000.00",
        "descripcion": "Sedán confiable y económico. Excelente para uso urbano y familiar.",
        "imagen_url": "",
    },
    {
        "marca": "Honda",
        "modelo": "Civic",
        "anio": 2024,
        "precio_base": "28000.00",
        "descripcion": "Sedán deportivo con tecnología avanzada y bajo consumo de combustible.",
        "imagen_url": "",
    },
    {
        "marca": "Mazda",
        "modelo": "CX-5",
        "anio": 2024,
        "precio_base": "32000.00",
        "descripcion": "SUV compacto con diseño premium y excelente desempeño en todo terreno.",
        "imagen_url": "",
    },
    {
        "marca": "Hyundai",
        "modelo": "Elantra",
        "anio": 2024,
        "precio_base": "22000.00",
        "descripcion": "Sedán moderno con garantía extendida y el mejor precio del segmento.",
        "imagen_url": "",
    },
]


def seed_vehiculos(apps, schema_editor):
    Vehiculo = apps.get_model("core", "Vehiculo")
    for v in VEHICULOS:
        Vehiculo.objects.get_or_create(
            marca=v["marca"],
            modelo=v["modelo"],
            anio=v["anio"],
            defaults={
                "precio_base": v["precio_base"],
                "descripcion": v["descripcion"],
                "imagen_url": v["imagen_url"],
            },
        )


def unseed_vehiculos(apps, schema_editor):
    Vehiculo = apps.get_model("core", "Vehiculo")
    for v in VEHICULOS:
        Vehiculo.objects.filter(
            marca=v["marca"], modelo=v["modelo"], anio=v["anio"]
        ).delete()


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0001_initial"),
    ]

    operations = [
        migrations.RunPython(seed_vehiculos, reverse_code=unseed_vehiculos),
    ]
