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
                'imagen_url': 'https://res.cloudinary.com/dshxmkd1v/image/upload/v1781578975/mlp-img-top-2024-corolla_a4x4mh.avif'
            },
            {
                'marca': 'Honda',
                'modelo': 'Civic',
                'anio': 2024,
                'descripcion': 'Sedán deportivo con tecnología avanzada y diseño moderno',
                'precio_base': Decimal('24000.00'),
                'imagen_url': 'https://res.cloudinary.com/dshxmkd1v/image/upload/v1781578831/2024-Honda-Civic-Si-Red_zaryif.webp'
            },
            {
                'marca': 'Hyundai',
                'modelo': 'Elantra',
                'anio': 2023,
                'descripcion': 'Sedán económico con tecnología touchscreen de última generación',
                'precio_base': Decimal('20500.00'),
                'imagen_url': 'https://res.cloudinary.com/dshxmkd1v/image/upload/v1781579120/hyundai_20elantrasesd6t_angularfront_black_xwpke0.webp'
            },
            {
                'marca': 'Volkswagen',
                'modelo': 'Passat',
                'anio': 2024,
                'descripcion': 'Sedán premium con interior lujoso y tecnología de punta',
                'precio_base': Decimal('28000.00'),
                'imagen_url': 'https://res.cloudinary.com/dshxmkd1v/image/upload/v1781579047/volkswagen-passat-2024-1021__d8a9f2157418048c_xl_hlwcxi.webp'
            },
            {
                'marca': 'Mazda',
                'modelo': 'CX-5',
                'anio': 2024,
                'descripcion': 'SUV compacta versátil con tracción AWD y manejo deportivo',
                'precio_base': Decimal('28500.00'),
                'imagen_url': 'https://res.cloudinary.com/dshxmkd1v/image/upload/v1781579275/mlp-img-top-2024-cx5_rk7nko.avif'
            },
            {
                'marca': 'Nissan',
                'modelo': 'Altima',
                'anio': 2023,
                'descripcion': 'Sedán ejecutivo con confort premium y tecnología de seguridad',
                'precio_base': Decimal('26500.00'),
                'imagen_url': 'https://res.cloudinary.com/dshxmkd1v/image/upload/v1781578919/model1_mp2uwd.png'
            },
            {
                'marca': 'Kia',
                'modelo': 'Sportage',
                'anio': 2024,
                'descripcion': 'SUV deportiva con diseño moderno y eficiencia de combustible',
                'precio_base': Decimal('27000.00'),
                'imagen_url': 'https://res.cloudinary.com/dshxmkd1v/image/upload/v1781579216/2024_24_1_wbxp05.png'
            },
            {
                'marca': 'Chevrolet',
                'modelo': 'Malibu',
                'anio': 2024,
                'descripcion': 'Sedán robusto con espacioso interior y tecnología moderna',
                'precio_base': Decimal('24500.00'),
                'imagen_url': 'https://res.cloudinary.com/dshxmkd1v/image/upload/v1781578700/2024.malibu.profile_u3279g.webp'
            },
            {
                'marca': 'Ford',
                'modelo': 'Fusion',
                'anio': 2023,
                'descripcion': 'Sedán híbrido con tecnología de conducción autónoma',
                'precio_base': Decimal('25000.00'),
                'imagen_url': 'https://res.cloudinary.com/dshxmkd1v/image/upload/v1781578786/Fusion_1__ev1zup.png'
            },
            {
                'marca': 'BMW',
                'modelo': '320i',
                'anio': 2024,
                'descripcion': 'Sedán de lujo con motor de alto rendimiento y interior premium',
                'precio_base': Decimal('45000.00'),
                'imagen_url': 'https://res.cloudinary.com/dshxmkd1v/image/upload/v1781578536/2024-BMW-3-Series-Gray_lzelxf.webp'
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
