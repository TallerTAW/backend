from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_
from datetime import datetime, date, time
from typing import List, Optional
from app.database import get_db
from app.models.reserva import Reserva
from app.models.cancha import Cancha
from app.models.usuario import Usuario
from app.models.disciplina import Disciplina
from app.schemas.reserva import ReservaResponse, ReservaCreate, ReservaUpdate
from app.core.security import get_password_hash
import random
import string
from app.schemas.cancha import VerificarDisponibilidadRequest
from sqlalchemy import text


router = APIRouter()

def generar_codigo_reserva():
    """Generar código único para la reserva"""
    letras = string.ascii_uppercase
    numeros = string.digits
    codigo = ''.join(random.choices(letras, k=3)) + ''.join(random.choices(numeros, k=3))
    return codigo

def calcular_costo_total(hora_inicio: time, hora_fin: time, precio_por_hora: float) -> float:
    """Calcular el costo total basado en la duración y precio por hora"""
    duracion_minutos = (hora_fin.hour * 60 + hora_fin.minute) - (hora_inicio.hour * 60 + hora_inicio.minute)
    duracion_horas = duracion_minutos / 60.0
    return round(duracion_horas * precio_por_hora, 2)

def verificar_disponibilidad_cancha(db: Session, id_cancha: int, fecha_reserva: date, hora_inicio: time, hora_fin: time, id_reserva_excluir: Optional[int] = None):
    """Verificar si la cancha está disponible en el horario solicitado"""
    query = db.query(Reserva).filter(
        Reserva.id_cancha == id_cancha,
        Reserva.fecha_reserva == fecha_reserva,
        Reserva.estado.in_(["pendiente", "confirmada", "en_curso"]),
        or_(
            # Solapamiento de horarios
            and_(Reserva.hora_inicio <= hora_inicio, Reserva.hora_fin > hora_inicio),
            and_(Reserva.hora_inicio < hora_fin, Reserva.hora_fin >= hora_fin),
            and_(Reserva.hora_inicio >= hora_inicio, Reserva.hora_fin <= hora_fin)
        )
    )
    
    if id_reserva_excluir:
        query = query.filter(Reserva.id_reserva != id_reserva_excluir)
    
    reserva_conflicto = query.first()
    return reserva_conflicto is None

@router.get("/", response_model=List[ReservaResponse])
def get_reservas(
    skip: int = 0,
    limit: int = 100,
    estado: Optional[str] = None,
    fecha_inicio: Optional[date] = None,
    fecha_fin: Optional[date] = None,
    id_usuario: Optional[int] = None,
    id_cancha: Optional[int] = None,
    db: Session = Depends(get_db)
):
    """Obtener lista de reservas con filtros opcionales"""
    query = db.query(Reserva)
    
    # Aplicar filtros
    if estado:
        query = query.filter(Reserva.estado == estado)
    
    if fecha_inicio:
        query = query.filter(Reserva.fecha_reserva >= fecha_inicio)
    
    if fecha_fin:
        query = query.filter(Reserva.fecha_reserva <= fecha_fin)
    
    if id_usuario:
        query = query.filter(Reserva.id_usuario == id_usuario)
    
    if id_cancha:
        query = query.filter(Reserva.id_cancha == id_cancha)
    
    return query.offset(skip).limit(limit).all()

@router.get("/{reserva_id}", response_model=ReservaResponse)
def get_reserva(reserva_id: int, db: Session = Depends(get_db)):
    """Obtener una reserva específica por ID"""
    reserva = db.query(Reserva).filter(Reserva.id_reserva == reserva_id).first()
    if not reserva:
        raise HTTPException(status_code=404, detail="Reserva no encontrada")
    return reserva

