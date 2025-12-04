import qrcode
import io
import base64
import uuid
import requests
from datetime import datetime
import resend

# Configuración
IMG_BB_API_KEY = "15132cfb77719e5061c3278a7fce1a17"  # TU API KEY AQUÍ
resend.api_key = "re_2DMkEMqu_9LGx97eTPHSf2dfVbbK2fzh2"

def send_email(to_email: str, subject: str, message: str, html_content: str = None):
    """
    Envía email usando Resend API
    """
    try:
        print(f"📧 [RESEND] Enviando email a: {to_email}")
        
        params = {
            "from": "OlympiaHub <onboarding@resend.dev>",
            "to": [to_email],
            "subject": subject,
            "text": message,
        }
        
        if html_content:
            params["html"] = html_content
        
        email = resend.Emails.send(params)
        
        print(f"✅ [RESEND] Email enviado. ID: {email['id']}")
        return True
        
    except Exception as e:
        print(f"❌ [RESEND] Error: {e}")
        return False

def generate_qr_image(qr_data: str):
    """Genera una imagen QR y la devuelve como bytes"""
    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_L,
        box_size=10,
        border=4,
    )
    qr.add_data(qr_data)
    qr.make(fit=True)
    
    img = qr.make_image(fill_color="black", back_color="white")
    
    # Convertir a bytes
    buffered = io.BytesIO()
    img.save(buffered, format="PNG")
    return buffered.getvalue()

def upload_qr_to_imgbb(qr_image_bytes: bytes) -> str:
    """
    Sube la imagen QR a ImgBB y devuelve la URL
    """
    try:
        print("📤 Subiendo QR a ImgBB...")
        
        # Convertir a base64
        qr_base64 = base64.b64encode(qr_image_bytes).decode()
        
        # Subir a ImgBB
        response = requests.post(
            "https://api.imgbb.com/1/upload",
            data={
                "key": IMG_BB_API_KEY,
                "image": qr_base64,
                "name": f"qr_reserva_{uuid.uuid4().hex[:8]}",
                "expiration": 604800  # 7 días en segundos
            }
        )
        
        if response.status_code == 200:
            data = response.json()
            qr_url = data["data"]["url"]
            print(f"✅ QR subido a ImgBB: {qr_url}")
            return qr_url
        else:
            print(f"❌ Error subiendo a ImgBB: {response.status_code}")
            print(f"   Respuesta: {response.text}")
            return None
            
    except Exception as e:
        print(f"❌ Error en upload_qr_to_imgbb: {e}")
        return None

