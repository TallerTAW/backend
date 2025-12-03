# 📍 ARCHIVO: app/routers/reservas_opcion.py
# 🎯 PROPÓSITO: Endpoint completo de reservas con integración de cupones y todas las funciones
# 💡 VERSIÓN FUSIONADA: Combina reservas_opcion.py original con reservas.py básico

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import and_, or_
from datetime import datetime, date, time
from typing import List, Optional
from app.database import get_db
from app.models.reserva import Reserva
from app.models.cancha import Cancha
from app.models.usuario import Usuario
from app.models.disciplina import Disciplina
from app.models.cupon import Cupon
from app.schemas.reserva import ReservaResponse, ReservaCreate, ReservaUpdate
from app.models.administra import Administra
import random
import string
from sqlalchemy import text

router = APIRouter()

def generar_codigo_reserva():
    """Generar código único para la reserva - MEJORADO"""
    letras = string.ascii_uppercase
    numeros = string.digits
    # Formato: AAA111 (3 letras + 3 números)
    codigo = ''.join(random.choices(letras, k=3)) + ''.join(random.choices(numeros, k=3))
    return codigo

def generar_codigo_unico_reserva(db: Session, max_intentos=10):
    """Generar código único con validación - NUEVA FUNCIÓN MEJORADA"""
    for intento in range(max_intentos):
        codigo = generar_codigo_reserva()
        # Verificar que no exista
        existe = db.query(Reserva).filter(Reserva.codigo_reserva == codigo).first()
        if not existe:
            return codigo
    
    # Si falla después de varios intentos, usar timestamp
    timestamp = int(datetime.now().timestamp())
    return f"RES{timestamp}"

def calcular_costo_total(hora_inicio: time, hora_fin: time, precio_por_hora: float) -> float:
    """Calcular el costo total basado en la duración y precio por hora"""
    duracion_minutos = (hora_fin.hour * 60 + hora_fin.minute) - (hora_inicio.hour * 60 + hora_inicio.minute)
    duracion_horas = duracion_minutos / 60.0
    return round(duracion_horas * precio_por_hora, 2)

# ========== ENDPOINTS BÁSICOS DE RESERVAS (del archivo reservas.py) ==========

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
    """Obtener lista de reservas con filtros opcionales y relaciones cargadas"""
    query = db.query(Reserva).options(
        joinedload(Reserva.usuario),
        joinedload(Reserva.cancha).joinedload(Cancha.espacio_deportivo),
        joinedload(Reserva.disciplina)
    )
    
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
    
    reservas = query.offset(skip).limit(limit).all()
    
    # ✅ VALIDACIÓN ADICIONAL: Loggear si hay reservas sin código (para debugging)
    reservas_sin_codigo = [r for r in reservas if not r.codigo_reserva]
    if reservas_sin_codigo:
        print(f"⚠️  ADVERTENCIA: {len(reservas_sin_codigo)} reservas sin código")
        # Generar códigos temporales para evitar errores en frontend
        for reserva in reservas_sin_codigo:
            reserva.codigo_reserva = f"TEMP-{reserva.id_reserva}"
    
    return reservas

@router.get("/{reserva_id}", response_model=ReservaResponse)
def get_reserva(reserva_id: int, db: Session = Depends(get_db)):
    """Obtener una reserva específica por ID con relaciones"""
    reserva = db.query(Reserva).options(
        joinedload(Reserva.usuario),
        joinedload(Reserva.cancha).joinedload(Cancha.espacio_deportivo),
        joinedload(Reserva.disciplina)
    ).filter(Reserva.id_reserva == reserva_id).first()
    
    if not reserva:
        raise HTTPException(status_code=404, detail="Reserva no encontrada")
    
    # ✅ VALIDACIÓN: Verificar que tenga código
    if not reserva.codigo_reserva:
        print(f"⚠️  ADVERTENCIA: Reserva {reserva_id} sin código_reserva")
        reserva.codigo_reserva = f"TEMP-{reserva_id}"
    
    return reserva

