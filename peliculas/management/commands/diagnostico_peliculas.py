from django.core.management.base import BaseCommand
from peliculas.models import Pelicula
import os

class Command(BaseCommand):
    help = "Diagnóstico completo de películas"

    def handle(self, *args, **options):
        self.stdout.write("\n" + "="*70)
        self.stdout.write("🔍 DIAGNÓSTICO COMPLETO DE PELÍCULAS")
        self.stdout.write("="*70 + "\n")

        peliculas = Pelicula.objects.all()
        self.stdout.write(f"📊 Total películas: {peliculas.count()}\n")

        for i, pelicula in enumerate(peliculas, 1):
            self.stdout.write(f"{'='*70}")
            self.stdout.write(f"🎬 PELÍCULA {i}: {pelicula.titulo}")
            self.stdout.write(f"{'='*70}")

            self.stdout.write("\n📋 INFORMACIÓN BÁSICA:")
            self.stdout.write(f"   ID: {pelicula.id}")
            self.stdout.write(f"   Título: '{pelicula.titulo}' (len={len(pelicula.titulo)})")

            campos = [
                ('genero', pelicula.genero),
                ('clasificacion', pelicula.clasificacion),
                ('duracion', pelicula.duracion),
                ('año', pelicula.año),
                ('en_cartelera', pelicula.en_cartelera),
                ('sinopsis', pelicula.sinopsis),
                ('director', pelicula.director),
                ('actores', pelicula.actores),
                ('fecha_estreno', pelicula.fecha_estreno),
            ]

            self.stdout.write("\n📝 CAMPOS:")
            problemas = []

            for nombre, valor in campos:
                tipo = type(valor).__name__

                if valor is None:
                    self.stdout.write(f"   ❌ {nombre}: None")
                    problemas.append(f"{nombre}=None")

                elif isinstance(valor, str):
                    if len(valor.strip()) == 0:
                        self.stdout.write(f"   ⚠️ {nombre}: vacío")
                        problemas.append(f"{nombre}=vacío")
                    else:
                        preview = valor[:50] + "..." if len(valor) > 50 else valor
                        self.stdout.write(f"   ✅ {nombre}: '{preview}' (len={len(valor)})")

                else:
                    self.stdout.write(f"   ✅ {nombre}: {valor} (tipo: {tipo})")

            # Poster
            if pelicula.poster:
                self.stdout.write(f"   ✅ poster: {pelicula.poster.name}")

                try:
                    if hasattr(pelicula.poster, 'path') and os.path.exists(pelicula.poster.path):
                        size = os.path.getsize(pelicula.poster.path)
                        self.stdout.write(f"      - Tamaño: {size/1024:.2f} KB")
                    else:
                        self.stdout.write("      ❌ archivo no existe")
                        problemas.append("poster_no_existe")

                except Exception as e:
                    self.stdout.write(f"      ❌ error: {e}")
                    problemas.append(f"poster_error:{e}")
            else:
                self.stdout.write("   ❌ poster: None")
                problemas.append("poster=None")

            if problemas:
                self.stdout.write(f"\n⚠️ PROBLEMAS: {', '.join(problemas)}")
            else:
                self.stdout.write("\n✅ SIN PROBLEMAS")

            self.stdout.write("\n🔤 __str__:")
            try:
                self.stdout.write(f"   {str(pelicula)}")
            except Exception as e:
                self.stdout.write(f"   ❌ {e}")

            self.stdout.write("\n")

        self.stdout.write("\n" + "="*70)
        self.stdout.write("✅ DIAGNÓSTICO COMPLETADO")
        self.stdout.write("="*70 + "\n")
