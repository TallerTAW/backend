from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from sqlalchemy import func, and_
from datetime import datetime, date
from typing import Optional
from app.database import get_db
from app.models.reserva import Reserva
from app.models.pago import Pago
from app.models.cancha import Cancha
from app.models.espacio_deportivo import EspacioDeportivo

router = APIRouter()

@router.get("/ingresos")
def reporte_ingresos(
    fecha_inicio: date = Query(..., description="Fecha de inicio del reporte"),
    fecha_fin: date = Query(..., description="Fecha de fin del reporte"),
    id_espacio_deportivo: Optional[int] = Query(None, description="Filtrar por espacio deportivo"),
    db: Session = Depends(get_db)
):
    # Base query para ingresos
    query = db.query(
        func.sum(Pago.monto).label("total_ingresos"),
        func.count(Pago.id_pago).label("total_pagos")
    ).join(Reserva).join(Cancha).join(EspacioDeportivo)
    
    # Filtrar por fechas
    query = query.filter(
        and_(
            Pago.fecha_pago >= datetime.combine(fecha_inicio, datetime.min.time()),
            Pago.fecha_pago <= datetime.combine(fecha_fin, datetime.max.time())
        )
    )
    
    # Filtrar por espacio deportivo si se especifica
    if id_espacio_deportivo:
        query = query.filter(EspacioDeportivo.id_espacio_deportivo == id_espacio_deportivo)
    
    # Filtrar solo pagos completados
    query = query.filter(Pago.estado == "completado")
    
    result = query.first()
    
    return {
        "fecha_inicio": fecha_inicio,
        "fecha_fin": fecha_fin,
        "total_ingresos": float(result.total_ingresos) if result.total_ingresos else 0,
        "total_pagos": result.total_pagos or 0
    }

@router.get("/uso-cancha")
def reporte_uso_cancha(
    fecha_inicio: date = Query(..., description="Fecha de inicio del reporte"),
    fecha_fin: date = Query(..., description="Fecha de fin del reporte"),
    db: Session = Depends(get_db)
):
    # Reporte de uso de canchas por espacio deportivo
    query = db.query(
        EspacioDeportivo.nombre.label("espacio"),
        Cancha.nombre.label("cancha"),
        func.count(Reserva.id_reserva).label("total_reservas"),
        func.sum(Reserva.costo_total).label("ingresos_generados")
    ).select_from(Reserva)\
     .join(Cancha)\
     .join(EspacioDeportivo)\
     .filter(
         and_(
             Reserva.fecha_reserva >= fecha_inicio,
             Reserva.fecha_reserva <= fecha_fin,
             Reserva.estado.in_(["confirmada", "completada"])
         )
     )\
     .group_by(EspacioDeportivo.nombre, Cancha.nombre)\
     .order_by(func.count(Reserva.id_reserva).desc())
    
    resultados = query.all()
    
    return [
        {
            "espacio": resultado.espacio,
            "cancha": resultado.cancha,
            "total_reservas": resultado.total_reservas,
            "ingresos_generados": float(resultado.ingresos_generados) if resultado.ingresos_generados else 0
        }
        for resultado in resultados
    ]

@router.get("/reservas-por-estado")
def reporte_reservas_por_estado(
    fecha_inicio: date = Query(..., description="Fecha de inicio del reporte"),
    fecha_fin: date = Query(..., description="Fecha de fin del reporte"),
    db: Session = Depends(get_db)
):
    # Reservas agrupadas por estado
    query = db.query(
        Reserva.estado,
        func.count(Reserva.id_reserva).label("cantidad")
    ).filter(
        and_(
            Reserva.fecha_creacion >= datetime.combine(fecha_inicio, datetime.min.time()),
            Reserva.fecha_creacion <= datetime.combine(fecha_fin, datetime.max.time())
        )
    ).group_by(Reserva.estado)
    
    resultados = query.all()
    
    return {
        "fecha_inicio": fecha_inicio,
        "fecha_fin": fecha_fin,
        "reservas_por_estado": [
            {"estado": resultado.estado, "cantidad": resultado.cantidad}
            for resultado in resultados
        ]
    }

@router.get("/horarios-populares")
def reporte_horarios_populares(
    fecha_inicio: date = Query(..., description="Fecha de inicio del reporte"),
    fecha_fin: date = Query(..., description="Fecha de fin del reporte"),
    db: Session = Depends(get_db)
):
    # Horarios más populares
    query = db.query(
        Reserva.hora_inicio,
        Reserva.hora_fin,
        func.count(Reserva.id_reserva).label("total_reservas")
    ).filter(
        and_(
            Reserva.fecha_reserva >= fecha_inicio,
            Reserva.fecha_reserva <= fecha_fin,
            Reserva.estado.in_(["confirmada", "completada"])
        )
    ).group_by(Reserva.hora_inicio, Reserva.hora_fin)\
     .order_by(func.count(Reserva.id_reserva).desc())\
     .limit(10)
    
    resultados = query.all()
    
    return [
        {
            "hora_inicio": str(resultado.hora_inicio),
            "hora_fin": str(resultado.hora_fin),
            "total_reservas": resultado.total_reservas
        }
        for resultado in resultados
    ]