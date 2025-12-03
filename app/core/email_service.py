import smtplib
import qrcode
import io
import base64
import uuid
import requests
import tempfile
import os
from datetime import datetime
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.image import MIMEImage
from pathlib import Path

# Configuración
IMG_BB_API_KEY = "15132cfb77719e5061c3278a7fce1a17"  # TU API KEY AQUÍ

def send_email(to_email: str, subject: str, message: str):
    try:
        sender_email = "leandroeguerdo@gmail.com"
        password = "otzxgnihrdjrysbo"  
        
        print(f"🎯 ENVIANDO EMAIL:")
        print(f"   De: {sender_email}")
        print(f"   A: {to_email}")
        print(f"   Asunto: {subject}")
        
        # Crear mensaje
        email_text = f"Subject: {subject}\nFrom: {sender_email}\nTo: {to_email}\n\n{message}"
        
        # Enviar con más detalles
        server = smtplib.SMTP("smtp.gmail.com", 587)
        server.ehlo()
        server.starttls()
        server.ehlo()
        server.login(sender_email, password)
        server.sendmail(sender_email, to_email, email_text)
        server.quit()
        
        print(f"✅ ✅ ✅ EMAIL ENVIADO EXITOSAMENTE a: {to_email}")
        return True
        
    except Exception as e:
        print(f"❌ ❌ ❌ ERROR ENVIANDO EMAIL: {e}")
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
    Envía email con código QR usando ImgBB
    """
    try:
        sender_email = "leandroeguerdo@gmail.com"
        password = "otzxgnihrdjrysbo"
        
        print(f"🎯 ENVIANDO EMAIL CON QR:")
        print(f"   De: {sender_email}")
        print(f"   A: {to_email}")
        
        # Generar QR con los datos
        qr_data = f"{datos['codigo_qr']}|{datos['token_verificacion']}"
        
        # Generar imagen QR
        qr_image_bytes = generate_qr_image(qr_data)
        
        # Subir a ImgBB
        qr_url = upload_qr_to_imgbb(qr_image_bytes)
        
        # Si falla ImgBB, usar base64 como fallback
        if not qr_url:
            print("⚠️ Usando base64 como fallback...")
            qr_base64 = base64.b64encode(qr_image_bytes).decode()
            qr_url = f"data:image/png;base64,{qr_base64}"
        
        # Formatear fecha
        fecha = datos['fecha_reserva']
        
        # Crear contenido HTML del email
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
                            <span>{datos['codigo_reserva']}</span>
                        </div>
                    </div>
                    
                    <div class="qr-section">
                        <h3>📱 Tu Código QR Personal</h3>
                        <p>Presenta este código QR al personal de control de acceso:</p>
                        
                        <!-- Imagen QR desde ImgBB -->
                        <img src="{qr_url}" alt="Código QR para {datos['codigo_qr']}" class="qr-image" />
                        
                        <div class="qr-code-text">
                            <strong>Código:</strong> {datos['codigo_qr']}<br>
                            <strong>Token:</strong> {datos['token_verificacion']}
                        </div>
                        
                        <a href="{qr_url}" class="button" target="_blank">🔗 Ver QR en tamaño completo</a>
                    </div>
                    
                    <div class="instructions">
                        <h4>📝 Instrucciones de Uso</h4>
                        <ol>
                            <li>Lleva este email contigo (puedes mostrarlo desde tu teléfono)</li>
                            <li>Presenta el código QR al personal de control de acceso</li>
                            <li>Si el QR no se ve, usa los códigos de texto mostrados arriba</li>
                            <li>Tu asistencia será registrada automáticamente</li>
                            <li>Este código es de un solo uso y personal</li>
                        </ol>
                    </div>
                    
                    <p style="text-align: center; font-size: 16px; color: #1a237e; margin-top: 25px;">
                        <strong>¡Te esperamos en {datos['nombre_cancha']}!</strong>
                    </p>
                </div>
                
                <div class="footer">
                    <p>Este es un mensaje automático, por favor no respondas a este email.</p>
                    <p>© {datetime.now().year} Sistema de Reservas Deportivas - OlympiaHub</p>
                    <p>ID de reserva: {datos['codigo_reserva']}</p>
                </div>
            </div>
        </body>
        </html>
        """
        
        # Crear mensaje MIME
        msg = MIMEMultipart('alternative')
        msg['Subject'] = f"🎟️ Tu código QR para la reserva en {datos['nombre_cancha']}"
        msg['From'] = sender_email
        msg['To'] = to_email
        
        # Versión texto plano (fallback)
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
        
        Enlace al QR: {qr_url if 'http' in str(qr_url) else 'Está incrustado en el email'}
        
        Presenta el código QR o los códigos de texto al personal de control de acceso.
        
        ¡Te esperamos en {datos['nombre_cancha']}!
        
        ---
        Este es un mensaje automático, por favor no respondas.
        """
        
        # Adjuntar ambas versiones
        msg.attach(MIMEText(text_content, 'plain'))
        msg.attach(MIMEText(html_content, 'html'))
        
        # Enviar email
        with smtplib.SMTP("smtp.gmail.com", 587) as server:
            server.starttls()
            server.login(sender_email, password)
            server.send_message(msg)
        
        print(f"✅ ✅ ✅ EMAIL CON QR ENVIADO EXITOSAMENTE a: {to_email}")
        return True
        
    except Exception as e:
        print(f"❌ ❌ ❌ ERROR ENVIANDO EMAIL CON QR: {e}")
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
            
            Presenta estos códigos al personal de control de acceso.
            
            ¡Te esperamos en {datos['nombre_cancha']}!
            """
            return send_email(to_email, simple_subject, simple_message)
        except Exception as e2:
            print(f"❌ Falló el envío simple: {e2}")
            return False

