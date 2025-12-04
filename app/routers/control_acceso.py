from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import func
from datetime import datetime, date, time, timedelta
from app.database import get_db
from app.models.asistente import AsistenteReserva
from app.models.reserva import Reserva
from app.models.usuario import Usuario
from pydantic import BaseModel
import traceback
import logging

logger = logging.getLogger(__name__)
router = APIRouter()

class VerificarQRRequest(BaseModel):
    codigo_qr: str
    token_verificacion: str

class VerificacionQRResponse(BaseModel):
    success: bool
    message: str
    asistente: dict = None
    reserva: dict = None
    error_info: dict = None

@router.post("/verificar-qr", response_model=VerificacionQRResponse)
def verificar_qr_asistente(
    request: VerificarQRRequest,
    db: Session = Depends(get_db)
):
    """
    Verificar QR de asistente para control de acceso
    Solo permite si la reserva está en estado "confirmada" o "en_curso"
    """
    try:
        codigo_qr = request.codigo_qr
        token_verificacion = request.token_verificacion
        
        logger.info(f"🔍 Iniciando verificación QR: {codigo_qr[:10]}...")
        
        # Buscar asistente con relaciones
        asistente = db.query(AsistenteReserva).options(
            joinedload(AsistenteReserva.reserva).joinedload(Reserva.cancha)
        ).filter(
            AsistenteReserva.codigo_qr == codigo_qr,
            AsistenteReserva.token_verificacion == token_verificacion
        ).first()
        
        if not asistente:
            logger.warning(f"❌ QR no encontrado: {codigo_qr}")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Código QR no válido o no encontrado"
            )
        
        logger.info(f"✅ Asistente encontrado: {asistente.nombre}")
        
        # Verificar si ya asistió
        if asistente.asistio:
            logger.warning(f"⚠️ Asistente ya registró asistencia: {asistente.nombre}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"El asistente {asistente.nombre} ya registró su asistencia"
            )
        
        # Obtener reserva
        reserva = asistente.reserva
        if not reserva:
            logger.error(f"❌ Reserva no encontrada para asistente: {asistente.id_asistente}")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Reserva no encontrada"
            )
        
        logger.info(f"📊 Reserva: {reserva.codigo_reserva} (ID: {reserva.id_reserva}), Estado: {reserva.estado}")
        
        # ✅ VERIFICACIÓN CRÍTICA: Solo permitir "confirmada" o "en_curso"
        if reserva.estado not in ["confirmada", "en_curso"]:
            logger.warning(f"❌ Estado no permitido: {reserva.estado}")
            
            # Mensaje específico para estado "pendiente"
            if reserva.estado == "pendiente":
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail={
                        "message": f"La reserva está en estado '{reserva.estado}'. Debe estar 'confirmada' para validar acceso.",
                        "reserva_info": {
                            "id_reserva": reserva.id_reserva,
                            "codigo_reserva": reserva.codigo_reserva,
                            "fecha": reserva.fecha_reserva.strftime("%d/%m/%Y"),
                            "horario": f"{reserva.hora_inicio} - {reserva.hora_fin}",
                            "cancha": reserva.cancha.nombre if reserva.cancha else "N/A",
                            "estado_actual": reserva.estado
                        },
                        "requiere_accion": "confirmar_reserva"
                    }
                )
            else:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail={
                        "message": f"La reserva está en estado '{reserva.estado}'. Solo se permite acceso para reservas 'confirmadas' o 'en_curso'.",
                        "reserva_info": {
                            "id_reserva": reserva.id_reserva,
                            "codigo_reserva": reserva.codigo_reserva,
                            "estado_actual": reserva.estado
                        }
                    }
                )
        
        # Verificar fecha (solo puede asistir el día de la reserva)
        fecha_hoy = date.today()
        if reserva.fecha_reserva != fecha_hoy:
            logger.warning(f"❌ Fecha no coincide: {reserva.fecha_reserva} vs {fecha_hoy}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={
                    "message": f"La reserva es para el {reserva.fecha_reserva.strftime('%d/%m/%Y')}, no puede validar hoy ({fecha_hoy.strftime('%d/%m/%Y')})",
                    "reserva_info": {
                        "id_reserva": reserva.id_reserva,
                        "fecha_reserva": reserva.fecha_reserva.strftime("%d/%m/%Y")
                    }
                }
            )
        
        # CORRECCIÓN: Calcular los horarios permitidos correctamente
        hora_actual = datetime.now().time()
        
        # Convertir hora_inicio y hora_fin a datetime para poder hacer operaciones
        hora_inicio_dt = datetime.combine(date.today(), reserva.hora_inicio)
        hora_fin_dt = datetime.combine(date.today(), reserva.hora_fin)
        
        # Calcular límites con 30 minutos de tolerancia
        hora_inicio_30min_antes_dt = hora_inicio_dt - timedelta(minutes=30)
        hora_fin_30min_despues_dt = hora_fin_dt + timedelta(minutes=30)
        
        # Convertir de nuevo a time
        hora_inicio_30min_antes = hora_inicio_30min_antes_dt.time()
        hora_fin_30min_despues = hora_fin_30min_despues_dt.time()
        
        logger.info(f"🕐 Hora actual: {hora_actual}")
        logger.info(f"🕐 Reserva: {reserva.hora_inicio} - {reserva.hora_fin}")
        logger.info(f"🕐 Permitido entre: {hora_inicio_30min_antes} - {hora_fin_30min_despues}")
        
        # Verificar si está dentro del horario permitido
        if hora_actual < hora_inicio_30min_antes:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={
                    "message": f"No puede validar todavía. Puede validar desde {hora_inicio_30min_antes.strftime('%H:%M')}",
                    "reserva_info": {
                        "id_reserva": reserva.id_reserva,
                        "horario_reserva": f"{reserva.hora_inicio} - {reserva.hora_fin}",
                        "puede_validar_desde": hora_inicio_30min_antes.strftime("%H:%M")
                    }
                }
            )
        
        if hora_actual > hora_fin_30min_despues:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={
                    "message": f"Ya pasó el tiempo para validar. Podía validar hasta {hora_fin_30min_despues.strftime('%H:%M')}",
                    "reserva_info": {
                        "id_reserva": reserva.id_reserva,
                        "horario_reserva": f"{reserva.hora_inicio} - {reserva.hora_fin}",
                        "podia_validar_hasta": hora_fin_30min_despues.strftime("%H:%M")
                    }
                }
            )
        
        # ✅ TODO VERIFICADO - REGISTRAR ASISTENCIA
        asistente.asistio = True
        asistente.fecha_validacion = datetime.now()
        
        try:
            db.commit()
            logger.info(f"✅ Asistencia registrada exitosamente: {asistente.nombre}")
            
            # Preparar respuesta exitosa
            response_data = {
                "success": True,
                "message": f"Asistencia registrada exitosamente para {asistente.nombre}",
                "asistente": {
                    "id_asistente": asistente.id_asistente,
                    "nombre": asistente.nombre,
                    "email": asistente.email,
                    "codigo_qr": asistente.codigo_qr,
                    "asistio": asistente.asistio,
                    "fecha_validacion": asistente.fecha_validacion
                },
                "reserva": {
                    "id_reserva": reserva.id_reserva,
                    "codigo_reserva": reserva.codigo_reserva,
                    "cancha": reserva.cancha.nombre if reserva.cancha else "N/A",
                    "fecha": reserva.fecha_reserva.strftime("%d/%m/%Y"),
                    "hora_inicio": reserva.hora_inicio.strftime("%H:%M"),
                    "hora_fin": reserva.hora_fin.strftime("%H:%M"),
                    "estado": reserva.estado
                }
            }
            
            return response_data
            
        except Exception as e:
            db.rollback()
            logger.error(f"❌ Error al guardar en BD: {str(e)}")
            traceback.print_exc()
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Error al registrar asistencia en la base de datos"
            )
            
    except HTTPException as he:
        logger.error(f"HTTP Exception: {he.detail}")
        raise he
    except Exception as e:
        logger.error(f"❌ Error inesperado: {str(e)}")
        traceback.print_exc()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error interno del servidor al verificar QR"
        )

