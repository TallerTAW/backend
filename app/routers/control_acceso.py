from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from datetime import datetime
from app.database import get_db
from app.models.reserva import Reserva
from app.models.usuario import Usuario

router = APIRouter()

@router.get("/validar-qr/{codigo_reserva}")
def validar_qr(codigo_reserva: str, db: Session = Depends(get_db)):
    """
    Validar código QR de una reserva para control de acceso
    """
    reserva = db.query(Reserva).filter(Reserva.codigo_reserva == codigo_reserva).first()
    
    if not reserva:
        raise HTTPException(status_code=404, detail="Reserva no encontrada")
    
    if reserva.estado != "confirmada":
        raise HTTPException(status_code=400, detail=f"La reserva está {reserva.estado}")
    
    hoy = datetime.now().date()
    if reserva.fecha_reserva != hoy:
        raise HTTPException(
            status_code=400, 
            detail=f"La reserva es para el {reserva.fecha_reserva}, no para hoy"
        )
    
    ahora = datetime.now().time()
    if ahora < reserva.hora_inicio or ahora > reserva.hora_fin:
        raise HTTPException(
            status_code=400,
            detail=f"Fuera del horario de reserva ({reserva.hora_inicio} - {reserva.hora_fin})"
        )
    
    usuario = db.query(Usuario).filter(Usuario.id_usuario == reserva.id_usuario).first()
    
    return {
        "valido": True,
        "reserva": {
            "id": reserva.id_reserva,
            "cancha": reserva.cancha.nombre,
            "espacio": reserva.cancha.espacio_deportivo.nombre,
            "hora_inicio": str(reserva.hora_inicio),
            "hora_fin": str(reserva.hora_fin),
            "usuario": f"{usuario.nombre} {usuario.apellido}",
            "cantidad_asistentes": reserva.cantidad_asistentes
        }
    }

@router.post("/registrar-ingreso/{codigo_reserva}")
def registrar_ingreso(codigo_reserva: str, db: Session = Depends(get_db)):
    """
    Registrar el ingreso efectivo del usuario (cambia estado a "en_curso")
    """
    reserva = db.query(Reserva).filter(Reserva.codigo_reserva == codigo_reserva).first()
    
    if not reserva:
        raise HTTPException(status_code=404, detail="Reserva no encontrada")
    
    hoy = datetime.now().date()
    if reserva.fecha_reserva != hoy:
        raise HTTPException(status_code=400, detail="La reserva no es para hoy")
    
    if reserva.estado != "confirmada":
        raise HTTPException(status_code=400, detail=f"No se puede registrar ingreso para reserva {reserva.estado}")
    
    reserva.estado = "en_curso"
    reserva.fecha_actualizacion = datetime.now()
    db.commit()
    
    return {
        "message": "Ingreso registrado correctamente",
        "estado": "en_curso",
        "hora_ingreso": datetime.now().time().isoformat()
    }

@router.post("/registrar-salida/{codigo_reserva}")
def registrar_salida(codigo_reserva: str, db: Session = Depends(get_db)):
    """
    Registrar la salida del usuario (cambia estado a "completada")
    """
    reserva = db.query(Reserva).filter(Reserva.codigo_reserva == codigo_reserva).first()
    
    if not reserva:
        raise HTTPException(status_code=404, detail="Reserva no encontrada")
    
    if reserva.estado != "en_curso":
        raise HTTPException(status_code=400, detail="La reserva no está en curso")
    
    reserva.estado = "completada"
    reserva.fecha_actualizacion = datetime.now()
    db.commit()
    
    return {
        "message": "Salida registrada correctamente",
        "estado": "completada",
        "hora_salida": datetime.now().time().isoformat()
    }

@router.get("/reservas-hoy")
def obtener_reservas_hoy(db: Session = Depends(get_db)):
    """
    Obtener todas las reservas para el día actual (para el control de acceso)
    """
    hoy = datetime.now().date()
    
    reservas = db.query(Reserva).filter(Reserva.fecha_reserva == hoy).all()
    
    resultado = []
    for reserva in reservas:
        usuario = db.query(Usuario).filter(Usuario.id_usuario == reserva.id_usuario).first()
        resultado.append({
            "id_reserva": reserva.id_reserva,
            "codigo_reserva": reserva.codigo_reserva,
            "cancha": reserva.cancha.nombre,
            "espacio": reserva.cancha.espacio_deportivo.nombre,
            "hora_inicio": str(reserva.hora_inicio),
            "hora_fin": str(reserva.hora_fin),
            "usuario": f"{usuario.nombre} {usuario.apellido}",
            "estado": reserva.estado,
            "cantidad_asistentes": reserva.cantidad_asistentes
        })
    
    return {
        "fecha": hoy.isoformat(),
        "total_reservas": len(reservas),
        "reservas": resultado
    }

@router.get("/reservas-activas")
def obtener_reservas_activas(db: Session = Depends(get_db)):
    """
    Obtener reservas que están actualmente en curso
    """
    ahora = datetime.now()
    hora_actual = ahora.time()
    hoy = ahora.date()
    
    reservas_activas = db.query(Reserva).filter(
        Reserva.fecha_reserva == hoy,
        Reserva.hora_inicio <= hora_actual,
        Reserva.hora_fin >= hora_actual,
        Reserva.estado.in_(["confirmada", "en_curso"])
    ).all()
    
    resultado = []
    for reserva in reservas_activas:
        usuario = db.query(Usuario).filter(Usuario.id_usuario == reserva.id_usuario).first()
        resultado.append({
            "id_reserva": reserva.id_reserva,
            "codigo_reserva": reserva.codigo_reserva,
            "cancha": reserva.cancha.nombre,
            "usuario": f"{usuario.nombre} {usuario.apellido}",
            "estado": reserva.estado,
            "hora_inicio": str(reserva.hora_inicio),
            "hora_fin": str(reserva.hora_fin)
        })
    
    return {
        "hora_actual": hora_actual.isoformat(),
        "reservas_activas": resultado
    }