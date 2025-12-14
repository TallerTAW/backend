# app/routers/libelula.py

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.core.libelula_service import LibelulaService, get_libelula_service # Se agregó get_libelula_service si no existía
from app.core.exceptions import PaymentGatewayError
from app.schemas.libelula import PaymentInitiation, PaymentInitiationResponse, WebhookData
# Asumimos que tienes una función para inyectar la sesión de DB
from app.database import get_db 
import traceback # Útil para logueo de errores internos

# Inicializamos el Router
router = APIRouter(
    prefix="/pagos/libelula",
    tags=["Pagos Libélula"],
)

# Dependencia para obtener la instancia del servicio de Libélula
# (Solo si no está ya en core/libelula_service.py)
# def get_libelula_service():
#     return LibelulaService()


# ====================================================================
# NOTA: Este endpoint ya NO es necesario, la lógica se movió a reservas_opcion.py
# para mantener la transacción de reserva y pago en el mismo lugar.
# Lo mantenemos comentado por si necesitas otra forma de iniciarlo.
# ====================================================================
# @router.post(
#     "/initiate-payment",
#     response_model=PaymentInitiationResponse,
#     status_code=status.HTTP_201_CREATED,
#     summary="Inicia una transacción de pago con Libélula"
# )
# async def initiate_payment(
#     payment_data: PaymentInitiation,
#     db: Session = Depends(get_db), 
#     service: LibelulaService = Depends(get_libelula_service)
# ):
#     try:
#         response = service.create_transaction(payment_data)
#         return response
    
#     except PaymentGatewayError as e:
#         raise HTTPException(
#             status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
#             detail=str(e)
#         )
#     except Exception as e:
#         raise HTTPException(
#             status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
#             detail="Error interno al procesar la solicitud de pago."
#         )


# ====================================================================
# ENDPOINT CRÍTICO PARA LA CONFIRMACIÓN DE PAGOS (WEBHOOK)
# ====================================================================

@router.post(
    "/webhook/notifications",
    status_code=status.HTTP_200_OK,
    summary="Endpoint para recibir las notificaciones (Webhooks) de Libélula"
)
async def handle_webhook(
    webhook_data: WebhookData,
    db: Session = Depends(get_db), # Necesario para actualizar el estado en la DB
    service: LibelulaService = Depends(get_libelula_service)
):
    """
    Este endpoint es llamado por los servidores de Libélula.
    Contiene la lógica crucial para actualizar el estado del pago en tu base de datos.
    """
    print(f"🎯 [WEBHOOK] Notificación de Libélula recibida para Transaction ID: {webhook_data.transaction_id}, Status: {webhook_data.status}")
    
    try:
        # ¡CORRECCIÓN CLAVE! Se pasa la sesión de DB al servicio
        success = service.process_webhook(db, webhook_data) 
        
        if success:
            # Es crucial responder 200 OK rápidamente para evitar reintentos.
            return {"message": "Webhook received and processed successfully"}
        else:
             # Retornamos 200 OK incluso si hubo un fallo lógico (pago no encontrado, etc.)
            return {"message": "Webhook received, but internal issue noted. No retry required."}


    except Exception as e:
        # En caso de error crítico (ej. error de DB o excepción no manejada), 
        # logueamos y retornamos 200 OK para evitar reintentos infinitos de Libélula.
        print(f"❌ [WEBHOOK] ERROR CRÍTICO al procesar el webhook de Libélula: {e}")
        traceback.print_exc()
        return {"message": "Webhook received, but critical internal error occurred during processing."}