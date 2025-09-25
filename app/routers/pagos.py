from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.database import get_db
from app.models.pago import Pago
from app.models.reserva import Reserva
from app.schemas.pago import PagoResponse, PagoCreate, PagoUpdate

router = APIRouter()

@router.get("/", response_model=list[PagoResponse])
def get_pagos(db: Session = Depends(get_db)):
    return db.query(Pago).all()

@router.get("/{pago_id}", response_model=PagoResponse)
def get_pago(pago_id: int, db: Session = Depends(get_db)):
    pago = db.query(Pago).filter(Pago.id_pago == pago_id).first()
    if not pago:
        raise HTTPException(status_code=404, detail="Pago no encontrado")
    return pago

@router.get("/reserva/{reserva_id}", response_model=PagoResponse)
def get_pago_por_reserva(reserva_id: int, db: Session = Depends(get_db)):
    pago = db.query(Pago).filter(Pago.id_reserva == reserva_id).first()
    if not pago:
        raise HTTPException(status_code=404, detail="Pago no encontrado para esta reserva")
    return pago

@router.post("/", response_model=PagoResponse)
def create_pago(pago_data: PagoCreate, db: Session = Depends(get_db)):
    # Verificar que la reserva existe
    reserva = db.query(Reserva).filter(Reserva.id_reserva == pago_data.id_reserva).first()
    if not reserva:
        raise HTTPException(status_code=404, detail="Reserva no encontrada")
    
    # Verificar que no exista ya un pago para esta reserva
    existing_pago = db.query(Pago).filter(Pago.id_reserva == pago_data.id_reserva).first()
    if existing_pago:
        raise HTTPException(status_code=400, detail="Ya existe un pago para esta reserva")
    
    nuevo_pago = Pago(**pago_data.dict())
    db.add(nuevo_pago)
    db.commit()
    db.refresh(nuevo_pago)
    
    # Actualizar estado de la reserva a "confirmada"
    reserva.estado = "confirmada"
    db.commit()
    
    return nuevo_pago

@router.put("/{pago_id}", response_model=PagoResponse)
def update_pago(pago_id: int, pago_data: PagoUpdate, db: Session = Depends(get_db)):
    pago = db.query(Pago).filter(Pago.id_pago == pago_id).first()
    if not pago:
        raise HTTPException(status_code=404, detail="Pago no encontrado")
    
    for field, value in pago_data.dict(exclude_unset=True).items():
        setattr(pago, field, value)
    
    db.commit()
    db.refresh(pago)
    return pago

@router.post("/{pago_id}/completar")
def completar_pago(pago_id: int, db: Session = Depends(get_db)):
    pago = db.query(Pago).filter(Pago.id_pago == pago_id).first()
    if not pago:
        raise HTTPException(status_code=404, detail="Pago no encontrado")
    
    pago.estado = "completado"
    db.commit()
    
    return {"message": "Pago marcado como completado"}