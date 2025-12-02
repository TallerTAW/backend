from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import and_, or_, func
from datetime import datetime, date, time
from typing import List, Optional
from app.database import get_db
from app.models.reserva import Reserva
from app.models.cancha import Cancha
from app.models.usuario import Usuario
from app.models.disciplina import Disciplina
from app.models.espacio_deportivo import EspacioDeportivo
from app.models.administra import Administra
from app.schemas.reserva import ReservaResponse, ReservaCreate, ReservaUpdate
from app.core.security import get_current_user
import random
import string

router = APIRouter()

# ✅ FUNCIONES AUXILIARES 
def generar_codigo_reserva():
    """Generar código único para la reserva"""
    letras = string.ascii_uppercase
    numeros = string.digits
    codigo = ''.join(random.choices(letras, k=3)) + ''.join(random.choices(numeros, k=3))
    return codigo

def generar_codigo_unico_reserva(db: Session, max_intentos=10):
    """Generar código único con validación"""
    for intento in range(max_intentos):
        codigo = generar_codigo_reserva()
        existe = db.query(Reserva).filter(Reserva.codigo_reserva == codigo).first()
        if not existe:
            return codigo
    timestamp = int(datetime.now().timestamp())
    return f"RES{timestamp}"

# ✅ ENDPOINT PRINCIPAL - VERSIÓN SIMPLIFICADA Y FUNCIONAL
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
    """
    🎯 OBTENER RESERVAS CON FILTRADO POR ROL - VERSIÓN SIMPLIFICADA
    """
    print(f"🔍 [GET_RESERVAS] Usuario: {current_user.rol} ID: {current_user.id_usuario}")
    
    # ✅ QUERY BASE
    query = db.query(Reserva).options(
        joinedload(Reserva.usuario),
        joinedload(Reserva.cancha),
        joinedload(Reserva.disciplina)
    )
    
    # ✅ FILTRADO POR ROL - ESTO ES CRÍTICO
    if current_user.rol == 'cliente':
        print(f"🔒 [CLIENTE] Filtrando solo reservas del usuario {current_user.id_usuario}")
        query = query.filter(Reserva.id_usuario == current_user.id_usuario)
        
    elif current_user.rol == 'gestor':
        print(f"🔒 [GESTOR] Filtrando reservas de espacios gestionados")
        
        # 1. Obtener espacios que gestiona
        espacios_gestor = db.query(Administra).filter(
            Administra.id_usuario == current_user.id_usuario
        ).all()
        
        if not espacios_gestor:
            print("❌ [GESTOR] No tiene espacios asignados")
            return []
        
        espacios_ids = [espacio.id_espacio_deportivo for espacio in espacios_gestor]
        print(f"📋 [GESTOR] Espacios IDs: {espacios_ids}")
        
        # 2. Obtener canchas de esos espacios
        canchas_gestor = db.query(Cancha).filter(
            Cancha.id_espacio_deportivo.in_(espacios_ids)
        ).all()
        
        if not canchas_gestor:
            print("❌ [GESTOR] No hay canchas en sus espacios")
            return []
        
        canchas_ids = [cancha.id_cancha for cancha in canchas_gestor]
        print(f"📋 [GESTOR] Canchas IDs: {canchas_ids}")
        
        # 3. Filtrar reservas por esas canchas
        query = query.filter(Reserva.id_cancha.in_(canchas_ids))
        
    elif current_user.rol == 'admin':
        print("🔓 [ADMIN] Mostrando todas las reservas")
        # Admin ve todo, no se aplica filtro
    
    else:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Rol de usuario no válido"
        )
    
    # ✅ APLICAR FILTROS ADICIONALES
    if estado:
        query = query.filter(Reserva.estado == estado)
        print(f"🔍 Filtro estado: {estado}")
    
    if fecha_inicio:
        query = query.filter(Reserva.fecha_reserva >= fecha_inicio)
        print(f"🔍 Filtro fecha_inicio: {fecha_inicio}")
    
    if fecha_fin:
        query = query.filter(Reserva.fecha_reserva <= fecha_fin)
        print(f"🔍 Filtro fecha_fin: {fecha_fin}")
    
    if id_usuario and current_user.rol in ['admin', 'gestor']:
        query = query.filter(Reserva.id_usuario == id_usuario)
        print(f"🔍 Filtro usuario: {id_usuario}")
    
    if id_cancha:
        query = query.filter(Reserva.id_cancha == id_cancha)
        print(f"🔍 Filtro cancha: {id_cancha}")
    
    # ✅ EJECUTAR CON ORDEN
    reservas = query.order_by(
        Reserva.fecha_reserva.desc(),
        Reserva.hora_inicio.desc()
    ).offset(skip).limit(limit).all()
    
    print(f"✅ [RESULTADO] Encontradas {len(reservas)} reservas")
    
    # ✅ CONVERTIR A DICCIONARIOS
    reservas_limpias = []
    for reserva in reservas:
        reserva_data = {
            "id_reserva": reserva.id_reserva,
            "fecha_reserva": reserva.fecha_reserva,
            "hora_inicio": reserva.hora_inicio,
            "hora_fin": reserva.hora_fin,
            "cantidad_asistentes": reserva.cantidad_asistentes or 0,
            "material_prestado": reserva.material_prestado,
            "id_disciplina": reserva.id_disciplina,
            "id_cancha": reserva.id_cancha,
            "id_usuario": reserva.id_usuario,
            "codigo_reserva": reserva.codigo_reserva or f"TEMP-{reserva.id_reserva}",
            "estado": reserva.estado,
            "costo_total": float(reserva.costo_total) if reserva.costo_total else 0.0,
            "fecha_creacion": reserva.fecha_creacion,
        }
        
        # ✅ AGREGAR RELACIONES
        if reserva.usuario:
            reserva_data["usuario"] = {
                "id_usuario": reserva.usuario.id_usuario,
                "nombre": reserva.usuario.nombre,
                "apellido": reserva.usuario.apellido,
                "email": reserva.usuario.email,
                "telefono": reserva.usuario.telefono
            }
        
        if reserva.cancha:
            reserva_data["cancha"] = {
                "id_cancha": reserva.cancha.id_cancha,
                "nombre": reserva.cancha.nombre,
                "tipo": reserva.cancha.tipo,
                "precio_por_hora": float(reserva.cancha.precio_por_hora) if reserva.cancha.precio_por_hora else 0.0
            }
            
            # Cargar espacio deportivo
            espacio = db.query(EspacioDeportivo).filter(
                EspacioDeportivo.id_espacio_deportivo == reserva.cancha.id_espacio_deportivo
            ).first()
            
            if espacio:
                reserva_data["cancha"]["espacio"] = {
                    "id_espacio_deportivo": espacio.id_espacio_deportivo,
                    "nombre": espacio.nombre
                }
        
        if reserva.disciplina:
            reserva_data["disciplina"] = {
                "id_disciplina": reserva.disciplina.id_disciplina,
                "nombre": reserva.disciplina.nombre
            }
        
        reservas_limpias.append(reserva_data)
    
    return reservas_limpias