@router.get("/usuario/{usuario_id}", response_model=List[ReservaResponse])
def get_reservas_usuario(usuario_id: int, db: Session = Depends(get_db)):
    """Obtener reservas de un usuario específico con relaciones"""
    print(f"👤 [BACKEND] Obteniendo reservas para usuario {usuario_id}")
    
    # Verificar que el usuario existe
    usuario = db.query(Usuario).filter(Usuario.id_usuario == usuario_id).first()
    if not usuario:
        print(f"❌ [BACKEND] Usuario {usuario_id} no encontrado")
        raise HTTPException(status_code=404, detail="Usuario no encontrado")
    
    # Obtener reservas del usuario con relaciones
    reservas = db.query(Reserva).options(
        joinedload(Reserva.usuario),
        joinedload(Reserva.cancha).joinedload(Cancha.espacio_deportivo),
        joinedload(Reserva.disciplina)
    ).filter(
        Reserva.id_usuario == usuario_id
    ).order_by(
        Reserva.fecha_reserva.desc(),
        Reserva.hora_inicio.desc()
    ).all()
    
    print(f"✅ [BACKEND] Encontradas {len(reservas)} reservas para usuario {usuario_id}")
    
    # ✅ VALIDACIÓN: Generar códigos temporales si son NULL
    for reserva in reservas:
        if not reserva.codigo_reserva:
            reserva.codigo_reserva = f"TEMP-{reserva.id_reserva}"
            print(f"⚠️  ADVERTENCIA: Reserva {reserva.id_reserva} sin código, usando temporal")
    
    return reservas

@router.patch("/{reserva_id}", response_model=ReservaResponse)
def update_reserva(reserva_id: int, reserva_data: ReservaUpdate, db: Session = Depends(get_db)):
    """Actualizar reserva (principalmente estado) - NUEVO ENDPOINT PATCH"""
    print(f"🔧 [BACKEND] Actualizando reserva {reserva_id} con datos: {reserva_data.dict()}")
    
    reserva = db.query(Reserva).filter(Reserva.id_reserva == reserva_id).first()
    if not reserva:
        print(f"❌ [BACKEND] Reserva {reserva_id} no encontrada")
        raise HTTPException(status_code=404, detail="Reserva no encontrada")

    # Log del estado actual
    print(f"📋 [BACKEND] Estado actual de reserva {reserva_id}: {reserva.estado}")
    
    # Actualizar campos permitidos
    campos_permitidos = ['estado', 'material_prestado', 'cantidad_asistentes']
    campos_actualizados = []
    
    for campo, valor in reserva_data.dict(exclude_unset=True).items():
        if campo in campos_permitidos and valor is not None:
            setattr(reserva, campo, valor)
            campos_actualizados.append(campo)
            print(f"✅ [BACKEND] Campo actualizado: {campo} = {valor}")

    if not campos_actualizados:
        print("⚠️ [BACKEND] No se actualizaron campos (ningún cambio o campos no permitidos)")
    
    try:
        db.commit()
        db.refresh(reserva)
        print(f"🎉 [BACKEND] Reserva {reserva_id} actualizada exitosamente. Campos: {campos_actualizados}")
        
        # Recargar con relaciones
        reserva_actualizada = db.query(Reserva).options(
            joinedload(Reserva.usuario),
            joinedload(Reserva.cancha).joinedload(Cancha.espacio_deportivo),
            joinedload(Reserva.disciplina)
        ).filter(Reserva.id_reserva == reserva_id).first()
        
        return reserva_actualizada
        
    except Exception as e:
        db.rollback()
        print(f"❌ [BACKEND] Error al actualizar reserva {reserva_id}: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Error al actualizar reserva: {str(e)}"
        )

