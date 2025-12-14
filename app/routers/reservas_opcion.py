# 📍 ARCHIVO: app/routers/reservas_opcion.py
# 🎯 PROPÓSITO: Endpoint completo de reservas con integración de cupones y PASARELA LIBÉLULA

from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import and_, or_
from datetime import datetime, date, time
from datetime import timedelta
from typing import List, Optional
from app.database import get_db
from app.models.reserva import Reserva
from app.models.cancha import Cancha
from app.models.usuario import Usuario
from app.models.disciplina import Disciplina
from app.models.cupon import Cupon
# NUEVAS IMPORTACIONES CLAVE para Pago Libélula
from app.models.pago import Pago 
from app.core.libelula_service import LibelulaService, get_libelula_service
from app.schemas.libelula import PaymentInitiation, PaymentInitiationResponse
from app.core.exceptions import PaymentGatewayError 
# Fin de NUEVAS IMPORTACIONES
from app.schemas.reserva import ReservaResponse, ReservaCreate, ReservaUpdate
from app.models.administra import Administra
from app.models.asistente import AsistenteReserva
from app.schemas.asistente import AsistenteCreate
from app.core.email_service import send_qr_email, send_email # Asegúrate de que send_email esté disponible
import random
import string
from sqlalchemy import text
import uuid
import secrets
from app.core.security import get_current_user
from app.core.security import get_password_hash
import traceback

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

@router.get("/", response_model=List[ReservaResponse])
def get_reservas(
    skip: int = 0,
    limit: int = 100,
    estado: Optional[str] = None,
    fecha_inicio: Optional[date] = None,
    fecha_fin: Optional[date] = None,
    id_usuario: Optional[int] = None,
    id_cancha: Optional[int] = None,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user)
):
    """Obtener lista de reservas con filtros opcionales y control de permisos"""
    
    if current_user.rol == "admin":
        # Admin ve todas las reservas
        query = db.query(Reserva)
        
    elif current_user.rol in ["gestor", "control_acceso"]:
        # Gestor/control_acceso ve solo reservas de sus espacios
        
        # 1. Obtener espacios donde el usuario está asignado
        espacios_gestor = db.query(Administra).filter(
            Administra.id_usuario == current_user.id_usuario
        ).all()
        
        espacios_ids = [espacio.id_espacio_deportivo for espacio in espacios_gestor]
        
        if not espacios_ids:
            return []
        
        # 2. Obtener canchas que pertenecen a esos espacios
        canchas_espacios = db.query(Cancha).filter(
            Cancha.id_espacio_deportivo.in_(espacios_ids)
        ).all()
        
        canchas_ids = [cancha.id_cancha for cancha in canchas_espacios]
        
        if not canchas_ids:
            return []
        
        # 3. Filtrar reservas por esas canchas
        query = db.query(Reserva).filter(Reserva.id_cancha.in_(canchas_ids))
        
    else:
        # Clientes no pueden ver todas las reservas
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="No tienes permisos para ver reservas"
        )
    
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
    
    reservas = query.options(
        joinedload(Reserva.usuario),
        joinedload(Reserva.cancha).joinedload(Cancha.espacio_deportivo),
        joinedload(Reserva.disciplina)
    ).offset(skip).limit(limit).all()
    
    reservas_sin_codigo = [r for r in reservas if not r.codigo_reserva]
    if reservas_sin_codigo:
        print(f"⚠️  ADVERTENCIA: {len(reservas_sin_codigo)} reservas sin código")
        for reserva in reservas_sin_codigo:
            reserva.codigo_reserva = f"TEMP-{reserva.id_reserva}"
    
    return reservas

@router.get("/{reserva_id}", response_model=ReservaResponse)
def get_reserva(
    reserva_id: int, 
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user)
):
    """Obtener una reserva específica por ID con relaciones y control de permisos"""
    
    reserva = db.query(Reserva).options(
        joinedload(Reserva.usuario),
        joinedload(Reserva.cancha).joinedload(Cancha.espacio_deportivo),
        joinedload(Reserva.disciplina)
    ).filter(Reserva.id_reserva == reserva_id).first()
    
    if not reserva:
        raise HTTPException(status_code=404, detail="Reserva no encontrada")
    
    if current_user.rol not in ["admin"] and current_user.rol in ["gestor", "control_acceso"]:
        # Si no es admin pero es gestor o control_acceso, verificar permisos
        
        try:
            # Obtener el espacio deportivo de la cancha de la reserva
            espacio_id = reserva.cancha.id_espacio_deportivo
            
            # Verificar si el usuario está asignado a ese espacio
            asignacion = db.query(Administra).filter(
                Administra.id_espacio_deportivo == espacio_id,
                Administra.id_usuario == current_user.id_usuario
            ).first()
            
            if not asignacion:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="No tienes permisos para ver esta reserva"
                )
                
        except AttributeError:
            # Si no se puede obtener el espacio_id
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="No tienes permisos para ver esta reserva"
            )
    
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

def generar_codigo_qr():
    """Genera un código único para el QR"""
    return f"QR-{uuid.uuid4().hex[:12].upper()}"

def generar_token_verificacion():
    """Genera un token seguro para verificación"""
    return secrets.token_urlsafe(32)