# ✅ NUEVO ENDPOINT: OBTENER FILTROS DISPONIBLES
@router.get("/filtros/disponibles")
def get_filtros_disponibles(
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user)
):
    """Obtener filtros disponibles según rol"""
    
    filtros = {
        "estados": ["pendiente", "confirmada", "en_curso", "completada", "cancelada"],
        "dias_semana": ["Lunes", "Martes", "Miércoles", "Jueves", "Viernes", "Sábado", "Domingo"]
    }
    
    if current_user.rol in ['admin', 'gestor']:
        # Agregar espacios y canchas disponibles
        if current_user.rol == 'admin':
            espacios = db.query(EspacioDeportivo).filter(
                EspacioDeportivo.estado == "activo"
            ).all()
            
            filtros["espacios"] = [
                {"id_espacio_deportivo": e.id_espacio_deportivo, "nombre": e.nombre}
                for e in espacios
            ]
            
        elif current_user.rol == 'gestor':
            espacios_ids = db.query(Administra.id_espacio_deportivo).filter(
                Administra.id_usuario == current_user.id_usuario
            ).all()
            
            if espacios_ids:
                espacios_ids = [e[0] for e in espacios_ids]
                espacios = db.query(EspacioDeportivo).filter(
                    EspacioDeportivo.id_espacio_deportivo.in_(espacios_ids),
                    EspacioDeportivo.estado == "activo"
                ).all()
                
                filtros["espacios"] = [
                    {"id_espacio_deportivo": e.id_espacio_deportivo, "nombre": e.nombre}
                    for e in espacios
                ]
    
    return filtros

