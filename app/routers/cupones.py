# 📍 ARCHIVO: app/routers/cupones.py
# 🎯 PROPÓSITO: Endpoint completo de cupones
# 💡 CAMBIOS: Mejorar debugging y validaciones

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_
from datetime import date, datetime
import random
import string
from typing import List
from decimal import Decimal

from app.database import get_db
from app.models.cupon import Cupon
from app.models.reserva import Reserva
from app.models.usuario import Usuario
from app.core.security import get_current_user
from app.schemas.cupon import (
    CuponResponse, CuponCreate, CuponUpdate, 
    CuponAplicar, CuponGenerarLote
)

router = APIRouter()

def generar_codigo_cupon(prefijo: str = "CUP") -> str:
    """Generar código único para el cupón"""
    letras = string.ascii_uppercase
    numeros = string.digits
    sufijo = ''.join(random.choices(letras + numeros, k=6))
    return f"{prefijo}_{sufijo}"

@router.get("/", response_model=List[CuponResponse])
def get_cupones(
    skip: int = 0,
    limit: int = 100,
    estado: str = None,
    id_usuario: int = None,
    db: Session = Depends(get_db)
):
    """Obtener lista de cupones con filtros opcionales"""
    query = db.query(Cupon)
    
    if estado:
        query = query.filter(Cupon.estado == estado)
    
    if id_usuario:
        query = query.filter(Cupon.id_usuario == id_usuario)
    
    return query.offset(skip).limit(limit).all()

@router.get("/{cupon_id}", response_model=CuponResponse)
def get_cupon(cupon_id: int, db: Session = Depends(get_db)):
    """Obtener un cupón específico por ID"""
    cupon = db.query(Cupon).filter(Cupon.id_cupon == cupon_id).first()
    if not cupon:
        raise HTTPException(status_code=404, detail="Cupón no encontrado")
    return cupon

@router.get("/codigo/{codigo}", response_model=CuponResponse)
def get_cupon_por_codigo(codigo: str, db: Session = Depends(get_db)):
    """Obtener un cupón por su código"""
    cupon = db.query(Cupon).filter(Cupon.codigo == codigo).first()
    if not cupon:
        raise HTTPException(status_code=404, detail="Cupón no encontrado")
    return cupon

