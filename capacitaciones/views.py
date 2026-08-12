import json
import mercadopago
from django.conf import settings
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.views.decorators.csrf import csrf_exempt
from django.http import HttpResponse, JsonResponse
from django.contrib import messages
from django.contrib.auth.models import User

# Todos los modelos importados juntos al inicio
from .models import Curso, Inscripcion, CodigoB2B, PerfilUsuario


# ==========================================
# 1. FLUJO B2B: CANJEAR CÓDIGO EMPRESARIAL
# ==========================================
@login_required
def canjear_codigo(request):
    if request.method == 'POST':
        codigo_ingresado = request.POST.get('codigo', '').strip()
        
        try:
            codigo_obj = CodigoB2B.objects.get(codigo=codigo_ingresado, activo=True)
            
            # Validación A: Verificar si el usuario YA está inscripto en este curso
            ya_inscripto = Inscripcion.objects.filter(usuario=request.user, curso=codigo_obj.curso).exists()
            if ya_inscripto:
                messages.warning(request, f"Ya te encuentras inscripto en el curso '{codigo_obj.curso.titulo}'.")
                return redirect('mis_cursos')

            # Validación B: Verificar cupos disponibles
            if codigo_obj.usos_actuales < codigo_obj.usos_maximos:
                # 1. Crear la inscripción
                Inscripcion.objects.create(
                    usuario=request.user,
                    curso=codigo_obj.curso,
                    origen_inscripcion='codigo_b2b',
                    codigo_b2b=codigo_obj
                )
                
                # 2. Vincular empresa al perfil del usuario
                perfil, _ = PerfilUsuario.objects.get_or_create(user=request.user)
                perfil.empresa = codigo_obj.empresa
                perfil.save()

                # 3. Descontar cupo
                codigo_obj.usos_actuales += 1
                if codigo_obj.usos_actuales >= codigo_obj.usos_maximos:
                    codigo_obj.activo = False
                codigo_obj.save()

                messages.success(request, f"¡Inscripción exitosa al curso {codigo_obj.curso.titulo}!")
                return redirect('mis_cursos')
            else:
                messages.error(request, "Este código ya agotó el límite de licencias permitidas.")

        except CodigoB2B.DoesNotExist:
            messages.error(request, "El código ingresado es inválido o no existe.")

    return render(request, 'capacitaciones/canjear_codigo.html')


# ==========================================
# 2. VISTA DE MIS CURSOS (DASHBOARD ALUMNO)
# ==========================================
@login_required
def mis_cursos(request):
    # Obtiene las inscripciones del usuario logueado
    inscripciones = Inscripcion.objects.filter(usuario=request.user)
    return render(request, 'capacitaciones/mis_cursos.html', {'inscripciones': inscripciones})


# ==========================================
# 3. FLUJO B2C: MERCADO PAGO
# ==========================================

# Catálogo público de cursos
def catalogo_cursos(request):
    cursos = Curso.objects.filter(activo=True, precio_b2c__gt=0)
    return render(request, 'capacitaciones/catalogo.html', {'cursos': cursos})


# Generación del Checkout Pro de Mercado Pago
@login_required
def iniciar_compra_b2c(request, curso_id):
    curso = get_object_or_404(Curso, id=curso_id, activo=True)
    sdk = mercadopago.SDK(settings.MERCADOPAGO_ACCESS_TOKEN)

    # Construir URLs dinámicas
    base_url = request.build_absolute_uri('/')[:-1] # Obtiene http://127.0.0.1:8000
    notification_url = request.build_absolute_uri('/webhook/mercadopago/')
    
    # Mercado Pago rechaza URLs de retorno o notificación no seguras en auto_return
    if "127.0.0.1" in notification_url or "localhost" in notification_url:
        notification_url = "https://webhook.site/test"

    preference_data = {
        "items": [
            {
                "id": str(curso.id),
                "title": curso.titulo,
                "quantity": 1,
                "currency_id": "ARS",
                "unit_price": float(curso.precio_b2c),
            }
        ],
        "payer": {
            "email": request.user.email or "test_user@test.com",
            "name": request.user.first_name or request.user.username,
        },
        "back_urls": {
            "success": f"{base_url}/pago-exitoso/",
            "failure": f"{base_url}/pago-fallido/",
            "pending": f"{base_url}/pago-fallido/",
        },
        # Comentamos auto_return en entorno local para evitar el rechazo con URLs HTTP
        # "auto_return": "approved",
        "notification_url": notification_url,
        "external_reference": f"{request.user.id}_{curso.id}"
    }

    preference_response = sdk.preference().create(preference_data)
    preference = preference_response.get("response", {})

    # Verificar si Mercado Pago devolvió init_point correctamente
    if "init_point" in preference:
        return redirect(preference["init_point"])
    else:
        # En caso de error de credenciales o formato, mostramos el detalle exacto en consola
        print("Error al crear preferencia MP:", preference)
        messages.error(request, f"Error de pasarela de pago: {preference.get('message', 'Credenciales o datos inválidos')}")
        return redirect('catalogo_cursos')

# Receptor Webhook
@csrf_exempt
def webhook_mercadopago(request):
    if request.method == 'POST':
        topic = request.GET.get('topic') or request.GET.get('type')
        payment_id = request.GET.get('id') or request.GET.get('data.id')

        if topic == 'payment' and payment_id:
            sdk = mercadopago.SDK(settings.MERCADOPAGO_ACCESS_TOKEN)
            payment_info = sdk.payment().get(payment_id)
            payment = payment_info["response"]

            if payment.get("status") == "approved":
                external_ref = payment.get("external_reference")
                if external_ref:
                    user_id, curso_id = external_ref.split("_")

                    usuario = User.objects.get(id=int(user_id))
                    curso = Curso.objects.get(id=int(curso_id))

                    Inscripcion.objects.get_or_create(
                        usuario=usuario,
                        curso=curso,
                        defaults={'origen_inscripcion': 'compra_b2c'}
                    )

        return HttpResponse(status=200)
    return HttpResponse(status=400)


# Pantallas de resultado de pago
@login_required
def pago_exitoso(request):
    return render(request, 'capacitaciones/pago_exitoso.html')

@login_required
def pago_fallido(request):
    return render(request, 'capacitaciones/pago_fallido.html')

def home(request):
    # Traemos hasta 3 cursos destacados para la portada
    cursos_destacados = Curso.objects.filter(activo=True, precio_b2c__gt=0)[:3]
    return render(request, 'capacitaciones/home.html', {'cursos': cursos_destacados})