@router.delete("/{reserva_id}")
def cancelar_reserva(reserva_id: int, motivo: str = None, db: Session = Depends(get_db)):
    """Cancelar reserva (borrado lógico cambiando estado) - NUEVO ENDPOINT DELETE"""
    print(f"🗑️ [BACKEND] Cancelando reserva {reserva_id}. Motivo: {motivo}")
    
    reserva = db.query(Reserva).filter(Reserva.id_reserva == reserva_id).first()
    if not reserva:
        print(f"❌ [BACKEND] Reserva {reserva_id} no encontrada")
        raise HTTPException(status_code=404, detail="Reserva no encontrada")
    
    if reserva.estado == 'cancelada':
        print(f"⚠️ [BACKEND] Reserva {reserva_id} ya está cancelada")
        raise HTTPException(status_code=400, detail="La reserva ya está cancelada")
    
    # Guardar el estado anterior para logging
    estado_anterior = reserva.estado
    
    # Cambiar estado a cancelada
    reserva.estado = 'cancelada'
    
    # Aquí podrías crear un registro en la tabla cancelacion si lo necesitas
    try:
        from app.models.cancelacion import Cancelacion
        cancelacion = Cancelacion(
            motivo=motivo or "Cancelación por administrador",
            id_reserva=reserva_id,
            id_usuario=reserva.id_usuario  # o el usuario que cancela
        )
        db.add(cancelacion)
        print(f"✅ [BACKEND] Registro de cancelación creado para reserva {reserva_id}")
    except Exception as e:
        print(f"⚠️ [BACKEND] No se pudo crear registro de cancelación: {str(e)}")
        # No fallar si no se puede crear el registro de cancelación
    
    try:
        db.commit()
        print(f"🎉 [BACKEND] Reserva {reserva_id} cancelada exitosamente. Estado anterior: {estado_anterior}")
        
        return {
            "detail": "Reserva cancelada exitosamente", 
            "motivo": motivo,
            "reserva_id": reserva_id,
            "estado_anterior": estado_anterior
        }
        
    except Exception as e:
        db.rollback()
        print(f"❌ [BACKEND] Error al cancelar reserva {reserva_id}: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Error al cancelar reserva: {str(e)}"
        )

# ========== ENDPOINTS COMPLETOS CON CUPONES (del archivo reservas_opcion.py original) ==========

