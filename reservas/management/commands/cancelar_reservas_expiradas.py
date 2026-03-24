# reservas/management/commands/cancelar_reservas_expiradas.py
# Colocar en: reservas/management/commands/cancelar_reservas_expiradas.py

from django.core.management.base import BaseCommand
from django.utils import timezone
from reservas.models import Reserva

class Command(BaseCommand):
    help = 'Cancela automáticamente las reservas pendientes cuyo tiempo de pago ha expirado'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Simula la ejecución sin cancelar realmente las reservas',
        )

    def handle(self, *args, **options):
        dry_run = options['dry_run']
        
        if dry_run:
            self.stdout.write(self.style.WARNING('🔍 MODO DRY-RUN: No se cancelarán reservas realmente'))
            self.stdout.write('')
        
        # Buscar reservas pendientes con tiempo de pago expirado
        ahora = timezone.now()
        reservas_expiradas = Reserva.objects.filter(
            estado='pendiente',
            fecha_limite_pago__lte=ahora
        ).select_related('usuario', 'funcion', 'funcion__pelicula')
        
        total = reservas_expiradas.count()
        
        if total == 0:
            self.stdout.write(self.style.SUCCESS('✅ No hay reservas expiradas por tiempo'))
            return
        
        self.stdout.write(f'🔍 Encontradas {total} reserva(s) con tiempo de pago expirado')
        self.stdout.write('')
        
        contador_canceladas = 0
        
        for reserva in reservas_expiradas:
            tiempo_expirado = (ahora - reserva.fecha_limite_pago).total_seconds() / 60
            
            self.stdout.write(
                f'📋 Reserva: {reserva.codigo_reserva} | '
                f'Usuario: {reserva.usuario.username} | '
                f'Película: {reserva.funcion.pelicula.titulo} | '
                f'Expiró hace: {int(tiempo_expirado)} minutos'
            )
            
            if not dry_run:
                reserva.estado = 'cancelada'
                reserva.save(update_fields=['estado'])
                contador_canceladas += 1
                self.stdout.write(self.style.SUCCESS('   ✅ Cancelada'))
            else:
                self.stdout.write(self.style.WARNING('   ⚠️ Sería cancelada (dry-run)'))
        
        self.stdout.write('')
        self.stdout.write(self.style.SUCCESS('='*60))
        if dry_run:
            self.stdout.write(self.style.WARNING(f'⚠️ Se cancelarían {total} reserva(s) (modo simulación)'))
        else:
            self.stdout.write(self.style.SUCCESS(f'✅ {contador_canceladas} reserva(s) cancelada(s) exitosamente'))
            self.stdout.write(self.style.SUCCESS(f'💺 Asientos liberados y disponibles nuevamente'))
        self.stdout.write(self.style.SUCCESS('='*60))