# ✅ NUEVO ENDPOINT: OBTENER ESTADÍSTICAS
@router.get("/estadisticas")
def get_estadisticas_reservas(
    estado: Optional[str] = None,
    fecha_inicio: Optional[date] = None,
    fecha_fin: Optional[date] = None,
    id_cancha: Optional[int] = None,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user)
):
    """Obtener estadísticas de reservas"""
    
    # Query base según rol
    query = db.query(Reserva)
    
    if current_user.rol == 'cliente':
        query = query.filter(Reserva.id_usuario == current_user.id_usuario)
    
    elif current_user.rol == 'gestor':
        # Obtener espacios del gestor
        espacios_ids = db.query(Administra.id_espacio_deportivo).filter(
            Administra.id_usuario == current_user.id_usuario
        ).all()
        
        if espacios_ids:
            espacios_ids = [e[0] for e in espacios_ids]
            canchas_ids = db.query(Cancha.id_cancha).filter(
                Cancha.id_espacio_deportivo.in_(espacios_ids)
            ).all()
            
            if canchas_ids:
                canchas_ids = [c[0] for c in canchas_ids]
                query = query.filter(Reserva.id_cancha.in_(canchas_ids))
            else:
                return {
                    "total": 0,
                    "confirmadas": 0,
                    "pendientes": 0,
                    "en_curso": 0,
                    "completadas": 0,
                    "canceladas": 0
                }
        else:
            return {
                "total": 0,
                "confirmadas": 0,
                "pendientes": 0,
                "en_curso": 0,
                "completadas": 0,
                "canceladas": 0
            }
    
    # Aplicar filtros
    if estado:
        query = query.filter(Reserva.estado == estado)
    
    if fecha_inicio:
        query = query.filter(Reserva.fecha_reserva >= fecha_inicio)
    
    if fecha_fin:
        query = query.filter(Reserva.fecha_reserva <= fecha_fin)
    
    if id_cancha:
        query = query.filter(Reserva.id_cancha == id_cancha)
    
    # Calcular estadísticas
    total = query.count()
    confirmadas = query.filter(Reserva.estado == 'confirmada').count()
    pendientes = query.filter(Reserva.estado == 'pendiente').count()
    en_curso = query.filter(Reserva.estado == 'en_curso').count()
    completadas = query.filter(Reserva.estado == 'completada').count()
    canceladas = query.filter(Reserva.estado == 'cancelada').count()
    
    return {
        "total": total,
        "confirmadas": confirmadas,
        "pendientes": pendientes,
        "en_curso": en_curso,
        "completadas": completadas,
        "canceladas": canceladas
    }

