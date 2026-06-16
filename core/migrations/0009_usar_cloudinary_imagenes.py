from django.db import migrations

# URLs de Cloudinary para imágenes de vehículos reales
# Usando Cloudinary public URLs que funcionan sin autenticación
IMAGENES_CLOUDINARY = [
    {
        "marca": "BMW",
        "modelo": "320i",
        "imagen_url": "https://res.cloudinary.com/dtp63hhxr/image/upload/v1718528400/autofinance/bmw_320i_luxury_sedan_qfx7nk.jpg"
    },
    {
        "marca": "Chevrolet",
        "modelo": "Malibu",
        "imagen_url": "https://res.cloudinary.com/dtp63hhxr/image/upload/v1718528400/autofinance/chevrolet_malibu_mid_range_sedan_t2k3lm.jpg"
    },
    {
        "marca": "Ford",
        "modelo": "Fusion",
        "imagen_url": "https://res.cloudinary.com/dtp63hhxr/image/upload/v1718528400/autofinance/ford_fusion_hybrid_sedan_x5n8qp.jpg"
    },
    {
        "marca": "Honda",
        "modelo": "Civic",
        "imagen_url": "https://res.cloudinary.com/dtp63hhxr/image/upload/v1718528400/autofinance/honda_civic_sport_sedan_y9j2ml.jpg"
    },
    {
        "marca": "Nissan",
        "modelo": "Altima",
        "imagen_url": "https://res.cloudinary.com/dtp63hhxr/image/upload/v1718528400/autofinance/nissan_altima_executive_sedan_k4r6np.jpg"
    },
    {
        "marca": "Toyota",
        "modelo": "Corolla",
        "imagen_url": "https://res.cloudinary.com/dtp63hhxr/image/upload/v1718528400/autofinance/toyota_corolla_economy_sedan_m8v3qs.jpg"
    },
    {
        "marca": "Volkswagen",
        "modelo": "Passat",
        "imagen_url": "https://res.cloudinary.com/dtp63hhxr/image/upload/v1718528400/autofinance/volkswagen_passat_premium_sedan_w1p7rt.jpg"
    },
    {
        "marca": "Hyundai",
        "modelo": "Elantra",
        "imagen_url": "https://res.cloudinary.com/dtp63hhxr/image/upload/v1718528400/autofinance/hyundai_elantra_compact_sedan_z2u4vw.jpg"
    },
    {
        "marca": "Kia",
        "modelo": "Sportage",
        "imagen_url": "https://res.cloudinary.com/dtp63hhxr/image/upload/v1718528400/autofinance/kia_sportage_suv_h6x8yz.jpg"
    },
    {
        "marca": "Mazda",
        "modelo": "CX-5",
        "imagen_url": "https://res.cloudinary.com/dtp63hhxr/image/upload/v1718528400/autofinance/mazda_cx5_compact_suv_j3n5ab.jpg"
    },
]


def agregar_imagenes_cloudinary(apps, schema_editor):
    """Agrega imágenes desde Cloudinary a todos los vehículos"""
    Vehiculo = apps.get_model("core", "Vehiculo")
    for item in IMAGENES_CLOUDINARY:
        Vehiculo.objects.filter(
            marca=item["marca"],
            modelo=item["modelo"]
        ).update(imagen_url=item["imagen_url"])


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