@router.post("/crear-con-asistentes", response_model=ReservaResponse)
def crear_reserva_con_asistentes(
    reserva_data: ReservaCreate,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
):
    """
    🎯 CREAR RESERVA CON ASISTENTES Y ENVIAR CÓDIGOS QR POR EMAIL
    💡 CARACTERÍSTICAS:
      - Crea la reserva normal
      - Registra cada asistente
      - Genera QR único para cada asistente
      - Envía email con QR a cada asistente
      - Valida que cantidad_asistentes coincida con lista
    """
    print(f"🎯 [BACKEND] Creando reserva con {len(reserva_data.asistentes)} asistentes")
    
    # ✅ VALIDACIÓN: Solo horas completas
    if reserva_data.hora_inicio.minute != 0 or reserva_data.hora_fin.minute != 0:
        raise HTTPException(
            status_code=400, 
            detail="Las reservas solo pueden hacerse en horas completas"
        )
    
    # ✅ VALIDACIÓN: Cantidad de asistentes debe coincidir
    if reserva_data.cantidad_asistentes != len(reserva_data.asistentes):
        raise HTTPException(
            status_code=400,
            detail=f"La cantidad de asistentes ({reserva_data.cantidad_asistentes}) no coincide con la lista proporcionada ({len(reserva_data.asistentes)})"
        )
    
    # ✅ VALIDACIÓN: No más asistentes que capacidad máxima (agregar si tienes ese dato)
    
    # Verificar que la cancha existe
    cancha = db.query(Cancha).filter(Cancha.id_cancha == reserva_data.id_cancha).first()
    if not cancha:
        raise HTTPException(status_code=404, detail="Cancha no encontrada")
    
    if cancha.estado != 'disponible':
        raise HTTPException(status_code=400, detail="La cancha no está disponible")
    
    cancha_nombre = cancha.nombre
    print(f"🏟️ [BACKEND] Cancha encontrada: {cancha.nombre} (ID: {cancha.id_cancha})")
    
    # Verificar usuario
    usuario = db.query(Usuario).filter(Usuario.id_usuario == reserva_data.id_usuario).first()
    if not usuario:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")
    
    # VERIFICAR DISPONIBILIDAD
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
    
    # Calcular costo total inicial
    costo_total = calcular_costo_total(
        reserva_data.hora_inicio, reserva_data.hora_fin, float(cancha.precio_por_hora)
    )
    
    # Generar código único de reserva
    codigo_reserva = generar_codigo_unico_reserva(db)
    
    if not codigo_reserva:
        codigo_reserva = f"RES-{int(datetime.now().timestamp())}"
    
    print(f"✅ [BACKEND] Código reserva: {codigo_reserva}")
    print(f"💰 [BACKEND] Costo inicial: ${costo_total}")
    
    # Extraer código cupón
    reserva_dict = reserva_data.dict()
    asistentes_data = reserva_dict.pop('asistentes', [])
    codigo_cupon = reserva_dict.pop('codigo_cupon', None)
    
    # Crear la reserva
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
        
        print(f"✅ [BACKEND] Reserva {nueva_reserva.id_reserva} creada")
        
        # ✅ APLICAR CUPÓN SI EXISTE
        cupon_aplicado = False
        if codigo_cupon:
            try:
                cupon = db.query(Cupon).filter(Cupon.codigo == codigo_cupon).first()
                if cupon and cupon.estado == "activo":
                    if cupon.tipo == "porcentaje":
                        descuento = (costo_total * float(cupon.monto_descuento)) / 100
                    else:
                        descuento = float(cupon.monto_descuento)
                    
                    if descuento > costo_total:
                        descuento = costo_total
                    
                    nuevo_costo = costo_total - descuento
                    nueva_reserva.costo_total = nuevo_costo
                    cupon.id_reserva = nueva_reserva.id_reserva
                    cupon.estado = "utilizado"
                    cupon_aplicado = True
                    
            except Exception as cupon_error:
                print(f"⚠️ [BACKEND] Error aplicando cupón: {str(cupon_error)}")
        
        # ✅ CREAR ASISTENTES Y GENERAR QR PARA CADA UNO
        asistentes_creados = []
        for asistente_data in asistentes_data:
            # Generar código QR único y token
            codigo_qr = generar_codigo_qr()
            token_verificacion = generar_token_verificacion()
            
            # Crear asistente
            asistente = AsistenteReserva(
                id_reserva=nueva_reserva.id_reserva,
                nombre=asistente_data["nombre"],
                email=asistente_data["email"],
                codigo_qr=codigo_qr,
                token_verificacion=token_verificacion,
                asistio=False
            )
            
            db.add(asistente)
            asistentes_creados.append(asistente)
            
            print(f"✅ [BACKEND] Asistente creado: {asistente.nombre} ({asistente.email})")
        
        db.commit()
        
        # ✅ ENVIAR EMAILS CON QR EN BACKGROUND
        for asistente in asistentes_creados:
            background_tasks.add_task(
                enviar_email_con_qr_asincrono,
                asistente=asistente,
                reserva=nueva_reserva,
                cancha_nombre=cancha_nombre,
                usuario=usuario
            )
        
        # Recargar con relaciones
        reserva_final = db.query(Reserva).options(
            joinedload(Reserva.usuario),
            joinedload(Reserva.cancha).joinedload(Cancha.espacio_deportivo),
            joinedload(Reserva.disciplina),
            joinedload(Reserva.asistentes)
        ).filter(Reserva.id_reserva == nueva_reserva.id_reserva).first()
        
        print(f"🎉 [BACKEND] Reserva con asistentes creada exitosamente: {nueva_reserva.id_reserva}")
        
        return reserva_final
        
    except Exception as e:
        db.rollback()
        print(f"❌ [BACKEND] Error al crear reserva con asistentes: {str(e)}")
        import traceback
        traceback.print_exc()
        raise HTTPException(
            status_code=500,
            detail=f"Error al crear reserva: {str(e)}"
        )

def enviar_email_con_qr_asincrono(asistente: AsistenteReserva, reserva: Reserva, cancha_nombre:str, usuario: Usuario):
    """
    Función asíncrona para enviar email con QR
    """
    try:
        # Importar aquí para evitar problemas de importación circular
        from app.core.email_service import send_qr_email_with_attachment  # O send_qr_email
        
        # Datos para el email
        datos_email = {
            "nombre_asistente": asistente.nombre,
            "email_asistente": asistente.email,
            "nombre_reservante": usuario.nombre,
            "nombre_cancha": cancha_nombre,
            "fecha_reserva": reserva.fecha_reserva.strftime("%d/%m/%Y"),
            "hora_inicio": reserva.hora_inicio.strftime("%H:%M"),
            "hora_fin": reserva.hora_fin.strftime("%H:%M"),
            "codigo_reserva": reserva.codigo_reserva,
            "codigo_qr": asistente.codigo_qr,
            "token_verificacion": asistente.token_verificacion
        }
        
        # Prueba con attachment primero (más confiable)
        enviado = send_qr_email_with_attachment(
            to_email=asistente.email,
            datos=datos_email
        )
        
        # Si falla, intenta con la versión normal
        if not enviado:
            print(f"⚠️ Attachment falló, intentando método normal...")
            from app.core.email_service import send_qr_email
            enviado = send_qr_email(asistente.email, datos_email)
        
        if enviado:
            print(f"✅ [EMAIL] QR enviado a {asistente.email}")
        else:
            print(f"❌ [EMAIL] Error al enviar QR a {asistente.email}")
            
    except Exception as e:
        print(f"❌ [EMAIL] Error en envío de email: {str(e)}")

