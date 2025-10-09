from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List, Optional

from app.database import get_db
from app.models.incidente import Incidente
from app.models.usuario import Usuario
from app.models.reserva import Reserva
from app.schemas.incidente import IncidenteCreate, IncidenteResponse, IncidenteUpdate

router = APIRouter()

@router.get("/", response_model=List[IncidenteResponse])
def listar_incidentes(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    return db.query(Incidente).offset(skip).limit(limit).all()

@router.get("/{incidente_id}", response_model=IncidenteResponse)
def obtener_incidente(incidente_id: int, db: Session = Depends(get_db)):
    incidente = db.query(Incidente).filter(Incidente.id_incidente == incidente_id).first()
    if not incidente:
        raise HTTPException(status_code=404, detail="Incidente no encontrado")
    return incidente

@router.post("/", response_model=IncidenteResponse, status_code=status.HTTP_201_CREATED)
def crear_incidente(payload: IncidenteCreate, db: Session = Depends(get_db)):
    # Validar usuario
    usuario = db.query(Usuario).filter(Usuario.id_usuario == payload.id_usuario).first()
    if not usuario:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")
    # Validar reserva si vino id_reserva
    if payload.id_reserva:
        reserva = db.query(Reserva).filter(Reserva.id_reserva == payload.id_reserva).first()
        if not reserva:
            raise HTTPException(status_code=404, detail="Reserva no encontrada")

    nuevo = Incidente(**payload.dict())
    db.add(nuevo)
    db.commit()
    db.refresh(nuevo)
    return nuevo

@router.put("/{incidente_id}", response_model=IncidenteResponse)
def actualizar_incidente(incidente_id: int, payload: IncidenteUpdate, db: Session = Depends(get_db)):
    incidente = db.query(Incidente).filter(Incidente.id_incidente == incidente_id).first()
    if not incidente:
        raise HTTPException(status_code=404, detail="Incidente no encontrado")

    for field, value in payload.dict(exclude_unset=True).items():
        setattr(incidente, field, value)

    db.commit()
    db.refresh(incidente)
    return incidente

@router.delete("/{incidente_id}", status_code=status.HTTP_204_NO_CONTENT)
def eliminar_incidente(incidente_id: int, db: Session = Depends(get_db)):
    incidente = db.query(Incidente).filter(Incidente.id_incidente == incidente_id).first()
    if not incidente:
        raise HTTPException(status_code=404, detail="Incidente no encontrado")
    db.delete(incidente)
    db.commit()
    return None

@router.get("/usuario/{usuario_id}", response_model=List[IncidenteResponse])
def incidentes_por_usuario(usuario_id: int, db: Session = Depends(get_db)):
    usuario = db.query(Usuario).filter(Usuario.id_usuario == usuario_id).first()
    if not usuario:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")
    return db.query(Incidente).filter(Incidente.id_usuario == usuario_id).order_by(Incidente.fecha_incidente.desc()).all()