# 🎯 PROPÓSITO: Endpoint básico de reservas con validaciones
# 💡 CAMBIOS: Agregar validaciones de código

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.database import get_db
from app.models.reserva import Reserva
from app.schemas.reserva import ReservaResponse, ReservaCreate

router = APIRouter()

@router.get("/", response_model=list[ReservaResponse])
def get_reservas(db: Session = Depends(get_db)):
    reservas = db.query(Reserva).all()
    
    # ✅ VALIDACIÓN: Verificar reservas sin código
    reservas_sin_codigo = [r for r in reservas if not r.codigo_reserva]
    if reservas_sin_codigo:
        print(f"⚠️  ADVERTENCIA: {len(reservas_sin_codigo)} reservas sin código en endpoint básico")
    
    return reservas

@router.get("/{reserva_id}", response_model=ReservaResponse)
def get_reserva(reserva_id: int, db: Session = Depends(get_db)):
    reserva = db.query(Reserva).filter(Reserva.id_reserva == reserva_id).first()
    if not reserva:
        raise HTTPException(status_code=404, detail="Reserva no encontrada")
    
    # ✅ VALIDACIÓN: Verificar que tenga código
    if not reserva.codigo_reserva:
        print(f"⚠️  ADVERTENCIA: Reserva {reserva_id} sin código_reserva en endpoint básico")
    
    return reserva

@router.post("/", response_model=ReservaResponse)
def create_reserva(reserva_data: ReservaCreate, db: Session = Depends(get_db)):
    """NOTA: Este endpoint es básico, usar reservas_opcion.py para funcionalidad completa"""
    # ✅ ADVERTENCIA: Este endpoint no genera código_reserva automáticamente
    # Recomendar usar el endpoint completo en reservas_opcion.py
    if not hasattr(reserva_data, 'codigo_reserva') or not reserva_data.codigo_reserva:
        raise HTTPException(
            status_code=400, 
            detail="Usar endpoint /reservas_opcion/ para creación completa con generación de código"
        )
    
    nueva_reserva = Reserva(**reserva_data.dict())
    db.add(nueva_reserva)
    db.commit()
    db.refresh(nueva_reserva)
    return nueva_reserva