import smtplib

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