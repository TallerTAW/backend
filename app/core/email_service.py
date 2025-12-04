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
            "from": "OlympiaHub <no-reply@olympiahub.app>",
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
    """Genera una imagen QR"""
    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_L,
        box_size=10,
        border=4,
    )
    qr.add_data(qr_data)
    qr.make(fit=True)
    
    img = qr.make_image(fill_color="black", back_color="white")
    
    buffered = io.BytesIO()
    img.save(buffered, format="PNG")
    qr_bytes = buffered.getvalue()
    
    # Convertir a base64 para Resend
    qr_base64 = base64.b64encode(qr_bytes).decode()
    return qr_base64

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
    Envía email con QR usando Resend
    """
    try:
        print(f"🎟️ [RESEND] Enviando QR email a: {to_email}")
        
        # Generar QR
        qr_data = f"{datos['codigo_qr']}|{datos['token_verificacion']}"
        qr_base64 = generate_qr_image(qr_data)
        
        # HTML con QR embebido
        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="UTF-8">
            <style>
                body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
                .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
                .header {{ background: #00BFFF; color: white; padding: 20px; text-align: center; }}
                .content {{ padding: 20px; background: #f9f9f9; }}
                .qr-section {{ text-align: center; margin: 20px 0; }}
                .qr-image {{ max-width: 250px; height: auto; }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1>🎟️ Tu Código QR - OlympiaHub</h1>
                </div>
                <div class="content">
                    <p>Hola <strong>{datos['nombre_asistente']}</strong>,</p>
                    <p><strong>{datos['nombre_reservante']}</strong> te ha incluido como asistente.</p>
                    
                    <div style="background: white; padding: 15px; border-radius: 8px; margin: 20px 0;">
                        <h3>📋 Detalles de la Reserva</h3>
                        <p><strong>Cancha:</strong> {datos['nombre_cancha']}</p>
                        <p><strong>Fecha:</strong> {datos['fecha_reserva']}</p>
                        <p><strong>Horario:</strong> {datos['hora_inicio']} - {datos['hora_fin']}</p>
                        <p><strong>Código Reserva:</strong> {datos['codigo_reserva']}</p>
                    </div>
                    
                    <div class="qr-section">
                        <h3>📱 Tu Código QR Personal</h3>
                        <img src="data:image/png;base64,{qr_base64}" alt="Código QR" class="qr-image" />
                        <p><strong>Código:</strong> {datos['codigo_qr']}</p>
                        <p><strong>Token:</strong> {datos['token_verificacion']}</p>
                    </div>
                    
                    <p style="text-align: center; margin-top: 30px;">
                        <strong>¡Te esperamos en {datos['nombre_cancha']}!</strong>
                    </p>
                </div>
            </div>
        </body>
        </html>
        """
        
        # Texto plano (fallback)
        text_content = f"""
        Tu código QR para la reserva
        
        Hola {datos['nombre_asistente']},
        
        {datos['nombre_reservante']} te ha incluido como asistente para:
        
        Cancha: {datos['nombre_cancha']}
        Fecha: {datos['fecha_reserva']}
        Horario: {datos['hora_inicio']} - {datos['hora_fin']}
        Código Reserva: {datos['codigo_reserva']}
        
        Tu código QR: {datos['codigo_qr']}
        Token: {datos['token_verificacion']}
        
        Presenta estos códigos al personal de control de acceso.
        
        ¡Te esperamos!
        """
        
        # Enviar con Resend
        return send_email(
            to_email=to_email,
            subject=f"🎟️ Tu código QR para {datos['nombre_cancha']} - {datos['codigo_reserva']}",
            message=text_content,
            html_content=html_content
        )
        
    except Exception as e:
        print(f"❌ [RESEND] Error enviando QR email: {e}")
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
    message = f"Hola {nombre},\n\nTu registro fue exitoso. Tu cuenta está pendiente de aprobación.\n\nSaludos,\nEquipo OlympiaHub"
    
    html_content = f"""
    <!DOCTYPE html>
    <html>
    <body style="font-family: Arial, sans-serif; line-height: 1.6;">
        <h2>Bienvenido a OlympiaHub, {nombre}!</h2>
        <p>Tu registro fue exitoso. Tu cuenta está pendiente de aprobación.</p>
        <p>Te notificaremos cuando sea activada.</p>
        <p>Saludos,<br>Equipo OlympiaHub</p>
    </body>
    </html>
    """
    
    return send_email(to_email, subject, message, html_content)

def send_approval_email(to_email: str, nombre: str, apellido: str, rol: str):
    subject = "✅ Tu cuenta ha sido aprobada - OlympiaHub"
    message = f"Felicidades {nombre}!\n\nTu cuenta ha sido aprobada.\n\nRol: {rol}\n\nYa puedes iniciar sesión."
    
    html_content = f"""
    <!DOCTYPE html>
    <html>
    <body style="font-family: Arial, sans-serif; line-height: 1.6;">
        <h2 style="color: #00BFFF;">¡Felicidades {nombre}!</h2>
        <p>Tu cuenta en OlympiaHub ha sido aprobada.</p>
        <p><strong>Rol:</strong> {rol}</p>
        <p>Ya puedes iniciar sesión y usar la plataforma.</p>
        <p>Bienvenid@ al equipo!</p>
    </body>
    </html>
    """
    
    return send_email(to_email, subject, message, html_content)