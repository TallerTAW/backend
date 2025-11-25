from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session, joinedload
from typing import List
from app.database import get_db
from app.models.reserva import Reserva
from app.models.usuario import Usuario
from app.models.cancha import Cancha
from app.models.espacio_deportivo import EspacioDeportivo
from app.models.disciplina import Disciplina
from app.schemas.reserva import ReservaResponse, ReservaCreate, ReservaUpdate

router = APIRouter()

@router.get("/", response_model=List[ReservaResponse])
def get_reservas(db: Session = Depends(get_db)):
    """Obtener todas las reservas con relaciones cargadas"""
    reservas = db.query(Reserva).options(
        joinedload(Reserva.usuario),
        joinedload(Reserva.cancha).joinedload(Cancha.espacio_deportivo),
        joinedload(Reserva.disciplina)
    ).all()
    
    # ✅ MEJOR VALIDACIÓN: Generar códigos temporales si son NULL
    for reserva in reservas:
        if not reserva.codigo_reserva:
            reserva.codigo_reserva = f"TEMP-{reserva.id_reserva}"
            print(f"⚠️  ADVERTENCIA: Reserva {reserva.id_reserva} sin código, usando temporal")
    
    return reservas

@router.get("/{reserva_id}", response_model=ReservaResponse)
def get_reserva(reserva_id: int, db: Session = Depends(get_db)):
    """Obtener una reserva específica con relaciones"""
    reserva = db.query(Reserva).options(
        joinedload(Reserva.usuario),
        joinedload(Reserva.cancha).joinedload(Cancha.espacio_deportivo),
        joinedload(Reserva.disciplina)
    ).filter(Reserva.id_reserva == reserva_id).first()
    
    if not reserva:
        raise HTTPException(status_code=404, detail="Reserva no encontrada")
    
    # ✅ Generar código temporal si es NULL
    if not reserva.codigo_reserva:
        reserva.codigo_reserva = f"TEMP-{reserva.id_reserva}"
    
    return reserva

@router.get("/usuario/{usuario_id}", response_model=List[ReservaResponse])
def get_reservas_usuario(usuario_id: int, db: Session = Depends(get_db)):
    """Obtener reservas de un usuario específico"""
    # Verificar que el usuario existe
    usuario = db.query(Usuario).filter(Usuario.id_usuario == usuario_id).first()
    if not usuario:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")
    
    reservas = db.query(Reserva).options(
        joinedload(Reserva.usuario),
        joinedload(Reserva.cancha).joinedload(Cancha.espacio_deportivo),
        joinedload(Reserva.disciplina)
    ).filter(
        Reserva.id_usuario == usuario_id
    ).order_by(
        Reserva.fecha_reserva.desc()
    ).all()
    
    # ✅ Generar códigos temporales si son NULL
    for reserva in reservas:
        if not reserva.codigo_reserva:
            reserva.codigo_reserva = f"TEMP-{reserva.id_reserva}"
    
    return reservas

@router.post("/", response_model=ReservaResponse)
def create_reserva(reserva_data: ReservaCreate, db: Session = Depends(get_db)):
    """NOTA: Este endpoint es básico, usar reservas_opcion.py para funcionalidad completa"""
    # ✅ ADVERTENCIA: Este endpoint no genera código_reserva automáticamente
    if not hasattr(reserva_data, 'codigo_reserva') or not reserva_data.codigo_reserva:
        raise HTTPException(
            status_code=400, 
            detail="Usar endpoint /reservas_opcion/ para creación completa con generación de código"
        )
    
    nueva_reserva = Reserva(**reserva_data.dict())
    db.add(nueva_reserva)
    db.commit()
    db.refresh(nueva_reserva)
    
    # Recargar con relaciones
    reserva_con_relaciones = db.query(Reserva).options(
        joinedload(Reserva.usuario),
        joinedload(Reserva.cancha).joinedload(Cancha.espacio_deportivo),
        joinedload(Reserva.disciplina)
    ).filter(Reserva.id_reserva == nueva_reserva.id_reserva).first()
    
    return reserva_con_relaciones

@router.patch("/{reserva_id}", response_model=ReservaResponse)  # Cambiar PUT por PATCH
def update_reserva(reserva_id: int, reserva_data: ReservaUpdate, db: Session = Depends(get_db)):
    """Actualizar reserva (principalmente estado)"""
    reserva = db.query(Reserva).filter(Reserva.id_reserva == reserva_id).first()
    if not reserva:
        raise HTTPException(status_code=404, detail="Reserva no encontrada")

    # Actualizar campos permitidos
    campos_permitidos = ['estado', 'material_prestado', 'cantidad_asistentes']
    for campo, valor in reserva_data.dict(exclude_unset=True).items():
        if campo in campos_permitidos and valor is not None:
            setattr(reserva, campo, valor)

    db.commit()
    
    # Recargar con relaciones
    reserva_actualizada = db.query(Reserva).options(
        joinedload(Reserva.usuario),
        joinedload(Reserva.cancha).joinedload(Cancha.espacio_deportivo),
        joinedload(Reserva.disciplina)
    ).filter(Reserva.id_reserva == reserva_id).first()
    
    return reserva_actualizada

@router.delete("/{reserva_id}")
def cancelar_reserva(reserva_id: int, motivo: str = None, db: Session = Depends(get_db)):
    """Cancelar reserva (borrado lógico cambiando estado)"""
    reserva = db.query(Reserva).filter(Reserva.id_reserva == reserva_id).first()
    if not reserva:
        raise HTTPException(status_code=404, detail="Reserva no encontrada")
    
    if reserva.estado == 'cancelada':
        raise HTTPException(status_code=400, detail="La reserva ya está cancelada")
    
    # Cambiar estado a cancelada
    reserva.estado = 'cancelada'
    
    # Aquí podrías crear un registro en la tabla cancelacion si lo necesitas
    from app.models.cancelacion import Cancelacion
    cancelacion = Cancelacion(
        motivo=motivo or "Cancelación por administrador",
        id_reserva=reserva_id,
        id_usuario=reserva.id_usuario  # o el usuario que cancela
    )
    db.add(cancelacion)
    
    db.commit()
    
    return {"detail": "Reserva cancelada exitosamente", "motivo": motivo}