@router.post(
    "/", 
    response_model=PaymentInitiationResponse, # Ahora retorna la URL de pago de Libélula
    status_code=status.HTTP_201_CREATED,
    summary="Crea una nueva reserva e inicia el flujo de pago con Libélula"
)
async def create_reserva(
    reserva_data: ReservaCreate,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user),
    libelula_service: LibelulaService = Depends(get_libelula_service) # Inyección del servicio de pagos
):
    """
    Crea la reserva, aplica cupones, crea el registro de pago y genera la URL de Libélula.
    """
    print(f"🎯 [BACKEND] Iniciando creación de reserva: {reserva_data.dict()}")
    
    # Asegurar que el ID de usuario del token se use para la reserva
    if current_user.id_usuario != reserva_data.id_usuario:
         reserva_data.id_usuario = current_user.id_usuario
    
    # ----------------------------------------------------
    # INICIO DE BLOQUE TRANSACCIONAL
    # ----------------------------------------------------
    try:
        # ✅ VALIDACIÓN: Horas completas
        if reserva_data.hora_inicio.minute != 0 or reserva_data.hora_fin.minute != 0:
            raise HTTPException(status_code=400, detail="Las reservas solo pueden hacerse en horas completas.")
        
        # Verificar cancha y disciplina
        cancha = db.query(Cancha).filter(Cancha.id_cancha == reserva_data.id_cancha).first()
        if not cancha or cancha.estado != 'disponible':
            raise HTTPException(status_code=404, detail="Cancha no disponible o no encontrada")
        
        disciplina = db.query(Disciplina).filter(Disciplina.id_disciplina == reserva_data.id_disciplina).first()
        if not disciplina:
            raise HTTPException(status_code=404, detail="Disciplina no encontrada")
        
        # VERIFICAR DISPONIBILIDAD USANDO FUNCIÓN POSTGRESQL (Tu lógica de DB)
        result = db.execute(
            text("SELECT verificar_disponibilidad(:cancha_id, :fecha, :hora_inicio, :hora_fin) as disponible"),
            {
                "cancha_id": reserva_data.id_cancha,
                "fecha": reserva_data.fecha_reserva,
                "hora_inicio": reserva_data.hora_inicio,
                "hora_fin": reserva_data.hora_fin
            }
        )
        if not result.scalar():
            raise HTTPException(status_code=400, detail="La cancha no está disponible en el horario solicitado")
        
        # Verificar rangos de horario y fecha pasada
        if reserva_data.hora_inicio < cancha.hora_apertura or reserva_data.hora_fin > cancha.hora_cierre:
            raise HTTPException(status_code=400, detail=f"El horario debe estar entre {cancha.hora_apertura} y {cancha.hora_cierre}")
        if reserva_data.fecha_reserva < date.today():
            raise HTTPException(status_code=400, detail="No se pueden hacer reservas en fechas pasadas")
        
        # Calcular costo total INICIAL
        costo_total = calcular_costo_total(
            reserva_data.hora_inicio, reserva_data.hora_fin, float(cancha.precio_por_hora)
        )
        
        # Generar código único de reserva
        codigo_reserva = generar_codigo_unico_reserva(db)
        
        # ✅ CREAR LA RESERVA INICIAL EN ESTADO 'pendiente'
        reserva_dict = reserva_data.dict()
        codigo_cupon = reserva_dict.pop('codigo_cupon', None)
        
        nueva_reserva = Reserva(
            **reserva_dict,
            costo_total=costo_total,
            codigo_reserva=codigo_reserva,
            estado="pendiente" # Estado inicial a la espera de pago
        )
        db.add(nueva_reserva)
        db.flush() # Obtener id_reserva antes de commitear
        
        # ✅ APLICAR CUPÓN SI SE PROPORCIONA
        if codigo_cupon:
            try:
                cupon = db.query(Cupon).filter(Cupon.codigo == codigo_cupon).first()
                if cupon and cupon.estado == "activo" and \
                   (not cupon.fecha_expiracion or cupon.fecha_expiracion >= date.today()) and \
                   (not cupon.id_reserva) and \
                   (not cupon.id_usuario or cupon.id_usuario == reserva_data.id_usuario):
                    
                    descuento = 0.0
                    monto_descuento_float = float(cupon.monto_descuento)
                    
                    if cupon.tipo == "porcentaje":
                        descuento = (costo_total * monto_descuento_float) / 100
                    else:
                        descuento = monto_descuento_float
                    
                    if descuento > costo_total:
                        descuento = costo_total
                    
                    nuevo_costo = costo_total - descuento
                    
                    # Actualizar reserva y cupón
                    nueva_reserva.costo_total = nuevo_costo
                    cupon.id_reserva = nueva_reserva.id_reserva
                    cupon.estado = "utilizado"
                    
                    costo_total = nuevo_costo # Actualizar el costo total para el pago
                else:
                    print(f"❌ [BACKEND] Cupón no válido o ya utilizado: {codigo_cupon}. Se continúa con el costo inicial.")
            except Exception as cupon_error:
                print(f"⚠️ [BACKEND] Error aplicando cupón: {str(cupon_error)}")
                traceback.print_exc()
        
        # ✅ CREAR REGISTRO DE PAGO EN ESTADO PENDIENTE
        db_pago = Pago(
            monto=costo_total, # Monto final después del cupón
            metodo_pago="Libelula",
            estado="pendiente", 
            id_reserva=nueva_reserva.id_reserva 
        )
        db.add(db_pago)
        db.flush() 

        # --- INICIAR TRANSACCIÓN CON LIBÉLULA ---
        if costo_total > 0:
            initiation_data = PaymentInitiation(
                reserva_id=nueva_reserva.id_reserva, 
                amount=costo_total,
                currency="GTQ" 
            )
            
            libelula_response = libelula_service.create_transaction(initiation_data)
            
            # Guardamos el ID de transacción generado por Libélula
            db_pago.id_transaccion = libelula_response.transaction_id
            print(f"✅ [BACKEND] Transacción Libélula iniciada. ID: {libelula_response.transaction_id}")
        else:
            # Si el costo es 0 (ej. 100% de descuento con cupón), se marca como pagado localmente
            libelula_response = PaymentInitiationResponse(
                transaction_id="CUPON_0",
                payment_url="/payment/success", # Redirección directa al frontend
                status="COMPLETED"
            )
            db_pago.id_transaccion = libelula_response.transaction_id
            db_pago.estado = "pagado" # O "COMPLETED"
            nueva_reserva.estado = "confirmada" 
            print("✅ [BACKEND] Costo cero. Pago completado automáticamente.")

        # ✅ COMMIT FINAL (Si todo lo anterior fue exitoso)
        db.commit()
        db.refresh(nueva_reserva)
        db.refresh(db_pago)
        
        # Retornamos la respuesta de Libélula (contiene payment_url)
        return libelula_response
        
    except PaymentGatewayError as e:
        # Si falla Libélula, revertimos la Reserva y el Pago local
        db.rollback()
        print(f"❌ [BACKEND] Rollback por error de pasarela: {e}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Error al iniciar el pago con Libélula: {e}"
        )
    except Exception as e:
        # Revertir por cualquier otro error inesperado
        db.rollback()
        print(f"❌ [BACKEND] Rollback por error interno: {e}")
        traceback.print_exc()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error interno al crear reserva: {e}"
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
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user) 
):
    """Obtener reservas solo para los espacios deportivos del gestor"""
    
    if current_user.id_usuario != gestor_id and current_user.rol != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Solo puedes ver tus propias reservas de gestor"
        )
    
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
    
    for reserva in reservas:
        if not reserva.codigo_reserva:
            reserva.codigo_reserva = f"TEMP-{reserva.id_reserva}"
    
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

