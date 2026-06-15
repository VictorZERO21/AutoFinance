from django.contrib import admin
from .models import Usuario, Vehiculo, Prestamo, Cronograma

# Registramos los modelos para que aparezcan en el panel web
admin.site.register(Usuario)
admin.site.register(Vehiculo)
admin.site.register(Prestamo)
admin.site.register(Cronograma)