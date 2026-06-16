# Generated migration to fix DNI constraint

import django.core.validators
from django.db import migrations, models


def set_empty_dni_to_null(apps, schema_editor):
    """Establece DNI vacíos a NULL"""
    Usuario = apps.get_model('core', 'Usuario')
    Usuario.objects.filter(dni='').update(dni=None)


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0002_alter_usuario_dni'),
    ]

    operations = [
        migrations.RunPython(set_empty_dni_to_null),
    ]
