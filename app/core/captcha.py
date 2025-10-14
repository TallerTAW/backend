# app/core/captcha.py
import requests
from app.config import settings  # Importar desde la nueva configuración

def verificar_captcha(token: str) -> bool:
    """
    Verifica el token del captcha con Google.
    """
    if not token:
        return False

    url = "https://www.google.com/recaptcha/api/siteverify"
    payload = {
        "secret": settings.RECAPTCHA_SECRET_KEY,
        "response": token
    }

    try:
        response = requests.post(url, data=payload, timeout=10)
        result = response.json()
        print("Respuesta de Google reCAPTCHA:", result)
        return result.get("success", False)
    except Exception as e:
        print(f"Error verificando reCAPTCHA: {e}")
        return False