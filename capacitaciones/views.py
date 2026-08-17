import json
import mercadopago
from django.conf import settings
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.views.decorators.csrf import csrf_exempt
from django.http import HttpResponse, JsonResponse
from django.contrib import messages
from django.contrib.auth.models import User
from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.utils.http import urlsafe_base64_encode, urlsafe_base64_decode
from django.utils.encoding import force_bytes, force_str
from django.contrib.auth.tokens import default_token_generator
import uuid
from .models import Curso, Inscripcion, Examen, Pregunta, Opcion, IntentoExamen, Certificado


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

def quien_soy(request):
    return render(request, 'capacitaciones/quien_soy.html')

def capacitaciones(request):
    # Obtenemos los cursos activos desde la base de datos
    cursos = Curso.objects.filter(activo=True)
    
    # Se los pasamos a la plantilla mediante el diccionario de contexto
    return render(request, 'capacitaciones/catalogo.html', {'cursos': cursos}) 

def contacto(request):
    return render(request, 'capacitaciones/contacto.html')


def detalle_curso(request, curso_id):
    curso = get_object_or_404(Curso, id=curso_id)
    return render(request, 'capacitaciones/detalle_curso.html', {'curso': curso})

# 1. VISTA DE REGISTRO
def registro(request):
    if request.method == 'POST':
        username = request.POST.get('username').strip()
        email = request.POST.get('email').strip()
        password = request.POST.get('password')

        # Validar si el usuario o email ya existen
        if User.objects.filter(username=username).exists():
            messages.error(request, "El nombre de usuario ya está registrado.")
            return render(request, 'capacitaciones/registro.html')

        if User.objects.filter(email=email).exists():
            messages.error(request, "El correo electrónico ya está registrado.")
            return render(request, 'capacitaciones/registro.html')

        # Crear el usuario inactivo
        user = User.objects.create_user(username=username, email=email, password=password)
        user.is_active = False  # No podrá loguearse hasta verificar email
        user.save()

        # Crear también su PerfilUsuario (si lo utilizas)
        PerfilUsuario.objects.get_or_create(user=user)

        # Generar Token y Enlace de Verificación
        uid = urlsafe_base64_encode(force_bytes(user.pk))
        token = default_token_generator.make_token(user)
        domain = request.build_absolute_uri('/')[:-1]
        link_activacion = f"{domain}/activar/{uid}/{token}/"

        # Contenido del correo
        asunto = "Confirma tu cuenta - Academia S&H"
        mensaje = f"Hola {username},\n\nGracias por registrarte. Para activar tu cuenta, haz clic en el siguiente enlace:\n{link_activacion}\n\nSi no solicitaste este registro, ignora este mensaje."

        try:
            send_mail(asunto, mensaje, settings.DEFAULT_FROM_EMAIL, [email])
            messages.success(request, "¡Registro casi listo! Te hemos enviado un correo de confirmación. Revisa tu bandeja de entrada o Spam.")
            return redirect('login')
        except Exception as e:
            messages.error(request, "Ocurrió un error al enviar el correo de activación. Inténtalo más tarde.")

    return render(request, 'capacitaciones/registro.html')


# 2. VISTA DE ACTIVACIÓN DE CUENTA
def activar_cuenta(request, uidb64, token):
    try:
        uid = force_str(urlsafe_base64_decode(uidb64))
        user = User.objects.get(pk=uid)
    except (TypeError, ValueError, OverflowError, User.DoesNotExist):
        user = None

    if user is not None and default_token_generator.check_token(user, token):
        user.is_active = True
        user.save()
        messages.success(request, "¡Tu cuenta ha sido activada con éxito! Ya puedes iniciar sesión.")
        return redirect('login')
    else:
        messages.error(request, "El enlace de activación es inválido o ha expirado.")
        return redirect('home')

@login_required
def ver_curso(request, curso_id):
    curso = get_object_or_404(Curso, id=curso_id)

    # Validar inscripción
    if not Inscripcion.objects.filter(usuario=request.user, curso=curso).exists():
        messages.error(request, "Debes estar inscripto para ver las clases.")
        return redirect('mis_cursos')

    lecciones = curso.lecciones.order_by('orden')
    leccion_principal = lecciones.first()  # Primera lección para reproducir

    return render(request, 'capacitaciones/ver_curso.html', {
        'curso': curso,
        'lecciones': lecciones,
        'leccion_principal': leccion_principal
    })


@login_required
def tomar_examen(request, curso_id):
    curso = get_object_or_404(Curso, id=curso_id)

    # 1. Validar inscripción
    if not Inscripcion.objects.filter(usuario=request.user, curso=curso).exists():
        messages.error(request, "Debes estar inscripto para rendir la evaluación.")
        return redirect('mis_cursos')

    # 2. Obtener examen
    try:
        examen = curso.examen
    except Examen.DoesNotExist:
        messages.warning(request, "Este curso aún no tiene un examen habilitado.")
        return redirect('ver_curso', curso_id=curso.id)

    # 3. Validar límite de intentos
    intentos_realizados = IntentoExamen.objects.filter(usuario=request.user, examen=examen).count()
    if intentos_realizados >= examen.limite_intentos:
        messages.error(request, f"Has alcanzado el límite máximo de {examen.limite_intentos} intentos para este examen.")
        return redirect('mis_cursos')

    # CORREGIDO: Se busca Pregunta por curso y se precargan las opciones
    preguntas = Pregunta.objects.filter(curso=curso)

    # 4. Procesar respuestas
    if request.method == 'POST':
        total_preguntas = preguntas.count()
        if total_preguntas == 0:
            messages.error(request, "El examen no contiene preguntas activas.")
            return redirect('ver_curso', curso_id=curso.id)

        respuestas_correctas = 0
        for pregunta in preguntas:
            opcion_id = request.POST.get(f'pregunta_{pregunta.id}')
            if opcion_id:
                try:
                    # CORREGIDO: Se utiliza la clase Opcion en lugar de OpcionRespuesta
                    opcion = Opcion.objects.get(id=int(opcion_id), pregunta=pregunta)
                    if opcion.es_correcta:
                        respuestas_correctas += 1
                except Opcion.DoesNotExist:
                    pass

        # Calcular porcentaje (0 - 100)
        nota_obtenida = int((respuestas_correctas / total_preguntas) * 100)
        aprobado = nota_obtenida >= examen.nota_minima_aprobacion

        # Registrar intento
        IntentoExamen.objects.create(
            usuario=request.user,
            examen=examen,
            nota_obtenida=nota_obtenida,
            aprobado=aprobado
        )

        # Generar certificado si aprobó y no tenía uno previo
        if aprobado and not Certificado.objects.filter(usuario=request.user, curso=curso).exists():
            Certificado.objects.create(
                codigo_validacion=str(uuid.uuid4())[:12].upper(),
                usuario=request.user,
                curso=curso
            )

        return render(request, 'capacitaciones/resultado_examen.html', {
            'curso': curso,
            'examen': examen,
            'nota_obtenida': nota_obtenida,
            'aprobado': aprobado,
            'correctas': respuestas_correctas,
            'total': total_preguntas,
            'intentos_restantes': examen.limite_intentos - (intentos_realizados + 1)
        })

    return render(request, 'capacitaciones/examen.html', {
        'curso': curso,
        'examen': examen,
        'preguntas': preguntas,
        'intentos_restantes': examen.limite_intentos - intentos_realizados
    })