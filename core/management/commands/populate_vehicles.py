from django.core.management.base import BaseCommand
from core.models import Vehiculo
from decimal import Decimal


class Command(BaseCommand):
    help = 'Puebla la base de datos con 10 vehículos de ejemplo'

    def handle(self, *args, **options):
        # Lista de 10 vehículos con datos realistas
        vehicles = [
            {
                'marca': 'Toyota',
                'modelo': 'Corolla',
                'anio': 2024,
                'descripcion': 'Sedán compacto confiable con excelente eficiencia de combustible',
                'precio_base': Decimal('22500.00'),
                'imagen_url': 'https://images.unsplash.com/photo-1621007947382-bb3c3994e3fb?w=500&q=80'
            },
            {
                'marca': 'Honda',
                'modelo': 'Civic',
                'anio': 2024,
                'descripcion': 'Sedán deportivo con tecnología avanzada y diseño moderno',
                'precio_base': Decimal('24000.00'),
                'imagen_url': 'https://images.unsplash.com/photo-1558618666-fcd25c85cd64?w=500&q=80'
            },
            {
                'marca': 'Hyundai',
                'modelo': 'Elantra',
                'anio': 2023,
                'descripcion': 'Sedán económico con tecnología touchscreen de última generación',
                'precio_base': Decimal('20500.00'),
                'imagen_url': 'https://images.unsplash.com/photo-1617654112368-307921291f42?w=500&q=80'
            },
            {
                'marca': 'Volkswagen',
                'modelo': 'Passat',
                'anio': 2024,
                'descripcion': 'Sedán premium con interior lujoso y tecnología de punta',
                'precio_base': Decimal('28000.00'),
                'imagen_url': 'https://images.unsplash.com/photo-1606611013016-969c19d24e38?w=500&q=80'
            },
            {
                'marca': 'Mazda',
                'modelo': 'CX-5',
                'anio': 2024,
                'descripcion': 'SUV compacta versátil con tracción AWD y manejo deportivo',
                'precio_base': Decimal('28500.00'),
                'imagen_url': 'https://images.unsplash.com/photo-1609708536965-32abf4b02100?w=500&q=80'
            },
            {
                'marca': 'Nissan',
                'modelo': 'Altima',
                'anio': 2023,
                'descripcion': 'Sedán ejecutivo con confort premium y tecnología de seguridad',
                'precio_base': Decimal('26500.00'),
                'imagen_url': 'https://images.unsplash.com/photo-1552820728-8ac41f1ce891?w=500&q=80'
            },
            {
                'marca': 'Kia',
                'modelo': 'Sportage',
                'anio': 2024,
                'descripcion': 'SUV deportiva con diseño moderno y eficiencia de combustible',
                'precio_base': Decimal('27000.00'),
                'imagen_url': 'https://images.unsplash.com/photo-1626701798572-d8bcd8c00cd2?w=500&q=80'
            },
            {
                'marca': 'Chevrolet',
                'modelo': 'Malibu',
                'anio': 2024,
                'descripcion': 'Sedán robusto con espacioso interior y tecnología moderna',
                'precio_base': Decimal('24500.00'),
                'imagen_url': 'https://images.unsplash.com/photo-1609335314336-0cd76b3efe2d?w=500&q=80'
            },
            {
                'marca': 'Ford',
                'modelo': 'Fusion',
                'anio': 2023,
                'descripcion': 'Sedán híbrido con tecnología de conducción autónoma',
                'precio_base': Decimal('25000.00'),
                'imagen_url': 'https://images.unsplash.com/photo-1609351537893-87b66e9a5a99?w=500&q=80'
            },
            {
                'marca': 'BMW',
                'modelo': '320i',
                'anio': 2024,
                'descripcion': 'Sedán de lujo con motor de alto rendimiento y interior premium',
                'precio_base': Decimal('45000.00'),
                'imagen_url': 'https://images.unsplash.com/photo-1519641776a10-3fc46ef32a77?w=500&q=80'
            },
        ]

        # Crear vehículos
        created_count = 0
        for vehicle_data in vehicles:
            vehiculo, created = Vehiculo.objects.get_or_create(
                marca=vehicle_data['marca'],
                modelo=vehicle_data['modelo'],
                anio=vehicle_data['anio'],
                defaults={
                    'descripcion': vehicle_data['descripcion'],
                    'precio_base': vehicle_data['precio_base'],
                    'imagen_url': vehicle_data['imagen_url'],
                }
            )
            if created:
                created_count += 1
                self.stdout.write(
                    self.style.SUCCESS(f'✓ Creado: {vehiculo.anio} {vehiculo.marca} {vehiculo.modelo}')
                )
            else:
                self.stdout.write(
                    self.style.WARNING(f'⊘ Ya existe: {vehiculo.anio} {vehiculo.marca} {vehiculo.modelo}')
                )

        self.stdout.write(
            self.style.SUCCESS(f'\n✓ Total creados: {created_count} vehículos')
        )
