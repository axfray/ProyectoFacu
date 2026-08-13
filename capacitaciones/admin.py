from django.contrib import admin
from .models import (
    Empresa, PerfilUsuario, Curso, Leccion, 
    Examen, Pregunta, OpcionRespuesta, 
    CodigoB2B, Inscripcion, IntentoExamen, Certificado
)

class OpcionInline(admin.TabularInline):
    model = OpcionRespuesta
    extra = 4

class PreguntaAdmin(admin.ModelAdmin):
    inlines = [OpcionInline]

class LeccionInline(admin.TabularInline):
    model = Leccion
    extra = 1

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

admin.site.register(Empresa)
admin.site.register(PerfilUsuario)
admin.site.register(Examen)
admin.site.register(Pregunta, PreguntaAdmin)
admin.site.register(Inscripcion)
admin.site.register(IntentoExamen)
admin.site.register(Certificado)