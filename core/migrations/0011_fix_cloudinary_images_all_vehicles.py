from django.db import migrations


IMAGENES_CLOUDINARY = [
    {
        "marca": "BMW",
        "modelo": "320i",
        "anio": 2024,
        "imagen_url": "https://res.cloudinary.com/dshxmkd1v/image/upload/v1781578536/2024-BMW-3-Series-Gray_lzelxf.webp",
    },
    {
        "marca": "Chevrolet",
        "modelo": "Malibu",
        "anio": 2024,
        "imagen_url": "https://res.cloudinary.com/dshxmkd1v/image/upload/v1781578700/2024.malibu.profile_u3279g.webp",
    },
    {
        "marca": "Ford",
        "modelo": "Fusion",
        "anio": 2023,
        "imagen_url": "https://res.cloudinary.com/dshxmkd1v/image/upload/v1781578786/Fusion_1__ev1zup.png",
    },
    {
        "marca": "Honda",
        "modelo": "Civic",
        "anio": 2024,
        "imagen_url": "https://res.cloudinary.com/dshxmkd1v/image/upload/v1781578831/2024-Honda-Civic-Si-Red_zaryif.webp",
    },
    {
        "marca": "Nissan",
        "modelo": "Altima",
        "anio": 2023,
        "imagen_url": "https://res.cloudinary.com/dshxmkd1v/image/upload/v1781578919/model1_mp2uwd.png",
    },
    {
        "marca": "Toyota",
        "modelo": "Corolla",
        "anio": 2024,
        "imagen_url": "https://res.cloudinary.com/dshxmkd1v/image/upload/v1781578975/mlp-img-top-2024-corolla_a4x4mh.avif",
    },
    {
        "marca": "Volkswagen",
        "modelo": "Passat",
        "anio": 2024,
        "imagen_url": "https://res.cloudinary.com/dshxmkd1v/image/upload/v1781579047/volkswagen-passat-2024-1021__d8a9f2157418048c_xl_hlwcxi.webp",
    },
    {
        "marca": "Hyundai",
        "modelo": "Elantra",
        "anio": 2023,
        "imagen_url": "https://res.cloudinary.com/dshxmkd1v/image/upload/v1781579120/hyundai_20elantrasesd6t_angularfront_black_xwpke0.webp",
    },
    {
        "marca": "Hyundai",
        "modelo": "Elantra",
        "anio": 2024,
        "imagen_url": "https://res.cloudinary.com/dshxmkd1v/image/upload/v1781579165/2024_24_e6eaa1.png",
    },
    {
        "marca": "Kia",
        "modelo": "Sportage",
        "anio": 2024,
        "imagen_url": "https://res.cloudinary.com/dshxmkd1v/image/upload/v1781579216/2024_24_1_wbxp05.png",
    },
    {
        "marca": "Mazda",
        "modelo": "CX-5",
        "anio": 2024,
        "imagen_url": "https://res.cloudinary.com/dshxmkd1v/image/upload/v1781579275/mlp-img-top-2024-cx5_rk7nko.avif",
    },
]


def aplicar_imagenes_cloudinary(apps, schema_editor):
    Vehiculo = apps.get_model("core", "Vehiculo")
    for item in IMAGENES_CLOUDINARY:
        Vehiculo.objects.filter(
            marca=item["marca"],
            modelo=item["modelo"],
            anio=item["anio"],
        ).update(imagen_url=item["imagen_url"])


def revertir_imagenes_cloudinary(apps, schema_editor):
    Vehiculo = apps.get_model("core", "Vehiculo")
    for item in IMAGENES_CLOUDINARY:
        Vehiculo.objects.filter(
            marca=item["marca"],
            modelo=item["modelo"],
            anio=item["anio"],
        ).update(imagen_url="")


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0010_alter_prestamo_valor_tasa_alter_vehiculo_imagen_url"),
    ]

    operations = [
        migrations.RunPython(aplicar_imagenes_cloudinary, revertir_imagenes_cloudinary),
    ]
