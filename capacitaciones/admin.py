from django.contrib import admin
from .models import (
    Empresa, PerfilUsuario, Curso, Leccion, 
    Examen, Pregunta, Opcion, 
    CodigoB2B, Inscripcion, IntentoExamen, Certificado
)

class LeccionInline(admin.TabularInline):
    model = Leccion
    extra = 1

class OpcionInline(admin.TabularInline):
    model = Opcion
    extra = 4

@admin.register(Pregunta)
class PreguntaAdmin(admin.ModelAdmin):
    inlines = [OpcionInline]
    list_display = ('texto', 'curso')
    list_filter = ('curso',)
    search_fields = ('texto',)

@admin.register(Curso)
class CursoAdmin(admin.ModelAdmin):
    list_display = ('titulo', 'precio_b2c', 'activo', 'creado_en')
    list_filter = ('activo',)
    search_fields = ('titulo',)
    inlines = [LeccionInline]

@admin.register(CodigoB2B)
class CodigoB2BAdmin(admin.ModelAdmin):
    list_display = ('codigo', 'empresa', 'curso', 'usos_actuales', 'usos_maximos', 'activo')
    list_filter = ('empresa', 'curso', 'activo')
    search_fields = ('codigo', 'empresa__nombre')

@admin.register(IntentoExamen)
class IntentoExamenAdmin(admin.ModelAdmin):
    list_display = ('usuario', 'examen', 'nota_obtenida', 'aprobado', 'fecha_intento')
    list_filter = ('aprobado',)

admin.site.register(Empresa)
admin.site.register(PerfilUsuario)
admin.site.register(Examen)
admin.site.register(Leccion)
admin.site.register(Inscripcion)
admin.site.register(Certificado)