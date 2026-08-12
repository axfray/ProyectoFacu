from django.contrib import admin
from .models import (
    Empresa, PerfilUsuario, Curso, Leccion, 
    Examen, Pregunta, OpcionRespuesta, 
    CodigoB2B, Inscripcion, IntentoExamen, Certificado
)

# Permite agregar opciones directamente dentro de la pregunta
class OpcionInline(admin.TabularInline):
    model = OpcionRespuesta
    extra = 4

class PreguntaAdmin(admin.ModelAdmin):
    inlines = [OpcionInline]

# Permite ver lecciones dentro del curso
class LeccionInline(admin.TabularInline):
    model = Leccion
    extra = 1

class CursoAdmin(admin.ModelAdmin):
    inlines = [LeccionInline]
    list_display = ('titulo', 'precio_b2c', 'activo', 'creado_en')
    list_filter = ('activo',)

class CodigoB2BAdmin(admin.ModelAdmin):
    list_display = ('codigo', 'empresa', 'curso', 'usos_actuales', 'usos_maximos', 'activo')
    list_filter = ('empresa', 'curso', 'activo')
    search_fields = ('codigo', 'empresa__nombre')

# Registro de modelos en el Admin
admin.site.register(Empresa)
admin.site.register(PerfilUsuario)
admin.site.register(Curso, CursoAdmin)
admin.site.register(Examen)
admin.site.register(Pregunta, PreguntaAdmin)
admin.site.register(CodigoB2B, CodigoB2BAdmin)
admin.site.register(Inscripcion)
admin.site.register(IntentoExamen)
admin.site.register(Certificado)
