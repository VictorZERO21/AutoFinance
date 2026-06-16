from django.contrib.auth.hashers import make_password
from django.db import migrations

USUARIO_DEMO = {
    "username": "vendedor_demo",
    "password": "autofinance123",
    "dni": "00000001",
    "nombre_completo": "Vendedor Demo",
    "rol": "ADMIN",
    "is_staff": True,
    "is_superuser": True,
    "is_active": True,
}


def seed_usuario(apps, schema_editor):
    Usuario = apps.get_model("core", "Usuario")
    if not Usuario.objects.filter(username=USUARIO_DEMO["username"]).exists():
        Usuario.objects.create(
            username=USUARIO_DEMO["username"],
            password=make_password(USUARIO_DEMO["password"]),
            dni=USUARIO_DEMO["dni"],
            nombre_completo=USUARIO_DEMO["nombre_completo"],
            rol=USUARIO_DEMO["rol"],
            is_staff=USUARIO_DEMO["is_staff"],
            is_superuser=USUARIO_DEMO["is_superuser"],
            is_active=USUARIO_DEMO["is_active"],
        )


def unseed_usuario(apps, schema_editor):
    Usuario = apps.get_model("core", "Usuario")
    Usuario.objects.filter(username=USUARIO_DEMO["username"]).delete()


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0002_seed_vehiculos"),
    ]

    operations = [
        migrations.RunPython(seed_usuario, reverse_code=unseed_usuario),
    ]