# ✅ NUEVO ENDPOINT: OBTENER RESERVAS POR ESPACIO
@router.get("/espacio/{espacio_id}")
def get_reservas_por_espacio(
    espacio_id: int,
    estado: Optional[str] = None,
    fecha_inicio: Optional[date] = None,
    fecha_fin: Optional[date] = None,
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user)
):
    """Obtener reservas por espacio deportivo"""
    
    # Verificar permisos
    if current_user.rol == 'cliente':
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="No tienes permiso para ver reservas por espacio"
        )
    
    if current_user.rol == 'gestor':
        # Verificar que el gestor administra este espacio
        asignacion = db.query(Administra).filter(
            Administra.id_usuario == current_user.id_usuario,
            Administra.id_espacio_deportivo == espacio_id
        ).first()
        
        if not asignacion:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="No tienes permiso para ver reservas de este espacio"
            )
    
    # Obtener canchas del espacio
    canchas = db.query(Cancha).filter(
        Cancha.id_espacio_deportivo == espacio_id
    ).all()
    
    if not canchas:
        return []
    
    canchas_ids = [cancha.id_cancha for cancha in canchas]
    
    # Query de reservas
    query = db.query(Reserva).options(
        joinedload(Reserva.usuario),
        joinedload(Reserva.cancha),
        joinedload(Reserva.disciplina)
    ).filter(
        Reserva.id_cancha.in_(canchas_ids)
    )
    
    # Aplicar filtros
    if estado:
        query = query.filter(Reserva.estado == estado)
    
    if fecha_inicio:
        query = query.filter(Reserva.fecha_reserva >= fecha_inicio)
    
    if fecha_fin:
        query = query.filter(Reserva.fecha_reserva <= fecha_fin)
    
    # Ejecutar query
    reservas = query.order_by(
        Reserva.fecha_reserva.desc(),
        Reserva.hora_inicio.desc()
    ).offset(skip).limit(limit).all()
    
    # Convertir a respuesta
    reservas_limpias = []
    for reserva in reservas:
        reserva_data = {
            "id_reserva": reserva.id_reserva,
            "fecha_reserva": reserva.fecha_reserva,
            "hora_inicio": reserva.hora_inicio,
            "hora_fin": reserva.hora_fin,
            "cantidad_asistentes": reserva.cantidad_asistentes or 0,
            "material_prestado": reserva.material_prestado,
            "id_disciplina": reserva.id_disciplina,
            "id_cancha": reserva.id_cancha,
            "id_usuario": reserva.id_usuario,
            "codigo_reserva": reserva.codigo_reserva or f"TEMP-{reserva.id_reserva}",
            "estado": reserva.estado,
            "costo_total": float(reserva.costo_total) if reserva.costo_total else 0.0,
            "fecha_creacion": reserva.fecha_creacion,
        }
        
        if reserva.usuario:
            reserva_data["usuario"] = {
                "id_usuario": reserva.usuario.id_usuario,
                "nombre": reserva.usuario.nombre,
                "apellido": reserva.usuario.apellido,
                "email": reserva.usuario.email,
                "telefono": reserva.usuario.telefono
            }
        
        if reserva.cancha:
            reserva_data["cancha"] = {
                "id_cancha": reserva.cancha.id_cancha,
                "nombre": reserva.cancha.nombre,
                "tipo": reserva.cancha.tipo,
                "precio_por_hora": float(reserva.cancha.precio_por_hora) if reserva.cancha.precio_por_hora else 0.0
            }
        
        if reserva.disciplina:
            reserva_data["disciplina"] = {
                "id_disciplina": reserva.disciplina.id_disciplina,
                "nombre": reserva.disciplina.nombre
            }
        
        reservas_limpias.append(reserva_data)
    
    return reservas_limpias