# Función alternativa con attachment (más confiable para algunos clientes)
def send_qr_email_with_attachment(to_email: str, datos: dict):
    """
    Versión que adjunta el QR como archivo
    """
    try:
        sender_email = "leandroeguerdo@gmail.com"
        password = "otzxgnihrdjrysbo"
        
        print(f"🎯 ENVIANDO EMAIL CON QR ATTACHMENT a {to_email}")
        
        # Generar QR
        qr_data = f"{datos['codigo_qr']}|{datos['token_verificacion']}"
        qr_image_bytes = generate_qr_image(qr_data)
        
        # Crear archivo temporal
        with tempfile.NamedTemporaryFile(suffix='.png', delete=False) as temp_file:
            temp_path = temp_file.name
            temp_file.write(qr_image_bytes)
        
        try:
            # Formatear fecha
            fecha = datos['fecha_reserva']
            
            # Crear mensaje
            msg = MIMEMultipart()
            msg['Subject'] = f"🎟️ Tu código QR para la reserva en {datos['nombre_cancha']}"
            msg['From'] = sender_email
            msg['To'] = to_email
            
            # Contenido HTML
            html_content = f"""
            <html>
            <body>
                <h2>Tu código QR para la reserva</h2>
                <p>Hola <strong>{datos['nombre_asistente']}</strong>,</p>
                <p><strong>{datos['nombre_reservante']}</strong> te ha incluido como asistente para:</p>
                <ul>
                    <li><strong>Cancha:</strong> {datos['nombre_cancha']}</li>
                    <li><strong>Fecha:</strong> {fecha}</li>
                    <li><strong>Horario:</strong> {datos['hora_inicio']} - {datos['hora_fin']}</li>
                    <li><strong>Código Reserva:</strong> {datos['codigo_reserva']}</li>
                </ul>
                <p><strong>Código QR:</strong> {datos['codigo_qr']}</p>
                <p><strong>Token:</strong> {datos['token_verificacion']}</p>
                <p>El código QR está adjunto como archivo "tu_codigo_qr.png"</p>
                <p>¡Te esperamos en {datos['nombre_cancha']}!</p>
            </body>
            </html>
            """
            
            msg.attach(MIMEText(html_content, 'html'))
            
            # Adjuntar imagen QR
            img_attachment = MIMEImage(qr_image_bytes, name='tu_codigo_qr.png')
            img_attachment.add_header('Content-Disposition', 'attachment', filename='tu_codigo_qr.png')
            msg.attach(img_attachment)
            
            # Enviar email
            with smtplib.SMTP("smtp.gmail.com", 587) as server:
                server.starttls()
                server.login(sender_email, password)
                server.send_message(msg)
            
            print(f"✅ ✅ ✅ EMAIL CON ATTACHMENT ENVIADO a: {to_email}")
            return True
            
        finally:
            # Limpiar archivo temporal
            if os.path.exists(temp_path):
                os.remove(temp_path)
                
    except Exception as e:
        print(f"❌ ERROR ENVIANDO EMAIL CON ATTACHMENT: {e}")
        import traceback
        traceback.print_exc()
        return False

# Funciones auxiliares
def send_welcome_email(to_email: str, nombre: str, apellido: str):
    subject = "Bienvenido a OlympiaHub - Cuenta Pendiente"
    message = f"""Hola {nombre},

Tu registro en OlympiaHub fue exitoso. Tu cuenta esta pendiente de aprobacion.

Te notificaremos cuando sea activada.

Saludos,
Equipo OlympiaHub"""
    return send_email(to_email, subject, message)

def send_approval_email(to_email: str, nombre: str, apellido: str, rol: str):
    subject = "Cuenta Aprobada - OlympiaHub!"
    message = f"""Felicidades {nombre}!

Tu cuenta en OlympiaHub ha sido aprobada.

Rol: {rol}

Ya puedes iniciar sesion y usar la plataforma.

Bienvenid@,
Equipo OlympiaHub"""
    return send_email(to_email, subject, message)