@router.post("/", response_model=ReservaResponse)
def create_reserva(reserva_data: ReservaCreate, db: Session = Depends(get_db)):
    """
    🎯 CREAR RESERVA CON SOPORTE PARA CUPONES - VERSIÓN CORREGIDA
    💡 CAMBIO PRINCIPAL: Integración completa del sistema de cupones durante la creación
    💡 CORRECCIÓN CRÍTICA: Conversión de decimal.Decimal a float en cálculo de descuentos
    """
    print(f"🎯 [BACKEND] Iniciando creación de reserva: {reserva_data.dict()}")

    # ✅ VALIDACIÓN: Solo horas completas (minutos en 00)
    if reserva_data.hora_inicio.minute != 0 or reserva_data.hora_fin.minute != 0:
        raise HTTPException(
            status_code=400, 
            detail="Las reservas solo pueden hacerse en horas completas (ej: 10:00, 11:00). Por favor, seleccione una hora en punto."
        )
    
    # Verificar que la cancha existe
    cancha = db.query(Cancha).filter(Cancha.id_cancha == reserva_data.id_cancha).first()
    if not cancha:
        raise HTTPException(status_code=404, detail="Cancha no encontrada")
    
    # ✅ VALIDACIÓN ADICIONAL: Cancha debe estar activa
    if cancha.estado != 'disponible':
        raise HTTPException(status_code=400, detail="La cancha no está disponible para reservas")
    
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
        print(f"🔍 [BACKEND] Verificando disponibilidad para cancha {reserva_data.id_cancha}, fecha {reserva_data.fecha_reserva}, horario {reserva_data.hora_inicio}-{reserva_data.hora_fin}")
        
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
        
        print(f"🔍 [BACKEND] Resultado verificación disponibilidad: {disponible}")
        
        if not disponible:
            raise HTTPException(
                status_code=400, 
                detail="La cancha no está disponible en el horario solicitado"
            )
            
    except Exception as e:
        print(f"❌ [BACKEND] Error en verificación de disponibilidad: {str(e)}")
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
    
    # Calcular costo total INICIAL (sin cupón)
    costo_total = calcular_costo_total(
        reserva_data.hora_inicio, reserva_data.hora_fin, float(cancha.precio_por_hora)
    )
    
    costo_inicial = costo_total  # Guardar para referencia
    
    # ✅ CORRECCIÓN IMPORTANTE: Generar código único de reserva CON VALIDACIÓN MEJORADA
    codigo_reserva = generar_codigo_unico_reserva(db)
    
    # ✅ VALIDACIÓN EXTRA: Asegurar que el código no sea None
    if not codigo_reserva:
        codigo_reserva = f"RES-{int(datetime.now().timestamp())}"
    
    print(f"✅ [BACKEND] Generado código reserva: {codigo_reserva}")
    print(f"💰 [BACKEND] Costo inicial calculado: ${costo_total}")
    
    # ✅ EXCLUIR CAMPO DE CUPÓN AL CREAR LA RESERVA INICIAL
    reserva_dict = reserva_data.dict()
    codigo_cupon = reserva_dict.pop('codigo_cupon', None)  # Extraer y remover código de cupón
    
    # Crear la reserva con costo inicial
    nueva_reserva = Reserva(
        **reserva_dict,
        costo_total=costo_total,
        codigo_reserva=codigo_reserva,
        estado="pendiente"
    )
    
    try:
        db.add(nueva_reserva)
        db.commit()
        db.refresh(nueva_reserva)
        
        # ✅ VERIFICACIÓN FINAL
        if not nueva_reserva.codigo_reserva:
            raise Exception("Error crítico: Reserva creada sin código")
            
        print(f"✅ [BACKEND] Reserva {nueva_reserva.id_reserva} creada exitosamente con código: {nueva_reserva.codigo_reserva}")
        
        # ✅ APLICAR CUPÓN SI SE PROPORCIONA - CORRECCIÓN PRINCIPAL
        cupon_aplicado = False
        descuento_aplicado = 0.0
        
        if codigo_cupon:
            try:
                print(f"🎫 [BACKEND] Intentando aplicar cupón: {codigo_cupon}")
                
                # Buscar el cupón
                cupon = db.query(Cupon).filter(Cupon.codigo == codigo_cupon).first()
                if not cupon:
                    print(f"❌ [BACKEND] Cupón no encontrado: {codigo_cupon}")
                    # No lanzar excepción, la reserva se crea sin cupón
                else:
                    print(f"✅ [BACKEND] Cupón encontrado: {cupon.codigo} - Tipo: {cupon.tipo} - Monto: {cupon.monto_descuento}")
                    
                    # Validaciones del cupón
                    if cupon.estado != "activo":
                        print(f"❌ [BACKEND] Cupón no está activo: {cupon.estado}")
                    elif cupon.fecha_expiracion and cupon.fecha_expiracion < date.today():
                        print(f"❌ [BACKEND] Cupón expirado: {cupon.fecha_expiracion}")
                    elif cupon.id_reserva:
                        print(f"❌ [BACKEND] Cupón ya utilizado en reserva: {cupon.id_reserva}")
                    elif cupon.id_usuario and cupon.id_usuario != reserva_data.id_usuario:
                        print(f"❌ [BACKEND] Cupón no válido para este usuario. Cupón usuario: {cupon.id_usuario}, Reserva usuario: {reserva_data.id_usuario}")
                    else:
                        # ✅ APLICAR DESCUENTO - LÓGICA CORREGIDA (CONVERSIÓN A FLOAT)
                        if cupon.tipo == "porcentaje":
                            # ✅ CORRECCIÓN CRÍTICA: Convertir decimal.Decimal a float
                            descuento = (costo_total * float(cupon.monto_descuento)) / 100
                            print(f"🎫 [BACKEND] Descuento porcentual: {cupon.monto_descuento}% = ${descuento}")
                        else:  # fijo
                            # ✅ CORRECCIÓN CRÍTICA: Convertir decimal.Decimal a float
                            descuento = float(cupon.monto_descuento)
                            print(f"🎫 [BACKEND] Descuento fijo: ${descuento}")
                        
                        # Asegurar que el descuento no sea mayor al costo total
                        if descuento > costo_total:
                            descuento = costo_total
                            print(f"⚠️ [BACKEND] Descuento ajustado a costo total: ${descuento}")
                        
                        nuevo_costo = costo_total - descuento
                        
                        # Actualizar reserva y cupón
                        nueva_reserva.costo_total = nuevo_costo
                        cupon.id_reserva = nueva_reserva.id_reserva
                        cupon.estado = "utilizado"
                        
                        db.commit()
                        db.refresh(nueva_reserva)
                        
                        cupon_aplicado = True
                        descuento_aplicado = float(descuento)
                        
                        print(f"✅ [BACKEND] Cupón aplicado exitosamente: ${descuento_aplicado} de descuento")
                        print(f"💰 [BACKEND] Costo actualizado: ${nuevo_costo} (antes: ${costo_inicial})")
                        
            except Exception as cupon_error:
                print(f"⚠️ [BACKEND] Error aplicando cupón: {str(cupon_error)}")
                import traceback
                traceback.print_exc()
                # No revertir la reserva por error en cupón, la reserva se mantiene con costo original
        
        # ✅ CONFIRMAR QUE LA RESERVA SE GUARDÓ CORRECTAMENTE
        reserva_verificada = db.query(Reserva).filter(Reserva.id_reserva == nueva_reserva.id_reserva).first()
        print(f"🔍 [BACKEND] Reserva verificada en BD: ID {reserva_verificada.id_reserva}, Estado: {reserva_verificada.estado}, Código: {reserva_verificada.codigo_reserva}, Costo Final: ${reserva_verificada.costo_total}")
        
        # Recargar con relaciones para la respuesta
        reserva_con_relaciones = db.query(Reserva).options(
            joinedload(Reserva.usuario),
            joinedload(Reserva.cancha).joinedload(Cancha.espacio_deportivo),
            joinedload(Reserva.disciplina)
        ).filter(Reserva.id_reserva == nueva_reserva.id_reserva).first()
        
        return reserva_con_relaciones
        
    except Exception as e:
        db.rollback()
        print(f"❌ [BACKEND] Error al crear reserva: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Error al crear reserva: {str(e)}"
        )

