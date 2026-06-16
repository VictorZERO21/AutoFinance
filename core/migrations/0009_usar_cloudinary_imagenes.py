from django.db import migrations

# URLs de imágenes de vehículos desde Cloudinary
# Imágenes reales subidas por el usuario
IMAGENES_CLOUDINARY = [
    {
        "marca": "BMW",
        "modelo": "320i",
        "imagen_url": "https://res.cloudinary.com/dshxmkd1v/image/upload/v1781578536/2024-BMW-3-Series-Gray_lzelxf.webp"
    },
    {
        "marca": "Chevrolet",
        "modelo": "Malibu",
        "imagen_url": "https://res.cloudinary.com/dshxmkd1v/image/upload/v1781578700/2024.malibu.profile_u3279g.webp"
    },
    {
        "marca": "Ford",
        "modelo": "Fusion",
        "imagen_url": "https://res.cloudinary.com/dshxmkd1v/image/upload/v1781578786/Fusion_1__ev1zup.png"
    },
    {
        "marca": "Honda",
        "modelo": "Civic",
        "imagen_url": "https://res.cloudinary.com/dshxmkd1v/image/upload/v1781578831/2024-Honda-Civic-Si-Red_zaryif.webp"
    },
    {
        "marca": "Nissan",
        "modelo": "Altima",
        "imagen_url": "https://res.cloudinary.com/dshxmkd1v/image/upload/v1781578919/model1_mp2uwd.png"
    },
    {
        "marca": "Toyota",
        "modelo": "Corolla",
        "imagen_url": "https://res.cloudinary.com/dshxmkd1v/image/upload/v1781578975/mlp-img-top-2024-corolla_a4x4mh.avif"
    },
    {
        "marca": "Volkswagen",
        "modelo": "Passat",
        "imagen_url": "https://res.cloudinary.com/dshxmkd1v/image/upload/v1781579047/volkswagen-passat-2024-1021__d8a9f2157418048c_xl_hlwcxi.webp"
    },
    {
        "marca": "Hyundai",
        "modelo": "Elantra",
        "imagen_url": "https://res.cloudinary.com/dshxmkd1v/image/upload/v1781579120/hyundai_20elantrasesd6t_angularfront_black_xwpke0.webp"
    },
    {
        "marca": "Hyundai",
        "modelo": "Elantra",
        "imagen_url": "https://res.cloudinary.com/dshxmkd1v/image/upload/v1781579165/2024_24_e6eaa1.png",
        "anio": 2024
    },
    {
        "marca": "Kia",
        "modelo": "Sportage",
        "imagen_url": "https://res.cloudinary.com/dshxmkd1v/image/upload/v1781579216/2024_24_1_wbxp05.png"
    },
    {
        "marca": "Mazda",
        "modelo": "CX-5",
        "imagen_url": "https://res.cloudinary.com/dshxmkd1v/image/upload/v1781579275/mlp-img-top-2024-cx5_rk7nko.avif"
    },
]


def agregar_imagenes_cloudinary(apps, schema_editor):
    """Agrega imágenes desde Cloudinary a todos los vehículos"""
    Vehiculo = apps.get_model("core", "Vehiculo")
    for item in IMAGENES_CLOUDINARY:
        # Caso especial para Hyundai Elantra 2024
        if item.get("anio"):
            Vehiculo.objects.filter(
                marca=item["marca"],
                modelo=item["modelo"],
                anio=item["anio"]
            ).update(imagen_url=item["imagen_url"])
        else:
            # Para otros vehículos, buscar solo por marca y modelo
            # y actualizar solo el primero encontrado (para evitar actualizar ambos Elantra)
            vehiculo = Vehiculo.objects.filter(
                marca=item["marca"],
                modelo=item["modelo"]
            ).first()
            if vehiculo:
                # Si es Hyundai Elantra sin año especificado, actualizar solo si es 2023
                if item["marca"] == "Hyundai" and item["modelo"] == "Elantra":
                    if vehiculo.anio == 2023:
                        vehiculo.imagen_url = item["imagen_url"]
                        vehiculo.save()
                else:
                    vehiculo.imagen_url = item["imagen_url"]
                    vehiculo.save()


def remover_imagenes(apps, schema_editor):
    """Remueve las imágenes de Cloudinary"""
    Vehiculo = apps.get_model("core", "Vehiculo")
    for item in IMAGENES_CLOUDINARY:
        Vehiculo.objects.filter(
            marca=item["marca"],
            modelo=item["modelo"]
        ).update(imagen_url="")


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0008_merge_0003_fix_dni_null_0007_update_tea_max_25"),
    ]

    operations = [
        migrations.RunPython(agregar_imagenes_cloudinary, remover_imagenes),
    ]