# ✅ ENDPOINT INDIVIDUAL
@router.get("/{reserva_id}", response_model=ReservaResponse)
def get_reserva(reserva_id: int, db: Session = Depends(get_db), current_user: Usuario = Depends(get_current_user)):
    """Obtener una reserva específica por ID"""
    reserva = db.query(Reserva).options(
        joinedload(Reserva.usuario),
        joinedload(Reserva.cancha),
        joinedload(Reserva.disciplina)
    ).filter(Reserva.id_reserva == reserva_id).first()
    
    if not reserva:
        raise HTTPException(status_code=404, detail="Reserva no encontrada")
    
    # ✅ VERIFICAR PERMISOS
    if current_user.rol == 'cliente' and reserva.id_usuario != current_user.id_usuario:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="No tienes permiso para ver esta reserva"
        )
    
    if current_user.rol == 'gestor':
        # Verificar si la cancha pertenece a un espacio que gestiona
        cancha = db.query(Cancha).filter(Cancha.id_cancha == reserva.id_cancha).first()
        if cancha:
            administra = db.query(Administra).filter(
                Administra.id_usuario == current_user.id_usuario,
                Administra.id_espacio_deportivo == cancha.id_espacio_deportivo
            ).first()
            
            if not administra:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="No tienes permiso para ver esta reserva"
                )
    
    # ✅ CONVERTIR A RESPUESTA
    reserva_data = {
        "id_reserva": reserva.id_reserva,
        "fecha_reserva": reserva.fecha_reserva,
        "hora_inicio": reserva.hora_inicio,
        "hora_fin": reserva.hora_fin,
        "cantidad_asistentes": reserva.cantidad_asistentes or 0,
        "material_prestado": reserva.material_prestado,
        "id_disciplina": reserva.id_disciplina,
        "id_cancha": reserva.id_cancha,
        "id_usuario": reserva.id_usuario,
        "codigo_reserva": reserva.codigo_reserva or f"TEMP-{reserva.id_reserva}",
        "estado": reserva.estado,
        "costo_total": float(reserva.costo_total) if reserva.costo_total else 0.0,
        "fecha_creacion": reserva.fecha_creacion,
    }
    
    if reserva.usuario:
        reserva_data["usuario"] = {
            "id_usuario": reserva.usuario.id_usuario,
            "nombre": reserva.usuario.nombre,
            "apellido": reserva.usuario.apellido,
            "email": reserva.usuario.email,
            "telefono": reserva.usuario.telefono
        }
    
    if reserva.cancha:
        reserva_data["cancha"] = {
            "id_cancha": reserva.cancha.id_cancha,
            "nombre": reserva.cancha.nombre,
            "tipo": reserva.cancha.tipo,
            "precio_por_hora": float(reserva.cancha.precio_por_hora) if reserva.cancha.precio_por_hora else 0.0
        }
    
    if reserva.disciplina:
        reserva_data["disciplina"] = {
            "id_disciplina": reserva.disciplina.id_disciplina,
            "nombre": reserva.disciplina.nombre
        }
    
    return reserva_data