# ========== ENDPOINTS ESPECIALES PARA DISPONIBILIDAD ==========

@router.get("/cancha/{cancha_id}/horarios-disponibles")
def get_horarios_disponibles(
    cancha_id: int,
    fecha: date,
    db: Session = Depends(get_db)
):
    """Obtener horarios disponibles usando la función PostgreSQL - VERSIÓN CON DEBUGGING EXTENSIVO"""
    try:
        print(f"🔍 [BACKEND] SOLICITUD HORARIOS - Cancha: {cancha_id}, Fecha: {fecha}")
        
        # 1. Verificar que la cancha existe y está activa
        cancha = db.query(Cancha).filter(Cancha.id_cancha == cancha_id).first()
        if not cancha:
            print(f"❌ [BACKEND] Cancha {cancha_id} no encontrada")
            raise HTTPException(status_code=404, detail="Cancha no encontrada")
        
        print(f"✅ [BACKEND] Cancha encontrada: {cancha.nombre} (Activa: {cancha.estado})")
        print(f"✅ [BACKEND] Horario cancha: {cancha.hora_apertura} - {cancha.hora_cierre}")
        
        # 2. Verificar reservas existentes DIRECTAMENTE para debugging
        reservas_directas = db.execute(text("""
            SELECT id_reserva, hora_inicio, hora_fin, estado, codigo_reserva 
            FROM reserva 
            WHERE id_cancha = :cancha_id 
            AND fecha_reserva = :fecha
            AND estado IN ('pendiente', 'confirmada', 'en_curso')
            ORDER BY hora_inicio
        """), {"cancha_id": cancha_id, "fecha": fecha}).fetchall()
        
        print(f"📊 [BACKEND] Reservas directas en BD: {len(reservas_directas)}")
        for r in reservas_directas:
            print(f"   - Reserva {r[0]}: {r[1]} a {r[2]} (Estado: {r[3]}, Código: {r[4]})")
        
        # 3. Ejecutar función PostgreSQL para obtener horarios
        print(f"🔍 [BACKEND] Ejecutando función listar_horarios_disponibles({cancha_id}, '{fecha}')...")
        
        result = db.execute(
            text("SELECT * FROM listar_horarios_disponibles(:p_id_cancha, :p_fecha)"),
            {"p_id_cancha": cancha_id, "p_fecha": fecha}
        ).fetchall()
        
        print(f"✅ [BACKEND] Función retornó {len(result)} horarios")
        
        # 4. Procesar resultados
        horarios = []
        for i, row in enumerate(result):
            horario_data = {
                "hora_inicio": str(row[0]),
                "hora_fin": str(row[1]),
                "disponible": row[2],
                "precio_hora": float(row[3]) if row[3] else 0.0,
                "mensaje": row[4]
            }
            horarios.append(horario_data)
            print(f"📅 [BACKEND] Horario {i}: {horario_data}")
        
        # 5. Estadísticas para debugging
        horarios_ocupados = [h for h in horarios if not h['disponible']]
        print(f"📈 [BACKEND] Estadísticas - Total: {len(horarios)}, Ocupados: {len(horarios_ocupados)}, Disponibles: {len(horarios) - len(horarios_ocupados)}")
        
        return horarios
        
    except Exception as e:
        print(f"❌ [BACKEND] ERROR en get_horarios_disponibles: {str(e)}")
        import traceback
        traceback.print_exc()
        raise HTTPException(
            status_code=500, 
            detail=f"Error al obtener horarios disponibles: {str(e)}"
        )

