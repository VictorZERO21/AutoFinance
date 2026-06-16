from django.db import migrations

# Imágenes actualizadas - URLs públicas sin problemas de CORS
IMAGENES_ACTUALIZADAS = [
    {"marca": "BMW", "modelo": "320i", "imagen_url": "https://picsum.photos/500/400?random=1"},
    {"marca": "Chevrolet", "modelo": "Malibu", "imagen_url": "https://picsum.photos/500/400?random=2"},
    {"marca": "Ford", "modelo": "Fusion", "imagen_url": "https://picsum.photos/500/400?random=3"},
    {"marca": "Honda", "modelo": "Civic", "imagen_url": "https://picsum.photos/500/400?random=4"},
    {"marca": "Nissan", "modelo": "Altima", "imagen_url": "https://picsum.photos/500/400?random=5"},
    {"marca": "Toyota", "modelo": "Corolla", "imagen_url": "https://picsum.photos/500/400?random=6"},
    {"marca": "Volkswagen", "modelo": "Passat", "imagen_url": "https://picsum.photos/500/400?random=7"},
    {"marca": "Hyundai", "modelo": "Elantra", "imagen_url": "https://picsum.photos/500/400?random=8"},
    {"marca": "Kia", "modelo": "Sportage", "imagen_url": "https://picsum.photos/500/400?random=9"},
    {"marca": "Mazda", "modelo": "CX-5", "imagen_url": "https://picsum.photos/500/400?random=10"},
]


def actualizar_imagenes(apps, schema_editor):
    """Actualiza las imágenes a URLs sin problemas de CORS"""
    Vehiculo = apps.get_model("core", "Vehiculo")
    for item in IMAGENES_ACTUALIZADAS:
        Vehiculo.objects.filter(
            marca=item["marca"],
            modelo=item["modelo"]
        ).update(imagen_url=item["imagen_url"])


def revertir_imagenes(apps, schema_editor):
    """Revierte al estado anterior"""
    pass


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0009_agregar_imagenes_todos_vehiculos"),
    ]

    operations = [
        migrations.RunPython(actualizar_imagenes, revertir_imagenes),
    ]
