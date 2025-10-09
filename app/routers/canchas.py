from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.database import get_db
from app.models.cancha import Cancha
from app.models.espacio_deportivo import EspacioDeportivo
from app.schemas.cancha import CanchaResponse, CanchaCreate, CanchaUpdate

router = APIRouter()

@router.get("/", response_model=list[CanchaResponse])
def get_canchas(db: Session = Depends(get_db)):
    """Obtener todas las canchas"""
    return db.query(Cancha).all()

@router.get("/{cancha_id}", response_model=CanchaResponse)
def get_cancha(cancha_id: int, db: Session = Depends(get_db)):
    """Obtener una cancha específica por ID"""
    cancha = db.query(Cancha).filter(Cancha.id_cancha == cancha_id).first()
    if not cancha:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Cancha no encontrada"
        )
    return cancha

@router.get("/espacio/{espacio_id}", response_model=list[CanchaResponse])
def get_canchas_por_espacio(espacio_id: int, db: Session = Depends(get_db)):
    """Obtener canchas por espacio deportivo"""
    # Verificar que el espacio existe
    espacio = db.query(EspacioDeportivo).filter(EspacioDeportivo.id_espacio_deportivo == espacio_id).first()
    if not espacio:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Espacio deportivo no encontrado"
        )
    
    return db.query(Cancha).filter(Cancha.id_espacio_deportivo == espacio_id).all()

@router.post("/", response_model=CanchaResponse)
def create_cancha(cancha_data: CanchaCreate, db: Session = Depends(get_db)):
    """Crear una nueva cancha"""
    # Verificar que el espacio deportivo existe
    espacio = db.query(EspacioDeportivo).filter(
        EspacioDeportivo.id_espacio_deportivo == cancha_data.id_espacio_deportivo
    ).first()
    
    if not espacio:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Espacio deportivo no encontrado"
        )
    
    # Verificar si ya existe una cancha con el mismo nombre en el mismo espacio
    existing_cancha = db.query(Cancha).filter(
        Cancha.nombre == cancha_data.nombre,
        Cancha.id_espacio_deportivo == cancha_data.id_espacio_deportivo
    ).first()
    
    if existing_cancha:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Ya existe una cancha con ese nombre en este espacio deportivo"
        )
    
    nueva_cancha = Cancha(**cancha_data.dict())
    db.add(nueva_cancha)
    db.commit()
    db.refresh(nueva_cancha)
    return nueva_cancha

@router.put("/{cancha_id}", response_model=CanchaResponse)
def update_cancha(cancha_id: int, cancha_data: CanchaUpdate, db: Session = Depends(get_db)):
    """Actualizar una cancha existente"""
    cancha = db.query(Cancha).filter(Cancha.id_cancha == cancha_id).first()
    if not cancha:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Cancha no encontrada"
        )
    
    # Verificar espacio deportivo si se está actualizando
    if cancha_data.id_espacio_deportivo is not None:
        espacio = db.query(EspacioDeportivo).filter(
            EspacioDeportivo.id_espacio_deportivo == cancha_data.id_espacio_deportivo
        ).first()
        if not espacio:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Espacio deportivo no encontrado"
            )
    
    # Verificar nombre único si se está actualizando - CORREGIDO
    if cancha_data.nombre is not None and cancha_data.nombre != cancha.nombre:
        # Determinar qué espacio deportivo usar para la verificación
        espacio_id_verificar = cancha_data.id_espacio_deportivo if cancha_data.id_espacio_deportivo is not None else cancha.id_espacio_deportivo
        
        existing_cancha = db.query(Cancha).filter(
            Cancha.nombre == cancha_data.nombre,
            Cancha.id_espacio_deportivo == espacio_id_verificar,
            Cancha.id_cancha != cancha_id
        ).first()
        
        if existing_cancha:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Ya existe una cancha con ese nombre en este espacio deportivo"
            )
    
    # Actualizar campos
    update_data = cancha_data.dict(exclude_unset=True)
    for field, value in update_data.items():
        setattr(cancha, field, value)
    
    db.commit()
    db.refresh(cancha)
    return cancha

@router.delete("/{cancha_id}")
def delete_cancha(cancha_id: int, db: Session = Depends(get_db)):
    """Eliminar una cancha (borrado físico)"""
    cancha = db.query(Cancha).filter(Cancha.id_cancha == cancha_id).first()
    if not cancha:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Cancha no encontrada"
        )
    
    # Verificar si la cancha tiene reservas activas
    from app.models.reserva import Reserva
    reservas_activas = db.query(Reserva).filter(
        Reserva.id_cancha == cancha_id,
        Reserva.estado.in_(["pendiente", "confirmada", "en_curso"])
    ).first()
    
    if reservas_activas:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No se puede eliminar la cancha porque tiene reservas activas"
        )
    
    db.delete(cancha)
    db.commit()
    
    return {"detail": "Cancha eliminada correctamente"}

@router.put("/{cancha_id}/desactivar")
def desactivar_cancha(cancha_id: int, db: Session = Depends(get_db)):
    """Desactivar una cancha (borrado lógico)"""
    cancha = db.query(Cancha).filter(Cancha.id_cancha == cancha_id).first()
    if not cancha:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Cancha no encontrada"
        )
    
    if cancha.estado == "inactiva":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="La cancha ya está inactiva"
        )
    
    cancha.estado = "inactiva"
    db.commit()
    db.refresh(cancha)
    
    return {"detail": "Cancha desactivada correctamente"}

@router.put("/{cancha_id}/activar")
def activar_cancha(cancha_id: int, db: Session = Depends(get_db)):
    """Activar una cancha previamente desactivada"""
    cancha = db.query(Cancha).filter(Cancha.id_cancha == cancha_id).first()
    if not cancha:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Cancha no encontrada"
        )
    
    if cancha.estado == "disponible":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="La cancha ya está activa"
        )
    
    cancha.estado = "disponible"
    db.commit()
    db.refresh(cancha)
    
    return {"detail": "Cancha activada correctamente"}