@router.get("/verificar-disponibilidad")
def verificar_disponibilidad(
    cancha_id: int,
    fecha: str,  # String, no date
    hora_inicio: str,
    hora_fin: str,
    db: Session = Depends(get_db)
):
    """Verificar disponibilidad usando la función PostgreSQL - VERSIÓN SIMPLIFICADA Y CORREGIDA"""
    try:
        print(f"🔍 [BACKEND] Verificando disponibilidad: cancha={cancha_id}, fecha={fecha}, {hora_inicio}-{hora_fin}")
        
        # Asegurar formato correcto para PostgreSQL
        # PostgreSQL espera formato TIME 'HH:MM:SS' y DATE 'YYYY-MM-DD'
        
        result = db.execute(
            text("""
                SELECT verificar_disponibilidad(
                    :p_id_cancha::integer, 
                    :p_fecha::date, 
                    :p_hora_inicio::time, 
                    :p_hora_fin::time
                ) as disponible
            """),
            {
                "p_id_cancha": cancha_id,
                "p_fecha": fecha,
                "p_hora_inicio": hora_inicio,
                "p_hora_fin": hora_fin
            }
        ).scalar()
        
        print(f"✅ [BACKEND] Resultado disponibilidad: {result}")
        
        return {"disponible": result}
        
    except Exception as e:
        print(f"❌ [BACKEND] Error al verificar disponibilidad: {str(e)}")
        import traceback
        traceback.print_exc()
        raise HTTPException(
            status_code=500, 
            detail=f"Error al verificar disponibilidad: {str(e)}"
        )

# ========== ENDPOINTS ADICIONALES ==========

@router.get("/estado/{reserva_id}")
def get_estado_reserva(reserva_id: int, db: Session = Depends(get_db)):
    """Obtener el estado de una reserva específica"""
    reserva = db.query(Reserva).filter(Reserva.id_reserva == reserva_id).first()
    if not reserva:
        raise HTTPException(status_code=404, detail="Reserva no encontrada")
    
    return {
        "id_reserva": reserva.id_reserva,
        "codigo_reserva": reserva.codigo_reserva,
        "estado": reserva.estado,
        "fecha_reserva": reserva.fecha_reserva,
        "hora_inicio": reserva.hora_inicio,
        "hora_fin": reserva.hora_fin
    }

