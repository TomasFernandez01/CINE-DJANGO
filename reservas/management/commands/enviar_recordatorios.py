# reservas/management/commands/enviar_recordatorios.py
# Crear esta estructura de carpetas:
# reservas/
#   management/
#     __init__.py  (archivo vacío)
#     commands/
#       __init__.py  (archivo vacío)
#       enviar_recordatorios.py  (este archivo)

from django.core.management.base import BaseCommand
from django.utils import timezone
from datetime import timedelta
from reservas.models import Reserva

try:
    from utils.email_utils import enviar_email_recordatorio_funcion
    EMAIL_DISPONIBLE = True
except ImportError:
    EMAIL_DISPONIBLE = False


class Command(BaseCommand):
    help = 'Envía recordatorios por email a usuarios con funciones mañana'

    def handle(self, *args, **options):
        if not EMAIL_DISPONIBLE:
            self.stdout.write(self.style.ERROR('❌ Módulo de emails no disponible'))
            return
        
        # Calcular el rango de fechas (mañana entre 00:00 y 23:59)
        ahora = timezone.now()
        manana_inicio = (ahora + timedelta(days=1)).replace(hour=0, minute=0, second=0, microsecond=0)
        manana_fin = manana_inicio + timedelta(days=1)
        
        # Buscar reservas confirmadas con función mañana
        reservas = Reserva.objects.filter(
            estado='confirmada',
            funcion__fecha_hora__gte=manana_inicio,
            funcion__fecha_hora__lt=manana_fin
        ).select_related('usuario', 'funcion', 'funcion__pelicula', 'funcion__sala')
        
        contador_exitosos = 0
        contador_fallidos = 0
        
        self.stdout.write(f'🔍 Buscando reservas para {manana_inicio.strftime("%d/%m/%Y")}...')
        self.stdout.write(f'📧 Encontradas {reservas.count()} reservas para enviar recordatorio')
        
        for reserva in reservas:
            try:
                if enviar_email_recordatorio_funcion(reserva):
                    contador_exitosos += 1
                    self.stdout.write(
                        self.style.SUCCESS(
                            f'✅ Recordatorio enviado a {reserva.usuario.email} '
                            f'para "{reserva.funcion.pelicula.titulo}"'
                        )
                    )
                else:
                    contador_fallidos += 1
                    self.stdout.write(
                        self.style.WARNING(
                            f'⚠️ Falló el envío a {reserva.usuario.email}'
                        )
                    )
            except Exception as e:
                contador_fallidos += 1
                self.stdout.write(
                    self.style.ERROR(
                        f'❌ Error enviando a {reserva.usuario.email}: {str(e)}'
                    )
                )
        
        # Resumen
        self.stdout.write('')
        self.stdout.write(self.style.SUCCESS('='*50))
        self.stdout.write(self.style.SUCCESS(f'✅ Recordatorios enviados: {contador_exitosos}'))
        if contador_fallidos > 0:
            self.stdout.write(self.style.WARNING(f'⚠️ Fallidos: {contador_fallidos}'))
        self.stdout.write(self.style.SUCCESS('='*50))