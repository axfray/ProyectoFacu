from django.urls import path
from django.contrib.auth import views as auth_views
from . import views

urlpatterns = [
    # 1. Páginas Principales e Institucionales
    path('', views.home, name='home'),
    path('home/', views.home),
    path('quien-soy/', views.quien_soy, name='quien_soy'),
    path('capacitaciones/', views.capacitaciones, name='capacitaciones'),
    path('contacto/', views.contacto, name='contacto'),
    path('curso/<int:curso_id>/', views.detalle_curso, name='detalle_curso'),

    # 2. Flujo B2C (Mercado Pago y Catálogo)
    path('cursos/', views.catalogo_cursos, name='catalogo_cursos'),
    path('comprar/<int:curso_id>/', views.iniciar_compra_b2c, name='comprar_curso'),
    path('webhook/mercadopago/', views.webhook_mercadopago, name='webhook_mp'),
    path('pago-exitoso/', views.pago_exitoso, name='pago_exitoso'),
    path('pago-fallido/', views.pago_fallido, name='pago_fallido'),

    # 3. Flujo B2B y Panel del Alumno
    path('canjear/', views.canjear_codigo, name='canjear_codigo'),
    path('mis-cursos/', views.mis_cursos, name='mis_cursos'),

    # 4. Autenticación y Registro de Usuarios
    path('login/', auth_views.LoginView.as_view(template_name='capacitaciones/login.html'), name='login'),
    path('logout/', auth_views.LogoutView.as_view(next_page='home'), name='logout'),
    path('registro/', views.registro, name='registro'),
    path('activar/<uidb64>/<token>/', views.activar_cuenta, name='activar_cuenta'),


    # Aula Virtual y Evaluaciones
    path('curso/<int:curso_id>/aula/', views.ver_curso, name='ver_curso'),
    path('curso/<int:curso_id>/examen/', views.tomar_examen, name='tomar_examen'),
]