@router.post("/", response_model=ReservaResponse)
def create_reserva(reserva_data: ReservaCreate, db: Session = Depends(get_db)):
    """Crear una nueva reserva con validación de disponibilidad usando función PostgreSQL"""
    # Verificar que la cancha existe
    cancha = db.query(Cancha).filter(Cancha.id_cancha == reserva_data.id_cancha).first()
    if not cancha:
        raise HTTPException(status_code=404, detail="Cancha no encontrada")
    
    # Verificar que la disciplina existe
    disciplina = db.query(Disciplina).filter(Disciplina.id_disciplina == reserva_data.id_disciplina).first()
    if not disciplina:
        raise HTTPException(status_code=404, detail="Disciplina no encontrada")
    
    # Verificar que el usuario existe
    usuario = db.query(Usuario).filter(Usuario.id_usuario == reserva_data.id_usuario).first()
    if not usuario:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")
    
    # VERIFICAR DISPONIBILIDAD USANDO FUNCIÓN POSTGRESQL
    try:
        result = db.execute(
            text("SELECT verificar_disponibilidad(:cancha_id, :fecha, :hora_inicio, :hora_fin) as disponible"),
            {
                "cancha_id": reserva_data.id_cancha,
                "fecha": reserva_data.fecha_reserva,
                "hora_inicio": reserva_data.hora_inicio,
                "hora_fin": reserva_data.hora_fin
            }
        )
        disponible = result.scalar()
        
        if not disponible:
            raise HTTPException(
                status_code=400, 
                detail="La cancha no está disponible en el horario solicitado"
            )
            
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error al verificar disponibilidad: {str(e)}"
        )
    
    # Verificar que el horario esté dentro del rango de la cancha
    if reserva_data.hora_inicio < cancha.hora_apertura or reserva_data.hora_fin > cancha.hora_cierre:
        raise HTTPException(
            status_code=400, 
            detail=f"El horario debe estar entre {cancha.hora_apertura} y {cancha.hora_cierre}"
        )
    
    # Verificar que la fecha no sea en el pasado
    if reserva_data.fecha_reserva < date.today():
        raise HTTPException(status_code=400, detail="No se pueden hacer reservas en fechas pasadas")
    
    # Calcular costo total
    costo_total = calcular_costo_total(
        reserva_data.hora_inicio, reserva_data.hora_fin, float(cancha.precio_por_hora)
    )
    
    # Generar código único de reserva
    codigo_reserva = generar_codigo_reserva()
    
    # Verificar que el código sea único
    while db.query(Reserva).filter(Reserva.codigo_reserva == codigo_reserva).first():
        codigo_reserva = generar_codigo_reserva()
    
    # Crear la reserva
    nueva_reserva = Reserva(
        **reserva_data.dict(),
        costo_total=costo_total,
        codigo_reserva=codigo_reserva,
        estado="pendiente"  # Estado inicial
    )
    
    db.add(nueva_reserva)
    db.commit()
    db.refresh(nueva_reserva)
    
    return nueva_reserva

@router.put("/{reserva_id}", response_model=ReservaResponse)
def update_reserva(reserva_id: int, reserva_data: ReservaUpdate, db: Session = Depends(get_db)):
    """Actualizar una reserva existente"""
    reserva = db.query(Reserva).filter(Reserva.id_reserva == reserva_id).first()
    if not reserva:
        raise HTTPException(status_code=404, detail="Reserva no encontrada")
    
    # No permitir modificar reservas canceladas o completadas
    if reserva.estado in ["cancelada", "completada"]:
        raise HTTPException(status_code=400, detail="No se puede modificar una reserva cancelada o completada")
    
    # Verificar disponibilidad si se cambia el horario o cancha
    if any(field in reserva_data.dict(exclude_unset=True) for field in ['hora_inicio', 'hora_fin', 'fecha_reserva', 'id_cancha']):
        hora_inicio = reserva_data.hora_inicio if reserva_data.hora_inicio else reserva.hora_inicio
        hora_fin = reserva_data.hora_fin if reserva_data.hora_fin else reserva.hora_fin
        fecha_reserva = reserva_data.fecha_reserva if reserva_data.fecha_reserva else reserva.fecha_reserva
        id_cancha = reserva_data.id_cancha if reserva_data.id_cancha else reserva.id_cancha
        
        if not verificar_disponibilidad_cancha(db, id_cancha, fecha_reserva, hora_inicio, hora_fin, reserva_id):
            raise HTTPException(status_code=400, detail="La cancha no está disponible en el nuevo horario")
    
    # Actualizar campos
    for field, value in reserva_data.dict(exclude_unset=True).items():
        setattr(reserva, field, value)
    
    # Recalcular costo si cambió el horario o la cancha
    if any(field in reserva_data.dict(exclude_unset=True) for field in ['hora_inicio', 'hora_fin', 'id_cancha']):
        cancha_id = reserva_data.id_cancha if reserva_data.id_cancha else reserva.id_cancha
        cancha = db.query(Cancha).filter(Cancha.id_cancha == cancha_id).first()
        hora_inicio = reserva_data.hora_inicio if reserva_data.hora_inicio else reserva.hora_inicio
        hora_fin = reserva_data.hora_fin if reserva_data.hora_fin else reserva.hora_fin
        
        reserva.costo_total = calcular_costo_total(hora_inicio, hora_fin, cancha.precio_por_hora)
    
    reserva.fecha_actualizacion = datetime.now()
    db.commit()
    db.refresh(reserva)
    
    return reserva