@router.get("/codigo/{codigo_reserva}", response_model=ReservaResponse)
def obtener_reserva_por_codigo(codigo_reserva: str, db: Session = Depends(get_db)):
    """Obtener reserva por código de reserva"""
    print(f"[BACKEND] Buscando reserva con código: {codigo_reserva}")
    
    reserva = db.query(Reserva).filter(Reserva.codigo_reserva == codigo_reserva).first()
    if not reserva:
        raise HTTPException(status_code=404, detail="Reserva no encontrada")
    
    return reserva

def enviar_email_completo_reserva(usuario: Usuario, reserva: Reserva, cancha_nombre: str, cantidad_invitados: int):
    """
    Enviar email completo con código y QR
    """
    try:
        from app.core.email_service import send_reservation_complete_email
        
        datos_email = {
            "nombre_usuario": usuario.nombre,
            "email_usuario": usuario.email,
            "nombre_cancha": cancha_nombre,
            "fecha_reserva": reserva.fecha_reserva.strftime("%d/%m/%Y"),
            "hora_inicio": reserva.hora_inicio.strftime("%H:%M"),
            "hora_fin": reserva.hora_fin.strftime("%H:%M"),
            "codigo_reserva": reserva.codigo_reserva,
            "cantidad_invitados": cantidad_invitados,
            "costo_total": float(reserva.costo_total)
        }
        
        enviado = send_reservation_complete_email(usuario.email, datos_email)
        
        if enviado:
            print(f"[EMAIL] Email completo enviado a {usuario.email}")
        else:
            print(f"[EMAIL] Error al enviar email completo a {usuario.email}")
            
    except Exception as e:
        print(f"[EMAIL] Error en envío de email completo: {str(e)}")


