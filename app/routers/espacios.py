from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.database import get_db
from app.models.espacio_deportivo import EspacioDeportivo
from app.schemas.espacio_deportivo import EspacioDeportivoResponse, EspacioDeportivoCreate, EspacioDeportivoUpdate

router = APIRouter()

@router.get("/", response_model=list[EspacioDeportivoResponse])
def get_espacios(include_inactive: bool = False, db: Session = Depends(get_db)):
    """Obtener espacios deportivos, incluir inactivos solo si se solicita"""
    query = db.query(EspacioDeportivo)
    if not include_inactive:
        query = query.filter(EspacioDeportivo.estado == "activo")
    return query.all()

@router.get("/{espacio_id}", response_model=EspacioDeportivoResponse)
def get_espacio(espacio_id: int, db: Session = Depends(get_db)):
    espacio = db.query(EspacioDeportivo).filter(EspacioDeportivo.id_espacio_deportivo == espacio_id).first()
    if not espacio:
        raise HTTPException(status_code=404, detail="Espacio deportivo no encontrado")
    return espacio

@router.post("/", response_model=EspacioDeportivoResponse)
def create_espacio(espacio_data: EspacioDeportivoCreate, db: Session = Depends(get_db)):
    # Verificar si ya existe un espacio con el mismo nombre
    existing_espacio = db.query(EspacioDeportivo).filter(EspacioDeportivo.nombre == espacio_data.nombre).first()
    if existing_espacio:
        raise HTTPException(status_code=400, detail="Ya existe un espacio deportivo con ese nombre")
    
    nuevo_espacio = EspacioDeportivo(**espacio_data.dict())
    db.add(nuevo_espacio)
    db.commit()
    db.refresh(nuevo_espacio)
    return nuevo_espacio

@router.put("/{espacio_id}", response_model=EspacioDeportivoResponse)
def update_espacio(espacio_id: int, espacio_data: EspacioDeportivoUpdate, db: Session = Depends(get_db)):
    espacio = db.query(EspacioDeportivo).filter(EspacioDeportivo.id_espacio_deportivo == espacio_id).first()
    if not espacio:
        raise HTTPException(status_code=404, detail="Espacio deportivo no encontrado")
    
    # Verificar nombre único si se está actualizando
    if espacio_data.nombre and espacio_data.nombre != espacio.nombre:
        existing_espacio = db.query(EspacioDeportivo).filter(
            EspacioDeportivo.nombre == espacio_data.nombre,
            EspacioDeportivo.id_espacio_deportivo != espacio_id
        ).first()
        if existing_espacio:
            raise HTTPException(status_code=400, detail="Ya existe un espacio deportivo con ese nombre")
    
    # Actualizar campos
    for field, value in espacio_data.dict(exclude_unset=True).items():
        setattr(espacio, field, value)
    
    db.commit()
    db.refresh(espacio)
    return espacio

@router.delete("/{espacio_id}")
def desactivar_espacio(espacio_id: int, db: Session = Depends(get_db)):
    """Desactivar espacio deportivo (borrado lógico)"""
    espacio = db.query(EspacioDeportivo).filter(EspacioDeportivo.id_espacio_deportivo == espacio_id).first()
    if not espacio:
        raise HTTPException(status_code=404, detail="Espacio deportivo no encontrado")
    
    if espacio.estado == "inactivo":
        raise HTTPException(status_code=400, detail="El espacio deportivo ya está inactivo")
    
    espacio.estado = "inactivo"
    db.commit()
    
    return {"detail": "Espacio deportivo desactivado exitosamente"}

@router.put("/{espacio_id}/activar")
def activar_espacio(espacio_id: int, db: Session = Depends(get_db)):
    """Reactivar un espacio deportivo previamente desactivado"""
    espacio = db.query(EspacioDeportivo).filter(EspacioDeportivo.id_espacio_deportivo == espacio_id).first()
    if not espacio:
        raise HTTPException(status_code=404, detail="Espacio deportivo no encontrado")
    
    if espacio.estado == "activo":
        raise HTTPException(status_code=400, detail="El espacio deportivo ya está activo")
    
    espacio.estado = "activo"
    db.commit()
    
    return {"detail": "Espacio deportivo activado exitosamente"}