@router.get("/asistentes/{reserva_id}")
def obtener_asistentes_reserva(
    reserva_id: int,
    db: Session = Depends(get_db)
):
    """Obtener lista de asistentes de una reserva"""
    reserva = db.query(Reserva).filter(Reserva.id_reserva == reserva_id).first()
    if not reserva:
        raise HTTPException(status_code=404, detail="Reserva no encontrada")
    
    asistentes = db.query(AsistenteReserva).filter(
        AsistenteReserva.id_reserva == reserva_id
    ).all()
    
    return {
        "reserva_id": reserva_id,
        "codigo_reserva": reserva.codigo_reserva,
        "total_asistentes": reserva.cantidad_asistentes,
        "asistentes_registrados": len(asistentes),
        "asistentes": [
            {
                "id": a.id_asistente,
                "nombre": a.nombre,
                "email": a.email,
                "asistio": a.asistio,
                "fecha_validacion": a.fecha_validacion
            }
            for a in asistentes
        ]
    }

# Endpoints adicionales para estadísticas
@router.get("/estadisticas/hoy")
def obtener_estadisticas_hoy(db: Session = Depends(get_db)):
    """Obtener estadísticas de asistencias del día"""
    hoy = date.today()
    
    # Total asistencias registradas hoy
    asistencias_hoy = db.query(AsistenteReserva).filter(
        func.date(AsistenteReserva.fecha_validacion) == hoy
    ).count()
    
    # Asistentes por estado de reserva
    asistentes_con_reserva = db.query(AsistenteReserva).join(Reserva).filter(
        Reserva.fecha_reserva == hoy
    ).all()
    
    estadisticas = {
        "fecha": hoy.isoformat(),
        "total_asistencias_hoy": asistencias_hoy,
        "total_reservas_hoy": len(set([a.id_reserva for a in asistentes_con_reserva])),
        "desglose_estado": {}
    }
    
    # Contar por estado de reserva
    for asistente in asistentes_con_reserva:
        estado = asistente.reserva.estado
        if estado not in estadisticas["desglose_estado"]:
            estadisticas["desglose_estado"][estado] = 0
        estadisticas["desglose_estado"][estado] += 1
    
    return estadisticas