# ✅ CREAR RESERVA (mantener tu código existente)
@router.post("/", response_model=ReservaResponse)
def create_reserva(reserva_data: ReservaCreate, db: Session = Depends(get_db)):
    """Crear nueva reserva"""
    print(f"🎯 [BACKEND] Iniciando creación de reserva: {reserva_data.dict()}")
    
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
    
    # CALCULAR COSTO TOTAL (simplificado)
    hora_inicio = reserva_data.hora_inicio
    hora_fin = reserva_data.hora_fin
    precio_hora = float(cancha.precio_por_hora) if cancha.precio_por_hora else 0.0
    
    duracion_horas = (
        (hora_fin.hour * 60 + hora_fin.minute) - 
        (hora_inicio.hour * 60 + hora_inicio.minute)
    ) / 60.0
    
    costo_total = round(duracion_horas * precio_hora, 2)
    
    # GENERAR CÓDIGO DE RESERVA
    codigo_reserva = generar_codigo_unico_reserva(db)
    
    # CREAR RESERVA
    reserva_dict = reserva_data.dict()
    codigo_cupon = reserva_dict.pop('codigo_cupon', None)
    
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
        
        # Cargar relaciones
        nueva_reserva = db.query(Reserva).options(
            joinedload(Reserva.usuario),
            joinedload(Reserva.cancha),
            joinedload(Reserva.disciplina)
        ).filter(Reserva.id_reserva == nueva_reserva.id_reserva).first()
        
        # Convertir a respuesta
        reserva_response = {
            "id_reserva": nueva_reserva.id_reserva,
            "fecha_reserva": nueva_reserva.fecha_reserva,
            "hora_inicio": nueva_reserva.hora_inicio,
            "hora_fin": nueva_reserva.hora_fin,
            "cantidad_asistentes": nueva_reserva.cantidad_asistentes or 0,
            "material_prestado": nueva_reserva.material_prestado,
            "id_disciplina": nueva_reserva.id_disciplina,
            "id_cancha": nueva_reserva.id_cancha,
            "id_usuario": nueva_reserva.id_usuario,
            "codigo_reserva": nueva_reserva.codigo_reserva,
            "estado": nueva_reserva.estado,
            "costo_total": float(nueva_reserva.costo_total) if nueva_reserva.costo_total else 0.0,
            "fecha_creacion": nueva_reserva.fecha_creacion,
        }
        
        if nueva_reserva.usuario:
            reserva_response["usuario"] = {
                "id_usuario": nueva_reserva.usuario.id_usuario,
                "nombre": nueva_reserva.usuario.nombre,
                "apellido": nueva_reserva.usuario.apellido,
                "email": nueva_reserva.usuario.email,
                "telefono": nueva_reserva.usuario.telefono
            }
        
        if nueva_reserva.cancha:
            reserva_response["cancha"] = {
                "id_cancha": nueva_reserva.cancha.id_cancha,
                "nombre": nueva_reserva.cancha.nombre,
                "tipo": nueva_reserva.cancha.tipo,
                "precio_por_hora": float(nueva_reserva.cancha.precio_por_hora) if nueva_reserva.cancha.precio_por_hora else 0.0
            }
        
        if nueva_reserva.disciplina:
            reserva_response["disciplina"] = {
                "id_disciplina": nueva_reserva.disciplina.id_disciplina,
                "nombre": nueva_reserva.disciplina.nombre
            }
        
        return reserva_response
        
    except Exception as e:
        db.rollback()
        print(f"❌ Error al crear reserva: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Error al crear reserva: {str(e)}"
        )

# ✅ ACTUALIZAR RESERVA
@router.patch("/{reserva_id}", response_model=ReservaResponse)
def update_reserva(reserva_id: int, reserva_data: ReservaUpdate, db: Session = Depends(get_db), current_user: Usuario = Depends(get_current_user)):
    """Actualizar reserva"""
    reserva = db.query(Reserva).filter(Reserva.id_reserva == reserva_id).first()
    if not reserva:
        raise HTTPException(status_code=404, detail="Reserva no encontrada")
    
    # ✅ VERIFICAR PERMISOS
    if current_user.rol == 'cliente' and reserva.id_usuario != current_user.id_usuario:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="No tienes permiso para modificar esta reserva"
        )
    
    # Actualizar campos permitidos
    campos_permitidos = ['estado', 'material_prestado', 'cantidad_asistentes']
    for campo, valor in reserva_data.dict(exclude_unset=True).items():
        if campo in campos_permitidos and valor is not None:
            setattr(reserva, campo, valor)

    try:
        db.commit()
        db.refresh(reserva)
        
        # Cargar relaciones
        reserva = db.query(Reserva).options(
            joinedload(Reserva.usuario),
            joinedload(Reserva.cancha),
            joinedload(Reserva.disciplina)
        ).filter(Reserva.id_reserva == reserva.id_reserva).first()
        
        # Convertir a respuesta
        reserva_response = {
            "id_reserva": reserva.id_reserva,
            "fecha_reserva": reserva.fecha_reserva,
            "hora_inicio": reserva.hora_inicio,
            "hora_fin": reserva.hora_fin,
            "cantidad_asistentes": reserva.cantidad_asistentes or 0,
            "material_prestado": reserva.material_prestado,
            "id_disciplina": reserva.id_disciplina,
            "id_cancha": reserva.id_cancha,
            "id_usuario": reserva.id_usuario,
            "codigo_reserva": reserva.codigo_reserva or f"TEMP-{reserva.id_reserva}",
            "estado": reserva.estado,
            "costo_total": float(reserva.costo_total) if reserva.costo_total else 0.0,
            "fecha_creacion": reserva.fecha_creacion,
        }
        
        if reserva.usuario:
            reserva_response["usuario"] = {
                "id_usuario": reserva.usuario.id_usuario,
                "nombre": reserva.usuario.nombre,
                "apellido": reserva.usuario.apellido,
                "email": reserva.usuario.email,
                "telefono": reserva.usuario.telefono
            }
        
        if reserva.cancha:
            reserva_response["cancha"] = {
                "id_cancha": reserva.cancha.id_cancha,
                "nombre": reserva.cancha.nombre,
                "tipo": reserva.cancha.tipo,
                "precio_por_hora": float(reserva.cancha.precio_por_hora) if reserva.cancha.precio_por_hora else 0.0
            }
        
        if reserva.disciplina:
            reserva_response["disciplina"] = {
                "id_disciplina": reserva.disciplina.id_disciplina,
                "nombre": reserva.disciplina.nombre
            }
        
        return reserva_response
        
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=500,
            detail=f"Error al actualizar reserva: {str(e)}"
        )