def send_qr_email(to_email: str, datos: dict):
    """
    Envía email con código QR usando ImgBB con Resend
    Versión mejorada y bonita como el antiguo código
    """
    try:
        print(f"🎯 [RESEND] Enviando QR email a: {to_email}")
        
        # Generar QR
        qr_data = f"{datos['codigo_qr']}|{datos['token_verificacion']}"
        qr_image_bytes = generate_qr_image(qr_data)
        
        # Subir a ImgBB
        qr_url = upload_qr_to_imgbb(qr_image_bytes)
        
        # Si falla ImgBB, usar base64 como fallback
        qr_display = ""
        if qr_url:
            qr_display = f'<img src="{qr_url}" alt="Código QR para {datos["codigo_qr"]}" class="qr-image" />'
        else:
            print("⚠️ Usando base64 como fallback...")
            qr_base64 = base64.b64encode(qr_image_bytes).decode()
            qr_display = f'<img src="data:image/png;base64,{qr_base64}" alt="Código QR" class="qr-image" />'
        
        # Formatear fecha
        fecha = datos['fecha_reserva']
        
        # HTML con diseño mejorado
        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>Tu QR para la reserva en {datos['nombre_cancha']}</title>
            <style>
                body {{
                    font-family: 'Arial', sans-serif;
                    line-height: 1.6;
                    color: #333;
                    max-width: 600px;
                    margin: 0 auto;
                    padding: 20px;
                    background-color: #f8f9fa;
                }}
                .container {{
                    background: white;
                    border-radius: 10px;
                    overflow: hidden;
                    box-shadow: 0 4px 12px rgba(0,0,0,0.1);
                }}
                .header {{
                    background: linear-gradient(135deg, #0f9fe1 0%, #9eca3f 100%);
                    color: white;
                    padding: 25px 20px;
                    text-align: center;
                }}
                .header h1 {{
                    margin: 0;
                    font-size: 24px;
                }}
                .content {{
                    padding: 30px;
                }}
                .greeting {{
                    font-size: 18px;
                    margin-bottom: 20px;
                    color: #1a237e;
                }}
                .info-card {{
                    background: #f0f7ff;
                    padding: 20px;
                    border-radius: 8px;
                    margin: 20px 0;
                    border-left: 5px solid #0f9fe1;
                }}
                .info-card h3 {{
                    color: #0f9fe1;
                    margin-top: 0;
                    font-size: 18px;
                }}
                .info-item {{
                    margin: 10px 0;
                    display: flex;
                }}
                .info-label {{
                    font-weight: bold;
                    min-width: 120px;
                    color: #1a237e;
                }}
                .qr-section {{
                    text-align: center;
                    margin: 30px 0;
                    padding: 20px;
                    background: #f8f9fa;
                    border-radius: 8px;
                    border: 2px dashed #0f9fe1;
                }}
                .qr-section h3 {{
                    color: #0f9fe1;
                    margin-bottom: 15px;
                }}
                .qr-image {{
                    max-width: 250px;
                    height: auto;
                    border: 1px solid #ddd;
                    border-radius: 8px;
                    padding: 10px;
                    background: white;
                    box-shadow: 0 2px 8px rgba(0,0,0,0.1);
                }}
                .instructions {{
                    background: #e8f5e9;
                    padding: 15px;
                    border-radius: 8px;
                    margin: 20px 0;
                    border-left: 5px solid #4caf50;
                }}
                .instructions h4 {{
                    color: #2e7d32;
                    margin-top: 0;
                }}
                .instructions ol {{
                    padding-left: 20px;
                }}
                .instructions li {{
                    margin: 8px 0;
                }}
                .footer {{
                    margin-top: 30px;
                    padding-top: 20px;
                    border-top: 1px solid #ddd;
                    color: #666;
                    font-size: 12px;
                    text-align: center;
                }}
                .qr-code-text {{
                    font-family: monospace;
                    background: #f5f5f5;
                    padding: 10px;
                    border-radius: 4px;
                    margin: 10px 0;
                    word-break: break-all;
                    font-size: 12px;
                }}
                .button {{
                    display: inline-block;
                    padding: 10px 20px;
                    background: #0f9fe1;
                    color: white;
                    text-decoration: none;
                    border-radius: 5px;
                    margin: 10px 0;
                    font-weight: bold;
                }}
                .status-badge {{
                    display: inline-block;
                    padding: 5px 15px;
                    background: #4caf50;
                    color: white;
                    border-radius: 20px;
                    font-size: 14px;
                    margin-left: 10px;
                }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1>🎟️ Tu Código QR para la Reserva</h1>
                </div>
                
                <div class="content">
                    <div class="greeting">
                        Hola <strong>{datos['nombre_asistente']}</strong>,
                    </div>
                    
                    <p><strong>{datos['nombre_reservante']}</strong> te ha incluido como asistente para la siguiente reserva:</p>
                    
                    <div class="info-card">
                        <h3>📋 Detalles de la Reserva</h3>
                        <div class="info-item">
                            <span class="info-label">Cancha:</span>
                            <span>{datos['nombre_cancha']}</span>
                        </div>
                        <div class="info-item">
                            <span class="info-label">Fecha:</span>
                            <span>{fecha}</span>
                        </div>
                        <div class="info-item">
                            <span class="info-label">Horario:</span>
                            <span>{datos['hora_inicio']} - {datos['hora_fin']}</span>
                        </div>
                        <div class="info-item">
                            <span class="info-label">Código Reserva:</span>
                            <span>{datos['codigo_reserva']} <span class="status-badge">ACTIVA</span></span>
                        </div>
                        <div class="info-item">
                            <span class="info-label">Reservado por:</span>
                            <span>{datos['nombre_reservante']}</span>
                        </div>
                    </div>
                    
                    <div class="qr-section">
                        <h3>📱 Tu Código QR Personal</h3>
                        <p>Presenta este código QR al personal de control de acceso:</p>
                        
                        <!-- Imagen QR -->
                        {qr_display}
                        
                        <div class="qr-code-text">
                            <strong>Código QR:</strong> {datos['codigo_qr']}<br>
                            <strong>Token de Verificación:</strong> {datos['token_verificacion']}
                        </div>
                        
                        {f'<a href="{qr_url}" class="button" target="_blank">🔗 Ver QR en tamaño completo</a>' if qr_url else ''}
                    </div>
                    
                    <div class="instructions">
                        <h4>📝 Instrucciones de Uso</h4>
                        <ol>
                            <li><strong>Lleva este email contigo</strong> (puedes mostrarlo desde tu teléfono)</li>
                            <li><strong>Presenta el código QR</strong> al personal de control de acceso</li>
                            <li>Si el QR no se escanea, <strong>usa los códigos de texto</strong> mostrados arriba</li>
                            <li>Tu asistencia será <strong>registrada automáticamente</strong></li>
                            <li>Este código es de <strong>un solo uso</strong> y <strong>personal</strong></li>
                            <li><strong>Llega 10 minutos antes</strong> del horario reservado</li>
                        </ol>
                    </div>
                    
                    <div class="info-card">
                        <h3>📍 Ubicación y Contacto</h3>
                        <div class="info-item">
                            <span class="info-label">Instalación:</span>
                            <span>{datos.get('nombre_complejo', 'OlympiaHub Sports Center')}</span>
                        </div>
                        <div class="info-item">
                            <span class="info-label">Soporte:</span>
                            <span>soporte@olympiahub.app</span>
                        </div>
                        <div class="info-item">
                            <span class="info-label">Teléfono:</span>
                            <span>+1 (555) 123-4567</span>
                        </div>
                    </div>
                    
                    <p style="text-align: center; font-size: 16px; color: #1a237e; margin-top: 25px;">
                        <strong>¡Te esperamos en {datos['nombre_cancha']}!</strong><br>
                        Que tengas un excelente partido 🏆
                    </p>
                </div>
                
                <div class="footer">
                    <p>Este es un mensaje automático, por favor no respondas a este email.</p>
                    <p>© {datetime.now().year} Sistema de Reservas Deportivas - OlympiaHub</p>
                    <p>ID de reserva: {datos['codigo_reserva']} | Código QR: {datos['codigo_qr']}</p>
                    <p>Si no reconoces esta reserva, por favor contacta a soporte@olympiahub.app</p>
                </div>
            </div>
        </body>
        </html>
        """
        
        # Texto plano (fallback)
        text_content = f"""
        Tu código QR para la reserva en {datos['nombre_cancha']}
        
        Hola {datos['nombre_asistente']},
        
        {datos['nombre_reservante']} te ha incluido como asistente para:
        
        Cancha: {datos['nombre_cancha']}
        Fecha: {fecha}
        Horario: {datos['hora_inicio']} - {datos['hora_fin']}
        Código de Reserva: {datos['codigo_reserva']}
        
        Tu código QR: {datos['codigo_qr']}
        Token de verificación: {datos['token_verificacion']}
        
        Enlace al QR: {qr_url if qr_url else 'Está incrustado en el email'}
        
        INSTRUCCIONES:
        1. Lleva este email contigo (puedes mostrarlo desde tu teléfono)
        2. Presenta el código QR al personal de control de acceso
        3. Si el QR no se ve, usa los códigos de texto mostrados arriba
        4. Tu asistencia será registrada automáticamente
        5. Este código es de un solo uso y personal
        
        ¡Te esperamos en {datos['nombre_cancha']}!
        
        ---
        Este es un mensaje automático, por favor no respondas.
        © {datetime.now().year} Sistema de Reservas Deportivas - OlympiaHub
        ID de reserva: {datos['codigo_reserva']}
        """
        
        # Enviar con Resend
        return send_email(
            to_email=to_email,
            subject=f"🎟️ Tu código QR para la reserva en {datos['nombre_cancha']} | {datos['codigo_reserva']}",
            message=text_content,
            html_content=html_content
        )
        
    except Exception as e:
        print(f"❌ [RESEND] Error enviando QR email: {e}")
        import traceback
        traceback.print_exc()
        
        # Envío simple como fallback
        try:
            simple_subject = f"Tu código QR para la reserva en {datos['nombre_cancha']}"
            simple_message = f"""
            Hola {datos['nombre_asistente']},
            
            Tu código QR para la reserva en {datos['nombre_cancha']} es:
            
            Código QR: {datos['codigo_qr']}
            Token: {datos['token_verificacion']}
            
            Fecha: {fecha}
            Horario: {datos['hora_inicio']} - {datos['hora_fin']}
            Código Reserva: {datos['codigo_reserva']}
            Reservado por: {datos['nombre_reservante']}
            
            Presenta estos códigos al personal de control de acceso.
            
            ¡Te esperamos en {datos['nombre_cancha']}!
            """
            return send_email(to_email, simple_subject, simple_message)
        except Exception as e2:
            print(f"❌ Falló el envío simple: {e2}")
            return False

# Función principal para envío de QR (usa la nueva versión con Resend)
def send_qr_email_with_attachment(to_email: str, datos: dict):
    """
    Función wrapper para mantener compatibilidad
    Ahora usa Resend en lugar de SMTP con attachment
    """
    return send_qr_email(to_email, datos)

# Funciones auxiliares con diseño mejorado
def send_welcome_email(to_email: str, nombre: str, apellido: str):
    html_content = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="UTF-8">
        <style>
            body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; max-width: 600px; margin: 0 auto; padding: 20px; }}
            .header {{ background: linear-gradient(135deg, #0f9fe1 0%, #9eca3f 100%); color: white; padding: 25px; text-align: center; border-radius: 10px 10px 0 0; }}
            .content {{ background: #f9f9f9; padding: 30px; border-radius: 0 0 10px 10px; }}
            .badge {{ display: inline-block; background: #ff9800; color: white; padding: 5px 15px; border-radius: 20px; font-size: 14px; }}
        </style>
    </head>
    <body>
        <div class="header">
            <h1>🌟 ¡Bienvenido a OlympiaHub, {nombre}!</h1>
        </div>
        <div class="content">
            <p>Hola <strong>{nombre} {apellido}</strong>,</p>
            <p>Tu registro en <strong>OlympiaHub</strong> fue exitoso. 🎉</p>
            
            <div style="background: #e3f2fd; padding: 15px; border-radius: 8px; margin: 20px 0; border-left: 5px solid #0f9fe1;">
                <h3 style="color: #0f9fe1; margin-top: 0;">📋 Estado de tu Cuenta</h3>
                <p><span class="badge">PENDIENTE DE APROBACIÓN</span></p>
                <p>Tu cuenta está en proceso de revisión por nuestro equipo administrativo.</p>
            </div>
            
            <p><strong>¿Qué sucede ahora?</strong></p>
            <ul>
                <li>Recibirás una notificación cuando tu cuenta sea aprobada</li>
                <li>El proceso generalmente toma 24-48 horas</li>
                <li>Una vez aprobado, podrás acceder a todas las funcionalidades</li>
            </ul>
            
            <p><strong>Funcionalidades que tendrás disponibles:</strong></p>
            <ul>
                <li>✅ Reserva de canchas deportivas</li>
                <li>✅ Gestión de equipos y jugadores</li>
                <li>✅ Control de accesos con QR</li>
                <li>✅ Sistema de pagos integrado</li>
            </ul>
            
            <p style="text-align: center; margin-top: 30px;">
                <strong>¡Gracias por unirte a nuestra comunidad deportiva!</strong> 🏀⚽🎾
            </p>
            
            <div style="margin-top: 30px; padding-top: 20px; border-top: 1px solid #ddd; font-size: 12px; color: #666; text-align: center;">
                <p>Este es un mensaje automático, por favor no respondas.</p>
                <p>© {datetime.now().year} OlympiaHub - Sistema de Gestión Deportiva</p>
                <p>Contacto: soporte@olympiahub.app</p>
            </div>
        </div>
    </body>
    </html>
    """
    
    text_content = f"""
    ¡Bienvenido a OlympiaHub, {nombre}!
    
    Tu registro fue exitoso. Tu cuenta está pendiente de aprobación.
    
    ESTADO: PENDIENTE DE APROBACIÓN
    
    ¿Qué sucede ahora?
    • Recibirás una notificación cuando tu cuenta sea aprobada
    • El proceso generalmente toma 24-48 horas
    • Una vez aprobado, podrás acceder a todas las funcionalidades
    
    Funcionalidades disponibles después de aprobación:
    • Reserva de canchas deportivas
    • Gestión de equipos y jugadores
    • Control de accesos con QR
    • Sistema de pagos integrado
    
    ¡Gracias por unirte a nuestra comunidad deportiva!
    
    Saludos,
    Equipo OlympiaHub
    """
    
    return send_email(
        to_email=to_email,
        subject="🌟 ¡Bienvenido a OlympiaHub - Cuenta Pendiente de Aprobación!",
        message=text_content,
        html_content=html_content
    )

def send_approval_email(to_email: str, nombre: str, apellido: str, rol: str):
    html_content = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="UTF-8">
        <style>
            body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; max-width: 600px; margin: 0 auto; padding: 20px; }}
            .header {{ background: linear-gradient(135deg, #4caf50 0%, #9eca3f 100%); color: white; padding: 25px; text-align: center; border-radius: 10px 10px 0 0; }}
            .content {{ background: #f9f9f9; padding: 30px; border-radius: 0 0 10px 10px; }}
            .badge {{ display: inline-block; background: #4caf50; color: white; padding: 5px 15px; border-radius: 20px; font-size: 14px; }}
            .role-card {{ background: #e8f5e9; padding: 15px; border-radius: 8px; margin: 15px 0; border-left: 5px solid #4caf50; }}
        </style>
    </head>
    <body>
        <div class="header">
            <h1>✅ ¡Tu cuenta ha sido aprobada!</h1>
        </div>
        <div class="content">
            <p>Hola <strong>{nombre} {apellido}</strong>,</p>
            
            <div style="text-align: center; margin: 20px 0;">
                <span class="badge" style="font-size: 18px; padding: 10px 25px;">🎉 ¡FELICITACIONES!</span>
            </div>
            
            <p>Nos complace informarte que tu cuenta en <strong>OlympiaHub</strong> ha sido <strong>aprobada exitosamente</strong>.</p>
            
            <div class="role-card">
                <h3 style="color: #2e7d32; margin-top: 0;">👤 Tu Rol en el Sistema</h3>
                <p style="font-size: 18px; text-align: center;"><strong>{rol.upper()}</strong></p>
            </div>
            
            <p><strong>🎯 ¿Qué puedes hacer ahora?</strong></p>
            <ul>
                <li><strong>Acceder al sistema</strong> con tus credenciales</li>
                <li><strong>Realizar reservas</strong> de canchas deportivas</li>
                <li><strong>Gestionar equipos</strong> y jugadores</li>
                <li><strong>Controlar accesos</strong> con sistema QR</li>
                <li><strong>Realizar pagos</strong> de manera segura</li>
            </ul>
            
            <div style="background: #fff3e0; padding: 15px; border-radius: 8px; margin: 20px 0; border-left: 5px solid #ff9800;">
                <h4 style="color: #e65100; margin-top: 0;">🚀 Primeros Pasos Recomendados:</h4>
                <ol>
                    <li>Inicia sesión en la plataforma</li>
                    <li>Completa tu perfil de usuario</li>
                    <li>Explora las canchas disponibles</li>
                    <li>Haz tu primera reserva de prueba</li>
                </ol>
            </div>
            
            <p style="text-align: center; margin-top: 30px;">
                <a href="https://olympiahub.app/login" style="display: inline-block; padding: 12px 30px; background: #0f9fe1; color: white; text-decoration: none; border-radius: 5px; font-weight: bold; font-size: 16px;">
                    🔑 INICIAR SESIÓN AHORA
                </a>
            </p>
            
            <p style="text-align: center; font-size: 14px; color: #666; margin-top: 20px;">
                Si tienes problemas para acceder, contacta a: <br>
                <strong>soporte@olympiahub.app</strong>
            </p>
            
            <div style="margin-top: 30px; padding-top: 20px; border-top: 1px solid #ddd; font-size: 12px; color: #666; text-align: center;">
                <p><strong>¡Bienvenido a la familia OlympiaHub!</strong> 🏆</p>
                <p>© {datetime.now().year} OlympiaHub - Sistema de Gestión Deportiva</p>
                <p>Transformando la gestión deportiva, un partido a la vez.</p>
            </div>
        </div>
    </body>
    </html>
    """
    
    text_content = f"""
    ¡FELICITACIONES {nombre}!
    
    Tu cuenta en OlympiaHub ha sido APROBADA exitosamente.
    
    ROL ASIGNADO: {rol}
    
    🎯 ¿Qué puedes hacer ahora?
    • Acceder al sistema con tus credenciales
    • Realizar reservas de canchas deportivas
    • Gestionar equipos y jugadores
    • Controlar accesos con sistema QR
    • Realizar pagos de manera segura
    
    🚀 Primeros Pasos Recomendados:
    1. Inicia sesión en: https://olympiahub.app/login
    2. Completa tu perfil de usuario
    3. Explora las canchas disponibles
    4. Haz tu primera reserva de prueba
    
    ¡Bienvenido a la familia OlympiaHub!
    
    Si tienes problemas para acceder, contacta a:
    soporte@olympiahub.app
    
    Saludos,
    Equipo OlympiaHub
    """
    
    return send_email(
        to_email=to_email,
        subject=f"✅ ¡Cuenta Aprobada! - Bienvenido a OlympiaHub como {rol}",
        message=text_content,
        html_content=html_content
    )