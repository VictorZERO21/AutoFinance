from django.db import migrations

# Imágenes reales de vehículos - URLs públicas que persisten
IMAGENES_VEHICULOS = [
    # Sedanes de lujo
    {"marca": "BMW", "modelo": "320i", "imagen_url": "https://images.unsplash.com/photo-1552820728-8ac41f1ce891?w=500&h=400&fit=crop"},
    
    # Sedanes de gama media
    {"marca": "Chevrolet", "modelo": "Malibu", "imagen_url": "https://images.unsplash.com/photo-1605559424843-9e4c3febda46?w=500&h=400&fit=crop"},
    {"marca": "Ford", "modelo": "Fusion", "imagen_url": "https://images.unsplash.com/photo-1578762335032-476db938df60?w=500&h=400&fit=crop"},
    {"marca": "Honda", "modelo": "Civic", "imagen_url": "https://images.unsplash.com/photo-1552820728-8ac41f1ce891?w=500&h=400&fit=crop"},
    {"marca": "Nissan", "modelo": "Altima", "imagen_url": "https://images.unsplash.com/photo-1605559424843-9e4c3febda46?w=500&h=400&fit=crop"},
    {"marca": "Toyota", "modelo": "Corolla", "imagen_url": "https://images.unsplash.com/photo-1578762335032-476db938df60?w=500&h=400&fit=crop"},
    {"marca": "Volkswagen", "modelo": "Passat", "imagen_url": "https://images.unsplash.com/photo-1552820728-8ac41f1ce891?w=500&h=400&fit=crop"},
    
    # Sedanes compactos/económicos
    {"marca": "Hyundai", "modelo": "Elantra", "imagen_url": "https://images.unsplash.com/photo-1605559424843-9e4c3febda46?w=500&h=400&fit=crop"},
    
    # SUVs
    {"marca": "Kia", "modelo": "Sportage", "imagen_url": "https://images.unsplash.com/photo-1606520829893-dd983d37cdf0?w=500&h=400&fit=crop"},
    {"marca": "Mazda", "modelo": "CX-5", "imagen_url": "https://images.unsplash.com/photo-1606520829893-dd983d37cdf0?w=500&h=400&fit=crop"},
]


def agregar_imagenes(apps, schema_editor):
    """Agrega imágenes reales a todos los vehículos"""
    Vehiculo = apps.get_model("core", "Vehiculo")
    for item in IMAGENES_VEHICULOS:
        Vehiculo.objects.filter(
            marca=item["marca"],
            modelo=item["modelo"]
        ).update(imagen_url=item["imagen_url"])


def remover_imagenes(apps, schema_editor):
    """Remueve las imágenes agregadas"""
    Vehiculo = apps.get_model("core", "Vehiculo")
    for item in IMAGENES_VEHICULOS:
        Vehiculo.objects.filter(
            marca=item["marca"],
            modelo=item["modelo"]
        ).update(imagen_url="")


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0008_merge_0003_fix_dni_null_0007_update_tea_max_25"),
    ]

    operations = [
        migrations.RunPython(agregar_imagenes, remover_imagenes),
    ]
