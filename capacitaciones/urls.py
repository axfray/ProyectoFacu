from django.urls import path
from django.contrib.auth import views as auth_views
from . import views

urlpatterns = [
    # Portada (responde en la raíz y en /home/)
    path('', views.home, name='home'),
    path('home/', views.home),

    # Flujo B2C (Mercado Pago y Catálogo)
    path('cursos/', views.catalogo_cursos, name='catalogo_cursos'),
    path('comprar/<int:curso_id>/', views.iniciar_compra_b2c, name='comprar_curso'),
    path('webhook/mercadopago/', views.webhook_mercadopago, name='webhook_mp'),
    path('pago-exitoso/', views.pago_exitoso, name='pago_exitoso'),
    path('pago-fallido/', views.pago_fallido, name='pago_fallido'),

    # Flujo B2B y Alumnos
    path('canjear/', views.canjear_codigo, name='canjear_codigo'),
    path('mis-cursos/', views.mis_cursos, name='mis_cursos'),

    # Rutas de Autenticación
    path('login/', auth_views.LoginView.as_view(template_name='capacitaciones/login.html'), name='login'),
    path('logout/', auth_views.LogoutView.as_view(next_page='home'), name='logout'),
]