@router.delete("/{reserva_id}")
def cancelar_reserva(reserva_id: int, motivo: str, db: Session = Depends(get_db)):
    """Cancelar una reserva (soft delete mediante cambio de estado)"""
    reserva = db.query(Reserva).filter(Reserva.id_reserva == reserva_id).first()
    if not reserva:
        raise HTTPException(status_code=404, detail="Reserva no encontrada")
    
    # Verificar que la reserva se puede cancelar
    if reserva.estado in ["cancelada", "completada"]:
        raise HTTPException(status_code=400, detail=f"La reserva ya está {reserva.estado}")
    
    # No permitir cancelar reservas que ya comenzaron
    ahora = datetime.now()
    if reserva.fecha_reserva == ahora.date() and reserva.hora_inicio <= ahora.time():
        raise HTTPException(status_code=400, detail="No se puede cancelar una reserva que ya comenzó")
    
    # Cambiar estado a cancelada
    reserva.estado = "cancelada"
    reserva.fecha_actualizacion = datetime.now()
    
    # Registrar la cancelación (aquí podrías crear un registro en la tabla Cancelacion)
    # Por simplicidad, solo cambiamos el estado por ahora
    
    db.commit()
    
    return {"message": "Reserva cancelada exitosamente"}

@router.get("/usuario/{usuario_id}", response_model=List[ReservaResponse])
def get_reservas_usuario(usuario_id: int, db: Session = Depends(get_db)):
    """Obtener todas las reservas de un usuario específico"""
    usuario = db.query(Usuario).filter(Usuario.id_usuario == usuario_id).first()
    if not usuario:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")
    
    return db.query(Reserva).filter(Reserva.id_usuario == usuario_id).order_by(Reserva.fecha_reserva.desc()).all()

@router.get("/cancha/{cancha_id}/disponibilidad")
def verificar_disponibilidad_cancha_fecha(
    cancha_id: int,
    fecha: date,
    db: Session = Depends(get_db)
):
    """Obtener horarios disponibles para una cancha en una fecha específica"""
    cancha = db.query(Cancha).filter(Cancha.id_cancha == cancha_id).first()
    if not cancha:
        raise HTTPException(status_code=404, detail="Cancha no encontrada")
    
    # Obtener reservas existentes para esa fecha
    reservas = db.query(Reserva).filter(
        Reserva.id_cancha == cancha_id,
        Reserva.fecha_reserva == fecha,
        Reserva.estado.in_(["pendiente", "confirmada"])
    ).all()
    
    # Generar horarios disponibles (bloques de 1 hora)
    horarios_disponibles = []
    hora_actual = cancha.hora_apertura
    hora_cierre = cancha.hora_cierre
    
    while hora_actual < hora_cierre:
        hora_fin = time(hora_actual.hour + 1, hora_actual.minute)
        if hora_fin > hora_cierre:
            break
        
        # Verificar si el horario está disponible
        disponible = True
        for reserva in reservas:
            if not (hora_fin <= reserva.hora_inicio or hora_actual >= reserva.hora_fin):
                disponible = False
                break
        
        if disponible:
            horarios_disponibles.append({
                "hora_inicio": hora_actual.isoformat(),
                "hora_fin": hora_fin.isoformat(),
                "disponible": True
            })
        else:
            horarios_disponibles.append({
                "hora_inicio": hora_actual.isoformat(),
                "hora_fin": hora_fin.isoformat(),
                "disponible": False,
                "reserva_id": next((r.id_reserva for r in reservas if not (hora_fin <= r.hora_inicio or hora_actual >= r.hora_fin)), None)
            })
        
        # Avanzar a la siguiente hora
        hora_actual = hora_fin
    
    return {
        "cancha": cancha.nombre,
        "fecha": fecha.isoformat(),
        "horarios_disponibles": horarios_disponibles
    }

@router.post("/{reserva_id}/confirmar")
def confirmar_reserva(reserva_id: int, db: Session = Depends(get_db)):
    """Confirmar una reserva (cambiar estado a confirmada)"""
    reserva = db.query(Reserva).filter(Reserva.id_reserva == reserva_id).first()
    if not reserva:
        raise HTTPException(status_code=404, detail="Reserva no encontrada")
    
    if reserva.estado != "pendiente":
        raise HTTPException(status_code=400, detail=f"Solo se pueden confirmar reservas pendientes. Estado actual: {reserva.estado}")
    
    reserva.estado = "confirmada"
    reserva.fecha_actualizacion = datetime.now()
    db.commit()
    
    return {"message": "Reserva confirmada exitosamente"}

@router.get("/proximas/{dias}")
def get_reservas_proximas(dias: int = 7, db: Session = Depends(get_db)):
    """Obtener reservas para los próximos N días"""
    hoy = date.today()
    fecha_limite = hoy.replace(day=hoy.day + dias)
    
    reservas = db.query(Reserva).filter(
        Reserva.fecha_reserva >= hoy,
        Reserva.fecha_reserva <= fecha_limite,
        Reserva.estado.in_(["pendiente", "confirmada"])
    ).order_by(Reserva.fecha_reserva, Reserva.hora_inicio).all()
    
    return reservas