@router.post("/crear-con-codigo-unico", response_model=ReservaResponse)
def crear_reserva_con_codigo_unico(
    reserva_data: ReservaCreate,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
):
    """
    CREAR RESERVA CON CÓDIGO ÚNICO - Con QR para usuario principal
    """
    print(f"[BACKEND] Creando reserva con código único - Asistentes: {reserva_data.cantidad_asistentes}")
    
    # ✅ VALIDACIÓN: Solo horas completas
    if reserva_data.hora_inicio.minute != 0 or reserva_data.hora_fin.minute != 0:
        raise HTTPException(
            status_code=400, 
            detail="Las reservas solo pueden hacerse en horas completas"
        )
    
    # Verificar que la cancha existe
    cancha = db.query(Cancha).filter(Cancha.id_cancha == reserva_data.id_cancha).first()
    if not cancha:
        raise HTTPException(status_code=404, detail="Cancha no encontrada")
    
    if cancha.estado != 'disponible':
        raise HTTPException(status_code=400, detail="La cancha no está disponible")
    
    cancha_nombre = cancha.nombre
    print(f"[BACKEND] Cancha: {cancha.nombre}")
    
    # Verificar usuario
    usuario = db.query(Usuario).filter(Usuario.id_usuario == reserva_data.id_usuario).first()
    if not usuario:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")
    
    # VERIFICAR DISPONIBILIDAD
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
    
    # Calcular costo total
    costo_total = calcular_costo_total(
        reserva_data.hora_inicio, reserva_data.hora_fin, float(cancha.precio_por_hora)
    )
    
    # Generar código único de reserva
    codigo_reserva = generar_codigo_unico_reserva(db)
    
    if not codigo_reserva:
        codigo_reserva = f"RES-{int(datetime.now().timestamp())}"
    
    print(f"[BACKEND] Código reserva: {codigo_reserva}")
    
    # Extraer código cupón
    reserva_dict = reserva_data.dict(exclude={'asistentes'})  # Excluir asistentes
    codigo_cupon = reserva_dict.pop('codigo_cupon', None)
    
    # Crear la reserva
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
        
        print(f"[BACKEND] Reserva {nueva_reserva.id_reserva} creada")
        
        # ✅ APLICAR CUPÓN SI EXISTE
        if codigo_cupon:
            try:
                cupon = db.query(Cupon).filter(Cupon.codigo == codigo_cupon).first()
                if cupon and cupon.estado == "activo":
                    if cupon.tipo == "porcentaje":
                        descuento = (costo_total * float(cupon.monto_descuento)) / 100
                    else:
                        descuento = float(cupon.monto_descuento)
                    
                    if descuento > costo_total:
                        descuento = costo_total
                    
                    nuevo_costo = costo_total - descuento
                    nueva_reserva.costo_total = nuevo_costo
                    cupon.id_reserva = nueva_reserva.id_reserva
                    cupon.estado = "utilizado"
                    
                    db.commit()
                    db.refresh(nueva_reserva)
                    
                    print(f"[BACKEND] Cupón aplicado: ${descuento} de descuento")
                    
            except Exception as cupon_error:
                print(f"[BACKEND] Error aplicando cupón: {str(cupon_error)}")
        
        # ✅ CREAR ASISTENTE PARA EL USUARIO PRINCIPAL (con su propio QR)
        from app.core.email_service import generar_codigo_qr, generar_token_verificacion
        
        # Generar QR único para el usuario principal
        codigo_qr_principal = generar_codigo_qr()
        token_principal = generar_token_verificacion()
        
        # Crear registro de asistente para el usuario principal
        asistente_principal = AsistenteReserva(
            id_reserva=nueva_reserva.id_reserva,
            nombre=usuario.nombre,
            email=usuario.email,
            codigo_qr=codigo_qr_principal,
            token_verificacion=token_principal,
            asistio=False,
            id_usuario=usuario.id_usuario
        )
        
        db.add(asistente_principal)
        db.commit()
        db.refresh(asistente_principal)
        
        print(f"[BACKEND] Asistente principal creado con QR: {codigo_qr_principal}")
        
        # ✅ ENVIAR EMAIL CON QR AL USUARIO PRINCIPAL
        background_tasks.add_task(
            enviar_email_con_qr_asincrono,
            asistente=asistente_principal,
            reserva=nueva_reserva,
            cancha_nombre=cancha_nombre,
            usuario=usuario
        )
        
        # ✅ ENVIAR EMAIL ADICIONAL CON CÓDIGO PARA INVITADOS
        cantidad_invitados = reserva_data.cantidad_asistentes - 1
        if cantidad_invitados > 0:
            background_tasks.add_task(
                enviar_email_codigo_invitados,
                usuario=usuario,
                reserva=nueva_reserva,
                cancha_nombre=cancha_nombre,
                cantidad_invitados=cantidad_invitados
            )
        
        # ✅ ASIGNAR CUPÓN DE 5% SI TIENE MENOS DE 5 RESERVAS
        reservas_usuario = db.query(Reserva).filter(
            Reserva.id_usuario == usuario.id_usuario,
            Reserva.estado != "cancelada"
        ).count()
        
        if reservas_usuario < 5:
            cupon_5 = generar_cupon_5_porciento(usuario.id_usuario, db)
            if cupon_5:
                print(f"[BACKEND] Cupón 5% asignado al usuario: {cupon_5.codigo}")
        
        # Recargar con relaciones
        reserva_final = db.query(Reserva).options(
            joinedload(Reserva.usuario),
            joinedload(Reserva.cancha).joinedload(Cancha.espacio_deportivo),
            joinedload(Reserva.disciplina)
        ).filter(Reserva.id_reserva == nueva_reserva.id_reserva).first()
        
        print(f"[BACKEND] Reserva con código único creada exitosamente")
        
        return reserva_final
        
    except Exception as e:
        db.rollback()
        print(f"[BACKEND] Error al crear reserva: {str(e)}")
        import traceback
        traceback.print_exc()
        raise HTTPException(
            status_code=500,
            detail=f"Error al crear reserva: {str(e)}"
        )
    