# ✅ CANCELAR RESERVA
@router.delete("/{reserva_id}")
def cancelar_reserva(reserva_id: int, motivo: str = None, db: Session = Depends(get_db), current_user: Usuario = Depends(get_current_user)):
    """Cancelar reserva"""
    reserva = db.query(Reserva).filter(Reserva.id_reserva == reserva_id).first()
    if not reserva:
        raise HTTPException(status_code=404, detail="Reserva no encontrada")
    
    # ✅ VERIFICAR PERMISOS
    if current_user.rol == 'cliente' and reserva.id_usuario != current_user.id_usuario:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="No tienes permiso para cancelar esta reserva"
        )
    
    if reserva.estado == 'cancelada':
        raise HTTPException(status_code=400, detail="La reserva ya está cancelada")
    
    reserva.estado = 'cancelada'
    
    try:
        db.commit()
        return {
            "detail": "Reserva cancelada exitosamente", 
            "motivo": motivo,
            "reserva_id": reserva_id
        }
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=500,
            detail=f"Error al cancelar reserva: {str(e)}"
        )

# ✅ ENDPOINT SIMPLE PARA ESTADÍSTICAS (opcional)
@router.get("/resumen/estadisticas")
def get_resumen_estadisticas(
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user)
):
    """Obtener resumen de estadísticas"""
    
    # Query base según rol
    query = db.query(Reserva)
    
    if current_user.rol == 'cliente':
        query = query.filter(Reserva.id_usuario == current_user.id_usuario)
    
    elif current_user.rol == 'gestor':
        # Obtener espacios del gestor
        espacios_ids = db.query(Administra.id_espacio_deportivo).filter(
            Administra.id_usuario == current_user.id_usuario
        ).all()
        
        if espacios_ids:
            espacios_ids = [e[0] for e in espacios_ids]
            canchas_ids = db.query(Cancha.id_cancha).filter(
                Cancha.id_espacio_deportivo.in_(espacios_ids)
            ).all()
            
            if canchas_ids:
                canchas_ids = [c[0] for c in canchas_ids]
                query = query.filter(Reserva.id_cancha.in_(canchas_ids))
            else:
                return {"total": 0, "por_estado": {}}
        else:
            return {"total": 0, "por_estado": {}}
    
    # Calcular total
    total = query.count()
    
    # Por estado
    por_estado = {}
    estados = ['pendiente', 'confirmada', 'en_curso', 'completada', 'cancelada']
    
    for estado in estados:
        count = query.filter(Reserva.estado == estado).count()
        por_estado[estado] = count
    
    return {
        "total": total,
        "por_estado": por_estado
    }