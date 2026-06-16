from django.db import migrations

IMAGENES = [
    {"marca": "Toyota",  "modelo": "Corolla", "imagen_url": "imagenes/COROLLA.png"},
    {"marca": "Honda",   "modelo": "Civic",   "imagen_url": "imagenes/civic.jpeg"},
    {"marca": "Hyundai", "modelo": "Elantra", "imagen_url": "imagenes/hyundai.jpeg"},
    {"marca": "Mazda",   "modelo": "CX-5",    "imagen_url": "imagenes/Mazda.png"},
]


def asignar_imagenes(apps, schema_editor):
    Vehiculo = apps.get_model("core", "Vehiculo")
    for item in IMAGENES:
        Vehiculo.objects.filter(
            marca=item["marca"], modelo=item["modelo"]
        ).update(imagen_url=item["imagen_url"])


def quitar_imagenes(apps, schema_editor):
    Vehiculo = apps.get_model("core", "Vehiculo")
    for item in IMAGENES:
        Vehiculo.objects.filter(
            marca=item["marca"], modelo=item["modelo"]
        ).update(imagen_url="")


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0005_imagen_url_to_charfield"),
    ]

    operations = [
        migrations.RunPython(asignar_imagenes, quitar_imagenes),
    ]