@router.get("/codigo/{codigo_reserva}", response_model=ReservaResponse)
def get_reserva_por_codigo(codigo_reserva: str, db: Session = Depends(get_db)):
    """Obtener una reserva por su código único con relaciones"""
    reserva = db.query(Reserva).options(
        joinedload(Reserva.usuario),
        joinedload(Reserva.cancha).joinedload(Cancha.espacio_deportivo),
        joinedload(Reserva.disciplina)
    ).filter(Reserva.codigo_reserva == codigo_reserva).first()
    
    if not reserva:
        raise HTTPException(status_code=404, detail="Reserva no encontrada")
    
    return reserva

@router.get("/gestor/mis-reservas", response_model=List[ReservaResponse])
def get_reservas_gestor(
    gestor_id: int,
    skip: int = 0,
    limit: int = 100,
    estado: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """Obtener reservas solo para los espacios deportivos del gestor"""
    print(f"👨‍💼 [BACKEND] Obteniendo reservas para gestor {gestor_id}")
    
    espacios_gestor = db.query(Administra).filter(
        Administra.id_usuario == gestor_id
    ).all()
    
    espacios_ids = [espacio.id_espacio_deportivo for espacio in espacios_gestor]
    
    if not espacios_ids:
        print(f"ℹ️ [BACKEND] Gestor {gestor_id} no tiene espacios asignados")
        return []
    
    print(f"🏟️ [BACKEND] Espacios del gestor: {espacios_ids}")
    
    # 2. Obtener las canchas que pertenecen a esos espacios
    canchas_espacios = db.query(Cancha).filter(
        Cancha.id_espacio_deportivo.in_(espacios_ids)
    ).all()
    
    canchas_ids = [cancha.id_cancha for cancha in canchas_espacios]
    
    if not canchas_ids:
        print(f"ℹ️ [BACKEND] No hay canchas en los espacios del gestor {gestor_id}")
        return []
    
    print(f"⚽ [BACKEND] Canchas del gestor: {canchas_ids}")
    
    # 3. Query para reservas de las canchas del gestor con relaciones
    query = db.query(Reserva).options(
        joinedload(Reserva.usuario),
        joinedload(Reserva.cancha).joinedload(Cancha.espacio_deportivo),
        joinedload(Reserva.disciplina)
    ).filter(Reserva.id_cancha.in_(canchas_ids))
    
    if estado:
        query = query.filter(Reserva.estado == estado)
    
    reservas = query.order_by(Reserva.fecha_reserva.desc()).offset(skip).limit(limit).all()
    
    print(f"✅ [BACKEND] Encontradas {len(reservas)} reservas para gestor {gestor_id}")
    
    return reservas

@router.get("/proximas/{dias}")
def get_reservas_proximas(dias: int = 7, db: Session = Depends(get_db)):
    """Obtener reservas próximas (en los próximos X días)"""
    fecha_actual = date.today()
    fecha_limite = fecha_actual + datetime.timedelta(days=dias)
    
    reservas = db.query(Reserva).options(
        joinedload(Reserva.usuario),
        joinedload(Reserva.cancha).joinedload(Cancha.espacio_deportivo),
        joinedload(Reserva.disciplina)
    ).filter(
        Reserva.fecha_reserva >= fecha_actual,
        Reserva.fecha_reserva <= fecha_limite,
        Reserva.estado.in_(["pendiente", "confirmada"])
    ).order_by(
        Reserva.fecha_reserva,
        Reserva.hora_inicio
    ).all()
    
    return reservas

@router.post("/{reserva_id}/confirmar")
def confirmar_reserva(reserva_id: int, db: Session = Depends(get_db)):
    """Confirmar una reserva pendiente"""
    reserva = db.query(Reserva).filter(Reserva.id_reserva == reserva_id).first()
    if not reserva:
        raise HTTPException(status_code=404, detail="Reserva no encontrada")
    
    if reserva.estado != "pendiente":
        raise HTTPException(status_code=400, detail="Solo se pueden confirmar reservas pendientes")
    
    reserva.estado = "confirmada"
    db.commit()
    
    return {"detail": "Reserva confirmada exitosamente"}