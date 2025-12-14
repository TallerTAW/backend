# app/core/libelula_service.py

import requests
from sqlalchemy.orm import Session # Importación clave para el webhook
from app.schemas.libelula import PaymentInitiation, PaymentInitiationResponse, WebhookData
from app.core.exceptions import PaymentGatewayError
from app.config import settings
from app.models.pago import Pago      # Necesario para actualizar el estado del pago
from app.models.reserva import Reserva # Necesario para actualizar el estado de la reserva


# Dependencia para que el router de Libélula pueda inyectar el servicio
def get_libelula_service():
    return LibelulaService()


class LibelulaService:
    def __init__(self):
        self.base_url = settings.LIBELULA_API_URL
        self.api_key = settings.LIBELULA_API_KEY
        self.webhook_url = settings.LIBELULA_WEBHOOK_URL 

    def create_transaction(self, initiation_data: PaymentInitiation) -> PaymentInitiationResponse:
        """
        Llama a la API de Libélula para iniciar una nueva transacción de pago.
        """
        endpoint = "/api/v1/transactions"
        
        # Datos requeridos por la API de Libélula
        payload = {
            "amount": initiation_data.amount,
            "currency": initiation_data.currency,
            "orderId": initiation_data.reserva_id,
            "returnUrl": f"{settings.FRONTEND_BASE_URL}/payment/success", 
            "cancelUrl": f"{settings.FRONTEND_BASE_URL}/payment/cancel", 
            "webhookUrl": self.webhook_url,
            "paymentMethod": "card", # Ejemplo, ajusta si es necesario
        }

        headers = {
            # Asumimos que la autenticación es con la API Key en el header
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }

        try:
            response = requests.post(self.base_url + endpoint, json=payload, headers=headers)
            response.raise_for_status()
            data = response.json()
            
            # Asegurar que la respuesta tenga los campos esperados
            if not data.get("transactionId") or not data.get("paymentUrl"):
                 raise PaymentGatewayError("Respuesta de Libélula incompleta o inesperada.")
            
            return PaymentInitiationResponse(
                transaction_id=data.get("transactionId"),
                payment_url=data.get("paymentUrl"),
                status=data.get("status", "PENDING")
            )

        except requests.exceptions.RequestException as e:
            # Captura errores de red o errores HTTP (4xx/5xx)
            error_detail = response.json() if 'response' in locals() and response.content else str(e)
            raise PaymentGatewayError(f"Error al iniciar transacción con Libélula: {error_detail}")


    def verify_webhook_signature(self, data: WebhookData) -> bool:
        """
        Verifica la firma del webhook para asegurar que proviene de Libélula.
        (Ajustada para asumir que no hay API Secret, se asume que si el webhookUrl
         es secreto, es suficiente. REEMPLAZAR si Libélula requiere verificación con Secret).
        """
        print(f"ADVERTENCIA: Usando verificación simplificada del webhook (sin API Secret) para transaccion {data.transaction_id}...")
        return True 

    def process_webhook(self, db: Session, data: WebhookData):
        """
        Procesa la notificación de estado de pago de Libélula.
        ACTUALIZA EL ESTADO DE PAGO Y RESERVA EN LA DB.
        """
        
        if not self.verify_webhook_signature(data):
            return False 

        # 1. Buscar el Pago asociado usando el ID de la transacción
        db_pago = db.query(Pago).filter(
            Pago.id_transaccion == data.transaction_id
        ).first()

        if not db_pago:
            print(f"❌ [WEBHOOK] No se encontró el Pago con transaction_id: {data.transaction_id}. Posiblemente ya procesado o ID inválido.")
            return False

        # 2. Buscar la Reserva asociada
        db_reserva = db.query(Reserva).filter(
            Reserva.id_reserva == db_pago.id_reserva
        ).first()

        if not db_reserva:
            print(f"❌ [WEBHOOK] No se encontró la Reserva con id: {db_pago.id_reserva}.")
            return False

        # 3. Determinar y actualizar el estado
        new_status = data.status.upper() 

        if db_pago.estado.upper() != new_status:
            db_pago.estado = new_status
            
            if new_status == "COMPLETED":
                # Si el pago fue exitoso
                db_reserva.estado = "confirmada" 
                print(f"✅ [WEBHOOK] Pago y Reserva CONFIRMADOS para Reserva ID: {db_reserva.id_reserva}")
                # Aquí se debería disparar el envío del email de confirmación/QR.
                
            elif new_status in ["FAILED", "CANCELLED", "REJECTED"]:
                # Si el pago falló o fue cancelado
                db_reserva.estado = "cancelada_pago" 
                print(f"⚠️ [WEBHOOK] Pago FALLIDO para Reserva ID: {db_reserva.id_reserva}. Estado: {new_status}")
            
            # 4. Guardar los cambios en la base de datos
            db.commit()
            db.refresh(db_pago)
            db.refresh(db_reserva)
        else:
            print(f"🔍 [WEBHOOK] Estado de pago ya en '{new_status}'. No se requiere actualización.")
        
        return True