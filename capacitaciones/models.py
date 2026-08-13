from django.db import models
from django.contrib.auth.models import User

class Empresa(models.Model):
    nombre = models.CharField(max_length=150)
    cuit_tax_id = models.CharField(max_length=50, unique=True, null=True, blank=True)
    contacto_email = models.EmailField(null=True, blank=True)
    creado_en = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.nombre

class PerfilUsuario(models.Model):
    ROLES = (
        ('super_admin', 'Super Admin'),
        ('empresa_admin', 'Admin Empresa'),
        ('alumno', 'Alumno'),
    )
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='perfil')
    rol = models.CharField(max_length=20, choices=ROLES, default='alumno')
    empresa = models.ForeignKey(Empresa, on_delete=models.SET_NULL, null=True, blank=True, related_name='empleados')

    def __str__(self):
        return f"{self.user.username} ({self.rol})"

class Curso(models.Model):
    titulo = models.CharField(max_length=200)
    descripcion = models.TextField()
    precio_b2c = models.DecimalField(max_digits=10, decimal_places=2, default=0.0)
    imagen_url = models.URLField(blank=True, null=True, help_text="URL de la imagen del curso")
    activo = models.BooleanField(default=True)
    creado_en = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.titulo

class Leccion(models.Model):
    curso = models.ForeignKey(Curso, on_delete=models.CASCADE, related_name='lecciones')
    titulo = models.CharField(max_length=200)
    contenido_html = models.TextField(blank=True)
    url_video = models.URLField(blank=True, null=True)
    orden = models.PositiveIntegerField(default=1)

    def __str__(self):
        return f"{self.curso.titulo} - {self.titulo}"

class Examen(models.Model):
    curso = models.OneToOneField(Curso, on_delete=models.CASCADE, related_name='examen')
    nota_minima_aprobacion = models.PositiveIntegerField(default=70)
    limite_intentos = models.PositiveIntegerField(default=3)

    def __str__(self):
        return f"Examen de {self.curso.titulo}"

class Pregunta(models.Model):
    examen = models.ForeignKey(Examen, on_delete=models.CASCADE, related_name='preguntas')
    enunciado = models.TextField()

    def __str__(self):
        return self.enunciado

class OpcionRespuesta(models.Model):
    pregunta = models.ForeignKey(Pregunta, on_delete=models.CASCADE, related_name='opciones')
    texto_opcion = models.CharField(max_length=255)
    es_correcta = models.BooleanField(default=False)

    def __str__(self):
        return f"{self.texto_opcion} ({'Correcta' if self.es_correcta else 'Incorrecta'})"

class CodigoB2B(models.Model):
    codigo = models.CharField(max_length=50, unique=True)
    empresa = models.ForeignKey(Empresa, on_delete=models.CASCADE, related_name='codigos')
    curso = models.ForeignKey(Curso, on_delete=models.CASCADE)
    usos_maximos = models.PositiveIntegerField()
    usos_actuales = models.PositiveIntegerField(default=0)
    activo = models.BooleanField(default=True)

    def __str__(self):
        return f"{self.codigo} - {self.empresa.nombre}"

class Inscripcion(models.Model):
    ORIGENES = (
        ('compra_b2c', 'Compra B2C'),
        ('codigo_b2b', 'Código B2B'),
        ('manual_admin', 'Manual Admin'),
    )
    usuario = models.ForeignKey(User, on_delete=models.CASCADE, related_name='inscripciones')
    curso = models.ForeignKey(Curso, on_delete=models.CASCADE)
    origen_inscripcion = models.CharField(max_length=20, choices=ORIGENES)
    codigo_b2b = models.ForeignKey(CodigoB2B, on_delete=models.SET_NULL, null=True, blank=True)
    fecha_inscripcion = models.DateTimeField(auto_now_add=True)

class IntentoExamen(models.Model):
    usuario = models.ForeignKey(User, on_delete=models.CASCADE, related_name='intentos')
    examen = models.ForeignKey(Examen, on_delete=models.CASCADE)
    nota_obtenida = models.PositiveIntegerField()
    aprobado = models.BooleanField()
    fecha_intento = models.DateTimeField(auto_now_add=True)

class Certificado(models.Model):
    codigo_validacion = models.CharField(max_length=100, unique=True)
    usuario = models.ForeignKey(User, on_delete=models.CASCADE, related_name='certificados')
    curso = models.ForeignKey(Curso, on_delete=models.CASCADE)
    fecha_emision = models.DateTimeField(auto_now_add=True)