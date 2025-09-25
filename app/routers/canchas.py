from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.database import get_db
from app.models.cancha import Cancha
from app.schemas.cancha import CanchaResponse, CanchaCreate, CanchaUpdate

router = APIRouter()

@router.get("/", response_model=list[CanchaResponse])
def get_canchas(db: Session = Depends(get_db)):
    """Obtener todas las canchas"""
    return db.query(Cancha).all()

@router.get("/{cancha_id}", response_model=CanchaResponse)
def get_cancha(cancha_id: int, db: Session = Depends(get_db)):
    """Obtener una cancha por ID"""
    cancha = db.query(Cancha).filter(Cancha.id_cancha == cancha_id).first()
    if not cancha:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Cancha no encontrada"
        )
    return cancha

@router.post("/", response_model=CanchaResponse, status_code=status.HTTP_201_CREATED)
def create_cancha(cancha_data: CanchaCreate, db: Session = Depends(get_db)):
    """Crear una nueva cancha"""
    
    # Verificar si ya existe una cancha con el mismo nombre en el mismo espacio deportivo
    existing_cancha = db.query(Cancha).filter(
        Cancha.nombre == cancha_data.nombre,
        Cancha.id_espacio_deportivo == cancha_data.id_espacio_deportivo
    ).first()
    
    if existing_cancha:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Ya existe una cancha con este nombre en el espacio deportivo seleccionado"
        )
    
    # Verificar que el espacio deportivo exista (deberías tener esta verificación)
    # from app.models.espacio_deportivo import EspacioDeportivo
    # espacio = db.query(EspacioDeportivo).filter(EspacioDeportivo.id_espacio_deportivo == cancha_data.id_espacio_deportivo).first()
    # if not espacio:
    #     raise HTTPException(status_code=400, detail="El espacio deportivo no existe")
    
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
    
    # Verificar duplicados de nombre si se está actualizando el nombre
    if cancha_data.nombre and cancha_data.nombre != cancha.nombre:
        existing_cancha = db.query(Cancha).filter(
            Cancha.nombre == cancha_data.nombre,
            Cancha.id_espacio_deportivo == cancha.id_espacio_deportivo,
            Cancha.id_cancha != cancha_id
        ).first()
        
        if existing_cancha:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Ya existe una cancha con este nombre en el espacio deportivo"
            )
    
    # Actualizar solo los campos proporcionados
    update_data = cancha_data.dict(exclude_unset=True)
    for field, value in update_data.items():
        setattr(cancha, field, value)
    
    db.commit()
    db.refresh(cancha)
    return cancha

@router.delete("/{cancha_id}")
def delete_cancha(cancha_id: int, db: Session = Depends(get_db)):
    """Eliminar una cancha"""
    cancha = db.query(Cancha).filter(Cancha.id_cancha == cancha_id).first()
    if not cancha:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Cancha no encontrada"
        )
    
    # Verificar si tiene reservas activas antes de eliminar
    if cancha.reservas:
        # Opción 1: Cambiar estado en lugar de eliminar
        cancha.estado = "mantenimiento"
        db.commit()
        return {"detail": "Cancha puesta en mantenimiento (tiene reservas asociadas)"}
        
        # Opción 2: Eliminar directamente (descomenta si prefieres esta opción)
        # db.delete(cancha)
        # db.commit()
        # return {"detail": "Cancha eliminada exitosamente"}
    else:
        db.delete(cancha)
        db.commit()
        return {"detail": "Cancha eliminada exitosamente"}

@router.put("/{cancha_id}/cambiar-estado")
def cambiar_estado_cancha(
    cancha_id: int, 
    nuevo_estado: str,
    db: Session = Depends(get_db)
):
    """Cambiar el estado de una cancha"""
    cancha = db.query(Cancha).filter(Cancha.id_cancha == cancha_id).first()
    if not cancha:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Cancha no encontrada"
        )
    
    estados_validos = ["disponible", "mantenimiento", "ocupada"]
    if nuevo_estado not in estados_validos:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Estado inválido. Los estados válidos son: {', '.join(estados_validos)}"
        )
    
    cancha.estado = nuevo_estado
    db.commit()
    db.refresh(cancha)
    
    return {"detail": f"Estado de la cancha actualizado a '{nuevo_estado}'"}

@router.get("/espacio-deportivo/{espacio_id}", response_model=list[CanchaResponse])
def get_canchas_por_espacio(espacio_id: int, db: Session = Depends(get_db)):
    """Obtener todas las canchas de un espacio deportivo específico"""
    canchas = db.query(Cancha).filter(Cancha.id_espacio_deportivo == espacio_id).all()
    return canchas