def enviar_email_codigo_invitados(usuario: Usuario, reserva: Reserva, cancha_nombre: str, cantidad_invitados: int):
    """
    Envía email con código para compartir con invitados
    """
    try:
        from app.core.email_service import send_email
        
        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="UTF-8">
            <style>
                body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; max-width: 600px; margin: 0 auto; padding: 20px; }}
                .header {{ background: linear-gradient(135deg, #0f9fe1 0%, #9eca3f 100%); color: white; padding: 25px; text-align: center; border-radius: 10px 10px 0 0; }}
                .content {{ background: #f9f9f9; padding: 30px; border-radius: 0 0 10px 10px; }}
                .code-section {{ background: white; padding: 20px; border: 3px solid #0f9fe1; border-radius: 8px; text-align: center; margin: 20px 0; }}
                .code {{ font-family: monospace; font-size: 28px; letter-spacing: 3px; color: #1a237e; font-weight: bold; background: #f0f7ff; padding: 15px; border-radius: 5px; }}
            </style>
        </head>
        <body>
            <div class="header">
                <h1>👥 Código para Invitados</h1>
                <p>Comparte con {cantidad_invitados} personas</p>
            </div>
            <div class="content">
                <p>Hola <strong>{usuario.nombre}</strong>,</p>
                <p>Tu reserva en <strong>{cancha_nombre}</strong> está lista.</p>
                
                <div style="background: #f0f7ff; padding: 15px; border-radius: 8px; margin: 15px 0; border-left: 4px solid #0f9fe1;">
                    <p><strong>📍 Cancha:</strong> {cancha_nombre}</p>
                    <p><strong>📅 Fecha:</strong> {reserva.fecha_reserva.strftime("%d/%m/%Y")}</p>
                    <p><strong>⏰ Horario:</strong> {reserva.hora_inicio.strftime("%H:%M")} - {reserva.hora_fin.strftime("%H:%M")}</p>
                    <p><strong>👥 Cupos para invitados:</strong> {cantidad_invitados} personas</p>
                </div>
                
                <div class="code-section">
                    <h3>🔑 Código para Invitar</h3>
                    <div class="code">{reserva.codigo_reserva}</div>
                    <p>Comparte este código exacto con tus {cantidad_invitados} invitados</p>
                </div>
                
                <div style="background: #e8f5e9; padding: 15px; border-radius: 8px; margin: 20px 0; border-left: 4px solid #4caf50;">
                    <h4>📝 Instrucciones para Invitados:</h4>
                    <ol style="margin: 10px 0; padding-left: 20px;">
                        <li><strong>Comparte el código</strong> con cada invitado</li>
                        <li><strong>Cada persona usa el código UNA VEZ</strong> para unirse</li>
                        <li><strong>Ellos irán a la página principal</strong> → "Unirse con código"</li>
                        <li><strong>Cada uno ingresará su nombre y email</strong></li>
                        <li><strong>Recibirán su propio QR</strong> por email</li>
                    </ol>
                </div>
                
                <div style="background: #fff3e0; padding: 15px; border-radius: 8px; margin: 20px 0; border-left: 4px solid #ff9800;">
                    <h4>✅ Ya recibiste:</h4>
                    <ul style="margin: 10px 0; padding-left: 20px;">
                        <li>📱 <strong>Tu QR personal</strong> (en email separado)</li>
                        <li>🔑 <strong>Este código para compartir</strong></li>
                        <li>📊 <strong>Acceso al dashboard</strong> para gestionar</li>
                    </ul>
                </div>
                
                <p style="text-align: center; margin-top: 30px; font-size: 16px;">
                    <strong>¡Disfruta del partido! 🏆</strong>
                </p>
                
                <div style="margin-top: 30px; padding-top: 20px; border-top: 1px solid #ddd; font-size: 12px; color: #666; text-align: center;">
                    <p>Código válido hasta: {reserva.fecha_reserva.strftime("%d/%m/%Y")}</p>
                    <p>Este es un mensaje automático, por favor no respondas.</p>
                    <p>© {datetime.now().year} OlympiaHub - Sistema de Gestión Deportiva</p>
                </div>
            </div>
        </body>
        </html>
        """
        
        text_content = f"""
        CÓDIGO PARA INVITADOS
        
        Hola {usuario.nombre},
        
        Tu reserva en {cancha_nombre} está lista.
        
        📅 Fecha: {reserva.fecha_reserva.strftime("%d/%m/%Y")}
        ⏰ Horario: {reserva.hora_inicio.strftime("%H:%M")} - {reserva.hora_fin.strftime("%H:%M")}
        👥 Cupos para invitados: {cantidad_invitados} personas
        
        🔑 CÓDIGO PARA INVITAR:
        {reserva.codigo_reserva}
        
        Instrucciones para Invitados:
        1. Comparte el código con cada invitado
        2. Cada persona usa el código UNA VEZ para unirse
        3. Ellos irán a la página principal → "Unirse con código"
        4. Cada uno ingresará su nombre y email
        5. Recibirán su propio QR por email
        
        ✅ Ya recibiste:
        • Tu QR personal (en email separado)
        • Este código para compartir
        • Acceso al dashboard para gestionar
        
        ¡Disfruta del partido!
        
        ---
        Código válido hasta: {reserva.fecha_reserva.strftime("%d/%m/%Y")}
        © {datetime.now().year} OlympiaHub
        """
        
        return send_email(
            to_email=usuario.email,
            subject=f"🔑 Código para Invitados | {reserva.codigo_reserva} | {cancha_nombre}",
            message=text_content,
            html_content=html_content
        )
        
    except Exception as e:
        print(f"[EMAIL] Error enviando email código invitados: {str(e)}")
        return False
    
def generar_qr_y_enviar_email_usuario_principal(usuario: Usuario, reserva: Reserva, cancha_nombre: str, cantidad_invitados: int):
    """
    Genera QR para el usuario principal y envía email completo
    """
    try:
        from app.core.email_service import generar_codigo_qr, generar_token_verificacion, send_qr_email
        
        # Generar QR único para el usuario principal
        codigo_qr = generar_codigo_qr()
        token_verificacion = generar_token_verificacion()
        
        # Crear datos para el email
        datos_email = {
            "nombre_asistente": usuario.nombre,
            "email_asistente": usuario.email,
            "nombre_reservante": usuario.nombre,
            "nombre_cancha": cancha_nombre,
            "fecha_reserva": reserva.fecha_reserva.strftime("%d/%m/%Y"),
            "hora_inicio": reserva.hora_inicio.strftime("%H:%M"),
            "hora_fin": reserva.hora_fin.strftime("%H:%M"),
            "codigo_reserva": reserva.codigo_reserva,
            "codigo_qr": codigo_qr,
            "token_verificacion": token_verificacion,
            "cantidad_invitados": cantidad_invitados,
            "costo_total": float(reserva.costo_total)
        }
        
        # Enviar email con QR
        enviado = send_qr_email(usuario.email, datos_email)
        
        if enviado:
            print(f"[EMAIL] QR principal enviado a {usuario.email}")
        else:
            print(f"[EMAIL] Error al enviar QR principal a {usuario.email}")
            
        return enviado, codigo_qr, token_verificacion
        
    except Exception as e:
        print(f"[EMAIL] Error generando QR principal: {str(e)}")
        return False, None, None

def generar_cupon_5_porciento(id_usuario: int, db: Session) -> Optional[Cupon]:
    """Generar cupón de 5% para usuarios con menos de 5 reservas"""
    try:
        # Generar código único
        letras = string.ascii_uppercase
        numeros = string.digits
        codigo = ''.join(random.choices(letras, k=3)) + ''.join(random.choices(numeros, k=3))
        
        cupon = Cupon(
            codigo=f"CUP5-{codigo}",
            monto_descuento=5.0,
            tipo="porcentaje",
            estado="activo",
            id_usuario=id_usuario,
            fecha_expiracion=date.today() + timedelta(days=30)
        )
        
        db.add(cupon)
        db.commit()
        db.refresh(cupon)
        
        return cupon
    except Exception as e:
        print(f"Error generando cupón 5%: {str(e)}")
        return None

@router.post("/unirse-con-codigo/{codigo_reserva}")
def unirse_con_codigo_reserva(
    codigo_reserva: str,
    invitado_data: dict,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user),  # ✅ Usuario autenticado
):
    """
    UN INVITADO SE UNE A UNA RESERVA USANDO EL CÓDIGO DE RESERVA
    """
    print(f"[BACKEND] Uniendo invitado con código: {codigo_reserva}")
    
    # Buscar la reserva por código_reserva
    reserva = db.query(Reserva).filter(Reserva.codigo_reserva == codigo_reserva).first()
    
    if not reserva:
        raise HTTPException(status_code=404, detail="Código de reserva no encontrado")
    
    # Verificar si aún hay cupo para invitados
    asistentes_actuales = db.query(AsistenteReserva).filter(
        AsistenteReserva.id_reserva == reserva.id_reserva
    ).count()
    
    total_actual = 1 + asistentes_actuales  # 1 es el que hizo la reserva
    
    if total_actual >= reserva.cantidad_asistentes:
        raise HTTPException(status_code=400, detail="No hay cupo disponible en esta reserva")
    
    # ✅ Usar datos del usuario logueado si no se proporcionan
    nombre = invitado_data.get("nombre") or current_user.nombre
    email = invitado_data.get("email") or current_user.email
    
    # Verificar si el email ya está registrado en esta reserva
    asistente_existente = db.query(AsistenteReserva).filter(
        AsistenteReserva.id_reserva == reserva.id_reserva,
        AsistenteReserva.email == email
    ).first()
    
    if asistente_existente:
        raise HTTPException(status_code=400, detail="Ya estás registrado en esta reserva")
    
    # Crear asistente
    codigo_qr = generar_codigo_qr()
    token_verificacion = generar_token_verificacion()
    
    asistente = AsistenteReserva(
        id_reserva=reserva.id_reserva,
        nombre=nombre,
        email=email,
        codigo_qr=codigo_qr,
        token_verificacion=token_verificacion,
        asistio=False,
    )
    
    try:
        db.add(asistente)
        db.commit()
        
        # Enviar email con QR al invitado
        background_tasks.add_task(
            enviar_email_con_qr_asincrono,
            asistente=asistente,
            reserva=reserva,
            cancha_nombre=reserva.cancha.nombre,
            usuario=reserva.usuario
        )
        
        # ✅ ASIGNAR CUPÓN DE 5% AL INVITADO SI ES SU PRIMERA RESERVA
        reservas_invitado = db.query(Reserva).filter(
            Reserva.id_usuario == current_user.id_usuario,
            Reserva.estado != "cancelada"
        ).count()
        
        if reservas_invitado < 5:
            cupon_5 = generar_cupon_5_porciento(current_user.id_usuario, db)
            if cupon_5:
                print(f"[BACKEND] Cupón 5% asignado al invitado: {current_user.email}")
        
        return {
            "message": "Te has unido exitosamente a la reserva",
            "email_enviado": True,
            "codigo_qr": codigo_qr,
            "cupos_restantes": reserva.cantidad_asistentes - (total_actual + 1),
            "reserva_id": reserva.id_reserva
        }
        
    except Exception as e:
        db.rollback()
        print(f"[BACKEND] Error uniendo invitado: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error al unirse a la reserva: {str(e)}")
    
@router.post("/registrar-y-unirse/{codigo_reserva}")
def registrar_y_unirse_reserva(
    codigo_reserva: str,
    usuario_data: dict,  # Datos del nuevo usuario
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
):
    """
    Registrar un nuevo usuario y unirlo automáticamente a una reserva
    """
    print(f"[BACKEND] Registrando y uniendo usuario con código: {codigo_reserva}")
    print(f"[BACKEND] Datos recibidos: {usuario_data}")
    
    # 1. Verificar que el código de reserva existe
    reserva = db.query(Reserva).filter(Reserva.codigo_reserva == codigo_reserva).first()
    if not reserva:
        raise HTTPException(status_code=404, detail="Código de reserva no encontrado")
    
    # 2. Verificar si hay cupo disponible
    asistentes_actuales = db.query(AsistenteReserva).filter(
        AsistenteReserva.id_reserva == reserva.id_reserva
    ).count()
    
    total_actual = 1 + asistentes_actuales  # 1 es el que hizo la reserva
    
    if total_actual >= reserva.cantidad_asistentes:
        raise HTTPException(status_code=400, detail="No hay cupo disponible en esta reserva")
    
    # 3. Verificar si el email ya está registrado
    usuario_existente = db.query(Usuario).filter(Usuario.email == usuario_data["email"]).first()
    if usuario_existente:
        raise HTTPException(status_code=400, detail="Este email ya está registrado")
    
    # 4. Verificar si el email ya está en la reserva
    asistente_existente = db.query(AsistenteReserva).filter(
        AsistenteReserva.id_reserva == reserva.id_reserva,
        AsistenteReserva.email == usuario_data["email"]
    ).first()
    
    if asistente_existente:
        raise HTTPException(status_code=400, detail="Ya estás registrado en esta reserva")
    
    try:
        # ✅ CORRECCIÓN: Hashear la contraseña
        
        hashed_password = get_password_hash(usuario_data.get("contrasenia", ""))
        
        # 5. Crear el usuario (activado automáticamente)
        nuevo_usuario = Usuario(
            nombre=usuario_data["nombre"],
            apellido=usuario_data.get("apellido", ""),
            email=usuario_data["email"],
            contrasenia=hashed_password,  # ✅ CONTRASEÑA HASHEADA
            telefono=usuario_data.get("telefono"),
            estado="activo",  # Activado automáticamente por tener código
            rol="cliente"
        )
        
        db.add(nuevo_usuario)
        db.commit()
        db.refresh(nuevo_usuario)
        
        print(f"[BACKEND] Usuario {nuevo_usuario.id_usuario} creado y activado")
        print(f"[BACKEND] Estado del usuario: {nuevo_usuario.estado}")
        
        # 6. Unir al usuario a la reserva
        codigo_qr = generar_codigo_qr()
        token_verificacion = generar_token_verificacion()
        
        asistente = AsistenteReserva(
            id_reserva=reserva.id_reserva,
            nombre=usuario_data["nombre"],
            email=usuario_data["email"],
            codigo_qr=codigo_qr,
            token_verificacion=token_verificacion,
            asistio=False
        )
        
        db.add(asistente)
        db.commit()
        
        print(f"[BACKEND] Usuario unido a reserva como asistente. QR: {codigo_qr}")
        
        # 7. Enviar emails
        # Email de bienvenida
        background_tasks.add_task(
            enviar_email_bienvenida_con_reserva,
            usuario=nuevo_usuario,
            reserva=reserva,
            cancha_nombre=reserva.cancha.nombre if reserva.cancha else "Cancha"
        )
        
        # Email con QR
        background_tasks.add_task(
            enviar_email_con_qr_asincrono,
            asistente=asistente,
            reserva=reserva,
            cancha_nombre=reserva.cancha.nombre if reserva.cancha else "Cancha",
            usuario=reserva.usuario
        )
        
        # 8. Asignar cupón de 5%
        cupon_5 = generar_cupon_5_porciento(nuevo_usuario.id_usuario, db)
        if cupon_5:
            print(f"[BACKEND] Cupón 5% asignado al nuevo usuario: {cupon_5.codigo}")
        
        return {
            "message": "Usuario registrado y unido exitosamente a la reserva",
            "usuario_id": nuevo_usuario.id_usuario,
            "reserva_id": reserva.id_reserva,
            "email_enviado": True,
            "codigo_qr": codigo_qr,
            "cupos_restantes": reserva.cantidad_asistentes - (total_actual + 1),
            "unido_a_reserva": True,  # ✅ IMPORTANTE: Indicar que sí se unió
            "estado": "activo"  # ✅ Confirmar estado activo
        }
        
    except Exception as e:
        db.rollback()
        print(f"[BACKEND] Error registrando y uniendo usuario: {str(e)}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Error al registrar y unir: {str(e)}")

def enviar_email_bienvenida_con_reserva(usuario: Usuario, reserva: Reserva, cancha_nombre: str):
    """Enviar email de bienvenida con información de la reserva"""
    try:
        from app.core.email_service import send_email
        
        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="UTF-8">
            <style>
                body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; max-width: 600px; margin: 0 auto; padding: 20px; }}
                .header {{ background: linear-gradient(135deg, #0f9fe1 0%, #9eca3f 100%); color: white; padding: 25px; text-align: center; border-radius: 10px 10px 0 0; }}
                .content {{ background: #f9f9f9; padding: 30px; border-radius: 0 0 10px 10px; }}
                .badge {{ display: inline-block; background: #4caf50; color: white; padding: 5px 15px; border-radius: 20px; font-size: 14px; }}
                .reserva-card {{ background: #e8f5e9; padding: 15px; border-radius: 8px; margin: 15px 0; border-left: 5px solid #4caf50; }}
            </style>
        </head>
        <body>
            <div class="header">
                <h1>🎉 ¡Bienvenido a OlympiaHub!</h1>
                <p>Tu cuenta ha sido activada automáticamente</p>
            </div>
            <div class="content">
                <p>Hola <strong>{usuario.nombre} {usuario.apellido}</strong>,</p>
                
                <p>Tu registro en <strong>OlympiaHub</strong> fue exitoso y tu cuenta ha sido <span class="badge">ACTIVADA AUTOMÁTICAMENTE</span> porque te uniste a una reserva.</p>
                
                <div class="reserva-card">
                    <h3 style="color: #2e7d32; margin-top: 0;">📋 Información de tu Reserva</h3>
                    <p><strong>Cancha:</strong> {cancha_nombre}</p>
                    <p><strong>Fecha:</strong> {reserva.fecha_reserva.strftime("%d/%m/%Y")}</p>
                    <p><strong>Horario:</strong> {reserva.hora_inicio.strftime("%H:%M")} - {reserva.hora_fin.strftime("%H:%M")}</p>
                    <p><strong>Código de Reserva:</strong> {reserva.codigo_reserva}</p>
                </div>
                
                <p><strong>📧 Revisa tu bandeja de entrada:</strong></p>
                <ul>
                    <li>Recibirás un email separado con tu <strong>código QR personal</strong></li>
                    <li>Presenta ese QR al personal de control de acceso</li>
                    <li>El QR es válido solo para esta reserva</li>
                </ul>
                
                <p><strong>🚀 Acceso Inmediato:</strong></p>
                <ul>
                    <li>Puedes iniciar sesión ahora mismo</li>
                    <li>Tienes acceso completo al sistema</li>
                    <li>Puedes ver todas tus reservas en el dashboard</li>
                </ul>
                
                <p style="text-align: center; margin-top: 30px;">
                    <a href="https://olympiahub.app/login" style="display: inline-block; padding: 12px 30px; background: #0f9fe1; color: white; text-decoration: none; border-radius: 5px; font-weight: bold; font-size: 16px;">
                        🔑 INICIAR SESIÓN AHORA
                    </a>
                </p>
                
                <div style="margin-top: 30px; padding-top: 20px; border-top: 1px solid #ddd; font-size: 12px; color: #666; text-align: center;">
                    <p>Este es un mensaje automático, por favor no respondas.</p>
                    <p>© {datetime.now().year} OlympiaHub - Sistema de Gestión Deportiva</p>
                </div>
            </div>
        </body>
        </html>
        """
        
        text_content = f"""
        ¡BIENVENIDO A OLYMPIAHUB!
        
        Hola {usuario.nombre} {usuario.apellido},
        
        Tu registro fue exitoso y tu cuenta ha sido ACTIVADA AUTOMÁTICAMENTE porque te uniste a una reserva.
        
        📋 INFORMACIÓN DE TU RESERVA:
        • Cancha: {cancha_nombre}
        • Fecha: {reserva.fecha_reserva.strftime("%d/%m/%Y")}
        • Horario: {reserva.hora_inicio.strftime("%H:%M")} - {reserva.hora_fin.strftime("%H:%M")}
        • Código de Reserva: {reserva.codigo_reserva}
        
        📧 REVISA TU BANDEJA DE ENTRADA:
        • Recibirás un email separado con tu código QR personal
        • Presenta ese QR al personal de control de acceso
        • El QR es válido solo para esta reserva
        
        🚀 ACCESO INMEDIATO:
        • Puedes iniciar sesión ahora mismo: https://olympiahub.app/login
        • Tienes acceso completo al sistema
        • Puedes ver todas tus reservas en el dashboard
        
        ---
        Este es un mensaje automático.
        © {datetime.now().year} OlympiaHub
        """
        
        return send_email(
            to_email=usuario.email,
            subject=f"🎉 ¡Bienvenido a OlympiaHub - Cuenta Activada! | Reserva: {reserva.codigo_reserva}",
            message=text_content,
            html_content=html_content
        )
        
    except Exception as e:
        print(f"[EMAIL] Error enviando email de bienvenida: {str(e)}")
        return False

@router.get("/test/{codigo}")
def test_endpoint(codigo: str):
    return {"codigo_recibido": codigo}