@router.get("/mis-cupones/", response_model=List[CuponResponse])
def get_mis_cupones(
    current_user: Usuario = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Obtener cupones del usuario actual"""
    return db.query(Cupon).filter(
        or_(
            Cupon.id_usuario == current_user.id_usuario,
            Cupon.id_usuario.is_(None)  # Cupones generales
        ),
        Cupon.estado == "activo",
        or_(
            Cupon.fecha_expiracion.is_(None),
            Cupon.fecha_expiracion >= date.today()
        )
    ).all()

@router.post("/", response_model=CuponResponse)
def create_cupon(cupon_data: CuponCreate, db: Session = Depends(get_db)):
    """Crear un nuevo cupón"""
    # Verificar que el código sea único
    existing_cupon = db.query(Cupon).filter(Cupon.codigo == cupon_data.codigo).first()
    if existing_cupon:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Ya existe un cupón con ese código"
        )
    
    # Verificar que el usuario existe si se especifica
    if cupon_data.id_usuario:
        usuario = db.query(Usuario).filter(Usuario.id_usuario == cupon_data.id_usuario).first()
        if not usuario:
            raise HTTPException(status_code=404, detail="Usuario no encontrado")
    
    # Validar que el descuento por porcentaje no sea mayor a 100%
    if cupon_data.tipo == "porcentaje" and cupon_data.monto_descuento > 100:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="El descuento porcentual no puede ser mayor al 100%"
        )
    
    nuevo_cupon = Cupon(**cupon_data.dict())
    db.add(nuevo_cupon)
    db.commit()
    db.refresh(nuevo_cupon)
    return nuevo_cupon

@router.post("/generar-lote", response_model=List[CuponResponse])
def generar_cupones_lote(lote_data: CuponGenerarLote, db: Session = Depends(get_db)):
    """Generar múltiples cupones automáticamente"""
    cupones_generados = []
    
    for i in range(lote_data.cantidad):
        # Generar código único
        codigo = generar_codigo_cupon(lote_data.prefijo)
        while db.query(Cupon).filter(Cupon.codigo == codigo).first():
            codigo = generar_codigo_cupon(lote_data.prefijo)
        
        cupon_data = CuponCreate(
            codigo=codigo,
            monto_descuento=lote_data.monto_descuento,
            tipo=lote_data.tipo,
            fecha_expiracion=lote_data.fecha_expiracion,
            estado="activo"
        )
        
        # Validar porcentaje
        if lote_data.tipo == "porcentaje" and lote_data.monto_descuento > 100:
            continue  # Saltar este cupón
        
        nuevo_cupon = Cupon(**cupon_data.dict())
        db.add(nuevo_cupon)
        cupones_generados.append(nuevo_cupon)
    
    db.commit()
    
    # Refrescar los objetos para obtener los IDs
    for cupon in cupones_generados:
        db.refresh(cupon)
    
    return cupones_generados

@router.put("/{cupon_id}", response_model=CuponResponse)
def update_cupon(cupon_id: int, cupon_data: CuponUpdate, db: Session = Depends(get_db)):
    """Actualizar un cupón existente"""
    cupon = db.query(Cupon).filter(Cupon.id_cupon == cupon_id).first()
    if not cupon:
        raise HTTPException(status_code=404, detail="Cupón no encontrado")
    
    # Verificar código único si se está actualizando
    if cupon_data.codigo and cupon_data.codigo != cupon.codigo:
        existing_cupon = db.query(Cupon).filter(
            Cupon.codigo == cupon_data.codigo,
            Cupon.id_cupon != cupon_id
        ).first()
        if existing_cupon:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Ya existe un cupón con ese código"
            )
    
    # Validar porcentaje
    if cupon_data.tipo == "porcentaje" and cupon_data.monto_descuento and cupon_data.monto_descuento > 100:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="El descuento porcentual no puede ser mayor al 100%"
        )
    
    # Actualizar campos
    for field, value in cupon_data.dict(exclude_unset=True).items():
        setattr(cupon, field, value)
    
    db.commit()
    db.refresh(cupon)
    return cupon

@router.post("/aplicar")
def aplicar_cupon(aplicar_data: CuponAplicar, db: Session = Depends(get_db)):
    """
    🎯 APLICAR CUPÓN A RESERVA EXISTENTE
    💡 NOTA: Esta función ahora se usa principalmente para aplicar cupones a reservas ya creadas
    """
    print(f"🎫 [CUPONES] Aplicando cupón: {aplicar_data.codigo_cupon} a reserva: {aplicar_data.id_reserva}")
    
    # Buscar el cupón
    cupon = db.query(Cupon).filter(Cupon.codigo == aplicar_data.codigo_cupon).first()
    if not cupon:
        raise HTTPException(status_code=404, detail="Cupón no encontrado")
    
    # Buscar la reserva
    reserva = db.query(Reserva).filter(Reserva.id_reserva == aplicar_data.id_reserva).first()
    if not reserva:
        raise HTTPException(status_code=404, detail="Reserva no encontrada")
    
    print(f"🔍 [CUPONES] Cupón encontrado: {cupon.codigo}, Reserva encontrada: {reserva.id_reserva}")
    
    # Validaciones del cupón
    if cupon.estado != "activo":
        raise HTTPException(status_code=400, detail="El cupón no está activo")
    
    if cupon.fecha_expiracion and cupon.fecha_expiracion < date.today():
        raise HTTPException(status_code=400, detail="El cupón ha expirado")
    
    if cupon.id_usuario and cupon.id_usuario != reserva.id_usuario:
        raise HTTPException(status_code=400, detail="Este cupón no es válido para este usuario")
    
    if cupon.id_reserva:
        raise HTTPException(status_code=400, detail="Este cupón ya ha sido utilizado")
    
    # Guardar costo original para referencia
    costo_original = reserva.costo_total
    print(f"💰 [CUPONES] Costo original de reserva: ${costo_original}")
    
    # Aplicar descuento a la reserva
    if cupon.tipo == "porcentaje":
        descuento = (reserva.costo_total * cupon.monto_descuento) / 100
        print(f"🎫 [CUPONES] Descuento porcentual: {cupon.monto_descuento}% = ${descuento}")
    else:  # fijo
        descuento = cupon.monto_descuento
        print(f"🎫 [CUPONES] Descuento fijo: ${descuento}")
    
    # Asegurar que el descuento no sea mayor al costo total
    if descuento > reserva.costo_total:
        descuento = reserva.costo_total
        print(f"⚠️ [CUPONES] Descuento ajustado a costo total: ${descuento}")
    
    nuevo_costo = reserva.costo_total - descuento
    print(f"💰 [CUPONES] Nuevo costo después de descuento: ${nuevo_costo}")
    
    # Actualizar reserva y cupón
    reserva.costo_total = nuevo_costo
    cupon.id_reserva = reserva.id_reserva
    cupon.estado = "utilizado"
    
    db.commit()
    
    print(f"✅ [CUPONES] Cupón aplicado exitosamente a reserva {reserva.id_reserva}")
    
    return {
        "message": "Cupón aplicado exitosamente",
        "descuento_aplicado": float(descuento),
        "nuevo_costo": float(nuevo_costo),
        "costo_original": float(costo_original),
        "reserva_id": reserva.id_reserva,
        "cupon_codigo": cupon.codigo
    }

@router.put("/{cupon_id}/activar")
def activar_cupon(cupon_id: int, db: Session = Depends(get_db)):
    """Activar un cupón inactivo"""
    cupon = db.query(Cupon).filter(Cupon.id_cupon == cupon_id).first()
    if not cupon:
        raise HTTPException(status_code=404, detail="Cupón no encontrado")
    
    if cupon.estado == "activo":
        raise HTTPException(status_code=400, detail="El cupón ya está activo")
    
    cupon.estado = "activo"
    db.commit()
    
    return {"detail": "Cupón activado exitosamente"}

@router.put("/{cupon_id}/desactivar")
def desactivar_cupon(cupon_id: int, db: Session = Depends(get_db)):
    """Desactivar un cupón (borrado lógico)"""
    cupon = db.query(Cupon).filter(Cupon.id_cupon == cupon_id).first()
    if not cupon:
        raise HTTPException(status_code=404, detail="Cupón no encontrado")
    
    if cupon.estado == "inactivo":
        raise HTTPException(status_code=400, detail="El cupón ya está inactivo")
    
    cupon.estado = "inactivo"
    db.commit()
    
    return {"detail": "Cupón desactivado exitosamente"}

@router.get("/usuario/{usuario_id}", response_model=List[CuponResponse])
def get_cupones_usuario(usuario_id: int, db: Session = Depends(get_db)):
    """Obtener cupones de un usuario específico"""
    usuario = db.query(Usuario).filter(Usuario.id_usuario == usuario_id).first()
    if not usuario:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")
    
    return db.query(Cupon).filter(
        or_(
            Cupon.id_usuario == usuario_id,
            Cupon.id_usuario.is_(None)  # Cupones generales
        ),
        Cupon.estado == "activo",
        or_(
            Cupon.fecha_expiracion.is_(None),
            Cupon.fecha_expiracion >= date.today()
        )
    ).all()

@router.get("/validar/{codigo}")
def validar_cupon(codigo: str, id_usuario: int = None, db: Session = Depends(get_db)):
    """Validar si un cupón es válido para usar"""
    cupon = db.query(Cupon).filter(Cupon.codigo == codigo).first()
    if not cupon:
        return {"valido": False, "mensaje": "Cupón no encontrado"}
    
    # Validaciones
    if cupon.estado != "activo":
        return {"valido": False, "mensaje": "El cupón no está activo"}
    
    if cupon.fecha_expiracion and cupon.fecha_expiracion < date.today():
        return {"valido": False, "mensaje": "El cupón ha expirado"}
    
    if cupon.id_reserva:
        return {"valido": False, "mensaje": "El cupón ya ha sido utilizado"}
    
    if cupon.id_usuario and id_usuario and cupon.id_usuario != id_usuario:
        return {"valido": False, "mensaje": "Este cupón no es válido para este usuario"}
    
    return {
        "valido": True,
        "mensaje": "Cupón válido",
        "cupon": {
            "id": cupon.id_cupon,
            "codigo": cupon.codigo,
            "tipo": cupon.tipo,
            "monto_descuento": float(cupon.monto_descuento),
            "fecha_expiracion": cupon.fecha_expiracion
        }
    }